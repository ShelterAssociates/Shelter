# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
import django.contrib.gis.db.models.fields
import master.models


class Migration(migrations.Migration):

    dependencies = [
        ('master', '0006_auto_20170419_1836'),
    ]

    operations = [
        migrations.AddField(
            model_name='slum',
            name='associated_with_SA',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='city',
            name='created_on',
            field=models.DateTimeField(default=datetime.datetime.now),
        ),
        migrations.AlterField(
            model_name='plottedshape',
            name='created_on',
            field=models.DateTimeField(default=datetime.datetime.now),
        ),
        migrations.AlterField(
            model_name='projectmaster',
            name='created_date',
            field=models.DateTimeField(default=datetime.datetime.now),
        ),
        migrations.AlterField(
            model_name='slum',
            name='shape',
            field=django.contrib.gis.db.models.fields.PolygonField(default='', srid=4326),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='survey',
            name='kobotool_survey_url',
            field=models.CharField(max_length=2048, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='survey',
            name='survey_type',
            field=models.CharField(max_length=2048, choices=[(b'Slum Level', b'Slum Level'), (b'Household Level', b'Household Level'), (b'Household Member Level', b'Household Member Level'), (b'Family Factsheet', b'Family Factsheet')]),
        ),
    ]
