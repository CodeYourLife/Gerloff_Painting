from django.db import models
from django.core.exceptions import ValidationError
from changeorder.models import TMPricesMaster
from employees.models import *
from equipment.models import *
from wallcovering.models import *


def validate_job_notes(value):
    if value == "auto_booking_note" or value == "auto_misc_note" or value == "employee_note" or value == "auto_co_note" or value == "auto_submittal_note" or value == "auto_start_date_note" or value == "daily_report":
        return value
    else:
        raise ValidationError("Category Not Allowed")


class Clients(models.Model):
    id = models.BigAutoField(primary_key=True)
    company = models.CharField(null=True, max_length=250)
    bid_fax = models.CharField(null=True, blank=True, max_length=50)
    bid_email = models.EmailField(null=True, blank=True)
    vendor_code = models.CharField(null=True, blank=True, max_length=100)
    address = models.CharField(null=True, max_length=100, blank=True)
    city = models.CharField(null=True, max_length=100,blank=True)
    state = models.CharField(null=True, max_length=100, blank=True)
    phone = models.CharField(null=True, max_length=50,blank=True)

    def __str__(self):
        return f"{self.company}"


class ClientEmployees(models.Model):
    person_pk = models.BigAutoField(primary_key=True)
    id = models.ForeignKey(Clients, on_delete=models.PROTECT)
    name = models.CharField(max_length=250)
    phone = models.CharField(blank=True, null=True, max_length=50)
    email = models.EmailField(blank=True, null=True)
    title = models.CharField(blank=True, null=True, max_length=250)

    def __str__(self):
        return f"{self.name}"


class JobNumbers(models.Model):
    letter = models.CharField(null=False, max_length=1)
    number = models.CharField(null=False, max_length=4)


class Jobs(models.Model):
    job_number = models.CharField(null=False, max_length=5, primary_key=True)
    job_name = models.CharField(null=True, max_length=250)
    estimator = models.ForeignKey(
        Employees, on_delete=models.PROTECT, null=True,blank=True, related_name='estimator')
    foreman = models.ForeignKey(

        Employees, on_delete=models.PROTECT, null=True,blank=True, related_name='foreman') #we still need to code the foreman
    superintendent = models.ForeignKey(
        Employees, on_delete=models.PROTECT, null=True,blank=True, related_name='superintendent')
    contract_amount = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    po_number = models.CharField(null=True, max_length=50, blank=True)
    retainage_percentage = models.CharField(
        null=True, max_length=50, blank=True)
    is_t_m_job = models.BooleanField(default=False)
    t_m_nte_amount = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    status = models.CharField(null=True, max_length=50)  # open,closed
    booked_date = models.DateField(null=True, blank=True)
    booked_by = models.CharField(null=True, max_length=50, blank=True)
    is_wage_scale = models.BooleanField(default=False)
    is_davis_bacon_wages = models.BooleanField(default=False) #delete - same thing as is_wage_scale
    spray_scale = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    brush_role = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    address = models.CharField(null=True, max_length=50)
    city = models.CharField(null=True, max_length=20)
    state = models.CharField(null=True, max_length=2)
    start_date = models.DateField(null=True, blank=True)
    duration = models.CharField(null=True, max_length=50, blank=True)
    estimate_number = models.CharField(null=True, max_length=50, blank=True)
    estimate_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    has_wallcovering = models.BooleanField(default=False)
    has_paint = models.BooleanField(default=False)
    has_owner_supplied_wallcovering = models.BooleanField(default=False) #we need to check - can we handle through the wallcovering app
    painting_budget = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    wallcovering_budget = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    is_send_auto_co_emails = models.BooleanField(default=True) #need to implement this
    is_send_auto_submittal_emails = models.BooleanField(default=True) #need to implement this
    notes = models.CharField(null=True, max_length=2000, blank=True)
    approved_change_orders = models.DecimalField(
        max_digits=10, decimal_places=4, blank=True, null=True)
    final_bill_amount = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    is_closed = models.BooleanField(default=False)#not sure what this is
    labor_done_Date = models.DateField(null=True, blank=True)
    ar_closed_date = models.DateField(null=True, blank=True)
    was_previously_closed = models.BooleanField(default=False)
    previously_closed_date = models.DateField(null=True, blank=True)
    cumulative_costs_at_closing = models.DecimalField(
        max_digits=9, decimal_places=2, blank=True, null=True)
    contract_status = models.IntegerField() #1-received #2 not received #3 not required
    insurance_status = models.IntegerField()

    submittals_required = models.IntegerField(null=True,blank=True) #replacing this with submittals_needed
    submittals_needed = models.BooleanField(default=False)
    has_special_paint = models.IntegerField(null=True,blank=True)#replacing this with special_paint_needed

    special_paint_needed = models.BooleanField(default=False)
    client = models.ForeignKey(
        Clients, related_name="Client", on_delete=models.PROTECT)
    client_Pm = models.ForeignKey(
        ClientEmployees, related_name="PM", on_delete=models.PROTECT, null=True, blank=True)
    client_Pm_Phone = models.CharField(null=True, max_length=50, blank=True)#not used
    client_Pm_Email = models.EmailField(null=True, blank=True)#not used
    client_Co_Contact = models.ForeignKey(ClientEmployees, related_name="CO", on_delete=models.PROTECT, null=True, blank=True) #not used - handled with another database i think
    client_Co_Email = models.EmailField(null=True, blank=True)#not used - handled with another database i think
    client_Submittal_Contact = models.ForeignKey(
        ClientEmployees, related_name="Submittals", on_delete=models.PROTECT, null=True,blank=True)#not used - handled with another database i think
    client_Submittal_Email = models.EmailField(null=True, blank=True)#not used - handled with another database i think
    client_Super = models.ForeignKey(
        ClientEmployees, related_name="Super", on_delete=models.PROTECT, null=True, blank=True)
    client_Super_Phone = models.CharField(max_length=50, blank=True, null=True) #not used
    client_Super_Email = models.EmailField(null=True, blank=True) #not used
    is_on_base = models.BooleanField(default=False)
    unsigned_tickets = models.IntegerField(null=True, blank=True)#not used
    assigned_inventory = models.IntegerField(null=True, blank=True) #not used
    assigned_rentals = models.IntegerField(null=True, blank=True) #not used
    is_bonded = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)#this is for supers to use - whether to show on upcoming jobs list
    start_date_checked = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.job_name}"


