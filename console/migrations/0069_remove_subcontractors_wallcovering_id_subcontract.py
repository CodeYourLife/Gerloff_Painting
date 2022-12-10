# Generated by Django 4.1.3 on 2022-12-05 21:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0068_remove_subcontractors_job_number'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='subcontractors',
            name='wallcovering_id',
        ),
        migrations.CreateModel(
            name='Subcontract',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('PO_number', models.CharField(max_length=250, null=True)),
                ('total_price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('description', models.CharField(max_length=250, null=True)),
                ('SOV1_description', models.CharField(max_length=250, null=True)),
                ('SOV1_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('SOV2_description', models.CharField(max_length=250, null=True)),
                ('SOV2_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('SOV3_description', models.CharField(max_length=250, null=True)),
                ('SOV3_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('SOV4_description', models.CharField(max_length=250, null=True)),
                ('SOV4_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('SOV5_description', models.CharField(max_length=250, null=True)),
                ('SOV5_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('SOV6_description', models.CharField(max_length=250, null=True)),
                ('SOV6_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('SOV7_description', models.CharField(max_length=250, null=True)),
                ('SOV7_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('job_number', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='console.jobs')),
                ('subcontractor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='console.subcontractors')),
                ('wallcovering_id', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='console.wallcovering')),
            ],
        ),
    ]
