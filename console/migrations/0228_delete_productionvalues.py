# Generated by Django 4.1.3 on 2023-03-19 17:49

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0227_remove_productionitems_category'),
    ]

    operations = [
        migrations.DeleteModel(
            name='ProductionValues',
        ),
    ]