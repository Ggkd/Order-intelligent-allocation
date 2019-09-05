from django.shortcuts import render, HttpResponse, redirect
from django.http import JsonResponse
from django.views.generic import View
from .models import *
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
from django.conf import settings
from django.core.mail import send_mail
from django.contrib import auth
from geetest import GeetestLib
import re
import random
from utils.mixin import LoginRequiredMixin
from django.core.urlresolvers import reverse
from apps.goods.models import *
from django_redis import get_redis_connection
from apps.order.models import *
from django.core.paginator import Paginator
from celery_tasks.tasks import send_register_active_email

# Create your views here.


class Register(View):
    """注册"""
    def get(self, request):
        return render(request, 'register.html')

    def post(self, request):
        # 获取数据
        username = request.POST.get('user_name')
        pwd = request.POST.get('pwd')
        cpwd = request.POST.get('cpwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')
        # 校验数据
        if not all([username, pwd, cpwd, email]):
            return JsonResponse({"status": 0, "errmsg": "请完善所有数据"})
        # 验证用户名是否存在
        user_name = User.objects.filter(username=username)
        if user_name:
            return JsonResponse({"status": 1, "errmsg": "用户名已存在"})
        # 校验用户名的长度
        if len(username) < 5 or len(username) > 20:
            return JsonResponse({"status": 2, "errmsg": "请输入5-20个字符的用户名"})
        # 验证密码长度
        if len(pwd) < 6 or len(pwd) > 17:
            return JsonResponse({"status": 3, "errmsg": "密码最少6位，最长16位"})
        # 验证密码是否一致
        if pwd != cpwd:
            return JsonResponse({"status": 4, "errmsg": "两次输入的密码不一致"})
        # 验证邮箱格式
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return JsonResponse({"status": 5, "errmsg": "邮箱格式不正确"})
        # 验证协议
        if allow != 'true':
            return JsonResponse({"status": 6, "errmsg": "请同意用户协议"})

        # 注册用户
        user = User.objects.create_user(username, email, pwd)
        user.is_active = 0
        user.save()

        # 发送激活码到用户邮箱 http:127.0.0.1:8080/user/active/id
        # 加密
        info = {"user_id": user.id}
        serializer = Serializer(settings.SECRET_KEY, 3600)
        token = serializer.dumps(info).decode()
        send_register_active_email.delay(email, username, token)
        # subject = '新百顺激活信息'
        # message = ''
        # sender = settings.EMAIL_FROM
        # receiver = [email]
        # html_message = '<h1>%s,欢迎加入新百顺</h1><br/>请点击下面的链接激活账户<a href="http:127.0.0.1:8080/user/active/%s">http:127.0.0.1:8080/user/active/%s</a>' % (
        # username, token, token)
        # send_mail(subject, message, sender, receiver, html_message=html_message)
        return JsonResponse({"status": 7, "msg": '/index'})


def active(request, token):
    """邮箱激活"""
    serializer = Serializer(settings.SECRET_KEY, 3600)
    try:
        info = serializer.loads(token)
        user_id = info["user_id"]
        user = User.objects.get(id=user_id)
        user.is_active = 1
        user.save()
        return redirect('/login')
    except SignatureExpired as e:
        return HttpResponse("验证连接已失效")


