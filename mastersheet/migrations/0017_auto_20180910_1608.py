# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mastersheet', '0016_auto_20180905_1654'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='toiletconstruction',
            options={'verbose_name': 'Toilet construction progress', 'verbose_name_plural': 'Toilet construction progress', 'permissions': (('can_view_mastersheet', 'Can view the mastersheet'), ('can_sync_toilet_status', 'Can sync toilet status'), ('can_upload_mastersheet', 'Can upload mastersheet'), ('can_delete_kobo_record', 'Can delete kobo record'), ('can_view_mastersheet_report', 'Can view mastersheet report'), ('can_export_mastersheet_report', 'Can export mastersheet report'))},
        ),
    ]
