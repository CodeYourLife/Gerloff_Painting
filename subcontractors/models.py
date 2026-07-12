from django.db import models
from jobs.models import *
from wallcovering.models import Wallcovering
import employees.models
from datetime import date
import datetime
from employees.models import *

class Subcontractors(models.Model):
    id = models.BigAutoField(primary_key=True)
    company = models.CharField(null=True, max_length=250)
    contact = models.CharField(null=True, max_length=250, blank=True)
    phone = models.CharField(null=True, max_length=20, blank=True)
    email = models.EmailField(null=True, blank=True)
    insurance_expire_date = models.DateField(blank=True, null=True)
    is_signed_labor_agreement = models.BooleanField(default=False)
    notes = models.CharField(null=True, max_length=2000, blank=True)
    is_inactive = models.BooleanField(default=False)
    username = models.CharField(null=True, max_length=100, blank=True)
    password = models.CharField(null=True, max_length=100, blank=True)
    pin = models.IntegerField(null=True, blank=True)
    has_workers_comp = models.BooleanField(default=False)
    has_auto_insurance = models.BooleanField(default=False)
    has_business_license = models.BooleanField(default=False)
    business_license_expiration_date = models.DateField(blank=True, null=True)
    has_w9_form = models.BooleanField(default=False)
    w9_form_date = models.DateField(blank=True, null=True)
    is_toolbox_required = models.BooleanField(default=True)


    def __str__(self):
        return f"{self.company}"

    def active_contracts(self):
        # used one time in subcontractor_home
        totalquantity = 0
        for x in Subcontracts.objects.filter(subcontractor=self, is_closed=False):
            totalquantity = totalquantity + 1
        return totalquantity

    def pending_invoices(self):
        #used one time in subcontractor_home
        totalquantity = 0
        for x in SubcontractorInvoice.objects.filter(subcontract__subcontractor=self, is_sent=False):
            totalquantity = totalquantity + 1
        return totalquantity

    def needs_payment(self):
        #used in new_subcontractor_payment
        if SubcontractorInvoice.objects.filter(subcontract__subcontractor=self, is_sent=True, processed=False).exists():
            return True
        else:
            return False


