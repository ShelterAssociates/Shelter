# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
import django.contrib.gis.db.models.fields
import master.models


class Migration(migrations.Migration):

    dependencies = [
        ('master', '0006_auto_20170419_1836'),
    ]

    operations = [
        migrations.AlterField(
            model_name='city',
            name='created_on',
            field=models.DateTimeField(default=datetime.datetime(2017, 10, 30, 13, 2, 29, 852967)),
        ),
        migrations.AlterField(
            model_name='plottedshape',
            name='created_on',
            field=models.DateTimeField(default=datetime.datetime(2017, 10, 30, 13, 2, 29, 862431)),
        ),
        migrations.AlterField(
            model_name='projectmaster',
            name='created_date',
            field=models.DateTimeField(default=datetime.datetime(2017, 10, 30, 13, 2, 29, 865695)),
        ),
        migrations.AlterField(
            model_name='rapid_slum_appraisal',
            name='drainage_image_bottomdown1',
            field=models.ImageField(upload_to=b'ShelterPhotos/', null=True, verbose_name=master.models.validate_image, blank=True),
        ),
        migrations.AlterField(
            model_name='rapid_slum_appraisal',
            name='drainage_image_bottomdown2',
            field=models.ImageField(upload_to=b'ShelterPhotos/', null=True, verbose_name=master.models.validate_image, blank=True),
        ),
        migrations.AlterField(
            model_name='rapid_slum_appraisal',
            name='drainage_info_left_image',
            field=models.ImageField(upload_to=b'ShelterPhotos/', null=True, verbose_name=master.models.validate_image, blank=True),
        ),
        migrations.AlterField(
            model_name='rapid_slum_appraisal',
            name='general_image_bottomdown1',
            field=models.ImageField(upload_to=b'ShelterPhotos/', null=True, verbose_name=master.models.validate_image, blank=True),
        ),
        migrations.AlterField(
            model_name='rapid_slum_appraisal',
            name='general_image_bottomdown2',
            field=models.ImageField(upload_to=b'ShelterPhotos/', null=True, verbose_name=master.models.validate_image, blank=True),
        ),
        migrations.AlterField(
            model_name='rapid_slum_appraisal',
            name='general_info_left_image',
            field=models.ImageField(upload_to=b'ShelterPhotos/', null=True, verbose_name=master.models.validate_image, blank=True),
        ),
        migrations.AlterField(
            model_name='rapid_slum_appraisal',
            name='gutter_image_bottomdown1',
            field=models.ImageField(upload_to=b'ShelterPhotos/', null=True, verbose_name=master.models.validate_image, blank=True),
        ),
        migrations.AlterField(
            model_name='rapid_slum_appraisal',
            name='gutter_image_bottomdown2',
            field=models.ImageField(upload_to=b'ShelterPhotos/', null=True, verbose_name=master.models.validate_image, blank=True),
        ),
        migrations.AlterField(
            model_name='rapid_slum_appraisal',
            name='gutter_info_left_image',
            field=models.ImageField(upload_to=b'ShelterPhotos/', null=True, verbose_name=master.models.validate_image, blank=True),
        ),
        migrations.AlterField(
            model_name='rapid_slum_appraisal',
            name='road_image_bottomdown2',
            field=models.ImageField(upload_to=b'ShelterPhotos/', null=True, verbose_name=master.models.validate_image, blank=True),
        ),
        migrations.AlterField(
            model_name='rapid_slum_appraisal',
            name='roads_and_access_info_left_image',
            field=models.ImageField(upload_to=b'ShelterPhotos/', null=True, verbose_name=master.models.validate_image, blank=True),
        ),
        migrations.AlterField(
            model_name='rapid_slum_appraisal',
            name='roads_image_bottomdown1',
            field=models.ImageField(upload_to=b'ShelterPhotos/', null=True, verbose_name=master.models.validate_image, blank=True),
        ),
        migrations.AlterField(
            model_name='rapid_slum_appraisal',
            name='toilet_image_bottomdown1',
            field=models.ImageField(upload_to=b'ShelterPhotos/', null=True, verbose_name=master.models.validate_image, blank=True),
        ),
        migrations.AlterField(
            model_name='rapid_slum_appraisal',
            name='toilet_image_bottomdown2',
            field=models.ImageField(upload_to=b'ShelterPhotos/', null=True, verbose_name=master.models.validate_image, blank=True),
        ),
        migrations.AlterField(
            model_name='rapid_slum_appraisal',
            name='toilet_info_left_image',
            field=models.ImageField(upload_to=b'ShelterPhotos/', null=True, verbose_name=master.models.validate_image, blank=True),
        ),
        migrations.AlterField(
            model_name='rapid_slum_appraisal',
            name='waste_management_image_bottomdown1',
            field=models.ImageField(upload_to=b'ShelterPhotos/', null=True, verbose_name=master.models.validate_image, blank=True),
        ),
        migrations.AlterField(
            model_name='rapid_slum_appraisal',
            name='waste_management_image_bottomdown2',
            field=models.ImageField(upload_to=b'ShelterPhotos/', null=True, verbose_name=master.models.validate_image, blank=True),
        ),
        migrations.AlterField(
            model_name='rapid_slum_appraisal',
            name='waste_management_info_left_image',
            field=models.ImageField(upload_to=b'ShelterPhotos/', null=True, verbose_name=master.models.validate_image, blank=True),
        ),
        migrations.AlterField(
            model_name='rapid_slum_appraisal',
            name='water_image_bottomdown1',
            field=models.ImageField(upload_to=b'ShelterPhotos/', null=True, verbose_name=master.models.validate_image, blank=True),
        ),
        migrations.AlterField(
            model_name='rapid_slum_appraisal',
            name='water_image_bottomdown2',
            field=models.ImageField(upload_to=b'ShelterPhotos/', null=True, verbose_name=master.models.validate_image, blank=True),
        ),
        migrations.AlterField(
            model_name='rapid_slum_appraisal',
            name='water_info_left_image',
            field=models.ImageField(upload_to=b'ShelterPhotos/', null=True, verbose_name=master.models.validate_image, blank=True),
        ),
        migrations.AlterField(
            model_name='slum',
            name='shape',
            field=django.contrib.gis.db.models.fields.PolygonField(srid=4326),
        ),
        migrations.AlterField(
            model_name='survey',
            name='kobotool_survey_url',
            field=models.CharField(max_length=2048, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='survey',
            name='survey_type',
            field=models.CharField(max_length=2048, choices=[(b'Slum Level', b'Slum Level'), (b'Household Level', b'Household Level'), (b'Household Member Level', b'Household Member Level'), (b'Family Factsheet', b'Family Factsheet')]),
        ),
    ]
