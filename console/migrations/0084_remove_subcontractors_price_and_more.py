# Generated by Django 4.1.3 on 2022-12-11 14:01

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0083_alter_rentals_off_rent_number'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='subcontractors',
            name='price',
        ),
        migrations.RemoveField(
            model_name='subcontractors',
            name='scope',
        ),
    ]
