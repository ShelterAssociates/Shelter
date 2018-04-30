# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mastersheet', '0006_auto_20180418_1202'),
    ]

    operations = [
        migrations.AddField(
            model_name='sbmupload',
            name='application_approved',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='sbmupload',
            name='application_verified',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='sbmupload',
            name='photo_approved',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='sbmupload',
            name='photo_verified',
            field=models.BooleanField(default=False),
        ),
    ]
