# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc
import master.models


class Migration(migrations.Migration):

    dependencies = [
        ('master', '0004_auto_20161208_1303'),
    ]

    operations = [
        migrations.AddField(
            model_name='rapid_slum_appraisal',
            name='drainage_report_image',
            field=models.ImageField(null=True, upload_to=b'ShelterPhotos/FactsheetPhotos/', blank=True),
        ),
        migrations.AddField(
            model_name='rapid_slum_appraisal',
            name='location_of_defecation',
            field=models.CharField(max_length=2048, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='city',
            name='created_on',
            field=models.DateTimeField(default=datetime.datetime(2017, 4, 14, 15, 21, 15, 366599)),
        ),
        migrations.AlterField(
            model_name='plottedshape',
            name='created_on',
            field=models.DateTimeField(default=datetime.datetime(2017, 4, 14, 15, 21, 15, 376181)),
        ),
        migrations.AlterField(
            model_name='projectmaster',
            name='created_date',
            field=models.DateTimeField(default=datetime.datetime(2017, 4, 14, 15, 21, 15, 379247)),
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
            name='name',
            field=models.CharField(default=datetime.datetime(2017, 4, 14, 9, 51, 49, 863374, tzinfo=utc), max_length=2048),
            preserve_default=False,
        ),
    ]
