# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('graphs', '0009_auto_20190923_1250'),
    ]

    operations = [
        migrations.AddField(
            model_name='dashboarddata',
            name='gen_population_density',
            field=models.FloatField(null=True, blank=True),
        ),
    ]