class Subcontracts(models.Model):
    id = models.BigAutoField(primary_key=True)
    job_number = models.ForeignKey('jobs.Jobs', on_delete=models.PROTECT)
    subcontractor = models.ForeignKey(
        Subcontractors, on_delete=models.PROTECT, related_name="subcontract")
    po_number = models.CharField(null=True, max_length=250, blank=True)
    total_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)  # DONT USE
    notes = models.CharField(null=True, max_length=2000, blank=True)
    date = models.DateField(null=True, blank=True)
    is_closed = models.BooleanField(default=False)
    is_retainage = models.BooleanField(default=True)
    retainage_percentage = models.DecimalField(
        max_digits=4, decimal_places=2, blank=True, null=True)
    is_certified_payroll_email_sent = models.BooleanField(default=False)
    is_entire_paint_job = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.subcontractor} {self.job_number}"

    def original_request(self):
        today = datetime.date.today()
        this_friday = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=4)
        last_friday = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=4) - datetime.timedelta(days=7)
        if today.weekday() > 4:
            this_friday += datetime.timedelta(days=7)
            last_friday += datetime.timedelta(days=7)
        total = 0
        # for x in SubcontractorInvoice.objects.filter(subcontract=self, date__gt=last_friday, date__lte=this_friday):
        #     total += x.original_amount
            #changing this to include all prior invoices if they weren't paid
        for x in SubcontractorInvoice.objects.filter(subcontract=self):
            if last_friday < x.date <= this_friday:
                if x.original_amount:total += x.original_amount
                else: total += 0
            elif not x.processed:
                if x.original_amount: total += x.original_amount
                else: total += 0
        return total

    def original_retainage_request(self):
        today = datetime.date.today()
        this_friday = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=4)
        last_friday = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=4) - datetime.timedelta(days=7)
        if today.weekday() > 4:
            this_friday += datetime.timedelta(days=7)
            last_friday += datetime.timedelta(days=7)
        total = 0
        for x in SubcontractorInvoice.objects.filter(subcontract=self):
        # for x in SubcontractorInvoice.objects.filter(subcontract=self, date__gt=last_friday, date__lte=this_friday):
            if last_friday < x.date <= this_friday:
                if x.original_retainage_amount:
                    total += x.original_retainage_amount
                else:
                    if x.retainage:
                        total += x.retainage
            elif not x.processed:
                if x.original_retainage_amount:
                    total += x.original_retainage_amount
                else:
                    if x.retainage:
                        total += x.retainage
        return total

    def is_approved_this_week(self):
        approved=False
        today = datetime.date.today()
        this_friday = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=4)
        last_friday = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=4) - datetime.timedelta(days=7)
        if today.weekday() > 4:
            this_friday += datetime.timedelta(days=7)
            last_friday += datetime.timedelta(days=7)
        for x in SubcontractorInvoice.objects.filter(subcontract=self):
            if last_friday < x.date <= this_friday:
                if x.is_sent:
                    approved=True
            elif not x.processed:
                if x.is_sent:
                    approved = True
        return approved

    def is_invoiced_this_week(self):
        approved=False
        today = datetime.date.today()
        this_friday = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=4)
        last_friday = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=4) - datetime.timedelta(days=7)
        if today.weekday() > 4:
            this_friday += datetime.timedelta(days=7)
            last_friday += datetime.timedelta(days=7)
        for x in SubcontractorInvoice.objects.filter(subcontract=self):
            if last_friday < x.date <= this_friday:
                approved=True
            elif not x.processed:
                approved = True
        return approved

    def amount_this_week(self):
        today = datetime.date.today()
        this_friday = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=4)
        last_friday = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=4) - datetime.timedelta(days=7)
        if today.weekday() > 4:
            this_friday += datetime.timedelta(days=7)
            last_friday += datetime.timedelta(days=7)
        total = 0
        for x in SubcontractorInvoice.objects.filter(subcontract=self, is_sent=True):
            if last_friday < x.date <= this_friday:
                if x.final_amount:
                    total += x.final_amount
            elif not x.processed:
                if x.final_amount:
                    total += x.final_amount
        # for x in SubcontractorInvoice.objects.filter(subcontract=self, date__gt=last_friday, date__lte=this_friday, is_sent=True):
        #     total += x.final_amount
        return total

    def retainage_this_week(self):
        today = datetime.date.today()
        this_friday = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=4)
        last_friday = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=4) - datetime.timedelta(days=7)
        if today.weekday() > 4:
            this_friday += datetime.timedelta(days=7)
            last_friday += datetime.timedelta(days=7)
        total = 0
        for x in SubcontractorInvoice.objects.filter(subcontract=self, is_sent=True):
            if last_friday < x.date <= this_friday:
                if x.retainage:
                    total += x.retainage
            elif not x.processed:
                if x.retainage:
                    total += x.retainage
        # for x in SubcontractorInvoice.objects.filter(subcontract=self, date__gt=last_friday, date__lte=this_friday, is_sent=True):
        #     total += x.retainage
        return total

    def pay_amount_this_week(self):
        today = datetime.date.today()
        this_friday = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=4)
        last_friday = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=4) - datetime.timedelta(days=7)
        if today.weekday() > 4:
            this_friday += datetime.timedelta(days=7)
            last_friday += datetime.timedelta(days=7)
        total = 0
        for x in SubcontractorInvoice.objects.filter(subcontract=self, is_sent=True):
            if last_friday < x.date <= this_friday:
                if x.final_amount:
                    if x.retainage:
                        total += x.final_amount - x.retainage
                    else:
                        total += x.final_amount
            elif not x.processed:
                if x.final_amount:
                    if x.retainage:
                        total += x.final_amount - x.retainage
                    else:
                        total += x.final_amount
        # for x in SubcontractorInvoice.objects.filter(subcontract=self, date__gt=last_friday, date__lte=this_friday, is_sent=True):
        #     total += x.final_amount - x.retainage
        return total

    def total_pending_amount(self):
        total = 0
        for x in SubcontractorInvoice.objects.filter(subcontract=self, is_sent=False):
            if x.final_amount:
                total = total + x.final_amount
        return total

    def total_billed(self):
        #used in subcontract.
        total = 0
        # for x in SubcontractorInvoice.objects.filter(subcontract=self, is_sent=True):
        for x in SubcontractorInvoice.objects.filter(subcontract=self):
            if x.final_amount:
                total = total + x.final_amount
        return total

    def total_approved(self):
        #joe added this 5.21.24. Only used in one place - in subcontract home (used in the summar bottom of page)
        total = 0
        # for x in SubcontractorInvoice.objects.filter(subcontract=self, is_sent=True):
        for x in SubcontractorInvoice.objects.filter(subcontract=self, is_sent=True):
            if x.final_amount:
                total = total + x.final_amount
        return total


    def total_paid(self):
        total = 0
        for x in SubcontractorInvoice.objects.filter(subcontract=self, is_sent=True):
            if x.final_amount:
                if x.retainage:
                    total += x.final_amount - x.retainage
                else:
                    total += x.final_amount
        return total

    def total_actually_paid(self):
        total = 0
        for x in SubcontractorInvoice.objects.filter(subcontract=self, processed=True):
            if x.final_amount:
                if x.retainage:
                    total += x.final_amount - x.retainage
                else:
                    total += x.final_amount
        return total

    def total_billed_prior(self):
        #saturday thru friday
        today = datetime.date.today()
        this_friday = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=4)
        last_friday = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=4) - datetime.timedelta(days=7)
        if today.weekday() > 4:
            this_friday += datetime.timedelta(days=7)
            last_friday += datetime.timedelta(days=7)
        total = 0
        for x in SubcontractorInvoice.objects.filter(subcontract=self, processed=True, date__lte=last_friday):
            if x.final_amount:
                total = total + x.final_amount
        return total

    def total_retainage(self):
        #portal invoice new - used if you do a retainage release
        total = 0
        for x in SubcontractorInvoice.objects.filter(subcontract=self):
            if x.retainage:
                total = total + x.retainage
        return total


    def total_retainage_approved(self):
        #portal invoice new - used if you do a retainage release
        total = 0
        for x in SubcontractorInvoice.objects.filter(subcontract=self, is_sent=True):
            if x.retainage:
                total = total + x.retainage
        return total

    def total_retainage_paid(self):
        #used when showing total retainage in the payments section
        total = 0
        for x in SubcontractorInvoice.objects.filter(subcontract=self, payment__isnull=False):
            if x.retainage:
                total = total + x.retainage
        return total


    def total_retainage_prior(self):
        #saturday thru friday
        today = datetime.date.today()
        this_friday = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=4)
        last_friday = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=4) - datetime.timedelta(days=7)
        if today.weekday() > 4:
            this_friday += datetime.timedelta(days=7)
            last_friday += datetime.timedelta(days=7)
        total = 0
        for x in SubcontractorInvoice.objects.filter(subcontract=self, processed=True, date__lte=last_friday):
            if x.retainage:
                total = total + x.retainage
        return total

    def total_retainage_pending(self):
        total = 0
        for x in SubcontractorInvoice.objects.filter(subcontract=self, is_sent=False):
            if x.retainage:
                total = total + x.retainage
        return total

    def total_contract_amount(self):
        total = 0
        for x in SubcontractItems.objects.filter(subcontract=self, is_approved=True):
            if x.total_cost():
                total += x.total_cost()
        return total

    def percent_complete(self):
        if self.total_contract_amount() != 0:
            return self.total_billed() / self.total_contract_amount()
        else:
            return 0
    def invoice_pending(self):
        if SubcontractorInvoice.objects.filter(subcontract=self, is_sent=False).exists():
            return True
        else:
            return False

    def invoice_ready(self):
        if SubcontractorInvoice.objects.filter(subcontract=self, is_sent=True).exists():
            for x in SubcontractorInvoice.objects.filter(subcontract=self, is_sent=True):
                if x.pay_date >= date.today():
                    return True
            return False
        else:
            return False

    def needs_paid(self):
        if SubcontractorInvoice.objects.filter(subcontract=self, is_sent=True, processed=False).exists():
            return True
        else:
            return False




