# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mastersheet', '0020_auto_20181015_1608'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='total',
            field=models.FloatField(default=0),
        ),
    ]
