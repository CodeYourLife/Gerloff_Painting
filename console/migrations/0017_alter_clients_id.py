# Generated by Django 4.1.3 on 2022-12-02 00:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0016_alter_clients_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='clients',
            name='id',
            field=models.BigAutoField(primary_key=True, serialize=False),
        ),
    ]
