# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

def migrate_data(apps, schema_editor):
	
	vendortype = apps.get_model('mastersheet', 'VendorType')
	materialtype = apps.get_model('mastersheet', 'MaterialType')
	temp = []
	for i in vendortype.objects.all():
		temp.append(
				materialtype(name = i.name, description = i.description,  display_flag = i.display_flag, display_order = i.display_order, created_date = i.created_date)
			)
	materialtype.objects.bulk_create(temp)


# def migrate_data_1(apps, schema_editor):
	

class Migration(migrations.Migration):

    dependencies = [
        ('mastersheet', '0018_auto_20181003_1734'),
    ]

    operations = [
    	migrations.RunPython(migrate_data),
    	# migrations.RunPython(migrate_data_1)
    ]
