# Generated by Django 4.1.3 on 2022-12-01 19:02

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0008_clients_superintendent_clients_superintendent_email_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='clients',
            name='superintendent',
        ),
        migrations.RemoveField(
            model_name='clients',
            name='superintendent_email',
        ),
        migrations.RemoveField(
            model_name='clients',
            name='superintendent_phone',
        ),
    ]
