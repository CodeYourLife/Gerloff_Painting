# Generated by Django 4.1.3 on 2022-12-03 16:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0035_rename_approved_change_orers_jobs_approved_change_orders_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Job_Numbers',
            fields=[
                ('job_number', models.IntegerField(primary_key=True, serialize=False)),
            ],
        ),
    ]
