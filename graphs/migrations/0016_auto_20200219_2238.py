# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('graphs', '0015_auto_20200117_1516'),
    ]

    operations = [
        migrations.AddField(
            model_name='householddata',
            name='ff_kobo_id',
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='householddata',
            name='kobo_id',
            field=models.IntegerField(null=True, blank=True),
        ),
    ]
