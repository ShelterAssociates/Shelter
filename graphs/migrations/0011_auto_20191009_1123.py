# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('graphs', '0010_dashboarddata_gen_population_density'),
    ]

    operations = [
        migrations.RenameField(
            model_name='dashboarddata',
            old_name='gen_population_density',
            new_name='household_owners_count',
        ),
    ]
