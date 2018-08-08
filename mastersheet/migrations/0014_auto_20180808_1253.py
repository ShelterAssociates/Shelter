# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mastersheet', '0013_auto_20180725_1628'),
    ]

    operations = [
        migrations.AddField(
            model_name='vendorhouseholdinvoicedetail',
            name='amount',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='vendorhouseholdinvoicedetail',
            name='quantity',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='toiletconstruction',
            name='status',
            field=models.CharField(blank=True, max_length=2, null=True, choices=[(b'1', b'Agreement done'), (b'2', b'Agreement cancel'), (b'3', b'Material not given'), (b'4', b'Construction not started'), (b'5', b'Under construction'), (b'6', b'Completed'), (b'7', b'Written-off')]),
        ),
    ]
