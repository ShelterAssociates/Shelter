# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('sponsor', '0002_auto_20171027_1637'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sponsor',
            name='intro_date',
            field=models.DateTimeField(default=datetime.datetime(2017, 10, 30, 13, 2, 29, 964892)),
        ),
        migrations.AlterField(
            model_name='sponsorproject',
            name='created_on',
            field=models.DateTimeField(default=datetime.datetime(2017, 10, 30, 13, 2, 29, 966716)),
        ),
        migrations.AlterField(
            model_name='sponsorprojectmou',
            name='release_date',
            field=models.DateTimeField(default=datetime.datetime(2017, 10, 30, 13, 2, 29, 969524)),
        ),
    ]
