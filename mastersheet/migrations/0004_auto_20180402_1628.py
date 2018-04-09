# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mastersheet', '0003_auto_20180323_1206'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='koboddsynctrack',
            options={'verbose_name': 'KoBo daily reporting sync', 'verbose_name_plural': 'KoBo daily reporting sync'},
        ),
        migrations.AlterUniqueTogether(
            name='communitymobilization',
            unique_together=set([('slum', 'activity_type', 'activity_date')]),
        ),
        migrations.AlterUniqueTogether(
            name='koboddsynctrack',
            unique_together=set([('slum', 'sync_date')]),
        ),
    ]
