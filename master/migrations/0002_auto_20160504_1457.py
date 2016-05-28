# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('master', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='city',
            name='created_on',
            field=models.DateTimeField(default=datetime.datetime(2016, 5, 4, 14, 57, 10, 193845)),
        ),
        migrations.AlterField(
            model_name='plottedshape',
            name='created_on',
            field=models.DateTimeField(default=datetime.datetime(2016, 5, 4, 14, 57, 10, 202533)),
        ),
        migrations.AlterField(
            model_name='projectmaster',
            name='created_date',
            field=models.DateTimeField(default=datetime.datetime(2016, 5, 4, 14, 57, 10, 205523)),
        ),
    ]
