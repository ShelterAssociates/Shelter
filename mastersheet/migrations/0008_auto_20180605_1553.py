# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mastersheet', '0007_auto_20180425_1259'),
    ]

    operations = [
        migrations.AddField(
            model_name='sbmupload',
            name='aadhar_number',
            field=models.CharField(max_length=15, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='sbmupload',
            name='phone_number',
            field=models.CharField(max_length=15, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='toiletconstruction',
            name='status',
            field=models.CharField(max_length=2, choices=[(b'1', b'Agreement done'), (b'2', b'Agreement cancel'), (b'3', b'Material not given'), (b'4', b'Construction not started'), (b'5', b'Under construction'), (b'6', b'completed'), (b'7', b'Written-off')]),
        ),
    ]
