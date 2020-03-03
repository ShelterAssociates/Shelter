# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('graphs', '0008_auto_20190917_1459'),
    ]

    operations = [
        migrations.RenameField(
            model_name='dashboarddata',
            old_name='water_no_service_percentile',
            new_name='water_shared_service_percentile',
        ),
        migrations.AddField(
            model_name='dashboarddata',
            name='count_of_toilets_completed',
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='dashboarddata',
            name='people_impacted',
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='dashboarddata',
            name='slum_population',
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='dashboarddata',
            name='waterstandpost_percentile',
            field=models.FloatField(null=True, blank=True),
        ),
    ]
