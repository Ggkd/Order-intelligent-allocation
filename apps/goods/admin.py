from django.contrib import admin
from .models import *
# Register your models here.

admin.site.register(GoodsSKU)
admin.site.register(GoodsType)
admin.site.register(Goods)
admin.site.register(GoodsImage)
admin.site.register(Warehouse)
admin.site.register(GoodsSkuWareHouse)
admin.site.register(Area)
admin.site.register(AreaGps)