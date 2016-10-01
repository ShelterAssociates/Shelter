# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('master', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='slum',
            name='factsheet',
            field=models.FileField(null=True, upload_to=b'factsheet/', blank=True),
        ),
        migrations.AddField(
            model_name='slum',
            name='photo',
            field=models.ImageField(null=True, upload_to=b'factsheet/', blank=True),
        ),
        migrations.AddField(
            model_name='wardofficecontact',
            name='address_info',
            field=models.CharField(max_length=2048, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='city',
            name='created_on',
            field=models.DateTimeField(default=datetime.datetime(2016, 9, 30, 20, 33, 47, 8803)),
        ),
        migrations.AlterField(
            model_name='plottedshape',
            name='created_on',
            field=models.DateTimeField(default=datetime.datetime(2016, 9, 30, 20, 33, 47, 16234)),
        ),
        migrations.AlterField(
            model_name='projectmaster',
            name='created_date',
            field=models.DateTimeField(default=datetime.datetime(2016, 9, 30, 20, 33, 47, 18954)),
        ),
    ]
