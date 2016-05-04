# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime
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
                ('name', models.CharField(max_length=512)),
                ('shape', models.CharField(max_length=2048)),
                ('ward_no', models.CharField(max_length=10)),
                ('description', models.CharField(max_length=2048)),
                ('office_address', models.CharField(max_length=2048)),
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
                ('city_code', models.CharField(max_length=5)),
                ('state_name', models.CharField(max_length=5)),
                ('state_code', models.CharField(max_length=20)),
                ('district_name', models.CharField(max_length=20)),
                ('district_code', models.CharField(max_length=5)),
                ('shape', models.CharField(max_length=2000)),
                ('created_on', models.DateTimeField(default=datetime.datetime(2016, 5, 4, 14, 57, 3, 173470))),
                ('created_by', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
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
                ('city_name', models.CharField(max_length=20)),
                ('city_code', models.CharField(max_length=20)),
                ('district_name', models.CharField(max_length=20)),
                ('district_code', models.CharField(max_length=20)),
                ('state_name', models.CharField(max_length=20)),
                ('state_code', models.CharField(max_length=20)),
            ],
        ),
        migrations.CreateModel(
            name='DrawableComponent',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('color', models.CharField(max_length=100)),
                ('extra', models.CharField(max_length=4096)),
                ('maker_icon', models.CharField(max_length=500)),
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
                ('name', models.CharField(max_length=200)),
                ('tel_nos', models.CharField(max_length=50)),
                ('address', models.CharField(max_length=512)),
                ('post_code', models.CharField(max_length=20)),
                ('additional_info', models.CharField(max_length=2048)),
                ('elected_rep_Party', models.CharField(max_length=50)),
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
                ('name', models.CharField(max_length=512)),
                ('shape', models.CharField(max_length=2048)),
                ('ward_no', models.CharField(max_length=10)),
                ('ward_code', models.CharField(max_length=10)),
                ('extra_info', models.CharField(max_length=4096)),
                ('administrative_ward', models.ForeignKey(to='master.AdministrativeWard')),
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
                ('slum', models.CharField(max_length=100)),
                ('name', models.CharField(max_length=512)),
                ('lat_long', models.CharField(max_length=2000)),
                ('created_on', models.DateTimeField(default=datetime.datetime(2016, 5, 4, 14, 57, 3, 183690))),
                ('created_by', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
                ('drawable_component', models.ForeignKey(to='master.DrawableComponent')),
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
                ('created_user', models.CharField(max_length=100)),
                ('created_date', models.DateTimeField(default=datetime.datetime(2016, 5, 4, 14, 57, 3, 186539))),
            ],
            options={
                'verbose_name': 'Project Master',
                'verbose_name_plural': 'Project Masters',
            },
        ),
        migrations.CreateModel(
            name='RoleMaster',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
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
                ('code', models.CharField(max_length=25)),
                ('description', models.CharField(max_length=100)),
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
                ('name', models.CharField(max_length=100)),
                ('shape', models.CharField(max_length=2048)),
                ('description', models.CharField(max_length=100)),
                ('shelter_slum_code', models.CharField(max_length=512)),
                ('electoral_ward', models.ForeignKey(to='master.ElectoralWard')),
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
                ('name', models.CharField(max_length=50)),
                ('description', models.CharField(max_length=200)),
                ('survey_type', models.CharField(max_length=50, choices=[(b'Slum Level', b'Slum Level'), (b'Household Level', b'Household Level'), (b'Household Member Level', b'Household Member Level')])),
                ('analysis_threshold', models.IntegerField()),
                ('kobotool_survey_id', models.CharField(max_length=50)),
                ('kobotool_survey_url', models.CharField(max_length=512)),
                ('city', models.ForeignKey(to='master.City')),
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
                ('city', models.ForeignKey(to='master.City')),
                ('role_master', models.ForeignKey(to='master.RoleMaster')),
                ('slum', models.ForeignKey(to='master.Slum')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
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
                ('title', models.CharField(max_length=25)),
                ('name', models.CharField(max_length=200)),
                ('telephone', models.CharField(max_length=50)),
                ('administrative_ward', models.ForeignKey(to='master.AdministrativeWard')),
            ],
            options={
                'verbose_name': 'Ward Officer Contact',
                'verbose_name_plural': 'Ward Officer Contacts',
            },
        ),
        migrations.AddField(
            model_name='electedrepresentative',
            name='electoral_ward',
            field=models.ForeignKey(to='master.ElectoralWard'),
        ),
        migrations.AddField(
            model_name='drawablecomponent',
            name='shape_code',
            field=models.ForeignKey(to='master.ShapeCode'),
        ),
        migrations.AddField(
            model_name='city',
            name='name',
            field=models.ForeignKey(to='master.CityReference'),
        ),
        migrations.AddField(
            model_name='administrativeward',
            name='city',
            field=models.ForeignKey(to='master.City'),
        ),
    ]
