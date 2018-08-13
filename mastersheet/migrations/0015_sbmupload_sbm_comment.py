# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mastersheet', '0014_auto_20180808_1253'),
    ]

    operations = [
        migrations.AddField(
            model_name='sbmupload',
            name='sbm_comment',
            field=models.TextField(null=True, blank=True),
        ),
    ]
