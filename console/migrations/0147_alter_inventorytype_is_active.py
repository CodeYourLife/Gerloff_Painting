# Generated by Django 4.1.3 on 2022-12-30 11:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0146_alter_inventorytype_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='inventorytype',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
    ]
