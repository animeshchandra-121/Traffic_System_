# Generated by Django 5.1.5 on 2025-07-03 04:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('new_application', '0004_auto_20250702_2325'),
    ]

    operations = [
        migrations.AddField(
            model_name='congestionevent',
            name='color',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AddField(
            model_name='congestionevent',
            name='score',
            field=models.FloatField(default=0.0),
        ),
    ]
