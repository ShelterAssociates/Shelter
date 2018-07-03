# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import master.models


class Migration(migrations.Migration):

    dependencies = [
        ('master', '0007_auto_20180625_1228'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='rapid_slum_appraisal',
            options={'ordering': ['slum_name'], 'permissions': (('can_view_slum_information', 'Can view the slum information'), ('can_generate_reports', 'Can generate reports'))},
        ),
        migrations.AlterModelOptions(
            name='survey',
            options={'verbose_name': 'Survey', 'verbose_name_plural': 'Surveys', 'permissions': (('can_view_survey_mapping', 'Can view the Survey Mapping'),)},
        ),
    ]
