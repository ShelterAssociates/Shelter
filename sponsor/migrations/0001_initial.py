# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
import jsonfield.fields
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('master', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Sponsor',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('organization_name', models.CharField(max_length=1024)),
                ('address', models.CharField(max_length=2048)),
                ('website_link', models.CharField(max_length=2048, null=True, blank=True)),
                ('intro_date', models.DateTimeField(default=datetime.datetime(2017, 3, 15, 18, 14, 46, 84877))),
                ('other_info', models.TextField(null=True, blank=True)),
                ('logo', models.ImageField(null=True, upload_to=b'sponsor_logo/', blank=True)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING)),
            ],
            options={
                'verbose_name': 'Sponsor',
                'verbose_name_plural': 'Sponsors',
            },
        ),
        migrations.CreateModel(
            name='SponsorContact',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=512)),
                ('email_id', models.CharField(max_length=512)),
                ('contact_no', models.CharField(max_length=256, null=True, blank=True)),
                ('status', models.CharField(max_length=2, choices=[(b'0', b'InActive'), (b'1', b'Active')])),
                ('sponsor', models.ForeignKey(to='sponsor.Sponsor', on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name': 'Sponsor Contact',
                'verbose_name_plural': 'Sponsor Contacts',
            },
        ),
        migrations.CreateModel(
            name='SponsorProject',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=512)),
                ('project_type', models.CharField(max_length=2, choices=[(b'1', b'Intervention'), (b'2', b'Collection')])),
                ('funds_sponsored', models.DecimalField(max_digits=10, decimal_places=2)),
                ('additional_info', models.TextField(null=True, blank=True)),
                ('start_date', models.DateTimeField(null=True, blank=True)),
                ('end_date', models.DateTimeField(null=True, blank=True)),
                ('funds_utilised', models.DecimalField(null=True, max_digits=10, decimal_places=2, blank=True)),
                ('status', models.CharField(max_length=2, choices=[(b'1', b'Planned'), (b'2', b'Activated'), (b'3', b'Closed')])),
                ('created_on', models.DateTimeField(default=datetime.datetime(2017, 3, 15, 18, 14, 46, 87019))),
                ('created_by', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING)),
            ],
            options={
                'verbose_name': 'Sponsor Project',
                'verbose_name_plural': 'Sponsor Projects',
            },
        ),
        migrations.CreateModel(
            name='SponsorProjectDetails',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('household_code', jsonfield.fields.JSONField(null=True, blank=True)),
                ('slum', models.ForeignKey(to='master.Slum', on_delete=models.CASCADE)),
                ('sponsor', models.ForeignKey(to='sponsor.Sponsor', on_delete=models.CASCADE)),
                ('sponsor_project', models.ForeignKey(to='sponsor.SponsorProject', on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name': 'Sponsor Project Detail',
                'verbose_name_plural': 'Sponsor Project Details',
            },
        ),
        migrations.AddField(
            model_name='sponsorproject',
            name='project_details',
            field=models.ManyToManyField(to='sponsor.Sponsor', through='sponsor.SponsorProjectDetails'),
        ),
    ]
