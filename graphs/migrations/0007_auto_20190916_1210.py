# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('graphs', '0006_qolscoredata'),
    ]

    operations = [
        migrations.CreateModel(
            name='DashboardData',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_on', models.DateTimeField(default=datetime.datetime.now)),
                ('modified_on', models.DateTimeField(default=datetime.datetime.now)),
                ('household_count', models.FloatField(null=True, blank=True)),
                ('gen_avg_household_size', models.FloatField(null=True, blank=True)),
                ('gen_tenement_density', models.FloatField(null=True, blank=True)),
                ('waste_no_collection_facility_percentile', models.FloatField(null=True, blank=True)),
                ('waste_door_to_door_collection_facility_percentile', models.FloatField(null=True, blank=True)),
                ('waste_dump_in_open_percent', models.FloatField(null=True, blank=True)),
                ('water_individual_connection_percentile', models.FloatField(null=True, blank=True)),
                ('water_no_service_percentile', models.FloatField(null=True, blank=True)),
                ('pucca_road', models.FloatField(null=True, blank=True)),
                ('kutcha_road', models.FloatField(null=True, blank=True)),
                ('road_with_no_vehicle_access', models.FloatField(null=True, blank=True)),
                ('pucca_road_coverage', models.FloatField(null=True, blank=True)),
                ('kutcha_road_coverage', models.FloatField(null=True, blank=True)),
                ('drains_coverage', models.FloatField(null=True, blank=True)),
                ('toilet_seat_to_person_ratio', models.FloatField(null=True, blank=True)),
                ('toilet_men_women_seats_ratio', models.FloatField(null=True, blank=True)),
                ('individual_toilet_coverage', models.FloatField(null=True, blank=True)),
                ('open_defecation_coverage', models.FloatField(null=True, blank=True)),
                ('ctb_coverage', models.FloatField(null=True, blank=True)),
                ('city', models.ForeignKey(to='master.City')),
                ('slum', models.ForeignKey(to='master.Slum')),
            ],
            options={
                'verbose_name': 'Dashboard data',
                'verbose_name_plural': 'Dashboard data',
            },
        ),
        migrations.AlterUniqueTogether(
            name='dashboarddata',
            unique_together=set([('id', 'slum')]),
        ),
    ]
