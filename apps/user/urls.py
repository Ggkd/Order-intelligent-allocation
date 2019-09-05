from django.conf.urls import url
from .views import active, Info, Site, Order, site_edit, site_delete, set_default, Logistic, logistic


urlpatterns = [
    url(r'^active/(?P<token>.*)$', active, name='active'),  #激活邮箱连接
    url(r'^info$', Info.as_view(), name='info'),  # 用户信息
    url(r'^site$', Site.as_view(), name='site'),  # 用户地址
    url(r'^site/edit$', site_edit),  # 编辑用户地址
    url(r'^site/delete$', site_delete),  # 删除用户地址
    url(r'^site/set_default', set_default),  # 用户地址设为默认
    url(r'^order/(?P<page>\d+)$', Order.as_view(), name='order'),  # 用户订单
    url(r'^logistic/(?P<order_id>\d+)$', Logistic.as_view(), name='logistic'),  # 订单物流
    url(r'^logistic$', logistic),
]
