from django.db import models
from django.core.exceptions import ValidationError

import employees.models
from changeorder.models import *
from employees.models import *
from equipment.models import *
from wallcovering.models import *
from subcontractors.models import *
from rentals.models import *
from datetime import date, timedelta
from django.db.models import Q
from django.db.models import Sum
from decimal import Decimal, ROUND_HALF_UP

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
    city = models.CharField(null=True, max_length=100, blank=True)
    state = models.CharField(null=True, max_length=100, blank=True)
    phone = models.CharField(null=True, max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    def __str__(self):
        return f"{self.company}"


class ClientEmployees(models.Model):
    person_pk = models.BigAutoField(primary_key=True)
    id = models.ForeignKey(Clients, on_delete=models.PROTECT)
    name = models.CharField(max_length=250)
    phone = models.CharField(blank=True, null=True, max_length=50)
    email = models.EmailField(blank=True, null=True)
    title = models.CharField(blank=True, null=True, max_length=250)
    is_active = models.BooleanField(default=True)
    def __str__(self):
        return f"{self.name}"


class JobNumbers(models.Model):
    letter = models.CharField(null=False, max_length=1)
    number = models.CharField(null=False, max_length=4)


class Jobs(models.Model):
    job_number = models.CharField(null=False, max_length=5, primary_key=True)
    job_name = models.CharField(null=True, max_length=250)
    estimator = models.ForeignKey(
        Employees, on_delete=models.PROTECT, null=True, blank=True, related_name='estimator')
    foreman = models.ForeignKey(Employees, on_delete=models.PROTECT, null=True, blank=True,
                                related_name='foreman')  # we still need to code the foreman
    superintendent = models.ForeignKey(
        Employees, on_delete=models.PROTECT, null=True, blank=True, related_name='superintendent')
    contract_amount = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    po_number = models.CharField(null=True, max_length=50, blank=True)
    retainage_percentage = models.CharField(
        null=True, max_length=50, blank=True)
    is_t_m_job = models.BooleanField(default=False)
    t_m_nte_amount = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    status = models.CharField(null=True, max_length=50)  # open,closed - DO NOT USE THIS ANYMORE. USE is_closed
    booked_date = models.DateField(null=True, blank=True)
    booked_by = models.CharField(null=True, max_length=50, blank=True)
    is_wage_scale = models.BooleanField(default=False)
    is_davis_bacon_wages = models.BooleanField(default=False)  # delete - same thing as is_wage_scale
    spray_scale = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    brush_role = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    address = models.CharField(null=True, max_length=500)
    city = models.CharField(null=True, max_length=20)
    state = models.CharField(null=True, max_length=2)
    start_date = models.DateField(null=True, blank=True)
    duration = models.CharField(null=True, max_length=50, blank=True)
    estimate_number = models.CharField(null=True, max_length=50, blank=True)
    estimate_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    has_wallcovering = models.BooleanField(default=False)
    has_paint = models.BooleanField(default=False)
    has_owner_supplied_wallcovering = models.BooleanField(
        default=False)  # we need to check - can we handle through the wallcovering app
    painting_budget = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    wallcovering_budget = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    is_send_auto_co_emails = models.BooleanField(default=True)  # need to implement this
    is_send_auto_submittal_emails = models.BooleanField(default=True)  # need to implement this
    notes = models.CharField(null=True, max_length=2000, blank=True)
    approved_change_orders = models.DecimalField(
        max_digits=10, decimal_places=4, blank=True, null=True)
    final_bill_amount = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    is_closed = models.BooleanField(default=False)  # lets use this instead of status
    labor_done_Date = models.DateField(null=True, blank=True)
    ar_closed_date = models.DateField(null=True, blank=True)
    was_previously_closed = models.BooleanField(default=False)
    previously_closed_date = models.DateField(null=True, blank=True)
    cumulative_costs_at_closing = models.DecimalField(
        max_digits=9, decimal_places=2, blank=True, null=True)
    contract_status = models.IntegerField()  # 1-received #2 not received #3 not required
    insurance_status = models.IntegerField()

    submittals_required = models.IntegerField(null=True, blank=True)  # replacing this with submittals_needed
    submittals_needed = models.BooleanField(default=False)
    has_special_paint = models.IntegerField(null=True, blank=True)  # replacing this with special_paint_needed

    special_paint_needed = models.BooleanField(default=False)
    client = models.ForeignKey(
        Clients, related_name="Client", on_delete=models.PROTECT)
    client_Pm = models.ForeignKey(
        ClientEmployees, related_name="PM", on_delete=models.PROTECT, null=True, blank=True)
    client_Pm_Phone = models.CharField(null=True, max_length=50, blank=True)  # not used
    client_Pm_Email = models.EmailField(null=True, blank=True)  # not used
    client_Co_Contact = models.ForeignKey(ClientEmployees, related_name="CO", on_delete=models.PROTECT, null=True,
                                          blank=True)  # not used - handled with another database i think
    client_Co_Email = models.EmailField(null=True, blank=True)  # not used - handled with another database i think
    client_Submittal_Contact = models.ForeignKey(
        ClientEmployees, related_name="Submittals", on_delete=models.PROTECT, null=True,
        blank=True)  # not used - handled with another database i think
    client_Submittal_Email = models.EmailField(null=True,
                                               blank=True)  # not used - handled with another database i think
    client_Super = models.ForeignKey(
        ClientEmployees, related_name="Super", on_delete=models.PROTECT, null=True, blank=True)
    client_Super_Phone = models.CharField(max_length=50, blank=True, null=True)  # not used
    client_Super_Email = models.EmailField(null=True, blank=True)  # not used
    is_on_base = models.BooleanField(default=False)
    unsigned_tickets = models.IntegerField(null=True, blank=True)  # not used
    assigned_inventory = models.IntegerField(null=True, blank=True)  # not used
    assigned_rentals = models.IntegerField(null=True, blank=True)  # not used
    is_bonded = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)  # this is for supers to use - whether to show on upcoming jobs list
    start_date_checked = models.DateField(null=True, blank=True)
    is_off_hours = models.BooleanField(default=False)
    closed_job_number = models.IntegerField(null=True, blank=True)  # added this
    is_work_order_done = models.BooleanField(default=False)
    man_hours_budgeted = models.IntegerField(null=True, blank=True)
    man_hours_used = models.IntegerField(null=True, blank=True)
    is_waiting_for_punchlist = models.BooleanField(default=False)
    is_labor_done = models.BooleanField(default=False)
    is_painting_subbed = models.BooleanField(default=False)
    has_safety_packet_been_sent = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.job_name}"

    def hours_to_date(self):
        result = self.clockshark_entries.aggregate(
            total=Sum("hours")
        )["total"]

        if result is None:
            return Decimal("0")

        return result.quantize(Decimal("1"), rounding=ROUND_HALF_UP)

    def subcontract_count(self):
        return Subcontracts.objects.filter(job_number=self).count()

    def wc_count(self):
        return Wallcovering.objects.filter(job_number=self).count()

    def equipment_count(self):
        return Inventory.objects.filter(job_number=self,is_closed=False).count()

    def rentals_count(self):
        return Rentals.objects.filter(is_closed=False, job_number=self).count()

    def tickets_count(self):
        return ChangeOrders.objects.filter(is_t_and_m=True, is_ticket_signed=False, is_closed=False,
                                           job_number=self).count()

    def field_notes_count(self):
        return JobNotes.objects.filter(
            Q(type="employee_note") | Q(type="daily_report") | Q(type="auto_start_date_note"), job_number=self).count()

    def approved_co_amount(self):
        total_amount =0
        for x in ChangeOrders.objects.filter(job_number=self, is_approved_to_bill=True):
            if x.price: total_amount += x.price
        return total_amount

    def is_entire_job_subbed(self):
        subbed_paint_jobs = Subcontracts.objects.filter(job_number=self, is_entire_paint_job=True)
        if not subbed_paint_jobs:
            return False
        else:
            return True

    def count_approved_changes(self):
        total_amount =0
        if ChangeOrders.objects.filter(job_number=self, is_approved_to_bill=True).exists():
            total_amount = ChangeOrders.objects.filter(job_number=self, is_approved_to_bill=True).count()
        return total_amount

    def pending_co_amount(self):
        total_amount = 0
        for x in ChangeOrders.objects.filter(job_number=self, is_approved_to_bill=False):
            if x.price: total_amount += x.price
        return total_amount

    def count_pending_changes(self):
        total_amount = 0
        if ChangeOrders.objects.filter(job_number=self, is_approved_to_bill=False).exists():
            total_amount = ChangeOrders.objects.filter(job_number=self, is_approved_to_bill=True).count()
        return total_amount

    def current_contract_amount(self):
        total_amount=0
        if self.is_t_m_job==False:
            total_amount=self.contract_amount
        else: total_amount=0
        for x in ChangeOrders.objects.filter(job_number=self, is_approved_to_bill=True):
            if x.price: total_amount += x.price
        return total_amount

    def formals(self):
        formals_list=[]
        current_gc_number = 999
        current_total = 0
        for x in ChangeOrders.objects.filter(job_number=self).exclude(gc_number = None).order_by('gc_number'):
            if current_gc_number == 999:
                count = ChangeOrders.objects.filter(job_number=self, gc_number = x.gc_number).count()
                if count == 1:
                    description = "COP " + str(x.cop_number) + " -" + x.description
                else:
                    description = "COPs: " + str(x.cop_number)
                current_gc_number = x.gc_number
                current_total = x.price
            elif x.gc_number != current_gc_number:
                formals_list.append({'gc_number':current_gc_number,'description':description, 'total':"$" + str(('{:,}'.format(current_total)))})
                count = ChangeOrders.objects.filter(job_number=self, gc_number=x.gc_number).count()
                if count == 1:
                    description = "COP " + str(x.cop_number) + " -" + x.description
                else:
                    description = "COPs: " + str(x.cop_number)
                current_gc_number = x.gc_number
                current_total = x.price
            else:
                current_total+= x.price
                description += ", " + str(x.cop_number)
        if current_gc_number != 999:
            formals_list.append({'gc_number': current_gc_number,'description':description, 'total':"$" + str(('{:,}'.format(current_total)))})
        return formals_list
    def check_start_date(self):
        if self.is_active:
            return False
        else:
            difference = date.today() - self.start_date_checked
            if int(difference.days) > 30:
                return True
            else:
                return False

    def time_since_checking(self):
        difference = date.today() - self.start_date_checked
        return int(difference.days)


    def next_two_weeks(self):
        if self.is_active == False:
            if date.today() > self.start_date:
                return True
            else:
                difference = self.start_date - date.today()
                if int(difference.days) < 14:
                    return True
                else:
                    return False
        else:
            return False

