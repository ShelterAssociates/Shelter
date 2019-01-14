# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('graphs', '0003_auto_20181210_1646'),
    ]

    operations = [
        migrations.AddField(
            model_name='householddata',
            name='ff_data',
            field=jsonfield.fields.JSONField(null=True, blank=True),
        ),
    ]
