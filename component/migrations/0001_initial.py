# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import jsonfield.fields
import django.contrib.gis.db.models.fields
from django.core.management import call_command

def loadfixture(apps, schema_editor):
    call_command('loaddata', 'initial_data.json')
    call_command('loaddata', 'filter_data.json')

class Migration(migrations.Migration):

    dependencies = [
        ('master', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Component',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('housenumber', models.CharField(max_length=5)),
                ('shape', django.contrib.gis.db.models.fields.GeometryField(srid=4326)),
            ],
            options={
                'verbose_name': 'Component',
                'verbose_name_plural': 'Components',
            },
        ),
        migrations.CreateModel(
            name='Fact',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('blob', jsonfield.fields.JSONField()),
            ],
            options={
                'verbose_name': 'Fact',
                'verbose_name_plural': 'Fact',
            },
        ),
        migrations.CreateModel(
            name='Metadata',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=2048)),
                ('level', models.CharField(max_length=1, choices=[(b'S', b'Slum'), (b'H', b'Household')])),
                ('type', models.CharField(max_length=1, choices=[(b'C', b'Component'), (b'F', b'Filter')])),
                ('display_type', models.CharField(max_length=1, choices=[(b'M', b'Map'), (b'T', b'Tabular')])),
                ('visible', models.BooleanField()),
                ('order', models.FloatField()),
                ('blob', jsonfield.fields.JSONField()),
                ('code', models.CharField(max_length=512, null=True, blank=True)),
            ],
            options={
                'verbose_name': 'Metadata',
                'verbose_name_plural': 'Metadata',
            },
        ),
        migrations.CreateModel(
            name='Section',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=2048)),
                ('order', models.FloatField()),
            ],
            options={
                'verbose_name': 'Section',
                'verbose_name_plural': 'Sections',
            },
        ),
        migrations.AddField(
            model_name='metadata',
            name='section',
            field=models.ForeignKey(to='component.Section', on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='fact',
            name='metadata',
            field=models.ForeignKey(to='component.Metadata', on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='fact',
            name='slum',
            field=models.ForeignKey(to='master.Slum', on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='component',
            name='metadata',
            field=models.ForeignKey(to='component.Metadata', on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='component',
            name='slum',
            field=models.ForeignKey(to='master.Slum', on_delete=models.CASCADE),
        ),
        migrations.RunPython(loadfixture),
    ]