class Login(View):
    """登录"""
    def get(self, request):
        username = request.COOKIES.get("username", '')
        checked = ''
        if username:
            checked = 'checked'
        return render(request, 'login.html', {"username": username, "checked": checked})

    def post(self, request):
        username = request.POST.get("username")
        password = request.POST.get("password")
        remember = request.POST.get("remember")
        if not all([username, password]):
            return JsonResponse({"status": 4, "errmsg": "请完善所有数据"})

        # 获取极验 滑动验证码相关的参数
        gt = GeetestLib(pc_geetest_id, pc_geetest_key)
        challenge = request.POST.get(gt.FN_CHALLENGE, '')
        validate = request.POST.get(gt.FN_VALIDATE, '')
        seccode = request.POST.get(gt.FN_SECCODE, '')
        status = request.session[gt.GT_STATUS_SESSION_KEY]
        user_id = request.session["user_id"]

        if status:
            result = gt.success_validate(challenge, validate, seccode, user_id)
        else:
            result = gt.failback_validate(challenge, validate, seccode)
        if result:
            # 验证码正确
            user_active = User.objects.filter(username=username).values("is_active")    # 判断激活
            user = auth.authenticate(username=username, password=password)
            if user_active:
                if user_active[0]["is_active"]:
                    if user:
                        auth.login(request, user)
                        # 下一次跳转的页面，和未登录时将要跳转的页面
                        next_url = request.GET.get('next', '/index')
                        # response = redirect(next_url)
                        if remember == 'true':
                            user_cookie = username
                            user_name = ""
                            # response.set_cookie("username", username, max_age=7*24*3600)
                        else:
                            # response.delete_cookie('username')
                            user_cookie = ''
                            user_name = username
                        return JsonResponse({"status": 0, "msg": next_url, "user_cookie": user_cookie, "user_name": user_name})
                    else:
                        return JsonResponse({"status": 3, "errmsg": "用户名或密码不正确"})
                else:
                    return JsonResponse({"status": 2, "errmsg": "用户未激活，请到邮箱激活！"})
            else:
                return JsonResponse({"status": 3, "errmsg": "用户名或密码不正确"})
        else:
            return JsonResponse({"status": 1, "errmsg": "验证码错误"})


# 请在官网申请ID使用，示例ID不可使用
pc_geetest_id = "b46d1900d0a894591916ea94ea91bd2c"
pc_geetest_key = "36fc3fe98530eea08dfc6ce76e3d24c4"
# pc_geetest_id = "48a6ebac4ebc6642d68c217fca33eb4d"
# pc_geetest_key = "4f1c085290bec5afdc54df73535fc361"


# 处理极验 获取验证码的视图
def get_geetest(request):
    user_id = 'test'
    gt = GeetestLib(pc_geetest_id, pc_geetest_key)
    status = gt.pre_process(user_id)
    request.session[gt.GT_STATUS_SESSION_KEY] = status
    request.session["user_id"] = user_id
    response_str = gt.get_response_str()
    return HttpResponse(response_str)


class Forget(View):
    """忘记密码"""
    def get(self, request):
        return render(request, 'forget.html')

    def post(self, request):
        email = request.POST.get("send_email")
        user = User.objects.get(email=email)
        username = user.username
        # 设置验证码
        checkcode = ''
        for i in range(4):
            current = random.randrange(0, 4)  # 生成随机数与循环次数比对
            current1 = random.randrange(0, 4)
            if current == i:
                tmp = chr(random.randint(65, 90))  # 65~90为ASCii码表A~Z
            elif current1 == i:
                tmp = chr(random.randint(97, 122))  # 97~122为ASCii码表a~z
            else:
                tmp = random.randint(0, 9)
            checkcode += str(tmp)
        # 发送激活码到用户邮箱
        subject = '新百顺重置密码'
        message = ''
        sender = settings.EMAIL_FROM
        receiver = [email]
        html_message = '<h1>欢迎%s,</h1><br/><h5>您的验证码为<h3>%s</h3></h5>' % (username, checkcode)
        send_mail(subject, message, sender, receiver, html_message=html_message)
        return JsonResponse({"checkcode": checkcode, "username": username})


def update_pass(request):
    """修改密码"""
    if request.method == 'POST':
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = User.objects.get(username=username)
        user.set_password(password)
        user.save()
        return JsonResponse({"status": "ok"})
    return JsonResponse({"status": "ko"})


def logout(request):
    """注销"""
    auth.logout(request)
    return redirect("/login")


class Info(LoginRequiredMixin, View):
    """用户信息"""
    def get(self, request):
        user = request.user
        address = Address.objects.get_default_address(user=user)
        # 连接redis
        con = get_redis_connection('default')
        # 用户浏览历史， 使用列表存储
        history_key = "history_%d" % user.id
        sku_id = con.lrange(history_key, 0, 4)  # 取前五个
        sku_list = list()
        for id in sku_id:
            sku_obj = GoodsSKU.objects.get(id=id)
            sku_list.append(sku_obj)
        return render(request, 'user_center_info.html', {"user": user,
                                                         "address": address,
                                                         "sku_list": sku_list})


