# Generated by Django 4.1.3 on 2022-12-11 15:55

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0103_remove_jobs_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='jobs',
            name='booked_by',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='jobs',
            name='client_Co_Email',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='jobs',
            name='client_Pm',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='PM', to='console.client_employees'),
        ),
        migrations.AlterField(
            model_name='jobs',
            name='client_Pm_Email',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='jobs',
            name='client_Pm_Phone',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='jobs',
            name='client_Submittal_Email',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='jobs',
            name='client_Super',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='Super', to='console.client_employees'),
        ),
        migrations.AlterField(
            model_name='jobs',
            name='client_Super_Email',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='jobs',
            name='client_Super_Phone',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='jobs',
            name='duration',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='jobs',
            name='estimate_number',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='jobs',
            name='foreman',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='jobs',
            name='notes',
            field=models.CharField(blank=True, max_length=2000, null=True),
        ),
        migrations.AlterField(
            model_name='jobs',
            name='po_number',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='jobs',
            name='retainage_percentage',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
