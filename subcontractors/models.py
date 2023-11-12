from django.db import models
from jobs.models import *
from wallcovering.models import Wallcovering
import employees.models

class Subcontractors(models.Model):
    id = models.BigAutoField(primary_key=True)
    company = models.CharField(null=True, max_length=250)
    contact = models.CharField(null=True, max_length=250, blank=True)
    phone = models.CharField(null=True, max_length=20, blank=True)
    email = models.EmailField(null=True, blank=True)
    insurance_expire_date = models.DateField(blank=True, null=True)
    is_signed_labor_agreement = models.BooleanField(default=False)
    notes = models.CharField(null=True, max_length=2000, blank=True)

    def __str__(self):
        return f"{self.company}"

    def active_contracts(self):
        totalquantity = 0
        for x in Subcontracts.objects.filter(subcontractor=self, is_closed=False):
            totalquantity = totalquantity+1
        return totalquantity


class Subcontracts(models.Model):
    id = models.BigAutoField(primary_key=True)
    job_number = models.ForeignKey('jobs.Jobs', on_delete=models.PROTECT)
    subcontractor = models.ForeignKey(
        Subcontractors, on_delete=models.PROTECT, related_name="subcontract")
    po_number = models.CharField(null=True, max_length=250)
    total_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)  # DONT USE
    notes = models.CharField(null=True, max_length=2000)
    date = models.DateField(null=True, blank=True)
    is_closed = models.BooleanField(default=False)
    is_retainage = models.BooleanField(default=True)
    retainage_percentage = models.DecimalField(
        max_digits=4, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return f"{self.subcontractor} {self.job_number}"

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

    def __str__(self):
        return f"{self.subcontract} {self.SOV_description}"

    def total_cost(self):
        totalcost = 0
        if self.SOV_is_lump_sum == True:
            totalcost = self.SOV_rate
        else:
            totalcost = self.SOV_total_ordered * self.SOV_rate
        return totalcost

    def quantity_billed(self):
        totalcost = float(0.00)
        for x in SubcontractorInvoiceItem.objects.filter(sov_item=self, invoice__is_sent=True):
            totalcost = float(totalcost) + float(x.quantity)
        if self.SOV_is_lump_sum == True:
            totalcost = float(totalcost) / float(self.SOV_rate)
        return totalcost

    def total_billed(self):
        totalcost = 0
        for x in SubcontractorInvoiceItem.objects.filter(sov_item=self, invoice__is_sent=True):
            if x.invoice.is_sent == True:
                totalcost = totalcost + x.quantity
        if self.SOV_is_lump_sum == False:
            totalcost = totalcost * self.SOV_rate
        return totalcost


class SubcontractorInvoice(models.Model):
    id = models.BigAutoField(primary_key=True)
    date = models.DateField()
    pay_app_number = models.IntegerField(default=0)
    subcontract = models.ForeignKey(
        Subcontracts, on_delete=models.PROTECT, related_name="invoice")
    retainage = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    final_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True)
    is_sent = models.BooleanField(default=False)
    notes = models.CharField(
        null=True, max_length=2000, blank=True)  # DONT USE

    def __str__(self):
        return f"{self.subcontract} {self.pay_app_number}"


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


class SubcontractNotes(models.Model):
    id = models.BigAutoField(primary_key=True)
    subcontract = models.ForeignKey(
        Subcontracts, on_delete=models.PROTECT, related_name="subcontract_notes")
    date = models.DateField(null=True, blank=True)
    user = models.ForeignKey(employees.models.Employees, on_delete=models.PROTECT)
    note = models.CharField(null=True, max_length=2000)
    invoice = models.ForeignKey(SubcontractorInvoice, null=True,
                                on_delete=models.PROTECT, related_name="subcontract_notes2")
