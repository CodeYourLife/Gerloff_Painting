# Generated by Django 4.1.3 on 2022-12-04 12:42

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0041_alter_jobs_contract_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='checklist',
            name='job_number',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='console.jobs'),
        ),
    ]
