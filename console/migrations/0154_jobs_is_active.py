# Generated by Django 4.1.3 on 2023-01-17 00:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0153_remove_wallcovering_packages_received_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='jobs',
            name='is_active',
            field=models.BooleanField(default=False),
        ),
    ]