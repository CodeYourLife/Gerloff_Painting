# Generated by Django 4.1.3 on 2023-03-10 13:58

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0213_inventory_assigned_to'),
    ]

    operations = [
        migrations.CreateModel(
            name='CertificationCategories',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('description', models.CharField(max_length=200, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Certifications',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('description', models.CharField(max_length=500, null=True)),
                ('date_received', models.DateField()),
                ('date_expires', models.DateField()),
                ('note', models.CharField(max_length=2000, null=True)),
                ('is_closed', models.BooleanField(default=False)),
                ('category', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='console.certificationcategories')),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='console.employees')),
                ('job', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='console.jobs')),
            ],
        ),
    ]
