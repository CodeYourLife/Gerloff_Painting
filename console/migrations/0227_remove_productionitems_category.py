# Generated by Django 4.1.3 on 2023-03-19 17:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0226_productionvalues_description2'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='productionitems',
            name='category',
        ),
    ]