class Site(LoginRequiredMixin, View):
    """用户收货地址"""
    def get(self, request):
        user = request.user
        addr_default = Address.objects.get_default_address(user=user)
        user_addr_list = Address.objects.filter(user=user)
        province_addr = Area.objects.filter(aparent__isnull=True)
        addr_num = len(user_addr_list)
        return render(request, 'user_center_site.html', {"user_addr_list": user_addr_list,
                                                         "addr_default": addr_default,
                                                         "addr_num": addr_num,
                                                         "user": user,
                                                         "province_addr": province_addr
                                                         })

    def post(self, request):
        user = request.user
        receiver = request.POST.get("receiver")
        prov_id = request.POST.get("prov_id")
        city_id = request.POST.get("city_id")
        count_id = request.POST.get("count_id")
        detail = request.POST.get("detail")
        code = request.POST.get("code")
        phone = request.POST.get("phone")
        is_default = request.POST.get("default")
        # 先验证是否设置默认
        if is_default == "true":
            # 其他地址设为非默认
            is_default = 1
            address_list = Address.objects.all()
            for address in address_list:
                address.is_default = 0
                address.save()
        else:
            if(len(Address.objects.filter(user=user,is_default=1))==0):
                is_default = 1
            else:
                is_default = 0
        # 插入数据
        prov_addr = Area.objects.get(id=prov_id)
        city_addr = Area.objects.get(id=city_id)
        if count_id == "----请选择----":
            count_addr = ''
        else:
            count_addr = Area.objects.get(id=count_id)

        Address.objects.create(user=user,
                               receiver=receiver,
                               addr_province=prov_addr,
                               addr_city=city_addr,
                               addr_country=count_addr,
                               addr_detail=detail,
                               zip_code=code,
                               phone=phone,
                               is_default=is_default)
        return JsonResponse({"status": 1})


def site_edit(request):
    """编辑收货地址"""
    if request.method == "POST":
        addr_id = request.POST.get("addr_id")
        addr_obj = Address.objects.get(id=addr_id)
        prov_id = Area.objects.filter(atitle=addr_obj.addr_province, aparent__isnull=True)
        prov_id = prov_id[0].id
        # 拼接城市option
        city_option_str = ''
        citys = Area.objects.filter(aparent_id=prov_id)     # 获取该省份的所有城市
        city_id = Area.objects.filter(atitle=addr_obj.addr_city, aparent__isnull=False)[0].id    # 获取该城市的id
        if len(citys) == 1:
            citys = Area.objects.filter(aparent_id=citys[0].id)
        for city in citys:
            if city.id == city_id:
                city_option_str += "<option value=%s selected>%s</option>" % (city.id, city.atitle)
            else:
                city_option_str += "<option value=%s>%s</option>" % (city.id, city.atitle)

        # 获取该城市的所有县
        # 拼接城市option
        count_option_str = ''
        if addr_obj.addr_country:
            count_id = Area.objects.get(atitle=addr_obj.addr_country).id
            counts = Area.objects.filter(aparent_id=city_id)
            for count in counts:
                if count.id == count_id:
                    count_option_str += "<option value=%s selected>%s</option>" % (count.id, count.atitle)
                else:
                    count_option_str += "<option value=%s>%s</option>" % (count.id, count.atitle)

        return JsonResponse({"receiver": addr_obj.receiver,
                             "prov_id": prov_id,
                             "city_option_str": city_option_str,
                             "count_option_str": count_option_str,
                             "detail_addr": addr_obj.addr_detail,
                             "zip_code": addr_obj.zip_code,
                             "phone": addr_obj.phone,
                             "is_default": addr_obj.is_default
                             })


def site_delete(request):
    """删除地址"""
    addr_id = request.POST.get("addr_id")
    Address.objects.get(id=addr_id).delete()
    return JsonResponse({"status": "ok"})


