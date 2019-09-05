from django.conf.urls import url
from .views import *

urlpatterns = [
    url(r'^place$', OrderPlace.as_view(), name='place'),  # 提交订单页面
    url(r'^commit$', OrderCommit.as_view(), name='commit'),  # 提交订单
    url(r'^pay$', OrderPay.as_view(), name='pay'),  # 订单支付
    url(r'^check$', OrderCheck.as_view(), name='check'),  # 订单支付
    url(r'^cancel$', OrderCancel.as_view(), name='cancel'),  # 取消订单
]
