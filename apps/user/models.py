from django.db import models
from django.contrib.auth.models import AbstractUser
from db.base_model import BaseModel
# Create your models here.


class User(AbstractUser, BaseModel):
    '''用户模型类'''

    class Meta:
        db_table = 'user'
        verbose_name = '用户'
        verbose_name_plural = verbose_name


class AddressManager(models.Manager):
    # 改变原有查询的结果集
    # 封装方法; 用户操作模型类对应的数据表
    def get_default_address(self, user):
        '''获取用户的默认收货地址'''
        # self.model: 获取self对象所在的模型类
        try:
            addr = self.get(user=user, is_default=True)
        except Exception as e:
            addr = None
        return addr


class Address(BaseModel):
    '''地址模型类'''
    user = models.ForeignKey('User', verbose_name='所属账户')
    receiver = models.CharField(max_length=20, verbose_name='收件人')
    addr_province = models.CharField(max_length=20, verbose_name='收货地址（省）')
    addr_city = models.CharField(max_length=20, verbose_name='收货地址（市）', null=True)
    addr_country = models.CharField(max_length=20, verbose_name='收货地址（县）', null=True)
    addr_detail = models.CharField(max_length=256, verbose_name='详细收件地址')
    zip_code = models.CharField(max_length=6, null=True, verbose_name='邮政编码')
    phone = models.CharField(max_length=11, verbose_name='联系电话')
    is_default = models.BooleanField(default=False, verbose_name='是否默认')

    objects = AddressManager()
    class Meta:
        db_table = 'address'
        verbose_name = '地址'
        verbose_name_plural = verbose_name
