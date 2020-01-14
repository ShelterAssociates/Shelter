# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('graphs', '0013_auto_20191203_1450'),
    ]

    operations = [
        migrations.AddField(
            model_name='followupdata',
            name='kobo_id',
            field=models.IntegerField(null=True, blank=True),
        ),
    ]
