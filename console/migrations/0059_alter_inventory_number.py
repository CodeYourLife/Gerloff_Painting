# Generated by Django 4.1.3 on 2022-12-05 16:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0058_alter_inventory_notes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='inventory',
            name='number',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
