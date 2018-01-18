# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('mastersheet', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activitytype',
            name='display_flag',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='sbmupload',
            name='created_date',
            field=models.DateTimeField(default=datetime.datetime.now),
        ),
        migrations.RemoveField(
            model_name='sbmupload',
            name='photo_uploaded'
        ),
        migrations.AddField(
            model_name='sbmupload',
            name='photo_uploaded',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='toiletconstruction',
            name='agreement_cancelled',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='toiletconstruction',
            name='comment',
            field=models.TextField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='toiletconstruction',
            name='completion_date',
            field=models.DateField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='toiletconstruction',
            name='material_shifted_to',
            field=models.CharField(max_length=5, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='toiletconstruction',
            name='phase_one_material_date',
            field=models.DateField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='toiletconstruction',
            name='phase_three_material_date',
            field=models.DateField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='toiletconstruction',
            name='phase_two_material_date',
            field=models.DateField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='toiletconstruction',
            name='septic_tank_date',
            field=models.DateField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='toiletconstruction',
            name='status',
            field=models.CharField(max_length=2, choices=[(b'1', b'Agreement done'), (b'2', b'Agreement cancel'), (b'3', b'Material not given'), (b'4', b'Construction not started'), (b'5', b'Under construction'), (b'6', b'completed')]),
        ),
        migrations.AlterField(
            model_name='vendor',
            name='created_date',
            field=models.DateTimeField(default=datetime.datetime.now),
        ),
        migrations.AlterField(
            model_name='vendorhouseholdinvoicedetail',
            name='created_date',
            field=models.DateTimeField(default=datetime.datetime.now),
        ),
        migrations.AlterField(
            model_name='vendortype',
            name='created_date',
            field=models.DateTimeField(default=datetime.datetime.now),
        ),
    ]
