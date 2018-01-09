# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import jsonfield.fields
import datetime
from django.core.management import call_command

def loadfixture(apps, schema_editor):
    call_command('loaddata', 'activity_type.json')
    call_command('loaddata', 'filter_data.json')

class Migration(migrations.Migration):

    dependencies = [
        ('master', '0007_auto_20180109_1659'),
    ]

    operations = [
        migrations.CreateModel(
            name='ActivityType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=512)),
                ('key', models.CharField(max_length=2)),
                ('display_flag', models.BooleanField()),
                ('display_order', models.FloatField()),
            ],
            options={
                'verbose_name': 'Activity type',
                'verbose_name_plural': 'Activity types',
            },
        ),
        migrations.CreateModel(
            name='CommunityMobilization',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('household_number', jsonfield.fields.JSONField(null=True, blank=True)),
                ('activity_date', models.DateField()),
                ('activity_type', models.ForeignKey(to='mastersheet.ActivityType')),
                ('slum', models.ForeignKey(to='master.Slum')),
            ],
            options={
                'verbose_name': 'Community mobilization',
                'verbose_name_plural': 'Community mobilization',
            },
        ),
        migrations.CreateModel(
            name='SBMUpload',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('household_number', models.CharField(max_length=5)),
                ('name', models.CharField(max_length=512)),
                ('application_id', models.CharField(max_length=512)),
                ('photo_uploaded', models.ImageField(null=True, upload_to=b'SBM_upload/', blank=True)),
                ('created_date', models.DateTimeField(default=datetime.datetime(2018, 1, 9, 16, 59, 32, 262981))),
                ('slum', models.ForeignKey(to='master.Slum')),
            ],
            options={
                'verbose_name': 'SBM application upload',
                'verbose_name_plural': 'SBM application uploads',
            },
        ),
        migrations.CreateModel(
            name='ToiletConstruction',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('household_number', models.CharField(max_length=5)),
                ('agreement_date', models.DateField()),
                ('agreement_cancelled', models.BooleanField()),
                ('septic_tank_date', models.DateField()),
                ('phase_one_material_date', models.DateField()),
                ('phase_two_material_date', models.DateField()),
                ('phase_three_material_date', models.DateField()),
                ('completion_date', models.DateField()),
                ('status', models.CharField(max_length=2, choices=[(b'1', b'Completed'), (b'2', b''), (b'3', b'')])),
                ('comment', models.TextField()),
                ('material_shifted_to', models.CharField(max_length=5)),
                ('slum', models.ForeignKey(to='master.Slum')),
            ],
            options={
                'verbose_name': 'Toilet construction progress',
                'verbose_name_plural': 'Toilet construction progress',
            },
        ),
        migrations.CreateModel(
            name='Vendor',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=512)),
                ('phone_number', models.CharField(max_length=15, null=True, blank=True)),
                ('email_address', models.CharField(max_length=512, null=True, blank=True)),
                ('description', models.TextField(null=True, blank=True)),
                ('gst_number', models.CharField(max_length=100)),
                ('created_date', models.DateTimeField(default=datetime.datetime(2018, 1, 9, 16, 59, 32, 260381))),
                ('city', models.ForeignKey(to='master.City')),
            ],
            options={
                'verbose_name': 'Vendor',
                'verbose_name_plural': 'Vendors',
            },
        ),
        migrations.CreateModel(
            name='VendorHouseholdInvoiceDetail',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('invoice_number', models.CharField(max_length=100)),
                ('invoice_date', models.DateField()),
                ('household_number', jsonfield.fields.JSONField(null=True, blank=True)),
                ('created_date', models.DateTimeField(default=datetime.datetime(2018, 1, 9, 16, 59, 32, 262068))),
                ('slum', models.ForeignKey(to='master.Slum')),
                ('vendor', models.ForeignKey(to='mastersheet.Vendor')),
            ],
            options={
                'verbose_name': 'Vendor to household invoice detail',
                'verbose_name_plural': 'Vendor to household invoice details',
            },
        ),
        migrations.CreateModel(
            name='VendorType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=512)),
                ('description', models.TextField(null=True, blank=True)),
                ('display_flag', models.BooleanField()),
                ('display_order', models.FloatField()),
                ('created_date', models.DateTimeField(default=datetime.datetime(2018, 1, 9, 16, 59, 32, 259208))),
            ],
            options={
                'verbose_name': 'Vendor type',
                'verbose_name_plural': 'Vendor types',
            },
        ),
        migrations.AddField(
            model_name='vendor',
            name='vendor_type',
            field=models.ForeignKey(to='mastersheet.VendorType'),
        ),
        migrations.AlterUniqueTogether(
            name='vendorhouseholdinvoicedetail',
            unique_together=set([('slum', 'invoice_number')]),
        ),
        migrations.AlterUniqueTogether(
            name='toiletconstruction',
            unique_together=set([('slum', 'household_number')]),
        ),
        migrations.AlterUniqueTogether(
            name='sbmupload',
            unique_together=set([('slum', 'household_number')]),
        ),
        migrations.AlterUniqueTogether(
            name='communitymobilization',
            unique_together=set([('slum', 'activity_type')]),
        ),
        migrations.RunPython(loadfixture),
    ]
