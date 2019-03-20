# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import master.models


class Migration(migrations.Migration):

    dependencies = [
        ('master', '0009_auto_20180709_1839'),
    ]

    operations = [
        migrations.AddField(
            model_name='slum',
            name='status',
            field=models.BooleanField(default=False),
        ),
    ]
