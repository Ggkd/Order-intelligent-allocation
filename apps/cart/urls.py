from django.conf.urls import url
from .views import CartAdd, CartList, CartUpdate, CartDelete

urlpatterns = [
    url(r'^add$', CartAdd.as_view(), name='add'),   # 添加购物车
    url(r'^list$', CartList.as_view(), name='list'),   # 购物车页面
    url(r'^update$', CartUpdate.as_view(), name='update'),   # 购物车更新
    url(r'^delete$', CartDelete.as_view(), name='delete'),   # 购物车删除
]