# Generated by Django 4.1.3 on 2022-12-04 22:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0050_alter_jobs_contract_amount_alter_jobs_superintendent'),
    ]

    operations = [
        migrations.AlterField(
            model_name='jobs',
            name='painting_budget',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='jobs',
            name='wallcovering_budget',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
    ]
