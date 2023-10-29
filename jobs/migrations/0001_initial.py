# Generated by Django 3.2.20 on 2023-09-29 13:09

from django.db import migrations, models
import django.db.models.deletion
import jobs.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('employees', '0001_initial'),
        ('equipment', '0001_initial'),
        ('changeorder', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClientEmployees',
            fields=[
                ('person_pk', models.BigAutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=250)),
                ('phone', models.CharField(blank=True, max_length=50, null=True)),
                ('email', models.EmailField(blank=True, max_length=254, null=True)),
                ('title', models.CharField(blank=True, max_length=250, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Clients',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('company', models.CharField(max_length=250, null=True)),
                ('bid_fax', models.CharField(blank=True, max_length=50, null=True)),
                ('bid_email', models.EmailField(blank=True, max_length=254, null=True)),
                ('vendor_code', models.CharField(blank=True, max_length=100, null=True)),
                ('address', models.CharField(max_length=100, null=True)),
                ('city', models.CharField(max_length=100, null=True)),
                ('state', models.CharField(max_length=100, null=True)),
                ('phone', models.CharField(max_length=50, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Estimates',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('to_number', models.IntegerField(default=0)),
                ('bid_date', models.DateField(blank=True, null=True)),
                ('take_off_name', models.CharField(max_length=2000, null=True)),
                ('estimator', models.CharField(max_length=250, null=True)),
                ('bidders', models.CharField(max_length=250, null=True)),
                ('has_docs_print', models.BooleanField(default=False)),
                ('comments', models.CharField(max_length=2000, null=True)),
                ('addenda', models.IntegerField(default=0)),
                ('site_visit_date', models.DateField(blank=True, null=True)),
                ('client_estimator_name', models.CharField(max_length=250, null=True)),
                ('client_estimator_email', models.EmailField(blank=True, max_length=254, null=True)),
                ('client_phone', models.CharField(max_length=50, null=True)),
                ('send_bids_to_email', models.EmailField(blank=True, max_length=254, null=True)),
                ('price', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ('job_number', models.CharField(max_length=50, null=True)),
                ('wage_rate_spray', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ('wate_rate_paint', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ('is_awarded_gc', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='JobNumbers',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('letter', models.CharField(max_length=1)),
                ('number', models.CharField(max_length=4)),
            ],
        ),
        migrations.CreateModel(
            name='Jobs',
            fields=[
                ('job_number', models.CharField(max_length=5, primary_key=True, serialize=False)),
                ('job_name', models.CharField(max_length=250, null=True)),
                ('estimator', models.CharField(max_length=50, null=True)),
                ('foreman', models.CharField(blank=True, max_length=50, null=True)),
                ('contract_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('po_number', models.CharField(blank=True, max_length=50, null=True)),
                ('retainage_percentage', models.CharField(blank=True, max_length=50, null=True)),
                ('is_t_m_job', models.BooleanField(default=False)),
                ('t_m_nte_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('status', models.CharField(max_length=50, null=True)),
                ('booked_date', models.DateField(blank=True, null=True)),
                ('booked_by', models.CharField(blank=True, max_length=50, null=True)),
                ('is_wage_scale', models.BooleanField(default=False)),
                ('is_davis_bacon_wages', models.BooleanField(default=False)),
                ('spray_scale', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('brush_role', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('address', models.CharField(max_length=50, null=True)),
                ('city', models.CharField(max_length=20, null=True)),
                ('state', models.CharField(max_length=2, null=True)),
                ('start_date', models.DateField(blank=True, null=True)),
                ('duration', models.CharField(blank=True, max_length=50, null=True)),
                ('estimate_number', models.CharField(blank=True, max_length=50, null=True)),
                ('estimate_price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('has_wallcovering', models.BooleanField(default=False)),
                ('has_paint', models.BooleanField(default=False)),
                ('has_owner_supplied_wallcovering', models.BooleanField(default=False)),
                ('painting_budget', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('wallcovering_budget', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('is_send_auto_co_emails', models.BooleanField(default=True)),
                ('is_send_auto_submittal_emails', models.BooleanField(default=True)),
                ('notes', models.CharField(blank=True, max_length=2000, null=True)),
                ('approved_change_orders', models.DecimalField(blank=True, decimal_places=4, max_digits=10, null=True)),
                ('final_bill_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('is_closed', models.BooleanField(default=False)),
                ('labor_done_Date', models.DateField(blank=True, null=True)),
                ('ar_closed_date', models.DateField(blank=True, null=True)),
                ('was_previously_closed', models.BooleanField(default=False)),
                ('previously_closed_date', models.DateField(blank=True, null=True)),
                ('cumulative_costs_at_closing', models.DecimalField(blank=True, decimal_places=2, max_digits=9, null=True)),
                ('contract_status', models.IntegerField()),
                ('insurance_status', models.IntegerField()),
                ('submittals_required', models.IntegerField(null=True)),
                ('has_special_paint', models.IntegerField(null=True)),
                ('client_Pm_Phone', models.CharField(blank=True, max_length=50, null=True)),
                ('client_Pm_Email', models.EmailField(blank=True, max_length=254, null=True)),
                ('client_Co_Email', models.EmailField(blank=True, max_length=254, null=True)),
                ('client_Submittal_Email', models.EmailField(blank=True, max_length=254, null=True)),
                ('client_Super_Phone', models.CharField(blank=True, max_length=50, null=True)),
                ('client_Super_Email', models.EmailField(blank=True, max_length=254, null=True)),
                ('is_on_base', models.BooleanField(default=False)),
                ('unsigned_tickets', models.IntegerField(blank=True, null=True)),
                ('assigned_inventory', models.IntegerField(blank=True, null=True)),
                ('assigned_rentals', models.IntegerField(blank=True, null=True)),
                ('is_bonded', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=False)),
                ('start_date_checked', models.DateField(blank=True, null=True)),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='Client', to='jobs.clients')),
                ('client_Co_Contact', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='CO', to='jobs.clientemployees')),
                ('client_Pm', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='PM', to='jobs.clientemployees')),
                ('client_Submittal_Contact', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='Submittals', to='jobs.clientemployees')),
                ('client_Super', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='Super', to='jobs.clientemployees')),
                ('superintendent', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='employees.employees')),
            ],
        ),
        migrations.CreateModel(
            name='Plans',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('job_number', models.CharField(max_length=10)),
                ('job_name', models.CharField(max_length=250, null=True)),
                ('description', models.CharField(max_length=2000, null=True)),
                ('estimates_number', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Orders',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('po_number', models.CharField(max_length=25)),
                ('description', models.CharField(max_length=2000)),
                ('date_ordered', models.DateField(blank=True, null=True)),
                ('partial_receipt', models.BooleanField(default=False)),
                ('notes', models.CharField(blank=True, max_length=2000, null=True)),
                ('job_number', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='jobs.jobs')),
                ('vendor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='equipment.vendors')),
            ],
        ),
        migrations.CreateModel(
            name='JobNotes',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('note', models.CharField(max_length=2000, null=True)),
                ('type', models.CharField(max_length=50, null=True, validators=[jobs.models.validate_job_notes])),
                ('user', models.CharField(max_length=50, null=True)),
                ('date', models.DateField(blank=True, null=True)),
                ('daily_employee_count', models.IntegerField(default=0)),
                ('note_date', models.DateField(blank=True, null=True)),
                ('job_number', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='jobs.jobs')),
            ],
        ),
        migrations.CreateModel(
            name='JobCharges',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('job', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='jobs.jobs')),
                ('master', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='changeorder.tmpricesmaster')),
            ],
        ),
        migrations.AddField(
            model_name='clientemployees',
            name='id',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='jobs.clients'),
        ),
        migrations.CreateModel(
            name='Checklist',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('category', models.CharField(max_length=1000, null=True)),
                ('checklist_item', models.CharField(max_length=2000, null=True)),
                ('is_closed', models.BooleanField(default=False)),
                ('notes', models.CharField(max_length=2500, null=True)),
                ('job_start_date_from_schedule', models.DateField(blank=True, null=True)),
                ('cop', models.BooleanField(default=False)),
                ('cop_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ('cop_sent_date', models.DateField(blank=True, null=True)),
                ('cop_number', models.IntegerField(default=0)),
                ('is_ewt', models.BooleanField(default=False)),
                ('ewt_date', models.DateField(blank=True, null=True)),
                ('is_submittal', models.BooleanField(default=False)),
                ('submittal_number', models.IntegerField(default=0)),
                ('submittal_description', models.CharField(max_length=2000, null=True)),
                ('submittal_date_sent', models.DateField(blank=True, null=True)),
                ('wallcovering_order_date', models.DateField(blank=True, null=True)),
                ('assigned', models.CharField(max_length=2000, null=True)),
                ('job_number', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='jobs.jobs')),
            ],
        ),
    ]