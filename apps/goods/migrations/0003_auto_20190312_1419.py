# -*- coding: utf-8 -*-
# Generated by Django 1.11.11 on 2019-03-12 06:19
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('goods', '0002_goodsgps'),
    ]

    operations = [
        migrations.AlterField(
            model_name='goodsgps',
            name='gps',
            field=models.IntegerField(default=0, verbose_name='地理位置'),
        ),
    ]
