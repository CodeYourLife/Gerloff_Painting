# Generated by Django 4.1.3 on 2023-02-07 01:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0176_subcontractnotes'),
    ]

    operations = [
        migrations.AddField(
            model_name='tmlist',
            name='notes',
            field=models.CharField(max_length=2000, null=True),
        ),
    ]
