# Generated by Django 4.1.3 on 2022-12-11 23:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0110_tmpricesmaster_rename_change_orders_changeorders_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='changeorders',
            name='date_approved',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='changeorders',
            name='date_sent',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='changeorders',
            name='date_signed',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='checklist',
            name='cop_sent_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='checklist',
            name='ewt_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='checklist',
            name='job_start_date_from_schedule',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='checklist',
            name='submittal_date_sent',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='checklist',
            name='wallcovering_order_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='estimates',
            name='bid_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='estimates',
            name='site_visit_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='inventory',
            name='date_out',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='inventory',
            name='date_returned',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='inventory',
            name='purchase_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='jobnotes',
            name='date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='jobnotes',
            name='note_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='jobs',
            name='ar_closed_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='jobs',
            name='booked_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='jobs',
            name='labor_done_Date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='jobs',
            name='previously_closed_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='jobs',
            name='start_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='orders',
            name='date_ordered',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='outgoingwallcovering',
            name='date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='rentals',
            name='off_rent_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='rentals',
            name='on_rent_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='subcontractitems',
            name='date',
            field=models.DateField(),
        ),
        migrations.AlterField(
            model_name='subcontracts',
            name='date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='submittals',
            name='date_returned',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='submittals',
            name='date_sent',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='wallcovering',
            name='pricing1_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='wallcoveringdelivery',
            name='date',
            field=models.DateField(blank=True, null=True),
        ),
    ]
