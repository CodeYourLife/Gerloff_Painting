# Generated by Django 4.1.3 on 2023-02-09 02:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0186_alter_jobs_client_pm'),
    ]

    operations = [
        migrations.AlterField(
            model_name='clientemployees',
            name='title',
            field=models.CharField(blank=True, max_length=250, null=True),
        ),
    ]