class JobNotes(models.Model):
    id = models.BigAutoField(primary_key=True)
    job_number = models.ForeignKey(Jobs, on_delete=models.PROTECT)
    note = models.CharField(null=True, max_length=2000)
    # booking note, field note, CO note, submittal note, start date note, daily report, etc
    type = models.CharField(null=True, max_length=50,
                            validators=[validate_job_notes])
    user = models.CharField(null=True, max_length=50)  # bridgette joe
    date = models.DateField(null=True, blank=True)
    daily_employee_count = models.IntegerField(null=True, blank=True)
    # use if you are having to back date a daily report
    note_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.job_number} {self.type}"


class Orders(models.Model):  # one pattern, one WC1, etc. may be broken up into several packages
    id = models.BigAutoField(primary_key=True)
    po_number = models.CharField(max_length=25)
    job_number = models.ForeignKey(Jobs, on_delete=models.PROTECT)
    vendor = models.ForeignKey(
        Vendors, on_delete=models.PROTECT, null=True, blank=True)
    # this is for if there are multiple patterns ordered'
    description = models.CharField(max_length=2000)
    date_ordered = models.DateField(null=True, blank=True)
    partial_receipt = models.BooleanField(default=False)
    # DONT USE THIS, USE ORDERITEMS
    notes = models.CharField(null=True, max_length=2000, blank=True)

    def __str__(self):
        return f"{self.job_number} {self.description}"

    def quantity_ordered(self):
        totalquantity = 0
        for x in OrderItems.objects.filter(order=self):
            totalquantity = totalquantity + x.quantity
        return totalquantity

    def quantity_received(self):
        totalquantity = 0
        for x in OrderItems.objects.filter(order=self):
            totalquantity = totalquantity + x.quantity_received()
        return totalquantity

    def packages_received(self):
        totalquantity = 0
        for x in Packages.objects.filter(delivery__order=self):
            totalquantity = totalquantity + x.quantity_received
        return totalquantity

    def packages_sent(self):
        totalquantity = 0
        for x in OutgoingItem.objects.filter(package__delivery__order=self):
            totalquantity = totalquantity + x.quantity_sent
        return totalquantity


class Estimates(models.Model):
    id = models.BigAutoField(primary_key=True)
    to_number = models.IntegerField(default=0)
    bid_date = models.DateField(null=True, blank=True)
    take_off_name = models.CharField(null=True, max_length=2000)
    estimator = models.CharField(null=True, max_length=250)
    bidders = models.CharField(null=True, max_length=250)
    has_docs_print = models.BooleanField(default=False)
    # estimate_status = models.enum.EnumField(choices=['Awarded','Bid Sent','Not Bidding', 'In Progress', 'To Joe', 'T/O Done'])
    comments = models.CharField(null=True, max_length=2000)
    addenda = models.IntegerField(default=0)
    site_visit_date = models.DateField(null=True, blank=True)
    client_estimator_name = models.CharField(null=True, max_length=250)
    client_estimator_email = models.EmailField(null=True, blank=True)
    client_phone = models.CharField(null=True, max_length=50)
    send_bids_to_email = models.EmailField(null=True, blank=True)
    price = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, null=True)
    job_number = models.CharField(null=True, max_length=50)
    wage_rate_spray = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, null=True)
    wate_rate_paint = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, null=True)
    is_awarded_gc = models.BooleanField(default=False)


class Plans(models.Model):
    id = models.BigAutoField(primary_key=True)
    job_number = models.CharField(null=False, max_length=10)
    job_name = models.CharField(null=True, max_length=250)
    description = models.CharField(null=True, max_length=2000)
    estimates_number = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)


class JobCharges(models.Model):
    id = models.BigAutoField(primary_key=True)
    job = models.ForeignKey(Jobs, on_delete=models.PROTECT)
    master = models.ForeignKey(TMPricesMaster, on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.job} {self.master}"
