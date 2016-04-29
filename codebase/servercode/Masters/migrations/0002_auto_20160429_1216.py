# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('Masters', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='city',
            name='created_on',
            field=models.DateTimeField(default=datetime.datetime(2016, 4, 29, 12, 16, 2, 159015)),
        ),
        migrations.AlterField(
            model_name='plottedshape',
            name='created_on',
            field=models.DateTimeField(default=datetime.datetime(2016, 4, 29, 12, 16, 2, 170237)),
        ),
        migrations.AlterField(
            model_name='projectmaster',
            name='created_date',
            field=models.DateTimeField(default=datetime.datetime(2016, 4, 29, 12, 16, 2, 173845)),
        ),
    ]
