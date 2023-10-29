# Generated by Django 3.2.20 on 2023-10-29 18:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0003_alter_jobnotes_daily_employee_count'),
    ]

    operations = [
        migrations.AddField(
            model_name='jobs',
            name='closed_job_number',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='jobs',
            name='is_off_hours',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='jobs',
            name='is_work_order_done',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='jobs',
            name='man_hours_budgeted',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='jobs',
            name='man_hours_used',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='jobs',
            name='address',
            field=models.CharField(max_length=500, null=True),
        ),
    ]