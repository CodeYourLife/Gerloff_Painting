# Generated by Django 4.1.3 on 2022-12-11 19:58

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0105_change_orders_is_approved'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='wallcovering_delivery',
            name='job_number',
        ),
    ]
