# Generated by Django 4.1.3 on 2023-01-22 13:02

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0168_subcontracts_is_closed'),
    ]

    operations = [
        migrations.RenameField(
            model_name='subcontractors',
            old_name='subcontractor',
            new_name='company',
        ),
        migrations.AlterField(
            model_name='subcontracts',
            name='subcontractor',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='subcontract', to='console.subcontractors'),
        ),
    ]
