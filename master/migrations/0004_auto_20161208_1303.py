# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
import colorfield.fields
import django.contrib.gis.db.models.fields
import master.models


class Migration(migrations.Migration):

    dependencies = [
        ('master', '0003_auto_20161005_1842'),
    ]

    operations = [
        migrations.CreateModel(
            name='drainage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('drainage_image', models.ImageField(null=True, upload_to=b'ShelterPhotos/FactsheetPhotos/', blank=True)),
            ],
        ),
        migrations.AlterModelOptions(
            name='rapid_slum_appraisal',
            options={'ordering': ['slum_name']},
        ),
        migrations.AlterModelOptions(
            name='slum',
            options={'ordering': ['name'], 'verbose_name': 'Slum', 'verbose_name_plural': 'Slums'},
        ),
        migrations.AlterField(
            model_name='administrativeward',
            name='background_color',
            field=colorfield.fields.ColorField(default=b'#BFFFD0', max_length=10),
        ),
        migrations.AlterField(
            model_name='administrativeward',
            name='border_color',
            field=colorfield.fields.ColorField(default=b'#BFFFD0', max_length=10),
        ),
        migrations.AlterField(
            model_name='administrativeward',
            name='name',
            field=models.CharField(default=b'', max_length=2048),
        ),
        migrations.AlterField(
            model_name='administrativeward',
            name='shape',
            field=django.contrib.gis.db.models.fields.PolygonField(default=b'', srid=4326),
        ),
        migrations.AlterField(
            model_name='administrativeward',
            name='ward_no',
            field=models.CharField(default=b'', max_length=2048),
        ),
        migrations.AlterField(
            model_name='city',
            name='background_color',
            field=colorfield.fields.ColorField(default=b'#94BBFF', max_length=10),
        ),
        migrations.AlterField(
            model_name='city',
            name='border_color',
            field=colorfield.fields.ColorField(default=b'#94BBFF', max_length=10),
        ),
        migrations.AlterField(
            model_name='city',
            name='created_on',
            field=models.DateTimeField(default=datetime.datetime(2016, 12, 8, 13, 3, 56, 8998)),
        ),
        migrations.AlterField(
            model_name='electedrepresentative',
            name='additional_info',
            field=models.CharField(max_length=2048, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='electoralward',
            name='background_color',
            field=colorfield.fields.ColorField(default=b'#FFEFA1', max_length=10),
        ),
        migrations.AlterField(
            model_name='electoralward',
            name='border_color',
            field=colorfield.fields.ColorField(default=b'#FFEFA1', max_length=10),
        ),
        migrations.AlterField(
            model_name='electoralward',
            name='name',
            field=models.CharField(default=b'', max_length=2048),
        ),
        migrations.AlterField(
            model_name='electoralward',
            name='shape',
            field=django.contrib.gis.db.models.fields.PolygonField(default=b'', srid=4326),
        ),
        migrations.AlterField(
            model_name='electoralward',
            name='ward_code',
            field=models.TextField(default=b'', max_length=2048),
        ),
        migrations.AlterField(
            model_name='electoralward',
            name='ward_no',
            field=models.CharField(default=b'', max_length=2048),
        ),
        migrations.AlterField(
            model_name='plottedshape',
            name='created_on',
            field=models.DateTimeField(default=datetime.datetime(2016, 12, 8, 13, 3, 56, 24067)),
        ),
        migrations.AlterField(
            model_name='projectmaster',
            name='created_date',
            field=models.DateTimeField(default=datetime.datetime(2016, 12, 8, 13, 3, 56, 27514)),
        ),
        migrations.AlterField(
            model_name='rapid_slum_appraisal',
            name='approximate_population',
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
            name='frequency_of_clearance_of_waste_containers',
            field=models.CharField(max_length=2048, null=True, blank=True),
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
            name='percentage_with_an_individual_water_connection',
            field=models.CharField(max_length=2048, null=True, blank=True),
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
            name='toilet_cost',
            field=models.CharField(max_length=2048, null=True, blank=True),
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
            name='toilet_seat_to_persons_ratio',
            field=models.CharField(max_length=2048, null=True, blank=True),
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
            model_name='wardofficecontact',
            name='address_info',
            field=models.CharField(default=b'', max_length=2048),
        ),
        migrations.AlterField(
            model_name='wardofficecontact',
            name='telephone',
            field=models.CharField(max_length=2048, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='drainage',
            name='slum_name',
            field=models.ForeignKey(to='master.Slum', on_delete=models.CASCADE),
        ),
    ]
