# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import jsonfield

class Migration(migrations.Migration):

    dependencies = [
        ('mastersheet', '0019_auto_20181003_1809'),
    ]

    operations = [
        
        migrations.AlterField(
            model_name='invoiceitems',
            name='quantity',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='invoiceitems',
            name='rate',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='invoiceitems',
            name='tax',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='invoiceitems',
            name='total',
            field=models.FloatField(default=0),
        ),
        
        migrations.RemoveField(
            model_name='vendor',
            name='vendor_type',
        ),
        migrations.AlterField(
            model_name='invoiceitems',
            name='household_numbers',
            field=jsonfield.fields.JSONField(default=[]),
            preserve_default=False,
        ),
        migrations.AlterUniqueTogether(
            name='invoice',
            unique_together=set([('vendor', 'invoice_number')]),
        )
    ]
