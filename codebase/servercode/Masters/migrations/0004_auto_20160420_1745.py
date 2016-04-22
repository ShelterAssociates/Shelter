# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('Masters', '0003_auto_20160420_1736'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Electrol_Ward',
            new_name='Electoral_Ward',
        ),
        migrations.RenameField(
            model_name='elected_representative',
            old_name='Eletrolward_id',
            new_name='Electoralward_id',
        ),
        migrations.RenameField(
            model_name='electoral_ward',
            old_name='Electrolward_code',
            new_name='Electoralward_code',
        ),
        migrations.RenameField(
            model_name='slum',
            old_name='ElectrolWard_id',
            new_name='ElectoralWard_id',
        ),
        migrations.AlterField(
            model_name='city',
            name='createdOn',
            field=models.DateTimeField(default=datetime.datetime(2016, 4, 20, 17, 45, 53, 550686)),
        ),
        migrations.AlterField(
            model_name='filter_master',
            name='createdOn',
            field=models.DateTimeField(default=datetime.datetime(2016, 4, 20, 17, 45, 53, 557353)),
        ),
        migrations.AlterField(
            model_name='plottedshape',
            name='createdOn',
            field=models.DateTimeField(default=datetime.datetime(2016, 4, 20, 17, 45, 53, 556270)),
        ),
        migrations.AlterField(
            model_name='projectmaster',
            name='created_date',
            field=models.DateTimeField(default=datetime.datetime(2016, 4, 20, 17, 45, 53, 562347)),
        ),
        migrations.AlterField(
            model_name='sponsor_project',
            name='createdOn',
            field=models.DateTimeField(default=datetime.datetime(2016, 4, 20, 17, 45, 53, 558628)),
        ),
    ]
