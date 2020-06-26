# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('mastersheet', '0002_auto_20180115_1455'),
    ]

    operations = [
        migrations.CreateModel(
            name='KoboDDSyncTrack',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('sync_date', models.DateTimeField()),
                ('created_on', models.DateTimeField(default=datetime.datetime.now)),
                ('created_by', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING)),
                ('slum', models.ForeignKey(to='master.Slum', on_delete=models.CASCADE)),
            ],
        ),
        migrations.AlterField(
            model_name='communitymobilization',
            name='activity_date',
            field=models.DateField(default=datetime.datetime.now),
        ),
        migrations.AlterField(
            model_name='toiletconstruction',
            name='agreement_date',
            field=models.DateField(default=datetime.datetime.now),
        ),
        migrations.AlterUniqueTogether(
            name='vendorhouseholdinvoicedetail',
            unique_together=set([('vendor', 'slum', 'invoice_number')]),
        ),
    ]
