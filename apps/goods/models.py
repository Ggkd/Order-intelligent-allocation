from django.db import models
from db.base_model import BaseModel
from tinymce.models import HTMLField
# Create your models here.


class GoodsType(BaseModel):
    """商品类型模型类"""
    name = models.CharField(max_length=20, verbose_name='种类名称')
    # logo = models.CharField(max_length=20, verbose_name='标识')
    image = models.ImageField(upload_to='type', verbose_name='商品类型图片')

    class Meta:
        db_table = 'goods_type'
        verbose_name = '商品种类'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class GoodsSKU(BaseModel):
    """商品SKU模型类"""
    status_choices = (
        (0, '下线'),
        (1, '上线'),
    )
    type = models.ForeignKey('GoodsType', verbose_name='商品种类')
    goods = models.ForeignKey('Goods', verbose_name='商品SPU')
    name = models.CharField(max_length=20, verbose_name='商品名称')
    desc = models.CharField(max_length=256, verbose_name='商品简介')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='商品价格')
    unite = models.CharField(max_length=20, verbose_name='商品单位')
    image = models.ImageField(upload_to='goods', verbose_name='商品图片')
    sales = models.IntegerField(default=0, verbose_name='商品销量')
    status = models.SmallIntegerField(default=1, choices=status_choices, verbose_name='商品状态')

    class Meta:
        db_table = 'goods_sku'
        verbose_name = '商品SKU'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class Warehouse(models.Model):
    name = models.CharField(max_length=20, verbose_name='仓库名称')
    addr = models.CharField(max_length=20, verbose_name='仓库地址')

    class Meta:
        db_table = 'goods_warehouse'
        verbose_name = '仓库'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class GoodsSkuWareHouse(models.Model):
    warehouse = models.ForeignKey(to='Warehouse', verbose_name='仓库')
    sku = models.ForeignKey(to='GoodsSKU', verbose_name='库存商品')
    stock = models.IntegerField(default=0, verbose_name='商品库存', null=True)

    class Meta:
        db_table = 'goods_ware'
        verbose_name = '商品库存'
        verbose_name_plural = verbose_name


class Area(models.Model):
    atitle = models.CharField(max_length=24, verbose_name="地区")
    aparent = models.ForeignKey(to='self', null=True)

    class Meta:
        db_table = 'area'
        verbose_name = '地区'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.atitle


class AreaGps(models.Model):
    area = models.OneToOneField(to='Area')
    gps_x = models.IntegerField(null=True, verbose_name='地理位置X轴')
    gps_y = models.IntegerField(null=True, verbose_name='地理位置Y轴')

    class Meta:
        db_table = 'area_gps'
        verbose_name = '地区坐标'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.area.atitle


class Goods(BaseModel):
    """商品SPU模型类"""
    name = models.CharField(max_length=20, verbose_name='商品SPU名称')
    # 富文本类型:带有格式的文本
    detail = HTMLField(blank=True, verbose_name='商品详情')

    class Meta:
        db_table = 'goods'
        verbose_name = '商品SPU'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class GoodsImage(BaseModel):
    """商品图片模型类"""
    sku = models.ForeignKey('GoodsSKU', verbose_name='商品')
    image = models.ImageField(upload_to='goods', verbose_name='图片路径')

    class Meta:
        db_table = 'goods_image'
        verbose_name = '商品图片'
        verbose_name_plural = verbose_name


class IndexGoodsBanner(BaseModel):
    """首页轮播商品展示模型类"""
    sku = models.ForeignKey('GoodsSKU', verbose_name='商品')
    image = models.ImageField(upload_to='banner', verbose_name='图片')
    index = models.SmallIntegerField(default=0, verbose_name='展示顺序')

    class Meta:
        db_table = 'index_banner'
        verbose_name = '首页轮播商品'
        verbose_name_plural = verbose_name


class IndexTypeGoodsBanner(BaseModel):
    """首页分类商品展示模型类"""
    DISPLAY_TYPE_CHOICES = (
        (0, "标题"),
        (1, "图片")
    )

    type = models.ForeignKey('GoodsType', verbose_name='商品类型')
    sku = models.ForeignKey('GoodsSKU', verbose_name='商品SKU')
    display_type = models.SmallIntegerField(default=1, choices=DISPLAY_TYPE_CHOICES, verbose_name='展示类型')
    index = models.SmallIntegerField(default=0, verbose_name='展示顺序')

    class Meta:
        db_table = 'index_type_goods'
        verbose_name = "主页分类展示商品"
        verbose_name_plural = verbose_name


class IndexPromotionBanner(BaseModel):
    """首页促销活动模型类"""
    name = models.CharField(max_length=20, verbose_name='活动名称')
    url = models.CharField(max_length=256, verbose_name='活动链接')
    image = models.ImageField(upload_to='banner', verbose_name='活动图片')
    index = models.SmallIntegerField(default=0, verbose_name='展示顺序')

    class Meta:
        db_table = 'index_promotion'
        verbose_name = "主页促销活动"
        verbose_name_plural = verbose_name