class SubcontractItems(models.Model):
    id = models.BigAutoField(primary_key=True)
    subcontract = models.ForeignKey(Subcontracts, on_delete=models.PROTECT)
    is_closed = models.BooleanField(default=False)
    wallcovering_id = models.ForeignKey(
        Wallcovering, on_delete=models.PROTECT, null=True, blank=True)
    SOV_description = models.CharField(
        null=True, max_length=250)  # install WC1
    # $1,050 - NOT USING THIS RIGHT NOW
    SOV_total = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    SOV_is_lump_sum = models.BooleanField(default=False)
    # yards, SF, hour, lump sum
    SOV_unit = models.CharField(null=True, max_length=50)
    # 1,000 yards.  $15,000 if lump sum.
    SOV_total_ordered = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    SOV_total_authorized = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)  # not used right now
    SOV_quantity_to_date = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)  # not used right now
    # if lump sum, this is the same as total_ordered
    SOV_rate = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    notes = models.CharField(null=True, max_length=2050, blank=True)
    date = models.DateField()
    is_approved = models.BooleanField(default=True)
    change_order = models.ForeignKey(
        ChangeOrders, on_delete=models.PROTECT, null=True, blank=True)

    def __str__(self):
        return f"{self.subcontract} {self.SOV_description}"

    def total_cost(self):
        totalcost = 0
        if self.SOV_is_lump_sum == True:
            totalcost = self.SOV_rate
        else:
            totalcost = self.SOV_total_ordered * self.SOV_rate
        return totalcost

    def quantity_billed(self):  # this will either be yards billed, or % of total
        totalcost = float(0.00)
        for x in SubcontractorInvoiceItem.objects.filter(sov_item=self, invoice__is_sent=True):
            totalcost = float(totalcost) + float(x.quantity)
        if self.SOV_is_lump_sum == True:
            if float(self.SOV_rate) == 0:
                totalcost = 0
            else:
                totalcost = float(totalcost) / float(self.SOV_rate)
        return totalcost

    def total_billed(self):
        #subcontractor invoice new and portal invoice new
        totalcost = 0
        for x in SubcontractorInvoiceItem.objects.filter(sov_item=self, invoice__is_sent=True):
            totalcost = totalcost + x.quantity
        if self.SOV_is_lump_sum == False:
            totalcost = totalcost * self.SOV_rate
        return totalcost

    def total_billed_and_pending(self):
        totalcost = 0
        for x in SubcontractorInvoiceItem.objects.filter(sov_item=self):
            totalcost = totalcost + x.quantity
        if self.SOV_is_lump_sum == False:
            totalcost = totalcost * self.SOV_rate
        return totalcost

    def quantity_billed_and_pending(self):
        #1
        totalcost = 0
        for x in SubcontractorInvoiceItem.objects.filter(sov_item=self):
            totalcost = float(totalcost) + float(x.quantity)
        if self.SOV_is_lump_sum == True:
            if float(self.SOV_rate) == 0:
                totalcost = 0
            else:
                totalcost = float(totalcost) / float(self.SOV_rate)
        return totalcost


