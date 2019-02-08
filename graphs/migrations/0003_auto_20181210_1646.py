# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('graphs', '0002_auto_20181205_1456'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='followupdata',
            name='household_data',
        ),
        migrations.AddField(
            model_name='followupdata',
            name='city',
            field=models.ForeignKey(default=b'', to='master.City'),
        ),
        migrations.AddField(
            model_name='followupdata',
            name='household_number',
            field=models.CharField(default=b'', max_length=5),
        ),
        migrations.AddField(
            model_name='followupdata',
            name='slum',
            field=models.ForeignKey(default=b'', to='master.Slum'),
        ),
    ]
