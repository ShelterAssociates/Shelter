# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('graphs', '0011_auto_20191009_1123'),
    ]

    operations = [
        migrations.AddField(
            model_name='dashboarddata',
            name='occupied_household_count',
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='dashboarddata',
            name='total_road_area',
            field=models.FloatField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='dashboarddata',
            name='fun_fmale_seats',
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='dashboarddata',
            name='fun_male_seats',
            field=models.IntegerField(null=True, blank=True),
        ),
    ]
