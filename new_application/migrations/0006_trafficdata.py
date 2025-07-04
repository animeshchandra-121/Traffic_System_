# Generated by Django 5.1.5 on 2025-07-03 10:30

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('new_application', '0005_congestionevent_color_congestionevent_score'),
    ]

    operations = [
        migrations.CreateModel(
            name='TrafficData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('vehicle_count', models.IntegerField(default=0, help_text='Total vehicles detected')),
                ('traffic_weight', models.FloatField(default=0.0, help_text='Calculated traffic weight/density')),
                ('green_time', models.IntegerField(blank=True, help_text='Green time of the signal at the moment of this snapshot', null=True)),
                ('auto_count', models.IntegerField(default=0)),
                ('bike_count', models.IntegerField(default=0)),
                ('bus_count', models.IntegerField(default=0)),
                ('car_count', models.IntegerField(default=0)),
                ('emergency_vehicles_count', models.IntegerField(default=0)),
                ('truck_count', models.IntegerField(default=0)),
                ('vehicle_type_counts_json', models.JSONField(default=dict, help_text='JSON representation of all vehicle type counts')),
                ('signal', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='data_snapshots', to='new_application.trafficsignal')),
            ],
            options={
                'verbose_name': 'Traffic Data Snapshot',
                'verbose_name_plural': 'Traffic Data Snapshots',
                'db_table': 'traffic_data',
                'ordering': ['-timestamp'],
            },
        ),
    ]
