# Generated by Django 4.1.3 on 2022-12-15 18:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0120_changeorders_ticket_description_painterhours'),
    ]

    operations = [
        migrations.AddField(
            model_name='changeorders',
            name='materials_used',
            field=models.CharField(blank=True, max_length=2000, null=True),
        ),
    ]
