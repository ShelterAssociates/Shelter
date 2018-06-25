# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mastersheet', '0010_auto_20180613_1638'),
    ]

    operations = [
        migrations.AddField(
            model_name='toiletconstruction',
            name='pocket',
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='sbmupload',
            name='application_id',
            field=models.CharField(max_length=512, null=True, blank=True),
        ),
    ]
