# Generated by Django 4.1.3 on 2023-01-17 18:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0155_alter_jobnotes_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='jobs',
            name='start_date_checked',
            field=models.DateField(blank=True, null=True),
        ),
    ]