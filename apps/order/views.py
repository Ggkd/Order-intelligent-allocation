from django.shortcuts import render, redirect
from django.views.generic import View
from django.http import JsonResponse
from django.core.urlresolvers import reverse
from django_redis import get_redis_connection
from apps.goods.models import *
from apps.user.models import *
from datetime import datetime
from django.db import transaction
from alipay import AliPay
from django.conf import settings
import os
from .models import *
import time

# Create your views here.


class OrderPlace(View):
    """提交订单跳转"""
    def post(self, request):
        user = request.user
        sku_list = request.POST.getlist("sku_ids")
        if not sku_list:
            return redirect(reverse('cart:list'))
        # 获取商品和数目，计算总价格
        skus = list()
        conn = get_redis_connection('default')
        total_amount = 0
        total_count = 0
        cart_key = "cart_%d" % user.id
        for sku_id in sku_list:
            sku_count = conn.hget(cart_key, sku_id)
            sku = GoodsSKU.objects.get(id=sku_id)
            # 计算小计
            amount = sku.price * int(sku_count)
            sku.count = sku_count
            sku.amount = amount
            total_count += int(sku_count)
            total_amount += amount
            skus.append(sku)
        # 运费
        transit_price = 20
        if total_amount > 50:
            transit_price = 0
        # 需总支付的金额
        total_pay = total_amount + transit_price
        address_list = Address.objects.filter(user=user)
        address_default = Address.objects.get_default_address(user=user)
        sku_ids = ','.join(sku_list)
        return render(request, 'place_order.html', {"skus": skus,
                                                    "total_count": total_count,
                                                    "total_amount": total_amount,
                                                    "total_pay": total_pay,
                                                    "transit_price": transit_price,
                                                    "address_list": address_list,
                                                    "address_default": address_default,
                                                    "sku_ids": sku_ids})


class OrderCommit(View):
    """创建订单"""
    @transaction.atomic    # 开启事务
    def post(self, request):
        user = request.user
        addr_id = request.POST.get("addr_id")
        pay_id = request.POST.get("pay_id")
        sku_ids = request.POST.get("sku_ids")
        transit_price = request.POST.get("transit_price")
        flag = request.POST.get("flag")
        if not user.is_authenticated():
            return JsonResponse({"status": 0, "errmsg": "请登录"})
        if not all([addr_id, pay_id, sku_ids]):
            return JsonResponse({"status": 1, "errmsg": "数据不完整"})
        # 验证地址
        try:
            address = Address.objects.get(id=addr_id)
        except Exception as e:
            return JsonResponse({"status": 2, "errmsg": "地址不存在"})
        # 创建订单；订单id格式：日期+用户id
        order_id = datetime.now().strftime("%Y%m%d%H%M%S")+str(user.id)
        # 订单商品总数目和总金额（先设为0，订单创建成功后再更新）
        total_count = 0
        total_amount = 0
        # 设置事务保存点
        save_id = transaction.savepoint()
        # 数据库操作放在事务里

        try:
            # 向order_info插入一条记录
            order = OrderInfo.objects.create(order_id=order_id,
                                             user=user,
                                             addr=address,
                                             pay_method=pay_id,
                                             total_count=total_count,
                                             total_price=total_amount,
                                             transit_price=transit_price,
                                             )

            # 用户订单中有几种商品就向order_good中添加几条记录
            conn = get_redis_connection('default')
            cart_key = "cart_%d" % user.id
            sku_ids = sku_ids.split(",")
            for sku_id in sku_ids:
                try:
                    sku = GoodsSKU.objects.select_for_update().get(id=sku_id)  # 悲观锁
                except Exception as e:
                    # 商品不存在，事务回滚
                    transaction.savepoint_rollback(save_id)
                    return JsonResponse({"status": 4, "errmsg": "商品不存在"})
                # 从redis获取商品数据
                sku_count = conn.hget(cart_key, sku_id)
                sku_price = sku.price

                # 向order_good插图一条记录
                OrderGoods.objects.create(order_id=order_id,
                                          sku=sku,
                                          count=int(sku_count),
                                          price=sku_price
                                          )
                # 累加计算订单的商品总数目和金额
                sku_amount = sku_price * int(sku_count)     # 商品小计
                total_count += int(sku_count)
                total_amount += sku_amount
            # 加上运费
            total_amount += int(transit_price)
            # 修改order_info表的总数量和金额
            order.total_count = total_count
            order.total_price = total_amount
            order.save()
        except Exception as e:
            # 创建失败，事务回滚
            transaction.savepoint_rollback(save_id)
            return JsonResponse({"status": 3, "errmsg": "下单失败"})

        # 清除购物车记录
        conn.hdel(cart_key, *sku_ids)
        if flag == '1':
            time.sleep(2)
        return JsonResponse({"status": 5, "order_id": order_id})


