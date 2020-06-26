# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime

class Migration(migrations.Migration):

    dependencies = [
        ('graphs', '0005_slumdata'),
    ]

    operations = [
        migrations.CreateModel(
            name='QOLScoreData',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_date', models.DateTimeField(default=datetime.datetime.now)),
                ('modified_date', models.DateTimeField(default=datetime.datetime.now)),
                ('general', models.FloatField(default=None,blank=True, null=True)),
                ('gutter', models.FloatField(default=None,blank=True, null=True)),
                ('water', models.FloatField(default=None,blank=True, null=True)),
                ('waste', models.FloatField(default=None,blank=True, null=True)),
                ('drainage', models.FloatField(default=None,blank=True, null=True)),
                ('road', models.FloatField(default=None,blank=True, null=True)),
                ('str_n_occup', models.FloatField(default=None,blank=True, null=True)),
                ('toilet', models.FloatField(default=None,blank=True, null=True)),
                ('total_score', models.FloatField(default=None,blank=True, null=True)),
                ('general_percentile',models.FloatField(default=None, blank=True, null=True)),
                ('gutter_percentile', models.FloatField(default=None, null=True, blank=True)),
                ('water_percentile', models.FloatField(default=None, null=True, blank=True)),
                ('waste_percentile', models.FloatField(default=None, null=True, blank=True)),
                ('drainage_percentile', models.FloatField(default=None, null=True, blank=True)),
                ('road_percentile', models.FloatField(default=None, null=True, blank=True)),
                ('str_n_ocup_percentile', models.FloatField(default=None, null=True, blank=True)),
                ('toilet_percentile', models.FloatField(default=None, null=True, blank=True)),
                ('totalscore_percentile', models.FloatField(default=None, null=True, blank=True)),
                ('city', models.ForeignKey(to='master.City', on_delete=models.DO_NOTHING)),
                ('slum', models.ForeignKey(to='master.Slum', on_delete=models.DO_NOTHING)),
            ],
        ),
    ]
