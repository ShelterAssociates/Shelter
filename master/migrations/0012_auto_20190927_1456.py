# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import master.models


class Migration(migrations.Migration):

    dependencies = [
        ('master', '0011_auto_20190926_1247'),
    ]

    operations = [
        migrations.AddField(
            model_name='slum',
            name='odf_status',
            field=models.CharField(default=((b'', b''), (b'OD', b'OD'), (b'ODF', b'ODF'), (b'ODF+', b'ODF+'), (b'ODF++', b'ODF++')), max_length=2048, choices=[(b'', b''), (b'OD', b'OD'), (b'ODF', b'ODF'), (b'ODF+', b'ODF+'), (b'ODF++', b'ODF++')]),
        ),
    ]
