# Generated by Django 4.1.3 on 2022-12-12 02:41

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0116_alter_packages_notes_alter_packages_unit_item1_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='subcontracts',
            old_name='PO_number',
            new_name='po_number',
        ),
    ]
