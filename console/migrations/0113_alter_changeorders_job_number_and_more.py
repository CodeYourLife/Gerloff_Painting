# Generated by Django 4.1.3 on 2022-12-11 23:51

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0112_alter_clientemployees_email_alter_clients_bid_email_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='changeorders',
            name='job_number',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='console.jobs'),
        ),
        migrations.AlterField(
            model_name='checklist',
            name='job_number',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='console.jobs'),
        ),
        migrations.AlterField(
            model_name='clientemployees',
            name='id',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='console.clients'),
        ),
        migrations.AlterField(
            model_name='inventory',
            name='inventory_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='console.inventorytype'),
        ),
        migrations.AlterField(
            model_name='inventory',
            name='job_number',
            field=models.ForeignKey(blank=True, on_delete=django.db.models.deletion.PROTECT, to='console.jobs'),
        ),
        migrations.AlterField(
            model_name='jobnotes',
            name='job_number',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='console.jobs'),
        ),
        migrations.AlterField(
            model_name='jobs',
            name='client',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='Client', to='console.clients'),
        ),
        migrations.AlterField(
            model_name='jobs',
            name='client_Co_Contact',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='CO', to='console.clientemployees'),
        ),
        migrations.AlterField(
            model_name='jobs',
            name='client_Pm',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='PM', to='console.clientemployees'),
        ),
        migrations.AlterField(
            model_name='jobs',
            name='client_Submittal_Contact',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='Submittals', to='console.clientemployees'),
        ),
        migrations.AlterField(
            model_name='jobs',
            name='client_Super',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='Super', to='console.clientemployees'),
        ),
        migrations.AlterField(
            model_name='jobs',
            name='superintendent',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='console.employees'),
        ),
        migrations.AlterField(
            model_name='orderitems',
            name='order',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='console.orders'),
        ),
        migrations.AlterField(
            model_name='orderitems',
            name='wallcovering',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='console.wallcovering'),
        ),
        migrations.AlterField(
            model_name='orders',
            name='job_number',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='console.jobs'),
        ),
        migrations.AlterField(
            model_name='orders',
            name='vendor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='console.vendors'),
        ),
        migrations.AlterField(
            model_name='outgoingitem',
            name='outgoing_event',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='console.outgoingwallcovering'),
        ),
        migrations.AlterField(
            model_name='outgoingitem',
            name='package',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='console.packages'),
        ),
        migrations.AlterField(
            model_name='outgoingwallcovering',
            name='job_number',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='console.jobs'),
        ),
        migrations.AlterField(
            model_name='packages',
            name='delivery',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='console.wallcoveringdelivery'),
        ),
        migrations.AlterField(
            model_name='packages',
            name='order_item1',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='order_item1', to='console.orderitems'),
        ),
        migrations.AlterField(
            model_name='packages',
            name='order_item2',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='order_item2', to='console.orderitems'),
        ),
        migrations.AlterField(
            model_name='packages',
            name='order_item3',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='order_item3', to='console.orderitems'),
        ),
        migrations.AlterField(
            model_name='packages',
            name='order_item4',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='order_item4', to='console.orderitems'),
        ),
        migrations.AlterField(
            model_name='packages',
            name='order_item5',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='order_item5', to='console.orderitems'),
        ),
        migrations.AlterField(
            model_name='rentals',
            name='company',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='console.vendors'),
        ),
        migrations.AlterField(
            model_name='rentals',
            name='job_number',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='console.jobs'),
        ),
        migrations.AlterField(
            model_name='subcontractitems',
            name='subcontract',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='console.subcontracts'),
        ),
        migrations.AlterField(
            model_name='subcontractitems',
            name='wallcovering_id',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='console.wallcovering'),
        ),
        migrations.AlterField(
            model_name='subcontracts',
            name='job_number',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='console.jobs'),
        ),
        migrations.AlterField(
            model_name='subcontracts',
            name='subcontractor',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='console.subcontractors'),
        ),
        migrations.AlterField(
            model_name='submittalitems',
            name='submittal',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='console.submittals'),
        ),
        migrations.AlterField(
            model_name='submittalitems',
            name='wallcovering_id',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='console.wallcovering'),
        ),
        migrations.AlterField(
            model_name='submittals',
            name='job_number',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='console.jobs'),
        ),
        migrations.AlterField(
            model_name='tmlist',
            name='change_order',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='console.changeorders'),
        ),
        migrations.AlterField(
            model_name='vendorcontact',
            name='company',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='console.vendors'),
        ),
        migrations.AlterField(
            model_name='vendors',
            name='category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='console.vendorcategory'),
        ),
        migrations.AlterField(
            model_name='wallcovering',
            name='job_number',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='console.jobs'),
        ),
        migrations.AlterField(
            model_name='wallcovering',
            name='vendor',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='console.vendors'),
        ),
        migrations.AlterField(
            model_name='wallcoveringdelivery',
            name='items',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='console.orderitems'),
        ),
        migrations.AlterField(
            model_name='wallcoveringdelivery',
            name='order',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='console.orders'),
        ),
    ]
