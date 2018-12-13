# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mastersheet', '0021_invoice_total'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='final_total',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='invoice',
            name='loading_unloading_charges',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='invoice',
            name='roundoff',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='invoice',
            name='transport_charges',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='invoiceitems',
            name='phase',
            field=models.CharField(blank=True, max_length=2, null=True, choices=[(b'1', b'Phase One'), (b'2', b'Phase Two'), (b'3', b'Phase Three')]),
        ),
    ]
