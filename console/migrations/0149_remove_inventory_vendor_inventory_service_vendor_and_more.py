# Generated by Django 4.1.3 on 2022-12-30 15:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0148_alter_inventoryitems2_type_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='inventory',
            name='vendor',
        ),
        migrations.AddField(
            model_name='inventory',
            name='service_vendor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='inventory2', to='console.vendors'),
        ),
        migrations.AlterField(
            model_name='inventory',
            name='purchased_from',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='inventory1', to='console.vendors'),
        ),
    ]