class SubcontractorPayments(models.Model):
    id = models.BigAutoField(primary_key=True)
    date = models.DateField()
    check_number = models.CharField(
        null=True, max_length=2000, blank=True)
    notes = models.CharField(
        null=True, max_length=2000, blank=True)
    final_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True)
    subcontractor = models.ForeignKey(
        Subcontractors, on_delete=models.PROTECT, related_name="payment")

    def __str__(self):
        return f"{self.subcontractor} {self.date} {self.check_number}"

class SubcontractorInvoice(models.Model):
    id = models.BigAutoField(primary_key=True)
    date = models.DateField()
    pay_app_number = models.IntegerField(default=0)
    subcontract = models.ForeignKey(
        Subcontracts, on_delete=models.PROTECT, related_name="invoice")
    retainage = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    final_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True)
    is_sent = models.BooleanField(default=False)  # everyone has approved
    processed = models.BooleanField(default=False)  # check has been cut
    pay_date = models.DateField(null=True, blank=True)
    notes = models.CharField(
        null=True, max_length=2000, blank=True)  # DONT USE
    payment = models.ForeignKey(
        SubcontractorPayments, on_delete=models.PROTECT, related_name="invoice2",null=True, blank=True)
    release_retainage = models.DecimalField(max_digits=10, decimal_places=2,null=True, blank=True)
    is_release_retainage = models.BooleanField(default=False)
    retainage_note = models.CharField(
        null=True, max_length=2000, blank=True)
    original_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    original_retainage_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    def __str__(self):
        return f"{self.subcontract} {self.pay_app_number}"

    def approvals_needed(self):
        total = 0
        if InvoiceApprovals.objects.filter(invoice=self, is_approved=False).exists():
            return InvoiceApprovals.objects.filter(invoice=self, is_approved=False).count()
        else:
            return 0


