# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('component', '0004_auto_20180521_1809'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='component',
            options={'verbose_name': 'Component', 'verbose_name_plural': 'Components', 'permissions': (('can_upload_KML', 'Can upload KML file'),)},
        ),
    ]
