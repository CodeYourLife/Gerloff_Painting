from django.db import models
from jobs.models import *
from wallcovering.models import Wallcovering
import employees.models
from datetime import date


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

    def __str__(self):
        return f"{self.company}"

    def active_contracts(self):
        totalquantity = 0
        for x in Subcontracts.objects.filter(subcontractor=self, is_closed=False):
            totalquantity = totalquantity + 1
        return totalquantity

    def pending_invoices(self):
        totalquantity = 0
        for x in SubcontractorInvoice.objects.filter(subcontract__subcontractor=self, is_sent=False):
            totalquantity = totalquantity + 1
        return totalquantity

    def needs_payment(self):
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

    def __str__(self):
        return f"{self.subcontractor} {self.job_number}"

    def total_pending_amount(self):
        total = 0
        for x in SubcontractorInvoice.objects.filter(subcontract=self, is_sent=False):
            total = total + x.final_amount
        return total

    def total_billed(self):
        total = 0
        for x in SubcontractorInvoice.objects.filter(subcontract=self, is_sent=True):
            total = total + x.final_amount
        return total

    def total_retainage(self):
        total = 0
        for x in SubcontractorInvoice.objects.filter(subcontract=self, is_sent=True):
            total = total + x.retainage
        return total

    def total_retainage_pending(self):
        total = 0
        for x in SubcontractorInvoice.objects.filter(subcontract=self, is_sent=False):
            total = total + x.retainage
        return total

    def total_contract_amount(self):
        total = 0
        for x in SubcontractItems.objects.filter(subcontract=self, is_approved=True):
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
            totalcost = float(totalcost) / float(self.SOV_rate)
        return totalcost

    def total_billed(self):
        totalcost = 0
        for x in SubcontractorInvoiceItem.objects.filter(sov_item=self, invoice__is_sent=True):
            totalcost = totalcost + x.quantity
        if self.SOV_is_lump_sum == False:
            totalcost = totalcost * self.SOV_rate
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


class SubcontractorInvoice(models.Model):
    id = models.BigAutoField(primary_key=True)
    date = models.DateField()
    pay_app_number = models.IntegerField(default=0)
    subcontract = models.ForeignKey(
        Subcontracts, on_delete=models.PROTECT, related_name="invoice")
    retainage = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    final_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True)
    is_sent = models.BooleanField(default=False)  # this actually means approved by victor
    processed = models.BooleanField(default=False)  # check has been cut
    pay_date = models.DateField(null=True, blank=True)
    notes = models.CharField(
        null=True, max_length=2000, blank=True)  # DONT USE
    payment = models.ForeignKey(
        SubcontractorPayments, on_delete=models.PROTECT, related_name="invoice2",null=True, blank=True)

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


class InvoiceBatch(models.Model):
    id = models.BigAutoField(primary_key=True)
    invoice = models.ForeignKey(SubcontractorInvoice, null=True,
                                on_delete=models.PROTECT, related_name="batch")


class PurchaseOrderNumber(models.Model):
    id = models.BigAutoField(primary_key=True)
    next_po_number = models.IntegerField(default=0)