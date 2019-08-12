# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('graphs', '0005_slumdata'),
    ]

    operations = [
        migrations.CreateModel(
            name='Quality_of_living',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_date', models.DateField()),
                ('modified_date', models.DateField(blank=True)),
                ('general', models.FloatField(default=None)),
                ('gutter', models.FloatField(default=None)),
                ('water', models.FloatField(default=None)),
                ('waste', models.FloatField(default=None)),
                ('drainage', models.FloatField(default=None)),
                ('road', models.FloatField(default=None)),
                ('toilet', models.FloatField(default=None)),
                ('total_score', models.FloatField(default=None)),
                ('city', models.ForeignKey(to='master.City')),
                ('slum', models.ForeignKey(to='master.Slum')),
            ],
        ),
    ]
