# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('graphs', '0007_auto_20190906_1835'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dashboarddata',
            name='household_count',
            field=models.FloatField(null=True, blank=True),
        ),
    ]
