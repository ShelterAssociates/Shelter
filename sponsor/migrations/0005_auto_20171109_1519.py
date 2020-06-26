# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import jsonfield.fields
import sponsor.models


class Migration(migrations.Migration):

    dependencies = [
        ('sponsor', '0004_auto_20171106_1948'),
    ]

    operations = [
        migrations.CreateModel(
            name='SponsorProjectDetailsSubFields',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('household_code', jsonfield.fields.JSONField(null=True, blank=True)),
                ('quarter', models.CharField(max_length=2, choices=[(b'1', b'First'), (b'2', b'Second'), (b'3', b'Third'), (b'4', b'Fourth')])),
                ('status', models.CharField(max_length=2, choices=[(b'1', b'Initiated'), (b'2', b'In-progress'), (b'3', b'Completed')])),
                ('count', models.IntegerField(null=True, blank=True)),
                ('zip_file', models.FileField(null=True, upload_to=sponsor.models.zip_path, blank=True)),
                ('zip_created_on', models.DateField(null=True, blank=True)),
            ],
            options={
                'verbose_name': 'Sponsor Project Detail Sub Field',
                'verbose_name_plural': 'Sponsor Project Detail Sub Fields',
            },
        ),
        migrations.RemoveField(
            model_name='sponsorprojectdetails',
            name='count',
        ),
        migrations.RemoveField(
            model_name='sponsorprojectdetails',
            name='quarter',
        ),
        migrations.RemoveField(
            model_name='sponsorprojectdetails',
            name='status',
        ),
        migrations.RemoveField(
            model_name='sponsorprojectdetails',
            name='zip_created_on',
        ),
        migrations.RemoveField(
            model_name='sponsorprojectdetails',
            name='zip_file',
        ),
        migrations.AddField(
            model_name='sponsorprojectdetailssubfields',
            name='sponsor_project_details',
            field=models.ForeignKey(to='sponsor.SponsorProjectDetails', on_delete=models.CASCADE),
        ),
    ]
