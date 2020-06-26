# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import master.models


class Migration(migrations.Migration):

    dependencies = [
        ('master', '0008_auto_20180702_1854'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='rapid_slum_appraisal',
            options={'ordering': ['slum_name'], 'permissions': (('can_generate_reports', 'Can generate reports'),)},
        ),
        migrations.AlterField(
            model_name='electoralward',
            name='administrative_ward',
            field=models.ForeignKey(blank=True, to='master.AdministrativeWard', null=True, on_delete=models.CASCADE),
        ),
        migrations.AlterField(
            model_name='slum',
            name='electoral_ward',
            field=models.ForeignKey(blank=True, to='master.ElectoralWard', null=True, on_delete=models.CASCADE),
        ),
    ]
