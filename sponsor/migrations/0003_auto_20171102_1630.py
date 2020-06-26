# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('sponsor', '0002_auto_20171027_1637'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProjectDocuments',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('document', models.FileField(upload_to=b'sponsor_project/')),
            ],
            options={
                'verbose_name': 'Project Document',
                'verbose_name_plural': 'Project Documents',
            },
        ),
        migrations.CreateModel(
            name='ProjectImages',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('image', models.ImageField(upload_to=b'sponsor_project/')),
            ],
            options={
                'verbose_name': 'Project Image',
                'verbose_name_plural': 'Project Images',
            },
        ),
        migrations.RemoveField(
            model_name='sponsorproject',
            name='document',
        ),
        migrations.RemoveField(
            model_name='sponsorproject',
            name='image',
        ),
        migrations.AlterField(
            model_name='sponsor',
            name='intro_date',
            field=models.DateTimeField(default=datetime.datetime.now),
        ),
        migrations.AlterField(
            model_name='sponsorproject',
            name='created_on',
            field=models.DateTimeField(default=datetime.datetime.now),
        ),
        migrations.AlterField(
            model_name='sponsorprojectmou',
            name='release_date',
            field=models.DateTimeField(default=datetime.datetime.now),
        ),
        migrations.AlterUniqueTogether(
            name='sponsorprojectdetails',
            unique_together=set([]),
        ),
        migrations.AddField(
            model_name='projectimages',
            name='sponsor_project',
            field=models.ForeignKey(to='sponsor.SponsorProject', on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='projectdocuments',
            name='sponsor_project',
            field=models.ForeignKey(to='sponsor.SponsorProject', on_delete=models.CASCADE),
        ),
    ]
