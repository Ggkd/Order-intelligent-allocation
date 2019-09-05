from django.conf.urls import url
from .views import List, Detail, Search

urlpatterns = [
    url(r'^list/(?P<type_id>\d+)/(?P<page>\d+)$', List.as_view(), name='list'),    # 商品列表页
    url(r'^detail/(?P<good_id>\d+)$', Detail.as_view(), name='detail'),    # 商品详情页
    url(r'^search$', Search.as_view(), name='search'),    # 搜索页数据
]
