from django.shortcuts import render
from django.views.generic import View
from django.http import JsonResponse
from apps.goods.models import *
from django_redis import get_redis_connection
from utils.mixin import LoginRequiredMixin
# Create your views here.


class CartAdd(View):
    """添加商品到购物车"""
    def post(self, request):
        user = request.user
        # 判断用户是否登录
        if not user.is_authenticated():
            return JsonResponse({"status": 0, "errmsg": "请登录！"})
        sku_id = request.POST.get("sku_id")
        count = request.POST.get("count")
        # 校验商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except Exception as e:
            return JsonResponse({"status": 1, "errmsg": "添加的商品不存在"})
        # 校验添加的商品数量格式
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({"status": 2, "errmsg": "数据格式不正确"})
        # 存储添加记录
        conn = get_redis_connection('default')
        cart_key = "cart_%d" % user.id
        # 校验sku_id是否已经存在
        cart_count = conn.hget(cart_key, sku_id)
        if cart_count:
            count += int(cart_count)
        conn.hset(cart_key, sku_id, count)
        total_count = conn.hlen(cart_key)
        return JsonResponse({"status": 3, "total_count": total_count})


class CartList(LoginRequiredMixin, View):
    """购物车清单"""
    def get(self, request):
        # 获取用户购物车清单
        user = request.user
        conn = get_redis_connection('default')
        cart_key = "cart_%d" % user.id
        cart_dict = conn.hgetall(cart_key)
        skus_list = list()  # 购物车列表
        total_count = 0
        total_amount = 0
        for sku_id, sku_count in cart_dict.items():
            sku = GoodsSKU.objects.get(id=sku_id)
            price = sku.price
            count = int(sku_count)
            amount = price * count  # 小计
            sku.count = count
            sku.amount = amount
            total_count += count
            total_amount += amount
            skus_list.append(sku)
        return render(request, 'cart.html', {"skus_list": skus_list,
                                             "total_count": total_count,
                                             "total_amount": total_amount})


class CartUpdate(View):
    """购物车更新商品"""
    def post(self, request):
        user =request.user
        sku_id = request.POST.get("sku_id")
        count = request.POST.get("count")
        if not user.is_authenticated():
            return JsonResponse({"status": 0, "errmsg": "请登录"})
        if not all([sku_id, count]):
            return JsonResponse({"status": 1, "errmsg": "数据不完整"})
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except Exception as e:
            return JsonResponse({"status": 2, "errmsg": "商品不存在"})
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse(({"status": 3, "errmsg": "数据格式不正确"}))
        # 业务处理
        conn = get_redis_connection('default')
        cart_key = "cart_%d" % user.id
        # 更新sku_id的值
        conn.hset(cart_key, sku_id, count)
        # 计算更新后商品的总数目
        total_count = 0
        values = conn.hvals(cart_key)
        for i in values:
            total_count += int(i)
        return JsonResponse({"status": 4, "total_count": total_count})


class CartDelete(View):
    """购物车删除商品"""
    def post(self, request):
        user = request.user
        sku_id = request.POST.get("sku_id")
        if not user.is_authenticated():
            return JsonResponse({"status": 1, "errmsg": "请登录"})
        if not sku_id:
            return JsonResponse({"status": 2, "errmsg": "数据不完整"})
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except Exception as e:
            return JsonResponse({"status": 3, "errmsg": "商品不存在"})
        # 从购物车中删除该商品
        conn = get_redis_connection('default')
        cart_key = "cart_%d" % user.id
        conn.hdel(cart_key, sku_id)
        # 重新计算商品的数量
        values = conn.hvals(cart_key)
        total_count = 0
        for i in values:
            total_count += int(i)
        return JsonResponse({"status": 4, "total_count": total_count})