# Generated by Django 4.1.3 on 2022-12-11 14:12

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0088_alter_wallcovering_notes'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='subcontract_items',
            name='SOV_type',
        ),
    ]
