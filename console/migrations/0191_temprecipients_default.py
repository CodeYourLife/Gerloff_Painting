# Generated by Django 4.1.3 on 2023-02-09 13:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0190_temprecipients_changeorder'),
    ]

    operations = [
        migrations.AddField(
            model_name='temprecipients',
            name='default',
            field=models.BooleanField(default=False),
        ),
    ]
