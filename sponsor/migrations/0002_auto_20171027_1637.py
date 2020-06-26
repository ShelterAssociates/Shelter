# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('sponsor', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SponsorProjectMOU',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('quarter', models.CharField(max_length=2, choices=[(b'1', b'First'), (b'2', b'Second'), (b'3', b'Third'), (b'4', b'Fourth')])),
                ('fund_released', models.DecimalField(max_digits=10, decimal_places=2)),
                ('release_date', models.DateTimeField(default=datetime.datetime(2017, 10, 27, 16, 37, 3, 253359))),
            ],
            options={
                'verbose_name': 'Sponsor project MOU',
                'verbose_name_plural': 'Sponsor project MOU',
            },
        ),
        migrations.RemoveField(
            model_name='sponsorproject',
            name='project_details',
        ),
        migrations.AddField(
            model_name='sponsorproject',
            name='document',
            field=models.FileField(null=True, upload_to=b'sponsor_project/', blank=True),
        ),
        migrations.AddField(
            model_name='sponsorproject',
            name='image',
            field=models.ImageField(null=True, upload_to=b'sponsor_project/', blank=True),
        ),
        migrations.AddField(
            model_name='sponsorproject',
            name='sponsor',
            field=models.ForeignKey(blank=True, to='sponsor.Sponsor', null=True, on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='sponsorprojectdetails',
            name='count',
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='sponsorprojectdetails',
            name='quarter',
            field=models.CharField(blank=True, max_length=2, null=True, choices=[(b'1', b'First'), (b'2', b'Second'), (b'3', b'Third'), (b'4', b'Fourth')]),
        ),
        migrations.AddField(
            model_name='sponsorprojectdetails',
            name='status',
            field=models.CharField(blank=True, max_length=2, null=True, choices=[(b'1', b'Initiated'), (b'2', b'In-progress'), (b'3', b'Completed')]),
        ),
        migrations.AlterField(
            model_name='sponsor',
            name='intro_date',
            field=models.DateTimeField(default=datetime.datetime(2017, 10, 27, 16, 37, 3, 248779)),
        ),
        migrations.AlterField(
            model_name='sponsorproject',
            name='created_on',
            field=models.DateTimeField(default=datetime.datetime(2017, 10, 27, 16, 37, 3, 250582)),
        ),
        migrations.AlterUniqueTogether(
            name='sponsorprojectdetails',
            unique_together=set([('sponsor', 'sponsor_project', 'slum')]),
        ),
        migrations.AddField(
            model_name='sponsorprojectmou',
            name='sponsor_project',
            field=models.ForeignKey(to='sponsor.SponsorProject', on_delete=models.CASCADE),
        ),
    ]