def set_default(request):
    """设为默认"""
    addr_id = request.POST.get("addr_id")
    print(addr_id)
    address_list = Address.objects.all()
    for address in address_list:
        if address.id == int(addr_id):
            address.is_default = 1
        else:
            address.is_default = 0
        address.save()
    return JsonResponse({"status": "ok"})


class Order(LoginRequiredMixin, View):
    """用户订单"""
    def get(self, request, page):
        user = request.user
        # 获取用户的所有订单
        orders = OrderInfo.objects.filter(user=user).order_by("-create_time")
        for order in orders:
            # 获取每个订单中的所有商品信息
            order_skus = OrderGoods.objects.filter(order_id=order.order_id)
            for order_sku in order_skus:
                # 计算小计
                amount = order_sku.count * order_sku.price
                # 判断该物品的库存情况
                order_sku_stocks = GoodsSkuWareHouse.objects.filter(sku_id=order_sku.sku.id)
                if order_sku_stocks:
                    for sku_stock in order_sku_stocks:
                        if order_sku.count <= sku_stock.stock:
                            stocks = ""
                        else:
                            stocks = "该商品库存不足"
                else:
                    stocks = "该商品暂时无货"
                # 动态给对象添加属性
                order_sku.amount = amount
                order_sku.stocks = stocks
            status = order.order_status
            if status == 1:
                status = "待支付"
            elif status == 5:
                status = "已完成"
            else:
                status = "待收货"
            order.status = status
            order.order_skus = order_skus

        # 分页
        paginator = Paginator(orders, 2)
        # 获取第page页的数据
        try:
            page = int(page)
        except Exception as e:
            page = 1
        if page < 1:
            page = 1
        if page > paginator.num_pages:
            page = paginator.num_pages

        # 进行页码的控制
        # 1.总页数小于5，显示所有页码
        # 2.当前页是前三页，显示1-5页
        # 3.当前页是后3页， 显示后5页
        # 4.其他情况，显示当前页的前2页，当前页的后2页
        page_list = list()
        if paginator.num_pages < 5:
            page_list = range(1, paginator.num_pages+1)
        elif page <= 3:
            page_list = range(1, 6)
        elif paginator.num_pages - page < 3:
            page_list = range(paginator.num_pages-4, paginator.num_pages+1)
        else:
            page_list = range(page-2, page+3)

        # 获取第page页的page对象
        order_page = paginator.page(page)
        return render(request, 'user_center_order.html', {"page_list": page_list, "order_page": order_page})


class Logistic(LoginRequiredMixin, View):
    """订单物流"""
    def get(self, request, order_id):
        user = request.user
        try:
            order = OrderInfo.objects.get(order_id=order_id)
            order_sku = OrderGoods.objects.filter(order=order)[0].sku   # 取第一商品的对象
        except Exception as e:
            return redirect(reverse('user:order'))

        return render(request, 'user_order_logistic.html', {"order_id": order_id,
                                                            "order_sku": order_sku})


def get_city(request, city_id):
    """城市选择"""
    citys = Area.objects.filter(aparent_id=city_id)
    if len(citys) == 1:
        citys = Area.objects.filter(aparent_id=citys[0].id)
    area_list = list()
    for area in citys:
        area_list.append((area.id, area.atitle))
    return JsonResponse(area_list, safe=False)


def ware_distance(warehouse_id):
    """仓库的垂直距离"""
    warehouse = Warehouse.objects.get(id=warehouse_id)
    # 根据地址计算gps距离
    gps_x = AreaGps.objects.get(area__atitle=warehouse.addr).gps_x
    gps_y = AreaGps.objects.get(area__atitle=warehouse.addr).gps_y
    # 计算垂直距离
    return (gps_x + gps_y) / 2


def user_addr_distance(order_id):
    """用户收货地址的垂直距离"""
    user_addr = OrderInfo.objects.get(order_id=order_id).addr
    gps_x = AreaGps.objects.get(area__atitle=user_addr.addr_province).gps_x
    gps_y = AreaGps.objects.get(area__atitle=user_addr.addr_province).gps_y
    user_gps_location = (gps_x + gps_y) / 2
    return user_gps_location


def get_ware(ware_id):
    """获取仓库的名称"""
    ware_name = Warehouse.objects.get(id=ware_id).name
    return ware_name


