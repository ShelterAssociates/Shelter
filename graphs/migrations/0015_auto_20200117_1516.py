# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('graphs', '0014_followupdata_kobo_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='dashboarddata',
            name='waste_other_services',
            field=models.FloatField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='dashboarddata',
            name='water_other_services',
            field=models.FloatField(null=True, blank=True),
        ),
    ]
