# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mastersheet', '0009_auto_20180613_1145'),
    ]

    operations = [
        migrations.AlterField(
            model_name='toiletconstruction',
            name='status',
            field=models.CharField(blank=True, max_length=2, null=True, choices=[(b'1', b'Agreement done'), (b'2', b'Agreement cancel'), (b'3', b'Material not given'), (b'4', b'Construction not started'), (b'5', b'Under construction'), (b'6', b'completed'), (b'7', b'Written-off')]),
        ),
    ]
