# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('component', '0002_auto_20170602_1607'),
    ]

    operations = [
        migrations.AddField(
            model_name='metadata',
            name='authenticate',
            field=models.BooleanField(default=False),
        ),
    ]
