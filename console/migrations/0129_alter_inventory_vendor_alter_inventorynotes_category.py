# Generated by Django 4.1.3 on 2022-12-19 20:44

import console.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0128_remove_inventorynotes_service_vendor'),
    ]

    operations = [
        migrations.AlterField(
            model_name='inventory',
            name='vendor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='console.vendors'),
        ),
        migrations.AlterField(
            model_name='inventorynotes',
            name='category',
            field=models.CharField(max_length=2000, null=True, validators=[console.models.validate_inventory_notes]),
        ),
    ]