class SubcontractorInvoiceItem(models.Model):
    id = models.BigAutoField(primary_key=True)
    invoice = models.ForeignKey(
        SubcontractorInvoice, on_delete=models.PROTECT, related_name="invoice_item")
    sov_item = models.ForeignKey(
        SubcontractItems, on_delete=models.PROTECT, related_name="invoice_item2")
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.CharField(null=True, max_length=2000, blank=True)

    def __str__(self):
        return f"{self.invoice} {self.sov_item}"

    def total_cost(self):
        totalcost = 0
        if self.sov_item.SOV_is_lump_sum == False:
            totalcost = self.quantity * self.sov_item.SOV_rate
        else:
            totalcost = self.quantity
        return totalcost


class SubcontractorOriginalInvoiceItem(models.Model):
    id = models.BigAutoField(primary_key=True)
    invoice = models.ForeignKey(
        SubcontractorInvoice, on_delete=models.PROTECT, related_name="original_invoice_item")
    sov_item = models.ForeignKey(
        SubcontractItems, on_delete=models.PROTECT, related_name="original_invoice_item2")
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.CharField(null=True, max_length=2000, blank=True)

    def __str__(self):
        return f"{self.invoice} {self.sov_item}"

    def total_cost(self):
        totalcost = 0
        if self.sov_item.SOV_is_lump_sum == False:
            totalcost = self.quantity * self.sov_item.SOV_rate
        else:
            totalcost = self.quantity
        return totalcost

class SubcontractNotes(models.Model):
    id = models.BigAutoField(primary_key=True)
    subcontract = models.ForeignKey(
        Subcontracts, on_delete=models.PROTECT, related_name="subcontract_notes")
    date = models.DateField(null=True, blank=True)
    user = models.ForeignKey(employees.models.Employees, on_delete=models.PROTECT)
    note = models.CharField(null=True, max_length=2000)
    invoice = models.ForeignKey(SubcontractorInvoice, null=True,
                                on_delete=models.PROTECT, related_name="subcontract_notes2")


class InvoiceApprovals(models.Model):
    id = models.BigAutoField(primary_key=True)
    employee = models.ForeignKey(employees.models.Employees, on_delete=models.PROTECT)
    invoice = models.ForeignKey(SubcontractorInvoice, on_delete=models.PROTECT, related_name="approver")
    date = models.DateField(null=True, blank=True)
    is_reviewed = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    made_changes = models.BooleanField(default=False)
    notes = models.CharField(null=True, max_length=2000, blank=True)

    def __str__(self):
        return f"{self.invoice} {self.employee}"


class InvoiceBatch(models.Model):
    id = models.BigAutoField(primary_key=True)
    invoice = models.ForeignKey(SubcontractorInvoice, null=True,
                                on_delete=models.PROTECT, related_name="batch")


class PurchaseOrderNumber(models.Model):
    id = models.BigAutoField(primary_key=True)
    next_po_number = models.IntegerField(default=0)

class Weekly_Approvals(models.Model):
    id = models.BigAutoField(primary_key=True)
    Monday = models.DateField()
    invoices_entered = models.BooleanField(default=False)
    date_invoices_entered = models.DateField(null=True, blank=True)
    notes = models.CharField(null=True, max_length=2000, blank=True)
    victor_email_sent = models.BooleanField(default=False)
    gene_email_sent = models.BooleanField(default=False)

