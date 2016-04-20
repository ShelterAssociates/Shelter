# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('Masters', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='city',
            name='createdOn',
            field=models.DateTimeField(default=datetime.datetime(2016, 4, 19, 23, 10, 45, 851109)),
        ),
        migrations.AlterField(
            model_name='filter_master',
            name='createdOn',
            field=models.DateTimeField(default=datetime.datetime(2016, 4, 19, 23, 10, 45, 860074)),
        ),
        migrations.AlterField(
            model_name='plottedshape',
            name='createdOn',
            field=models.DateTimeField(default=datetime.datetime(2016, 4, 19, 23, 10, 45, 858425)),
        ),
        migrations.AlterField(
            model_name='projectmaster',
            name='created_date',
            field=models.DateTimeField(default=datetime.datetime(2016, 4, 19, 23, 10, 45, 866899)),
        ),
        migrations.AlterField(
            model_name='sponsor_project',
            name='createdOn',
            field=models.DateTimeField(default=datetime.datetime(2016, 4, 19, 23, 10, 45, 862061)),
        ),
        migrations.AlterField(
            model_name='survey',
            name='Survey_type',
            field=models.CharField(max_length=50, choices=[(b'Slum Level', b'Slum Level'), (b'Household Level', b'Household Level'), (b'Household Member Level', b'Household Member Level')]),
        ),
        migrations.AlterField(
            model_name='survey',
            name='kobotoolSurvey_url',
            field=models.CharField(max_length=500),
        ),
    ]