class OrderPay(View):
    """订单支付"""
    def post(self, request):
        user = request.user
        order_id = request.POST.get("order_id")
        if not user.is_authenticated():
            return JsonResponse({"status": 0, "errmsg": "请登录"})
        if not order_id:
            return JsonResponse({"status": 1, "errmsg": "订单不存在"})
        try:
            # 验证订单
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=user,
                                          pay_method=3,
                                          order_status=1)
            print(order)
        except Exception as e:
            return JsonResponse({"status": 2, "errmsg": "无效的订单"})

        # 使用python sdk调用支付宝的支付接口
        # 初始化
        alipay = AliPay(
            appid="2016092700610367",
            app_notify_url=None,  # 默认回调url
            app_private_key_path=os.path.join(settings.BASE_DIR, "apps/order/app_private_key.pem"),
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_path=os.path.join(settings.BASE_DIR, "apps/order/alipay_public_key.pem"),
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=True  # 默认False
        )
        # 调用支付接口
        # 电脑网站支付，需要跳转到https://openapi.alipaydev.com/gateway.do? + order_string
        total_pay = order.total_price
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,
            total_amount=str(total_pay),
            subject="新百顺%s" % order_id,
            return_url=None,
            notify_url=None  # 可选, 不填则使用默认notify url
        )
        # 反应应答
        pay_url = "https://openapi.alipaydev.com/gateway.do?" + order_string
        return JsonResponse({"status": 3, "pay_url": pay_url})


class OrderCheck(View):
    """支付校验"""
    def post(self, request):
        user = request.user
        order_id = request.POST.get("order_id")
        if not user.is_authenticated():
            return JsonResponse({"status": 0, "errmsg": "请登录"})
        if not order_id:
            return JsonResponse({"status": 1, "errmsg": "订单不存在"})
        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=user,
                                          pay_method=3,
                                          order_status=1)
        except Exception as e:
            return JsonResponse({"status": 2, "errmsg": "无效的订单"})

        # 使用python sdk调用支付宝的支付接口
        # 初始化
        alipay = AliPay(
            appid="2016092700610367",
            app_notify_url=None,  # 默认回调url
            app_private_key_path=os.path.join(settings.BASE_DIR, "apps/order/app_private_key.pem"),
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_path=os.path.join(settings.BASE_DIR, "apps/order/alipay_public_key.pem"),
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=True  # 默认False
        )
        # 调用支付宝的交易查询接口
        while True:
            response = alipay.api_alipay_trade_query(order_id)
            code = response.get('code')
            if code == '10000' and response['trade_status'] == 'TRADE_SUCCESS':
                order.trade_no = response.get('trade_no')
                order.order_status = 3
                order.save()
                return JsonResponse({'status': 3, 'msg': '支付成功'})
            elif code == '40004' or (code == '10000' and response['trade_status'] == 'WAIT_BUYER_PAY'):
                # 等待支付
                continue
            else:
                return JsonResponse({'status': 4, 'errmsg': '支付失败'})


class OrderCancel(View):
    """订单取消"""
    def post(self, request):
        user = request.user
        order_id = request.POST.get("order_id")
        if not user.is_authenticated():
            return JsonResponse({"status": 0, "errmsg": "请登录"})
        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=user,
                                          )
        except Exception as e:
            return JsonResponse({"status": 1, "errmsg": "无效的订单"})
        order.order_status = 5
        order.save()
        return JsonResponse({"status": 2})