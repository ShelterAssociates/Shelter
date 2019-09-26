# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import master.models


class Migration(migrations.Migration):

    dependencies = [
        ('master', '0010_auto_20190315_1634'),
    ]

    operations = [
        migrations.AddField(
            model_name='rapid_slum_appraisal',
            name='drainage_coverage',
            field=models.CharField(max_length=2048, null=True, blank=True),
        ),
    ]
