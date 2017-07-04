# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('component', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='metadata',
            name='icon',
            field=models.ImageField(null=True, upload_to=b'componentIcons/', blank=True),
        ),
        migrations.AlterField(
            model_name='metadata',
            name='type',
            field=models.CharField(max_length=1, choices=[(b'C', b'Component'), (b'F', b'Filter'), (b'S', b'Sponsor')]),
        ),
    ]
