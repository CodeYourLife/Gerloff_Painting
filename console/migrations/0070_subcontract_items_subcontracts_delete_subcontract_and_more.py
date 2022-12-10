# Generated by Django 4.1.3 on 2022-12-05 22:02

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0069_remove_subcontractors_wallcovering_id_subcontract'),
    ]

    operations = [
        migrations.CreateModel(
            name='Subcontract_Items',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('SOV_description', models.CharField(max_length=250, null=True)),
                ('SOV_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('is_closed', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Subcontracts',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('PO_number', models.CharField(max_length=250, null=True)),
                ('total_price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('description', models.CharField(max_length=250, null=True)),
                ('job_number', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='console.jobs')),
                ('subcontractor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='console.subcontractors')),
            ],
        ),
        migrations.DeleteModel(
            name='Subcontract',
        ),
        migrations.AddField(
            model_name='subcontract_items',
            name='subcontract',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='console.subcontracts'),
        ),
        migrations.AddField(
            model_name='subcontract_items',
            name='wallcovering_id',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='console.wallcovering'),
        ),
    ]
