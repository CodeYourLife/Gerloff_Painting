# Generated by Django 4.1.3 on 2022-12-05 21:38

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0067_change_orders_is_closed'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='subcontractors',
            name='job_number',
        ),
    ]
