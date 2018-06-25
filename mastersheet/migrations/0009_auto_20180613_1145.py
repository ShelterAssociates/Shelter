# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

def flood_material_shifted_to(app, schema_editor):
    TC = app.get_model("mastersheet", "ToiletConstruction")
    non_empty_fields = TC.objects.filter(material_shifted_to__isnull = False)
    for tc in non_empty_fields:
        tc.p1_material_shifted_to = tc.material_shifted_to
        tc.p2_material_shifted_to = tc.material_shifted_to
        tc.p3_material_shifted_to = tc.material_shifted_to
        tc.st_material_shifted_to = tc.material_shifted_to
        tc.save()


class Migration(migrations.Migration):

    dependencies = [
        ('mastersheet', '0008_auto_20180605_1553'),
    ]

    operations = [
        
        migrations.AddField(
            model_name='toiletconstruction',
            name='p1_material_shifted_to',
            field=models.CharField(max_length=5, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='toiletconstruction',
            name='p2_material_shifted_to',
            field=models.CharField(max_length=5, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='toiletconstruction',
            name='p3_material_shifted_to',
            field=models.CharField(max_length=5, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='toiletconstruction',
            name='st_material_shifted_to',
            field=models.CharField(max_length=5, null=True, blank=True),
        ),
        migrations.RunPython(flood_material_shifted_to),
        migrations.RemoveField(
            model_name='toiletconstruction',
            name='material_shifted_to',
        ),
    ]
