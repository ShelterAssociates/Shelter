# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('graphs', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='followupdata',
            name='household_number',
        ),
        migrations.RemoveField(
            model_name='followupdata',
            name='slum',
        ),
        migrations.AddField(
            model_name='followupdata',
            name='flag_followup_in_rhs',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='followupdata',
            name='household_data',
            field=models.ForeignKey(default=b'', to='graphs.HouseholdData'),
        ),
        migrations.AddField(
            model_name='householddata',
            name='city',
            field=models.ForeignKey(default='3', to='master.City'),
            preserve_default=False,
        ),
        migrations.AlterUniqueTogether(
            name='householddata',
            unique_together=set([('slum', 'household_number')]),
        ),
    ]