class Standard_Approvers(models.Model):
    id = models.BigAutoField(primary_key=True)
    job_description = models.CharField(null=True, max_length=2000, blank=True) #should be estimator or superintendent
    employee = models.ForeignKey(employees.models.Employees, on_delete=models.PROTECT,null=True, blank=True)

class Subcontractor_Approvers(models.Model):
    id = models.BigAutoField(primary_key=True)
    job_description = models.CharField(null=True, max_length=2000, blank=True) #should be estimator or superintendent
    employee = models.ForeignKey(employees.models.Employees, on_delete=models.PROTECT,null=True, blank=True)
    subcontractor = models.ForeignKey(Subcontractors, on_delete=models.PROTECT)

class Subcontract_Approvers(models.Model):
    id = models.BigAutoField(primary_key=True)
    job_description = models.CharField(null=True, max_length=2000, blank=True) #should be estimator or superintendent
    employee = models.ForeignKey(employees.models.Employees, on_delete=models.PROTECT,null=True, blank=True)
    subcontract = models.ForeignKey(Subcontracts, on_delete=models.PROTECT)

class Subcontractor_Employees(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(null=True, max_length=2000, blank=True)
    subcontractor = models.ForeignKey(Subcontractors, on_delete=models.PROTECT)
    username = models.CharField(null=True, max_length=2000, blank=True)
    password1 = models.CharField(null=True, max_length=2000, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(null=True, max_length=50, blank=True)
    nickname = models.CharField(null=True, max_length=250, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    has_access_to_TM = models.BooleanField(default=False)
    has_access_to_toolbox = models.BooleanField(default=False)
    date_enrolled = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name or f"Subcontractor Employee {self.id}"


class SubcontractorRespiratorClearance(models.Model):
    id = models.BigAutoField(primary_key=True)
    subcontractor = models.ForeignKey(Subcontractors, on_delete=models.PROTECT)
    employee = models.ForeignKey(
        Subcontractor_Employees,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    employee_name = models.CharField(max_length=250, null=True, blank=True)
    date_created = models.DateField(null=True, blank=True)
    date_completed = models.DateField(null=True, blank=True)
    approved_for_use = models.BooleanField(default=False)
    date_approved = models.DateField(null=True, blank=True)
    date_expires = models.DateField(null=True, blank=True)
    is_closed = models.BooleanField(default=False)
    is_physician_required = models.BooleanField(default=False)
    is_physician_actually_required = models.BooleanField(default=False)
    physician_approved = models.BooleanField(default=False)
    gender = models.CharField(max_length=50, null=True, blank=True)
    height = models.CharField(max_length=50, null=True, blank=True)
    weight = models.CharField(max_length=50, null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    language = models.CharField(max_length=20, default="English")
    form_data = models.JSONField(default=dict, blank=True)

    @property
    def employee_display_name(self):
        if self.employee:
            return self.employee.name
        return self.employee_name or "Unassigned"

    def status_label(self):
        if not self.date_completed:
            return "Not completed yet"
        if not self.approved_for_use:
            return "Not approved yet"
        return self.date_expires or ""

    def __str__(self):
        return f"{self.subcontractor} - {self.employee_display_name}"


class SubcontractorRespiratorNotes(models.Model):
    id = models.BigAutoField(primary_key=True)
    main = models.ForeignKey(SubcontractorRespiratorClearance, on_delete=models.CASCADE)
    date = models.DateField()
    employee = models.ForeignKey(
        'employees.Employees',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    subcontractor_employee = models.ForeignKey(
        Subcontractor_Employees,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    note = models.CharField(max_length=2000, blank=True, null=True)

    @property
    def author(self):
        if self.employee:
            return self.employee
        if self.subcontractor_employee:
            return self.subcontractor_employee
        return ""


class Subcontractor_Job_Assignments(models.Model):
    id = models.BigAutoField(primary_key=True)
    employee = models.ForeignKey(Subcontractor_Employees, on_delete=models.PROTECT)
    job = models.ForeignKey('jobs.Jobs', on_delete=models.PROTECT)

class CompletedSubToolboxTalks(models.Model):
    id = models.BigAutoField(primary_key=True)
    date = models.DateField(null=True, blank=True)
    employee = models.ForeignKey(Subcontractor_Employees, on_delete=models.PROTECT)
    master = models.ForeignKey('employees.ScheduledToolboxTalks', on_delete=models.PROTECT)
    job = models.ForeignKey('jobs.Jobs', on_delete=models.PROTECT, null=True, blank=True)
    is_excused = models.BooleanField(default=False)
    note = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = ('employee', 'master', 'job')

#Used in sub employee portal
class ViewedSubToolboxTalks(models.Model):
    id = models.BigAutoField(primary_key=True)
    date = models.DateField(null=True, blank=True)
    employee = models.ForeignKey(Subcontractor_Employees, on_delete=models.PROTECT)
    master = models.ForeignKey('employees.ScheduledToolboxTalks', on_delete=models.PROTECT)
    language = models.CharField(max_length=50, blank=True, null=True)  # This will say English or Spanish

# NOT USING THIS MODEL CURRENTLY
class ScheduledToolboxTalkSubEmployees(models.Model):
    scheduled = models.ForeignKey(ScheduledToolboxTalks, on_delete=models.CASCADE)
    employee = models.ForeignKey(Subcontractor_Employees, on_delete=models.PROTECT)
    job = models.ForeignKey('jobs.Jobs', on_delete=models.PROTECT,null=True, blank=True)

    class Meta:
        unique_together = ('scheduled', 'employee', 'job')

class ScheduledToolboxTalkSubJobs(models.Model):
    scheduled = models.ForeignKey(ScheduledToolboxTalks, on_delete=models.CASCADE)
    job = models.ForeignKey('jobs.Jobs', on_delete=models.PROTECT)
    subcontractor = models.ForeignKey(Subcontractors, on_delete=models.PROTECT)

class CompletedSubToolboxJobTalks(models.Model):
    id = models.BigAutoField(primary_key=True)
    scheduled = models.ForeignKey(ScheduledToolboxTalks, on_delete=models.PROTECT)
    subcontractor = models.ForeignKey(Subcontractors, on_delete=models.PROTECT)
    job = models.ForeignKey('jobs.Jobs', on_delete=models.PROTECT)
    date = models.DateField(auto_now_add=True)
    is_excused = models.BooleanField(default=False)

    class Meta:
        unique_together = ('scheduled', 'subcontractor', 'job')

#each employee that was part of CompletedSubToolboxJobTalks
class CompletedSubToolboxJobTalkEmployees(models.Model):
    id = models.BigAutoField(primary_key=True)
    completed = models.ForeignKey(
        CompletedSubToolboxJobTalks,
        on_delete=models.CASCADE,
        related_name='employees'
    )
    employee = models.ForeignKey(
        Subcontractor_Employees,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    custom_name = models.CharField(max_length=250, null=True, blank=True)
    added_to_employee_list = models.BooleanField(default=False)
    note = models.TextField(null=True, blank=True)

#If a job is not delegated, this keeps track of subcontractor foreman talks
class ViewedSubToolboxJobTalks(models.Model):
    id = models.BigAutoField(primary_key=True)
    scheduled = models.ForeignKey(ScheduledToolboxTalks, on_delete=models.CASCADE)
    subcontractor = models.ForeignKey(Subcontractors, on_delete=models.PROTECT)
    job = models.ForeignKey('jobs.Jobs', on_delete=models.PROTECT)
    language = models.CharField(max_length=20)  # English / Spanish
    date = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ('scheduled', 'subcontractor', 'job', 'language')

#USED FROM THE PORTAL.  ALLOWS SUB EMPLOYEES TO DO THEIR OWN TOOLBOX TALKS
class SubcontractorEmployeeDelegation(models.Model):
    id = models.BigAutoField(primary_key=True)
    subcontractor = models.ForeignKey(Subcontractors, on_delete=models.PROTECT)
    subcontract = models.ForeignKey(Subcontracts, on_delete=models.PROTECT)
    date = models.DateField(auto_now_add=True)

