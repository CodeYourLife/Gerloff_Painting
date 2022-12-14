# Generated by Django 4.1.3 on 2022-12-11 13:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0078_remove_submittal_items_cop_primary_key_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='subcontract_items',
            name='SOV_amount',
        ),
        migrations.RemoveField(
            model_name='subcontractors',
            name='po_number',
        ),
        migrations.RemoveField(
            model_name='subcontractors',
            name='total_authorized',
        ),
        migrations.RemoveField(
            model_name='subcontractors',
            name='total_ordered',
        ),
        migrations.AddField(
            model_name='subcontract_items',
            name='SOV_quantity_to_date',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='subcontract_items',
            name='SOV_rate',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='subcontract_items',
            name='SOV_total',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='subcontract_items',
            name='SOV_total_authorized',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='subcontract_items',
            name='SOV_total_ordered',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='subcontract_items',
            name='SOV_type',
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='subcontract_items',
            name='SOV_unit',
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='subcontract_items',
            name='date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='subcontract_items',
            name='notes',
            field=models.CharField(max_length=2050, null=True),
        ),
        migrations.AddField(
            model_name='subcontracts',
            name='date',
            field=models.CharField(max_length=2050, null=True),
        ),
        migrations.AlterField(
            model_name='outgoing_wallcovering',
            name='date',
            field=models.CharField(max_length=2050, null=True),
        ),
        migrations.AlterField(
            model_name='wallcovering_delivery',
            name='date',
            field=models.CharField(max_length=2050, null=True),
        ),
    ]