class JobNotes(models.Model):
    id = models.BigAutoField(primary_key=True)
    job_number = models.ForeignKey(Jobs, on_delete=models.PROTECT)
    note = models.CharField(null=True, max_length=2000)
    # booking note, field note, CO note, submittal note, start date note, daily report, etc
    type = models.CharField(null=True, max_length=50,
                            validators=[validate_job_notes])
    user = models.ForeignKey(employees.models.Employees, on_delete=models.PROTECT)
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


class Email_Errors(models.Model):
    id = models.BigAutoField(primary_key=True)
    error = models.CharField(null=True, max_length=2000)
    user = models.CharField(null=True, max_length=2000)
    #user = request.user.first_name + " " + request.user.last_name
    #for subs =
    date = models.DateField(null=True, blank=True)

class Competent_Persons(models.Model):
    id = models.BigAutoField(primary_key=True)
    job = models.ForeignKey(Jobs, on_delete=models.PROTECT)
    employee = models.ForeignKey(employees.models.Employees, on_delete=models.PROTECT)
    date = models.DateField(null=True, blank=True)

class ClockSharkTimeEntry(models.Model):
    clockshark_id = models.CharField(max_length=255, null=True)
    job = models.ForeignKey(Jobs,on_delete=models.CASCADE,related_name="clockshark_entries",null=True,blank=True)
    employee_first_name = models.CharField(max_length=100,null=True)
    employee_last_name = models.CharField(max_length=100, null=True)
    job_number = models.CharField(max_length=50,null=True)
    clock_in = models.DateTimeField(null=True, blank=True)
    clock_out = models.DateTimeField(null=True, blank=True)
    hours = models.DecimalField(max_digits=6, decimal_places=2,null=True)
    synced_at = models.DateTimeField(auto_now=True)
    work_day = models.DateField(null=True, blank=True)
    job_name = models.CharField(null=True, max_length=250)
    hours_adjust = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    hours_adjust_note = models.CharField(null=True, max_length=250, blank=True)
    lunch = models.DecimalField(max_digits=6, decimal_places=2,null=True)

    class Meta:
        indexes = [
            models.Index(fields=["job_number"]),
            models.Index(fields=["clock_in"]),
        ]



