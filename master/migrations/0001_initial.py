# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
import django.contrib.gis.db.models.fields
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AdministrativeWard',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=2048, null=True, blank=True)),
                ('shape', django.contrib.gis.db.models.fields.PolygonField(srid=4326, null=True, blank=True)),
                ('ward_no', models.CharField(max_length=2048, null=True, blank=True)),
                ('description', models.TextField(max_length=2048, null=True, blank=True)),
                ('office_address', models.CharField(max_length=2048, null=True, blank=True)),
            ],
            options={
                'verbose_name': 'Administrative Ward',
                'verbose_name_plural': 'Administrative Wards',
            },
        ),
        migrations.CreateModel(
            name='City',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('city_code', models.CharField(max_length=2048)),
                ('state_name', models.CharField(max_length=2048)),
                ('state_code', models.CharField(max_length=2048)),
                ('district_name', models.CharField(max_length=2048)),
                ('district_code', models.CharField(max_length=2048)),
                ('shape', django.contrib.gis.db.models.fields.PolygonField(srid=4326)),
                ('created_on', models.DateTimeField(default=datetime.datetime(2016, 9, 30, 20, 32, 9, 517171))),
                ('created_by', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING)),
            ],
            options={
                'verbose_name': 'City',
                'verbose_name_plural': 'Cities',
            },
        ),
        migrations.CreateModel(
            name='CityReference',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('city_name', models.CharField(max_length=2048)),
                ('city_code', models.CharField(max_length=2048)),
                ('district_name', models.CharField(max_length=2048)),
                ('district_code', models.CharField(max_length=2048)),
                ('state_name', models.CharField(max_length=2048)),
                ('state_code', models.CharField(max_length=2048)),
            ],
        ),
        migrations.CreateModel(
            name='DrawableComponent',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=2048)),
                ('color', models.CharField(max_length=2048)),
                ('extra', models.CharField(max_length=2048)),
                ('maker_icon', models.CharField(max_length=2048)),
            ],
            options={
                'verbose_name': 'Drawable Component',
                'verbose_name_plural': 'Drawable Components',
            },
        ),
        migrations.CreateModel(
            name='ElectedRepresentative',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=2048)),
                ('tel_nos', models.CharField(max_length=2048)),
                ('address', models.CharField(max_length=2048)),
                ('post_code', models.CharField(max_length=2048)),
                ('additional_info', models.CharField(max_length=2048)),
                ('elected_rep_Party', models.CharField(max_length=2048)),
            ],
            options={
                'verbose_name': 'Elected Representative',
                'verbose_name_plural': 'Elected Representatives',
            },
        ),
        migrations.CreateModel(
            name='ElectoralWard',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=2048, null=True, blank=True)),
                ('shape', django.contrib.gis.db.models.fields.PolygonField(srid=4326, null=True, blank=True)),
                ('ward_no', models.CharField(max_length=2048, null=True, blank=True)),
                ('ward_code', models.TextField(max_length=2048, null=True, blank=True)),
                ('extra_info', models.CharField(max_length=2048, null=True, blank=True)),
                ('administrative_ward', models.ForeignKey(to='master.AdministrativeWard', on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name': 'Electoral Ward',
                'verbose_name_plural': 'Electoral Wards',
            },
        ),
        migrations.CreateModel(
            name='PlottedShape',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('slum', models.CharField(max_length=2048)),
                ('name', models.CharField(max_length=2048)),
                ('lat_long', models.CharField(max_length=2048)),
                ('created_on', models.DateTimeField(default=datetime.datetime(2016, 9, 30, 20, 32, 9, 525432))),
                ('created_by', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING)),
                ('drawable_component', models.ForeignKey(to='master.DrawableComponent', on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name': 'Plotted Shape',
                'verbose_name_plural': 'Plotted Shapes',
            },
        ),
        migrations.CreateModel(
            name='ProjectMaster',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_user', models.CharField(max_length=2048)),
                ('created_date', models.DateTimeField(default=datetime.datetime(2016, 9, 30, 20, 32, 9, 528014))),
            ],
            options={
                'verbose_name': 'Project Master',
                'verbose_name_plural': 'Project Masters',
            },
        ),
        migrations.CreateModel(
            name='Rapid_Slum_Appraisal',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('approximate_population', models.TextField(null=True, blank=True)),
                ('toilet_cost', models.TextField(null=True, blank=True)),
                ('toilet_seat_to_persons_ratio', models.TextField(null=True, blank=True)),
                ('percentage_with_an_individual_water_connection', models.TextField(null=True, blank=True)),
                ('frequency_of_clearance_of_waste_containers', models.TextField(null=True, blank=True)),
                ('general_info_left_image', models.ImageField(null=True, upload_to=b'ShelterPhotos/', blank=True)),
                ('toilet_info_left_image', models.ImageField(null=True, upload_to=b'ShelterPhotos/', blank=True)),
                ('waste_management_info_left_image', models.ImageField(null=True, upload_to=b'ShelterPhotos/', blank=True)),
                ('water_info_left_image', models.ImageField(null=True, upload_to=b'ShelterPhotos/', blank=True)),
                ('roads_and_access_info_left_image', models.ImageField(null=True, upload_to=b'ShelterPhotos/', blank=True)),
                ('drainage_info_left_image', models.ImageField(null=True, upload_to=b'ShelterPhotos/', blank=True)),
                ('gutter_info_left_image', models.ImageField(null=True, upload_to=b'ShelterPhotos/', blank=True)),
                ('general_image_bottomdown1', models.ImageField(null=True, upload_to=b'ShelterPhotos/', blank=True)),
                ('general_image_bottomdown2', models.ImageField(null=True, upload_to=b'ShelterPhotos/', blank=True)),
                ('toilet_image_bottomdown1', models.ImageField(null=True, upload_to=b'ShelterPhotos/', blank=True)),
                ('toilet_image_bottomdown2', models.ImageField(null=True, upload_to=b'ShelterPhotos/', blank=True)),
                ('waste_management_image_bottomdown1', models.ImageField(null=True, upload_to=b'ShelterPhotos/', blank=True)),
                ('waste_management_image_bottomdown2', models.ImageField(null=True, upload_to=b'ShelterPhotos/', blank=True)),
                ('water_image_bottomdown1', models.ImageField(null=True, upload_to=b'ShelterPhotos/', blank=True)),
                ('water_image_bottomdown2', models.ImageField(null=True, upload_to=b'ShelterPhotos/', blank=True)),
                ('roads_image_bottomdown1', models.ImageField(null=True, upload_to=b'ShelterPhotos/', blank=True)),
                ('road_image_bottomdown2', models.ImageField(null=True, upload_to=b'ShelterPhotos/', blank=True)),
                ('drainage_image_bottomdown1', models.ImageField(null=True, upload_to=b'ShelterPhotos/', blank=True)),
                ('drainage_image_bottomdown2', models.ImageField(null=True, upload_to=b'ShelterPhotos/', blank=True)),
                ('gutter_image_bottomdown1', models.ImageField(null=True, upload_to=b'ShelterPhotos/', blank=True)),
                ('gutter_image_bottomdown2', models.ImageField(null=True, upload_to=b'ShelterPhotos/', blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='RoleMaster',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=2048)),
                ('city', models.IntegerField(choices=[(b'0', b'None'), (b'1', b'All'), (b'2', b'Allow Selection')])),
                ('slum', models.IntegerField(choices=[(b'0', b'None'), (b'1', b'All'), (b'2', b'Allow Selection')])),
                ('kml', models.BooleanField()),
                ('dynamic_query', models.BooleanField()),
                ('predefined_query', models.BooleanField()),
                ('can_request', models.BooleanField()),
                ('users', models.BooleanField()),
                ('create_save_query', models.BooleanField()),
                ('deploy_survey', models.BooleanField()),
                ('upload_images', models.BooleanField()),
                ('prepare_reports', models.BooleanField()),
            ],
            options={
                'verbose_name': 'Role Master',
                'verbose_name_plural': 'Role Masters',
            },
        ),
        migrations.CreateModel(
            name='ShapeCode',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.CharField(max_length=2048)),
                ('description', models.CharField(max_length=2048)),
            ],
            options={
                'verbose_name': 'Shape Code',
                'verbose_name_plural': 'Shape Codes',
            },
        ),
        migrations.CreateModel(
            name='Slum',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=2048, null=True, blank=True)),
                ('shape', django.contrib.gis.db.models.fields.PolygonField(srid=4326, null=True, blank=True)),
                ('description', models.TextField(max_length=2048, null=True, blank=True)),
                ('shelter_slum_code', models.CharField(max_length=2048, null=True, blank=True)),
                ('electoral_ward', models.ForeignKey(to='master.ElectoralWard', on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name': 'Slum',
                'verbose_name_plural': 'Slums',
            },
        ),
        migrations.CreateModel(
            name='Survey',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=2048)),
                ('description', models.CharField(max_length=2048)),
                ('survey_type', models.CharField(max_length=2048, choices=[(b'Slum Level', b'Slum Level'), (b'Household Level', b'Household Level'), (b'Household Member Level', b'Household Member Level')])),
                ('analysis_threshold', models.IntegerField()),
                ('kobotool_survey_id', models.CharField(max_length=2048)),
                ('kobotool_survey_url', models.CharField(max_length=2048)),
                ('city', models.ForeignKey(to='master.City', on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name': 'Survey',
                'verbose_name_plural': 'Surveys',
            },
        ),
        migrations.CreateModel(
            name='UserRoleMaster',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('city', models.ForeignKey(to='master.City', on_delete=models.DO_NOTHING)),
                ('role_master', models.ForeignKey(to='master.RoleMaster', on_delete=models.CASCADE)),
                ('slum', models.ForeignKey(to='master.Slum', on_delete=models.CASCADE)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING)),
            ],
            options={
                'verbose_name': 'User Role Master',
                'verbose_name_plural': 'User Role Masters',
            },
        ),
        migrations.CreateModel(
            name='WardOfficeContact',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=2048)),
                ('name', models.CharField(max_length=2048)),
                ('telephone', models.CharField(max_length=2048)),
                ('administrative_ward', models.ForeignKey(to='master.AdministrativeWard', on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name': 'Ward Officer Contact',
                'verbose_name_plural': 'Ward Officer Contacts',
            },
        ),
        migrations.AddField(
            model_name='rapid_slum_appraisal',
            name='slum_name',
            field=models.ForeignKey(to='master.Slum', on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='electedrepresentative',
            name='electoral_ward',
            field=models.ForeignKey(to='master.ElectoralWard', on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='drawablecomponent',
            name='shape_code',
            field=models.ForeignKey(to='master.ShapeCode', on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='city',
            name='name',
            field=models.ForeignKey(to='master.CityReference', on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='administrativeward',
            name='city',
            field=models.ForeignKey(to='master.City', on_delete=models.CASCADE),
        ),
    ]
