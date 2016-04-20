# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('Masters', '0002_auto_20160419_2310'),
    ]

    operations = [
        migrations.RenameField(
            model_name='plottedshape',
            old_name='creaatedBy',
            new_name='createdBy',
        ),
        migrations.RemoveField(
            model_name='filter_master',
            name='name',
        ),
        migrations.AddField(
            model_name='filter_master',
            name='Name',
            field=models.CharField(default='', max_length=512),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='administrative_ward',
            name='Description',
            field=models.CharField(max_length=2048),
        ),
        migrations.AlterField(
            model_name='administrative_ward',
            name='Name',
            field=models.CharField(max_length=512),
        ),
        migrations.AlterField(
            model_name='administrative_ward',
            name='OfficeAddress',
            field=models.CharField(max_length=2048),
        ),
        migrations.AlterField(
            model_name='city',
            name='createdOn',
            field=models.DateTimeField(default=datetime.datetime(2016, 4, 20, 17, 34, 59, 398628)),
        ),
        migrations.AlterField(
            model_name='drawable_component',
            name='Extra',
            field=models.CharField(max_length=4096),
        ),
        migrations.AlterField(
            model_name='drawable_component',
            name='Maker_icon',
            field=models.CharField(max_length=500),
        ),
        migrations.AlterField(
            model_name='elected_representative',
            name='AdditionalInfo',
            field=models.CharField(max_length=2048),
        ),
        migrations.AlterField(
            model_name='elected_representative',
            name='Address',
            field=models.CharField(max_length=512),
        ),
        migrations.AlterField(
            model_name='elected_representative',
            name='Name',
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name='elected_representative',
            name='Telnos',
            field=models.CharField(max_length=50),
        ),
        migrations.AlterField(
            model_name='electrol_ward',
            name='Name',
            field=models.CharField(max_length=512),
        ),
        migrations.AlterField(
            model_name='electrol_ward',
            name='WardNo',
            field=models.CharField(max_length=10),
        ),
        migrations.AlterField(
            model_name='filter_master',
            name='VisibleTo',
            field=models.IntegerField(choices=[(b'0', b'0'), (b'1', b'1'), (b'2', b'2')]),
        ),
        migrations.AlterField(
            model_name='filter_master',
            name='createdOn',
            field=models.DateTimeField(default=datetime.datetime(2016, 4, 20, 17, 34, 59, 408304)),
        ),
        migrations.AlterField(
            model_name='plottedshape',
            name='Name',
            field=models.CharField(max_length=512),
        ),
        migrations.AlterField(
            model_name='plottedshape',
            name='createdOn',
            field=models.DateTimeField(default=datetime.datetime(2016, 4, 20, 17, 34, 59, 406665)),
        ),
        migrations.AlterField(
            model_name='projectmaster',
            name='created_date',
            field=models.DateTimeField(default=datetime.datetime(2016, 4, 20, 17, 34, 59, 414893)),
        ),
        migrations.AlterField(
            model_name='rolemaster',
            name='CanRequest',
            field=models.BooleanField(choices=[(b'0', b'0'), (b'1', b'1')]),
        ),
        migrations.AlterField(
            model_name='rolemaster',
            name='City',
            field=models.IntegerField(choices=[(b'0', b'0'), (b'1', b'1'), (b'2', b'2')]),
        ),
        migrations.AlterField(
            model_name='rolemaster',
            name='CreateSaveQuery',
            field=models.BooleanField(choices=[(b'0', b'0'), (b'1', b'1')]),
        ),
        migrations.AlterField(
            model_name='rolemaster',
            name='DeploySurvey',
            field=models.BooleanField(choices=[(b'0', b'0'), (b'1', b'1')]),
        ),
        migrations.AlterField(
            model_name='rolemaster',
            name='DynamicQuery',
            field=models.BooleanField(choices=[(b'0', b'0'), (b'1', b'1')]),
        ),
        migrations.AlterField(
            model_name='rolemaster',
            name='KML',
            field=models.BooleanField(choices=[(b'0', b'0'), (b'1', b'1')]),
        ),
        migrations.AlterField(
            model_name='rolemaster',
            name='PredefinedQuery',
            field=models.BooleanField(choices=[(b'0', b'0'), (b'1', b'1')]),
        ),
        migrations.AlterField(
            model_name='rolemaster',
            name='PrepareReports',
            field=models.BooleanField(choices=[(b'0', b'0'), (b'1', b'1')]),
        ),
        migrations.AlterField(
            model_name='rolemaster',
            name='Slum',
            field=models.IntegerField(choices=[(b'0', b'0'), (b'1', b'1'), (b'2', b'2')]),
        ),
        migrations.AlterField(
            model_name='rolemaster',
            name='UploadImages',
            field=models.BooleanField(choices=[(b'0', b'0'), (b'1', b'1')]),
        ),
        migrations.AlterField(
            model_name='rolemaster',
            name='Users',
            field=models.BooleanField(choices=[(b'0', b'0'), (b'1', b'1')]),
        ),
        migrations.AlterField(
            model_name='shapercode',
            name='Code',
            field=models.CharField(max_length=25),
        ),
        migrations.AlterField(
            model_name='sponser',
            name='Phonenumber',
            field=models.CharField(max_length=50),
        ),
        migrations.AlterField(
            model_name='sponser',
            name='address',
            field=models.CharField(max_length=2048),
        ),
        migrations.AlterField(
            model_name='sponser',
            name='description',
            field=models.CharField(max_length=2048),
        ),
        migrations.AlterField(
            model_name='sponser',
            name='organization',
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name='sponsor_project',
            name='Name',
            field=models.CharField(max_length=512),
        ),
        migrations.AlterField(
            model_name='sponsor_project',
            name='Type',
            field=models.IntegerField(choices=[(b'0', b'0'), (b'1', b'1')]),
        ),
        migrations.AlterField(
            model_name='sponsor_project',
            name='createdOn',
            field=models.DateTimeField(default=datetime.datetime(2016, 4, 20, 17, 34, 59, 410086)),
        ),
        migrations.AlterField(
            model_name='survey',
            name='kobotoolSurvey_url',
            field=models.CharField(max_length=512),
        ),
        migrations.AlterField(
            model_name='wardoffice_contacts',
            name='Name',
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name='wardoffice_contacts',
            name='Telephone',
            field=models.CharField(max_length=50),
        ),
        migrations.AlterField(
            model_name='wardoffice_contacts',
            name='Title',
            field=models.CharField(max_length=25),
        ),
    ]
