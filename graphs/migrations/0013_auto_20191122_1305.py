# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

class Migration(migrations.Migration):

    dependencies = [
        ('graphs', '0012_auto_20191018_1606'),
    ]

    operations = [
        migrations.CreateModel(
            name='SlumCTBdataSplit',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True)),
                ('ctb_id', models.IntegerField(null=True)),
                ('electricity_in_ctb', models.TextField(null=True, blank=True)),
                ('sewage_disposal_system', models.TextField(null=True, blank=True)),
                ('ctb_available_at_night', models.TextField(null=True, blank=True)),
                ('cleanliness_of_the_ctb', models.TextField(null=True, blank=True)),
                ('ctb_cleaning_frequency', models.TextField(null=True, blank=True)),
                ('water_availability', models.TextField(null=True, blank=True)),
                ('water_supply_type', models.TextField(null=True, blank=True)),
                ('ctb_structure_condition', models.TextField(null=True, blank=True)),
                ('doors_in_good_condtn', models.TextField(null=True, blank=True)),
                ('seats_in_good_condtn', models.TextField(null=True, blank=True)),
                ('ctb_tank_capacity', models.TextField(null=True, blank=True)),
                ('cost_of_ctb_use', models.TextField(null=True, blank=True)),
                ('ctb_caretaker', models.TextField(null=True, blank=True)),
                ('ctb_for_child', models.TextField(null=True, blank=True)),
                ('cond_of_ctb_for_child', models.TextField(null=True, blank=True)),
                ('city', models.ForeignKey(to='master.City')),
                ('slum', models.ForeignKey(to='master.Slum')),
            ],
        ),
        migrations.CreateModel(
            name='SlumDataSplit',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('land_status', models.TextField(null=True, blank=True)),
                ('land_ownership', models.TextField(null=True, blank=True)),
                ('land_topography', models.TextField(null=True, blank=True)),
                ('availability_of_water', models.TextField(null=True, blank=True)),
                ('quality_of_water', models.TextField(null=True, blank=True)),
                ('coverage_of_water', models.TextField(null=True, blank=True)),
                ('alternative_source_of_water', models.TextField(null=True, blank=True)),
                ('community_dump_sites', models.TextField(null=True, blank=True)),
                ('dump_in_drains', models.TextField(null=True, blank=True)),
                ('number_of_waste_container', models.TextField(null=True, blank=True)),
                ('waste_coverage_by_mla_tempo', models.TextField(null=True, blank=True)),
                ('waste_coverage_door_to_door', models.TextField(null=True, blank=True)),
                ('waste_coverage_by_ghantagadi', models.TextField(null=True, blank=True)),
                ('waste_coverage_by_ulb_van', models.TextField(null=True, blank=True)),
                ('waste_coll_freq_by_mla_tempo', models.TextField(null=True, blank=True)),
                ('waste_coll_freq_door_to_door', models.TextField(null=True, blank=True)),
                ('waste_coll_freq_by_ghantagadi', models.TextField(null=True, blank=True)),
                ('waste_coll_freq_by_ulb_van', models.TextField(null=True, blank=True)),
                ('waste_coll_freq_by_garbage_bin', models.TextField(null=True, blank=True)),
                ('is_the_settlement_below_or_above', models.TextField(null=True, blank=True)),
                ('are_the_huts_below_or_above', models.TextField(null=True, blank=True)),
                ('point_of_vehicular_access', models.TextField(null=True, blank=True)),
                ('do_the_drains_get_blocked', models.TextField(null=True, blank=True)),
                ('is_the_drainage_gradient_adequ', models.TextField(null=True, blank=True)),
                ('do_gutters_flood', models.TextField(null=True, blank=True)),
                ('is_gutter_gradient_adequate', models.TextField(null=True, blank=True)),
                ('city', models.ForeignKey(to='master.City')),
                ('slum', models.ForeignKey(to='master.Slum')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='slumdatasplit',
            unique_together=set([('id', 'slum')]),
        ),
    ]
