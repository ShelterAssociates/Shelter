# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mastersheet', '0004_auto_20180402_1628'),
    ]

    operations = [
        migrations.AlterField(
            model_name='toiletconstruction',
            name='agreement_cancelled',
            field=models.NullBooleanField(),
        ),
    ]
