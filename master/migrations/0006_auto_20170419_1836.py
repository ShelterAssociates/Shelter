# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
import django.contrib.gis.db.models.fields
import master.models


class Migration(migrations.Migration):

    dependencies = [
        ('master', '0005_auto_20170414_1521'),
    ]

    operations = [
        migrations.AddField(
            model_name='rapid_slum_appraisal',
            name='percentage_with_individual_toilet',
            field=models.CharField(max_length=2048, null=True, blank=True),
        ),
    ]
