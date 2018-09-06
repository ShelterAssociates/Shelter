# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mastersheet', '0015_sbmupload_sbm_comment'),
    ]

    operations = [
        migrations.AddField(
            model_name='toiletconstruction',
            name='factsheet_done',
            field=models.DateField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='toiletconstruction',
            name='toilet_connected_to',
            field=models.DateField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='toiletconstruction',
            name='use_of_toilet',
            field=models.DateField(null=True, blank=True),
        ),
    ]
