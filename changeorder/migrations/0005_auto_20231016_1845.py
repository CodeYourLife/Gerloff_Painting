# Generated by Django 3.2.20 on 2023-10-16 18:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('changeorder', '0004_auto_20231010_2003'),
    ]

    operations = [
        migrations.AddField(
            model_name='signature',
            name='date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='signature',
            name='notes',
            field=models.CharField(blank=True, max_length=1000, null=True),
        ),
    ]