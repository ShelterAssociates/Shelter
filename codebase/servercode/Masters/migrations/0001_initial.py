# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('auth', '0006_require_contenttypes_0002'),
    ]

    operations = [
        migrations.CreateModel(
            name='Administrative_Ward',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('Name', models.CharField(max_length=50)),
                ('Shape', models.CharField(max_length=2048)),
                ('Ward_no', models.CharField(max_length=10)),
                ('Description', models.CharField(max_length=512)),
                ('OfficeAddress', models.CharField(max_length=512)),
            ],
        ),
        migrations.CreateModel(
            name='City',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('Name', models.CharField(max_length=20)),
                ('Shape', models.CharField(max_length=2000)),
                ('State_code', models.CharField(max_length=5)),
                ('District_Code', models.CharField(max_length=5)),
                ('City_code', models.CharField(max_length=5)),
                ('createdOn', models.DateTimeField(default=datetime.datetime(2016, 4, 19, 18, 54, 58, 818841))),
                ('createdBy', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Drawable_Component',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('Name', models.CharField(max_length=100)),
                ('Color', models.CharField(max_length=100)),
                ('Extra', models.CharField(max_length=100)),
                ('Maker_icon', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='Elected_Representative',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('Name', models.CharField(max_length=50)),
                ('Telnos', models.CharField(max_length=20)),
                ('Address', models.CharField(max_length=100)),
                ('Postcode', models.CharField(max_length=20)),
                ('AdditionalInfo', models.CharField(max_length=200)),
                ('ElectedRep_Party', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='Electrol_Ward',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('Name', models.CharField(max_length=50)),
                ('Shape', models.CharField(max_length=2048)),
                ('WardNo', models.CharField(max_length=200)),
                ('Electrolward_code', models.CharField(max_length=10)),
                ('Electoralward_Desc', models.CharField(max_length=4096)),
                ('AdministrativeWard_id', models.ForeignKey(to='Masters.Administrative_Ward')),
            ],
        ),
        migrations.CreateModel(
            name='Filter',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('query', models.CharField(max_length=4096)),
            ],
        ),
        migrations.CreateModel(
            name='Filter_Master',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=30)),
                ('IsDeployed', models.CharField(max_length=1)),
                ('VisibleTo', models.IntegerField()),
                ('createdOn', models.DateTimeField(default=datetime.datetime(2016, 4, 19, 18, 54, 58, 830515))),
                ('createdBy', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='FilterMasterMetadata',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('filter_id', models.ForeignKey(to='Masters.Filter_Master')),
                ('user_id', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
                ('user_type', models.ForeignKey(to='auth.Group')),
            ],
        ),
        migrations.CreateModel(
            name='PlottedShape',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('Slum', models.CharField(max_length=100)),
                ('Name', models.CharField(max_length=100)),
                ('Lat_long', models.CharField(max_length=2000)),
                ('createdOn', models.DateTimeField(default=datetime.datetime(2016, 4, 19, 18, 54, 58, 826798))),
                ('Drawable_Component_id', models.ForeignKey(to='Masters.Drawable_Component')),
                ('creaatedBy', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ProjectMaster',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_user', models.CharField(max_length=100)),
                ('created_date', models.DateTimeField(default=datetime.datetime(2016, 4, 19, 18, 54, 58, 836896))),
            ],
        ),
        migrations.CreateModel(
            name='RoleMaster',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('RoleName', models.CharField(max_length=100)),
                ('City', models.IntegerField()),
                ('Slum', models.IntegerField()),
                ('KML', models.CharField(max_length=1)),
                ('DynamicQuery', models.CharField(max_length=1)),
                ('PredefinedQuery', models.CharField(max_length=1)),
                ('CanRequest', models.CharField(max_length=1)),
                ('Users', models.CharField(max_length=1)),
                ('CreateSaveQuery', models.CharField(max_length=1)),
                ('DeploySurvey', models.CharField(max_length=1)),
                ('UploadImages', models.CharField(max_length=1)),
                ('PrepareReports', models.CharField(max_length=1)),
            ],
        ),
        migrations.CreateModel(
            name='ShaperCode',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('Code', models.CharField(max_length=100)),
                ('Description', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='Slum',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('Name', models.CharField(max_length=100)),
                ('Shape', models.CharField(max_length=2048)),
                ('Description', models.CharField(max_length=100)),
                ('Shelter_slum_code', models.CharField(max_length=512)),
                ('ElectrolWard_id', models.ForeignKey(to='Masters.Electrol_Ward')),
            ],
        ),
        migrations.CreateModel(
            name='Sponser',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('organization', models.CharField(max_length=100)),
                ('address', models.CharField(max_length=50)),
                ('Phonenumber', models.CharField(max_length=20)),
                ('description', models.CharField(max_length=256)),
                ('image', models.CharField(max_length=2048)),
            ],
        ),
        migrations.CreateModel(
            name='Sponsor_Project',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('Name', models.CharField(max_length=50)),
                ('Type', models.CharField(max_length=30)),
                ('createdOn', models.DateTimeField(default=datetime.datetime(2016, 4, 19, 18, 54, 58, 832838))),
                ('Sponsor_id', models.ForeignKey(to='Masters.Sponser')),
                ('createdBy', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Sponsor_ProjectMetadata',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('household_code', models.IntegerField()),
                ('Sponsor_Project_id', models.ForeignKey(to='Masters.Sponsor_Project')),
                ('slum_id', models.ForeignKey(to='Masters.Slum')),
            ],
        ),
        migrations.CreateModel(
            name='Sponsor_user',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('Sponsor_id', models.ForeignKey(to='Masters.Sponser')),
                ('auth_user_id', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Survey',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('Name', models.CharField(max_length=50)),
                ('Description', models.CharField(max_length=200)),
                ('Survey_type', models.CharField(max_length=50)),
                ('AnalysisThreshold', models.IntegerField()),
                ('kobotoolSurvey_id', models.CharField(max_length=50)),
                ('kobotoolSurvey_url', models.CharField(max_length=50)),
                ('City_id', models.ForeignKey(to='Masters.City')),
            ],
        ),
        migrations.CreateModel(
            name='UserRoleMaster',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('City_id', models.ForeignKey(to='Masters.City')),
                ('role_id', models.ForeignKey(to='Masters.RoleMaster')),
                ('slum_id', models.ForeignKey(to='Masters.Slum')),
                ('user_id', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='WardOffice_Contacts',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('Name', models.CharField(max_length=50)),
                ('Title', models.CharField(max_length=10)),
                ('Telephone', models.CharField(max_length=20)),
                ('Administrativeward_id', models.ForeignKey(to='Masters.Administrative_Ward')),
            ],
        ),
        migrations.AddField(
            model_name='filter',
            name='Filter_Master_id',
            field=models.ForeignKey(to='Masters.Filter_Master'),
        ),
        migrations.AddField(
            model_name='elected_representative',
            name='Eletrolward_id',
            field=models.ForeignKey(to='Masters.Electrol_Ward'),
        ),
        migrations.AddField(
            model_name='drawable_component',
            name='Shapecode_id',
            field=models.ForeignKey(to='Masters.ShaperCode'),
        ),
        migrations.AddField(
            model_name='administrative_ward',
            name='City_id',
            field=models.ForeignKey(to='Masters.City'),
        ),
    ]
