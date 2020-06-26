# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
import jsonfield.fields
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('mastersheet', '0017_auto_20180910_1608'),
    ]

    operations = [
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('invoice_date', models.DateField(null=True, blank=True)),
                ('invoice_number', models.CharField(max_length=100, null=True, blank=True)),
                ('challan_number', models.CharField(max_length=100, null=True, blank=True)),
                ('created_on', models.DateTimeField(default=datetime.datetime.now)),
                ('modified_on', models.DateTimeField(default=datetime.datetime.now)),
                ('created_by', models.ForeignKey(related_name='invoice_created_by', to=settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING)),
                ('modified_by', models.ForeignKey(related_name='invoice_modified_by', to=settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING)),
                ('vendor', models.ForeignKey(to='mastersheet.Vendor', on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name': 'Invoice',
                'verbose_name_plural': 'Invoices',
            },
        ),
        migrations.CreateModel(
            name='InvoiceItems',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('household_numbers', jsonfield.fields.JSONField(null=True, blank=True)),
                ('quantity', models.FloatField(null=True, blank=True)),
                ('unit', models.CharField(blank=True, max_length=100, null=True, choices=[(b'1', b'Tempo/Piago'), (b'2', b'Bags'), (b'3', b'Nos')])),
                ('rate', models.FloatField(null=True, blank=True)),
                ('tax', models.FloatField(null=True, blank=True)),
                ('total', models.FloatField(null=True, blank=True)),
                ('created_on', models.DateTimeField(default=datetime.datetime.now)),
                ('modified_on', models.DateTimeField(default=datetime.datetime.now)),
                ('created_by', models.ForeignKey(related_name='invoiceitem_created_by', to=settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING)),
                ('invoice', models.ForeignKey(to='mastersheet.Invoice', on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name': 'Invoice item',
                'verbose_name_plural': 'Invoice items',
            },
        ),
        migrations.CreateModel(
            name='MaterialType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=512)),
                ('description', models.TextField(null=True, blank=True)),
                ('display_flag', models.BooleanField()),
                ('display_order', models.FloatField()),
                ('created_date', models.DateTimeField(default=datetime.datetime.now)),
            ],
            options={
                'verbose_name': 'Material Type',
                'verbose_name_plural': 'Material Types',
            },
        ),
        migrations.AddField(
            model_name='invoiceitems',
            name='material_type',
            field=models.ForeignKey(to='mastersheet.MaterialType', on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='invoiceitems',
            name='modified_by',
            field=models.ForeignKey(related_name='invoiceitem_modified_by', to=settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING),
        ),
        migrations.AddField(
            model_name='invoiceitems',
            name='slum',
            field=models.ForeignKey(to='master.Slum', on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='invoice',
            name='paid',
            field=models.BooleanField(default=False),
        ),
    ]
