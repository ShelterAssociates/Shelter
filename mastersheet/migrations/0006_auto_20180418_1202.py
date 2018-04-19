# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mastersheet', '0005_auto_20180406_1227'),
    ]

    operations = [
        migrations.AlterField(
            model_name='toiletconstruction',
            name='agreement_date',
            field=models.DateField(null=True, blank=True),
        ),
    ]
