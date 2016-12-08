# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
import colorfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('master', '0002_auto_20160930_2033'),
    ]

    operations = [
        migrations.AddField(
            model_name='administrativeward',
            name='background_color',
            field=colorfield.fields.ColorField(default=b'#BFFFD0', max_length=10, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='administrativeward',
            name='border_color',
            field=colorfield.fields.ColorField(default=b'#BFFFD0', max_length=10, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='city',
            name='background_color',
            field=colorfield.fields.ColorField(default=b'#94BBFF', max_length=10, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='city',
            name='border_color',
            field=colorfield.fields.ColorField(default=b'#94BBFF', max_length=10, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='electoralward',
            name='background_color',
            field=colorfield.fields.ColorField(default=b'#FFEFA1', max_length=10, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='electoralward',
            name='border_color',
            field=colorfield.fields.ColorField(default=b'#FFEFA1', max_length=10, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='city',
            name='created_on',
            field=models.DateTimeField(default=datetime.datetime(2016, 10, 5, 18, 42, 43, 863286)),
        ),
        migrations.AlterField(
            model_name='plottedshape',
            name='created_on',
            field=models.DateTimeField(default=datetime.datetime(2016, 10, 5, 18, 42, 43, 871388)),
        ),
        migrations.AlterField(
            model_name='projectmaster',
            name='created_date',
            field=models.DateTimeField(default=datetime.datetime(2016, 10, 5, 18, 42, 43, 874112)),
        ),
    ]
