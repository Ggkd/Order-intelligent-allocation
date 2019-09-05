from django.shortcuts import render, redirect
from django.views.generic import View
from .models import *
from django_redis import get_redis_connection
from django.core.paginator import Paginator
from django.core.urlresolvers import reverse
from apps.order.models import *
from django.http import JsonResponse

# Create your views here.


class Index(View):
    """商品首页"""
    def get(self, request):
        user = request.user
        # 获取商品类型及商品
        types = GoodsType.objects.all()
        for type in types:
            title_skus = GoodsSKU.objects.filter(type=type)[7:10]
            image_skus = GoodsSKU.objects.filter(type=type)[:4]
            type.title_skus = title_skus
            type.image_skus = image_skus

        # 获取购物车商品数量
        cart_count = 0
        if user.is_authenticated():
            conn = get_redis_connection('default')
            cart_key = "cart_%d" % user.id
            cart_count = conn.hlen(cart_key)
        return render(request, 'index.html', {"user": user,
                                              "types": types,
                                              "cart_count": cart_count})


class List(View):
    """商品列表页"""
    sale_flag = True    # 第二次点击改变排序的标志
    price_flag = True

    def get(self, request, type_id, page):
        user = request.user
        # 获取分类
        types = GoodsType.objects.all()
        # 获取当前分类
        current_type = GoodsType.objects.get(id=type_id)
        # 获取当前分类下的所有商品
        skus = GoodsSKU.objects.filter(type=current_type)
        # 根据sort排序
        sort = request.GET.get("sort", "default")
        if sort == 'sales':
            # 根据销量排序
            if List.sale_flag:
                skus = skus.order_by('-sales')
                List.sale_flag = False
            else:
                skus = skus.order_by('sales')
                List.sale_flag = True
        elif sort == "price":
            # 根据价格排序
            if List.price_flag:
                skus = skus.order_by('price')
                List.price_flag = False
            else:
                skus = skus.order_by('-price')
                List.price_flag = True
        else:
            # 默认排序
            sort = 'default'
            skus = skus.order_by('id')

        # 分页
        paginator = Paginator(skus, 15)     # 创建分页对象
        # 异常处理
        try:
            page = int(page)
        except Exception as e:
            page = 1
        if page > paginator.num_pages:
            page = paginator.num_pages
        if page < 1:
            page = 1
        # 进行页码的控制
        # 1.总页数小于5，显示所有页码
        # 2.当前页是前三页，显示1-5页
        # 3.当前页是后3页， 显示后5页
        # 4.其他情况，显示当前页的前2页，当前页的后2页
        if paginator.num_pages < 5:
            page_list = range(1, paginator.num_pages+1)
        elif page <= 3:
            page_list = range(1, 6)
        elif paginator.num_pages - page <= 2:
            page_list = range(paginator.num_pages-4, paginator.num_pages+1)
        else:
            page_list = range(page-2, page+3)

        # 获取第page页的Page对象
        sku_page = paginator.page(page)
        # 获取新品
        new_skus = GoodsSKU.objects.filter(type=current_type).order_by('-create_time')[:2]
        # 获取用户购物车商品数量
        con = get_redis_connection('default')
        cart_count = 0
        if user.is_authenticated():
            cart_key = "cart_%d" % user.id
            cart_count = con.hlen(cart_key)
        return render(request, 'list.html', {"user": user,
                                             "types": types,
                                             "current_type": current_type,
                                             "cart_count": cart_count,
                                             "new_skus": new_skus,
                                             "page_list": page_list,
                                             "sku_page": sku_page,
                                             "sort": sort})


class Detail(View):
    """商品详情页"""
    def get(self, request, good_id):
        user = request.user
        types = GoodsType.objects.all()
        # 获取商品详情
        try:
            sku = GoodsSKU.objects.get(id=good_id)
        except Exception as e:
            return redirect('/index')
        # 获取同一个spu的其他商品
        same_sku = GoodsSKU.objects.filter(goods=sku.goods).exclude(id=good_id)
        # 获取新品
        new_sku = GoodsSKU.objects.filter(type=sku.type).order_by('-create_time')[:2]
        # 获取评论
        sku_comment = OrderGoods.objects.filter(sku=sku).exclude(comment='')
        # 获取用户购物车的商品数量
        conn = get_redis_connection('default')
        cart_count = 0
        if user.is_authenticated():
            cart_key = "cart_%d" % user.id
            cart_count = conn.hlen(cart_key)
            # 添加用户的浏览记录
            history_key = "history_%d" % user.id
            # 先移除该商品的所有记录
            conn.lrem(history_key, 0, good_id)
            # 把商品添加到列表的左侧
            conn.lpush(history_key, good_id)
            conn.ltrim(history_key, 0, 4)
        # 判断该物品的库存情况
        order_sku_stocks = GoodsSkuWareHouse.objects.filter(sku_id=good_id)
        if order_sku_stocks:
            stock = ""
        else:
            stock = "该商品暂时无货"
        return render(request, 'detail.html', {"user": user,
                                               "types": types,
                                               "sku": sku,
                                               "cart_count": cart_count,
                                               "same_sku": same_sku,
                                               "new_sku": new_sku,
                                               "sku_comment": sku_comment,
                                               "stock": stock})


class Search(View):
    def get(self, request):
        user = request.user
        # 获取所有类型
        types = GoodsType.objects.all()
        listr = ''
        for type in types:
            listr += '<li><a href = "/goods/list/%d/1" >%s</a></li>' % (type.id, type.name)

        # 获取购物车商品数量
        cart_count = 0
        if user.is_authenticated():
            conn = get_redis_connection('default')
            cart_key = "cart_%d" % user.id
            cart_count = conn.hlen(cart_key)
        return JsonResponse({"listr": listr, "cart_count": cart_count})