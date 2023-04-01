# Generated by Django 4.1.3 on 2023-03-10 17:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0217_alter_employees_level_alter_employees_nickname_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='metricassessment',
            name='job',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='console.jobs'),
        ),
        migrations.AlterField(
            model_name='metricassessment',
            name='note',
            field=models.CharField(blank=True, max_length=2000, null=True),
        ),
    ]