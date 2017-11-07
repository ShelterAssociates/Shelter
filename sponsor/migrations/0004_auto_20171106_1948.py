# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
import sponsor.models


class Migration(migrations.Migration):

    dependencies = [
        ('sponsor', '0003_auto_20171102_1630'),
    ]

    operations = [
        migrations.AddField(
            model_name='sponsorprojectdetails',
            name='zip_created_on',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='sponsorprojectdetails',
            name='zip_file',
            field=models.FileField(null=True, upload_to=sponsor.models.zip_path, blank=True),
        ),
        migrations.AlterField(
            model_name='sponsor',
            name='intro_date',
            field=models.DateField(default=datetime.datetime.now),
        ),
        migrations.AlterField(
            model_name='sponsorproject',
            name='created_on',
            field=models.DateField(default=datetime.datetime.now),
        ),
        migrations.AlterField(
            model_name='sponsorproject',
            name='end_date',
            field=models.DateField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='sponsorproject',
            name='start_date',
            field=models.DateField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='sponsorprojectmou',
            name='release_date',
            field=models.DateField(default=datetime.datetime.now),
        ),
    ]
