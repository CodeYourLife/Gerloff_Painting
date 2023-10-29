# Generated by Django 3.2.20 on 2023-10-10 17:30

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('employees', '0002_initial'),
        ('jobs', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='jobs',
            name='special_paint_needed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='jobs',
            name='submittals_needed',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='clients',
            name='address',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='clients',
            name='city',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='clients',
            name='phone',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='clients',
            name='state',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='jobs',
            name='client_Co_Contact',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='CO', to='jobs.clientemployees'),
        ),
        migrations.AlterField(
            model_name='jobs',
            name='client_Submittal_Contact',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='Submittals', to='jobs.clientemployees'),
        ),
        migrations.AlterField(
            model_name='jobs',
            name='estimator',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='estimator', to='employees.employees'),
        ),
        migrations.AlterField(
            model_name='jobs',
            name='foreman',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='foreman', to='employees.employees'),
        ),
        migrations.AlterField(
            model_name='jobs',
            name='has_special_paint',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='jobs',
            name='submittals_required',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='jobs',
            name='superintendent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='superintendent', to='employees.employees'),
        ),
    ]
