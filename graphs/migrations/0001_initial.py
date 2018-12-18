# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('master', '0010_auto_20181126_1720'),
    ]

    operations = [
        migrations.CreateModel(
            name='FollowupData',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('household_number', models.CharField(max_length=5)),
                ('submission_date', models.DateTimeField()),
                ('created_date', models.DateTimeField(default=datetime.datetime.now)),
                ('followup_data', jsonfield.fields.JSONField(null=True, blank=True)),
                ('slum', models.ForeignKey(to='master.Slum')),
            ],
            options={
                'verbose_name': 'Followup data',
                'verbose_name_plural': 'Followup data',
            },
        ),
        migrations.CreateModel(
            name='HouseholdData',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('household_number', models.CharField(max_length=5)),
                ('submission_date', models.DateTimeField()),
                ('created_date', models.DateTimeField(default=datetime.datetime.now)),
                ('rhs_data', jsonfield.fields.JSONField(null=True, blank=True)),
                ('slum', models.ForeignKey(to='master.Slum')),
            ],
            options={
                'verbose_name': 'Household data',
                'verbose_name_plural': 'Household data',
            },
        ),
    ]
