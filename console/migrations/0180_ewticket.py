# Generated by Django 4.1.3 on 2023-02-08 11:58

import console.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0179_tmlist_description'),
    ]

    operations = [
        migrations.CreateModel(
            name='EWTicket',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('week_ending', models.DateField()),
                ('notes', models.CharField(max_length=2000, null=True)),
                ('category', models.CharField(max_length=50, validators=[console.models.validate_tm_category])),
                ('monday', models.DecimalField(decimal_places=2, max_digits=10, null=True)),
                ('tuesday', models.DecimalField(decimal_places=2, max_digits=10, null=True)),
                ('wednesday', models.DecimalField(decimal_places=2, max_digits=10, null=True)),
                ('thursday', models.DecimalField(decimal_places=2, max_digits=10, null=True)),
                ('friday', models.DecimalField(decimal_places=2, max_digits=10, null=True)),
                ('saturday', models.DecimalField(decimal_places=2, max_digits=10, null=True)),
                ('sunday', models.DecimalField(decimal_places=2, max_digits=10, null=True)),
                ('ot', models.BooleanField(default=False)),
                ('description', models.CharField(max_length=2000, null=True)),
                ('quantity', models.DecimalField(decimal_places=2, max_digits=10, null=True)),
                ('units', models.CharField(max_length=50, null=True)),
                ('change_order', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='console.changeorders')),
                ('employee', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='console.employees')),
                ('master', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='console.tmpricesmaster')),
            ],
        ),
    ]
