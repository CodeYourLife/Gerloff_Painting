# Generated by Django 4.1.3 on 2022-12-02 00:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0022_alter_clients_id'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='clients',
            name='id',
        ),

    ]
