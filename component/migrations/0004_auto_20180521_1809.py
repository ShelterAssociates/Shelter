# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('component', '0003_metadata_authenticate'),
    ]

    operations = [
        migrations.AlterField(
            model_name='component',
            name='housenumber',
            field=models.CharField(max_length=100),
        ),
    ]