class ClockSharkErrors(models.Model):
    job = models.ForeignKey(Jobs,on_delete=models.CASCADE,related_name="clockshark_entry_errors",null=True,blank=True)
    employee_first_name = models.CharField(max_length=100,null=True)
    employee_last_name = models.CharField(max_length=100, null=True)
    job_number = models.CharField(max_length=50,null=True)
    clock_in = models.DateTimeField(null=True, blank=True)
    clock_out = models.DateTimeField(null=True, blank=True)
    hours = models.DecimalField(max_digits=6, decimal_places=2,null=True)
    synced_at = models.DateTimeField(auto_now=True)
    work_day = models.DateField(null=True, blank=True)
    error = models.CharField(null=True, max_length=2000)
    job_name = models.CharField(null=True, max_length=250)
    clockshark_id = models.CharField(max_length=255, null=True)

    def __str__(self):
        return f"{self.employee_first_name} {self.employee_last_name} {self.error}"


class SiriusHours(models.Model):
    id = models.BigAutoField(primary_key=True)
    job = models.ForeignKey(Jobs,on_delete=models.CASCADE,related_name="sirius_hours",null=True,blank=True)
    job_number = models.CharField(max_length=50,null=True) #this may not match a booked job
    date = models.DateField(null=True, blank=True)
    hours = models.DecimalField(max_digits=8, decimal_places=2,null=True)
    notes = models.CharField(null=True, max_length=2000)

    def __str__(self):
        return f"{self.job_number} {self.job}"