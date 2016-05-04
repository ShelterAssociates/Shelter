# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('master', '0002_auto_20160504_1457'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Sponsor',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('organization', models.CharField(max_length=200)),
                ('address', models.CharField(max_length=2048)),
                ('website', models.CharField(max_length=2048)),
                ('intro_date', models.DateTimeField(default=datetime.datetime(2016, 5, 4, 14, 57, 10, 206692))),
                ('other_info', models.CharField(max_length=2048)),
                ('image', models.CharField(max_length=2048)),
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
                ('contact_no', models.CharField(max_length=256)),
                ('status', models.CharField(max_length=2, choices=[(b'0', b'InActive'), (b'1', b'Active')])),
                ('sponsor', models.ForeignKey(to='sponsor.Sponsor')),
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
                ('type', models.IntegerField(choices=[(b'0', b'Intervention'), (b'1', b'Collection')])),
                ('funds_sponsored', models.DecimalField(max_digits=10, decimal_places=2)),
                ('additional_info', models.CharField(max_length=2048)),
                ('start_date', models.DateTimeField()),
                ('end_date', models.DateTimeField()),
                ('funds_utilised', models.DecimalField(max_digits=10, decimal_places=2)),
                ('status', models.CharField(max_length=2, choices=[(b'0', b'Planned'), (b'1', b'Activated'), (b'2', b'Closed')])),
                ('created_on', models.DateTimeField(default=datetime.datetime(2016, 5, 4, 14, 57, 10, 209367))),
                ('created_by', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
                ('sponsor', models.ForeignKey(to='sponsor.Sponsor')),
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
                ('household_code', models.IntegerField()),
                ('slum', models.ForeignKey(to='master.Slum')),
                ('sponsor_project', models.ForeignKey(to='sponsor.SponsorProject')),
            ],
            options={
                'verbose_name': 'Sponsor Project Detail',
                'verbose_name_plural': 'Sponsor Project Details',
            },
        ),
    ]
