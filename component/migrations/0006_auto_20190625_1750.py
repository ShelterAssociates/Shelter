# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from component.models import Component
from master.models import Slum, City

def updatefixture(apps, schema_editor):
    components = Component.objects.all()
    for component in components:
        component.object_id = component.slum_id
        component.save()

class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('component', '0005_auto_20180702_1858'),
    ]

    operations = [
        migrations.AlterField(
            model_name='metadata',
            name='level',
            field=models.CharField(max_length=1, choices=[(b'C', b'City'), (b'S', b'Slum'), (b'H', b'Household')]),
        ),
        migrations.RemoveField(
            model_name='fact',
            name='metadata',
        ),
        migrations.RemoveField(
            model_name='fact',
            name='slum',
        ),
        migrations.AddField(
            model_name='component',
            name='content_type',
            field=models.ForeignKey(default=12, to='contenttypes.ContentType', on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='component',
            name='object_id',
            field=models.PositiveIntegerField(default=0),
            preserve_default=False,
        ),
        migrations.DeleteModel(
            name='Fact',
        ),
        migrations.RunPython(updatefixture),
        # migrations.RemoveField(
        #     model_name='component',
        #     name='slum',
        # ),
    ]
