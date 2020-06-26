# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('graphs', '0004_householddata_ff_data'),
    ]

    operations = [
        migrations.CreateModel(
            name='SlumData',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('submission_date', models.DateTimeField()),
                ('created_on', models.DateTimeField(default=datetime.datetime.now)),
                ('modified_on', models.DateTimeField(default=datetime.datetime.now)),
                ('rim_data', jsonfield.fields.JSONField(null=True, blank=True)),
                ('city', models.ForeignKey(to='master.City', on_delete=models.DO_NOTHING)),
                ('slum', models.ForeignKey(to='master.Slum', on_delete=models.DO_NOTHING)),
            ],
            options={
                'verbose_name': 'Slum data',
                'verbose_name_plural': 'Slum data',
            },
        ),
    ]
