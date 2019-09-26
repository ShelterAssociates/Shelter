# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import master.models


class Migration(migrations.Migration):

    dependencies = [
        ('master', '0019_auto_20190916_1210'),
    ]

    operations = [
        migrations.AddField(
            model_name='rapid_slum_appraisal',
            name='drainage_coverage',
            field=models.CharField(max_length=2048, null=True, blank=True),
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
    ]
