"""finished URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.contrib import admin
from apps.user.views import Register, Login, Forget
from apps.user.views import logout, get_geetest, update_pass,get_city
from apps.goods.views import Index


urlpatterns = [
    url(r'^admin/', admin.site.urls),   # 管理后台
    url(r'^tinymce/', include('tinymce.urls')),   # 富文本编辑器
    url(r'^search/', include('haystack.urls')),   # 搜索引擎
    url(r'^register$', Register.as_view(), name='register'),    # 注册
    url(r'^login$', Login.as_view(), name='login'),  # 登录
    url(r'^forget$', Forget.as_view(), name='forget'),   # 忘记密码
    url(r'^update_pass$', update_pass, name='update_pass'),   # 修改密码
    url(r'^logout$', logout, name='logout'),    # 注销
    url(r'^user/', include('apps.user.urls', namespace='user')),
    url(r'^cart/', include('apps.cart.urls', namespace='cart')),
    url(r'^goods/', include('apps.goods.urls', namespace='goods')),
    url(r'^order/', include('apps.order.urls', namespace='order')),
    url(r'^index$', Index.as_view(), name='index'),     # 首页
    url(r'^get_city(?P<city_id>\d+)$', get_city, name='get_city'),     # 获取城市
    # 极验滑动验证码 获取验证码的url
    url(r'^pc-geetest/register', get_geetest),
]