def get_good(good_id):
    """获取商品的名称"""
    good_name = GoodsSKU.objects.get(id=good_id).name
    return good_name


def logistic(request):
    # 库存足够的仓库字典
    short_warehouse = dict()  # 格式{"sku_id": [warehouse_id,]}
    order_id = request.GET.get("order_id")
    print(request.GET.get("order_id"))
    html_str = ""  # 前台结构
    order_skus = OrderGoods.objects.filter(order_id=order_id)  # 获取该订单的所有商品
    print(order_skus)
    html_str += '<li role="presentation" ><a role="tab" data-toggle="tab"></a><P>获取该订单的所有商品</P></li>'
    for order_sku in order_skus:
        # print(order_sku.sku_id)
        order_sku_stocks = GoodsSkuWareHouse.objects.filter(sku_id=order_sku.sku_id)  # 判断商品的库存
        if order_sku_stocks:
            # 判断所有仓库是否存有该商品
            # print(order_sku.sku_id, order_sku_stocks)
            good_name = get_good(order_sku.sku_id)
            html_str += '<li role="presentation" ><a role="tab" data-toggle="tab"></a><P>判断所有仓库是否存有%s商品</P></li>' % good_name
            for sku_stock in order_sku_stocks:
                # 如果有仓库存有该商品，查看该仓库存该商品的库存和仓库
                # print(order_sku.sku_id, sku_stock.warehouse_id, sku_stock.stock)
                # 判断仓库中该商品库存大于购买的数量的仓库
                html_str += '<li role="presentation"><a role="tab" data-toggle="tab"></a><p>如果有仓库存有该商品，查看该仓库存该商品的库存和仓库，判断仓库中该商品库存大于购买的数量的仓库</p></li>'
                if order_sku.count <= sku_stock.stock:
                    html_str += '<li role="presentation"><a role="tab" data-toggle="tab"></a><p>库存足够的情况：获取仓库的地址并获取仓库垂直距离</p></li>'
                    # 库存足够的情况
                    # 获取仓库的地址
                    # 获取仓库垂直距离
                    ware_name = get_ware(sku_stock.warehouse_id)
                    gps_location = ware_distance(sku_stock.warehouse_id)
                    html_str += '<li role="presentation" class="active"><a role="tab" data-toggle="tab"></a><p style="color:red">正在计算%s的地址和垂直距离，垂直距离为%f</p></li>' % (ware_name, gps_location)
                    # 获取用户的收获地址
                    user_addr = OrderInfo.objects.get(order_id=order_id).addr
                    address = user_addr.addr_province + user_addr.addr_city + user_addr.addr_country + user_addr.addr_detail
                    # 获取收货地址的垂直距离
                    user_gps_location = user_addr_distance(order_id)
                    html_str += '<li role="presentation" class="active"><a role="tab" data-toggle="tab"></a><p style="color:red">获取用户的收获地址:%s；计算垂直距离：%f</p></li>' % (address, user_gps_location)
                    # 计算最短距离
                    shortcut = abs(gps_location - user_gps_location)
                    html_str += '<li role="presentation"><a role="tab" data-toggle="tab"></a><p>计算与%s垂直距离：%f</p></li>' % (ware_name, shortcut)
                    # 先判断最短路径下商品和仓库是否存在
                    html_str += '<li role="presentation"><a role="tab" data-toggle="tab"></a><p>先判断最短路径下商品和仓库是否存在，如果存在就排序。与字典中存在的商品对应仓库比较，距离小就修改，否则不修改；循环列表中的每个仓库</p></li>'
                    if order_sku.sku_id in short_warehouse.keys():
                        # 如果存在就排序。与字典中存在的商品对应仓库比较，距离小就修改，否则不修改
                        # 循环列表中的每个仓库
                        for index, pre_warehouse_id in enumerate(short_warehouse[order_sku.sku_id]):
                            pre_warehouse = ware_distance(int(pre_warehouse_id))
                            # 计算列表中存在的最短距离
                            pre_shortcut = abs(pre_warehouse - user_gps_location)
                            pre_ware_name = get_ware(int(pre_warehouse_id))
                            html_str += '<li role="presentation"><a role="tab" data-toggle="tab"></a><p>正在比较%s与%s那个仓库距离收货地址最近</p></li>' % (ware_name, pre_ware_name)
                            if shortcut < pre_shortcut:
                                short_warehouse[order_sku.sku_id][index] = sku_stock.warehouse_id
                                html_str += '<li role="presentation" class="active"><a role="tab" data-toggle="tab"></a><p style="color:red">比较结果：%s距离收货地址最近</p></li>' % ware_name
                            # elif shortcut == pre_shortcut:
                            #     short_warehouse[order_sku.sku_id].append(sku_stock.warehouse_id)
                            else:
                                html_str += '<li role="presentation" class="active"><a role="tab" data-toggle="tab"></a><p style="color:red">比较结果：%s距离收货地址最近</p></li>' % pre_ware_name
                    else:
                        # 不存在就直接添加
                        short_warehouse[order_sku.sku_id] = [sku_stock.warehouse_id]
                else:
                    good_name = get_good(order_sku.sku_id)
                    ware_name = get_ware(sku_stock.warehouse_id)
                    html_str += '<li role="presentation" class="active"><a role="tab" data-toggle="tab"></a><p style="color:red">%s仓库中：%s商品库存不足</p></li>' % (ware_name, good_name)
                    print("%d仓库中：%d商品库存不足" % (order_sku.sku_id, sku_stock.warehouse_id))
        else:
            good_name = get_good(order_sku.sku_id)
            html_str += '<li role="presentation" class="active"><a role="tab" data-toggle="tab"></a><p style="color:red">%s商品所有仓库库存不足</p></li>' % good_name
            print("%d商品库存不足" % order_sku.sku_id)

    print(short_warehouse)
    # 判断所有商品都在那个仓库， 有几个商品在一个仓库;  3种情况：
    # 1.所有商品都在一个同一个仓库
    # 2.个别商品在同一个商品
    # 3.所有商品分别在一个仓库
    # 格式{"sku_id": [warehouse_id,],"sku_id": [warehouse_id,],"sku_id": [warehouse_id,]}
    html_str += '<li role="presentation" class="active"><a role="tab" data-toggle="tab"></a><p style="color:red">判断所有商品都在那个仓库，有几个商品在一个仓库，3种情况：1.所有商品都在一个同一个仓库；2.个别商品在同一个商品；3.所有商品分别在一个仓库</p></li>'

    sku_id_list = list()    # 将所有商品id记录在一起，格式["sku_id","sku_id","sku_id"]
    for sku_id in short_warehouse.keys():
        sku_id_list.append(sku_id)

    new_short_warehouse = dict()    # 新的商品_仓库字典
    pre_same_ware = set()   # 前一个相同集合
    same_ware = True    # 是否所有在一个仓库的flag
    for index, sku_id in enumerate(sku_id_list):
        cur_sku_id = sku_id     # 记录当前的sku_id
        for next_sku_id in sku_id_list[index+1: len(sku_id_list)]:
            # 从当前的下一个sku_id到最后一个，逐个判断是否有相同仓库
            cur_good_name = get_good(cur_sku_id)
            next_good_name = get_good(next_sku_id)
            html_str += '<li role="presentation"><a role="tab" data-toggle="tab"></a><p>正在判断%s商品和%s商品是否有相同仓库</p></li>' % (cur_good_name, next_good_name)
            cur_same_ware = set(short_warehouse[cur_sku_id]) & set(short_warehouse[next_sku_id])
            if cur_same_ware:
                for ware_id in cur_same_ware:
                    ware_name = get_ware(ware_id)
                    html_str += '<li role="presentation" class="active"><a role="tab" data-toggle="tab"></a><p style="color:red">%s商品和%s商品有相同仓库:%s</p></li>' % (cur_good_name, next_good_name, ware_name)
                    if cur_sku_id in new_short_warehouse.keys():
                        new_short_warehouse[cur_sku_id].append(ware_id)
                    else:
                        new_short_warehouse[cur_sku_id] = [ware_id]
                    if next_sku_id in new_short_warehouse.keys():
                        new_short_warehouse[next_sku_id].append(ware_id)
                    else:
                        new_short_warehouse[next_sku_id] = [ware_id]
                # 求当前cur_same_ware与pre_same_ware的交集，
                if not pre_same_ware:  # 初始值为空，先将其设为第一个cur_same_ware
                    pre_same_ware = cur_same_ware
                all_same_ware = (pre_same_ware & cur_same_ware)
                if all_same_ware:
                    pre_same_ware = all_same_ware
                    print(pre_same_ware)
                else:
                    same_ware = False
                    # 获取集合中的仓库，以及对应的sku_id
                print(cur_sku_id, next_sku_id, cur_same_ware)
            else:
                same_ware = False

    print(new_short_warehouse)

    html_str += '<li role="presentation"><a role="tab" data-toggle="tab"></a><p>最后决定商品分配的情况</p></li>'

    if new_short_warehouse:
        if same_ware is False:
            print("部分商品不在同一个仓库")
            html_str += '<li role="presentation" class="active"><a role="tab" data-toggle="tab"></a><p style="color:red">部分商品不在同一个仓库</p></li>'
            # 获取商品在同一个仓库的仓库id，以及对应的sku_id
            for ware_id in pre_same_ware:
                for sku_id, ware_id_list in new_short_warehouse.items():
                    if ware_id in ware_id_list:
                        # print("%d将从 %d仓库配送" % (sku_id, ware_id))
                        good_name = get_good(sku_id)
                        ware_name = get_ware(ware_id)
                        html_str += '<li role="presentation" class="active"><a role="tab" data-toggle="tab"></a><p style="color:red">%s将从 %s配送</p></li>' % (good_name, ware_name)
            # 找到库存的所有商品id列表
            new_sku_id_list = list()
            for sku_id in new_short_warehouse:
                new_sku_id_list.append(sku_id)
            # 找出原来列表比现在列表中多的商品及仓库
            no_same_ware_sku = (set(sku_id_list) - set(new_sku_id_list))    # type 集合
            for sku_id in no_same_ware_sku:
                # print("%d 将从 %d仓库配送" % (sku_id, short_warehouse[sku_id][0]))
                good_name = get_good(sku_id)
                ware_name = get_ware(short_warehouse[sku_id][0])
                html_str += '<li role="presentation" class="active"><a role="tab" data-toggle="tab"></a><p style="color:red">%s将从 %s配送</p></li>' % (good_name, ware_name)
        else:
            # 全部商品在同一个仓库
            html_str += '<li role="presentation" class="active"><a role="tab" data-toggle="tab"></a><p style="color:red">全部商品在一个仓库</p></li>'
            print("全部商品在一个仓库")
            for ware_id in pre_same_ware:
                for sku_id, ware_id_list in new_short_warehouse.items():
                    if ware_id in ware_id_list:
                        # print("%d将从 %d仓库配送" % (sku_id, ware_id))
                        good_name = get_good(sku_id)
                        ware_name = get_ware(ware_id)
                        html_str += '<li role="presentation" class="active"><a role="tab" data-toggle="tab"></a><p style="color:red">%s将从 %s配送</p></li>' % (good_name, ware_name)
    else:
        html_str += '<li role="presentation" class="active"><a role="tab" data-toggle="tab"></a><p style="color:red">所有商品不在同一个仓库</p></li>'
        print("所有商品不在同一个仓库")
        new_sku_id_list = list()
        for sku_id in new_short_warehouse:
            new_sku_id_list.append(sku_id)
        # 找出原来列表比现在列表中多的商品及仓库
        no_same_ware_sku = (set(sku_id_list) - set(new_sku_id_list))  # type 集合
        for sku_id in no_same_ware_sku:
            # print("%d 将从 %d仓库配送" % (sku_id, short_warehouse[sku_id][0]))
            good_name = get_good(sku_id)
            ware_name = get_ware(short_warehouse[sku_id][0])
            html_str += '<li role="presentation" class="active"><a role="tab" data-toggle="tab"></a><p style="color:red">%s将从 %s配送</p></li>' % (good_name, ware_name)

    return JsonResponse({"html_str": html_str})