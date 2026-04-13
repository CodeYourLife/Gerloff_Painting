from django.db import models
from django.core.exceptions import ValidationError
import employees.models



def validate_tm_category(value):
    if value == "Labor" or value == "Material" or value == "Equipment" or value == "Inventory" or value == "Misc" or value == "Bond" or value == "Sundries":
        return value
    else:
        raise ValidationError(
            "Category must be Labor, Material, Equipment, Inventory, Bond or Misc")


class TMPricesMaster(models.Model):
    id = models.BigAutoField(primary_key=True)
    category = models.CharField(null=False, max_length=50, validators=[
                                validate_tm_category])  # Labor, Material, Equipment, Bond, Inventory
    item = models.CharField(null=False, max_length=50)
    unit = models.CharField(null=False, max_length=50)  # gallons, hours
    rate = models.DecimalField(max_digits=9, decimal_places=2)

    def __str__(self):
        return f"{self.item}"

class JobPrices(models.Model):
    id = models.BigAutoField(primary_key=True)
    master = models.ForeignKey('changeorder.TMPricesMaster', on_delete=models.PROTECT)
    rate = models.DecimalField(max_digits=9, decimal_places=2)
    job_number = models.ForeignKey('jobs.Jobs', on_delete=models.PROTECT)

    class Meta:
        unique_together = ('master', 'job_number')

class JobCharges2(models.Model):
    id = models.BigAutoField(primary_key=True)
    category = models.CharField(null=False, max_length=50, validators=[
        validate_tm_category])  # Misc
    item = models.CharField(null=False, max_length=50)
    unit = models.CharField(null=False, max_length=50)  # gallons, hours
    rate = models.DecimalField(max_digits=9, decimal_places=2)
    job = models.ForeignKey('jobs.Jobs', on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.item}"

class Signature(models.Model):
    id = models.BigAutoField(primary_key=True)
    type = models.CharField(null=False, max_length=50)
    change_order_id = models.IntegerField(null=False)
    signature = models.TextField(null=False)
    name = models.CharField(null=False, max_length=50)
    notes = models.CharField(null=True, blank=True, max_length=1000)
    date = models.DateField(null=True, blank=True)


class ChangeOrders(models.Model):
    id = models.BigAutoField(primary_key=True)
    job_number = models.ForeignKey('jobs.Jobs', on_delete=models.PROTECT)
    cop_number = models.IntegerField(default=0)
    is_t_and_m = models.BooleanField(default=False)
    description = models.CharField(null=True, max_length=700)
    date_sent = models.DateField(null=True, blank=True)
    date_approved = models.DateField(null=True, blank=True)
    gc_number = models.CharField(null=True, max_length=20, blank=True)
    is_approved = models.BooleanField(default=False)
    is_closed = models.BooleanField(default=False)
    notes = models.CharField(null=True, max_length=1000, blank=True)
    is_work_complete = models.BooleanField(default=False)
    is_ticket_signed = models.BooleanField(default=False)
    date_signed = models.DateField(null=True, blank=True)
    date_week_ending = models.DateField(null=True, blank=True)
    ticket_description = models.CharField(
        null=True, max_length=2000, blank=True)
    materials_used = models.CharField(null=True, max_length=2000, blank=True)
    price = models.DecimalField(
        max_digits=9, decimal_places=2, null=True, blank=True)
    full_description = models.CharField(null=True, max_length=2000, blank=True)
    is_approved_to_bill = models.BooleanField(default=False)
    sent_to = models.CharField(null=True, max_length=2000, blank=True)
    is_printed = models.BooleanField(default=False)
    is_old_form_printed = models.BooleanField(default=False)
    digital_ticket_signed_date = models.DateField(null=True, blank=True)
    approval_explanation = models.TextField(null=True, blank=True)
    price_before_bond = models.DecimalField(
        max_digits=9, decimal_places=2, null=True, blank=True)
    created_by_subcontractor = models.ForeignKey('subcontractors.Subcontractors', on_delete=models.PROTECT,null=True,blank=True)
    originated_in_management_console = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.job_number} {self.cop_number}"

    def status(self):
        status = "Not Sent"
        if self.is_closed:
            status = "Voided"
        else:
            if self.is_approved:
                if self.is_approved_to_bill:
                    status = "Approved"
                else:
                    status = "Informal Approval"
            elif self.date_sent:
                status = "Sent to GC"
            else:
                if self.is_t_and_m:
                    if self.is_ticket_signed:
                        tmproposal = TMProposal.objects.filter(change_order=self).first()
                        if tmproposal:
                            if tmproposal.date_sent_for_approval:
                                status="PM Review"
                            else:
                                status="Proposal in Progress"
                        else:
                            status = "Ticket Signed"
                    else:
                        if self.need_ticket() == True and self.is_printed == False:
                            status = "Ticket Not Completed"
                        else:
                            status = "Ticket Not Signed"
        return status

    def need_ticket(self):
        if self.is_t_and_m == True:
            if self.is_ticket_signed == False:
                if EWT.objects.filter(change_order=self).exists():
                    return False
                else:
                    return True
            else:
                return False
        else:
            return False

    def needs_ticket_signed(self):
        if self.is_t_and_m == True:
            if self.is_ticket_signed == False:
                return True
            else:
                return False
        else:
            return False

    def digital_ticket_completed(self):
        if EWT.objects.filter(change_order=self).exists():
            return True
        else:
            return False

class ChangeOrderNotes(models.Model):
    id = models.BigAutoField(primary_key=True)
    cop_number = models.ForeignKey('changeorder.ChangeOrders', on_delete=models.PROTECT)
    date = models.DateField(null=True, blank=True)
    user = models.ForeignKey(employees.models.Employees, on_delete=models.PROTECT)
    note = models.CharField(null=True, max_length=2000)

class ClientJobRoles(models.Model):
    id = models.BigAutoField(primary_key=True)
    employee = models.ForeignKey(
        'jobs.ClientEmployees', on_delete=models.PROTECT, related_name='roles')
    job = models.ForeignKey('jobs.Jobs', on_delete=models.PROTECT)
    # Submittals, #Change Orders, anything else
    #currently, "Change Orders" is used to determine who receives change order proposals for a job
    #i am adding "Extra Work Tickets" to determine who receives extra work tickets, in advance of price
    role = models.CharField(max_length=100)
    notes = models.CharField(max_length=2000, blank=True)

    def __str__(self):
        return f"{self.job} {self.role} {self.employee}"

class TempRecipients(models.Model):
    id = models.BigAutoField(primary_key=True)
    person = models.ForeignKey('jobs.ClientEmployees', on_delete=models.PROTECT)
    changeorder = models.ForeignKey(ChangeOrders, on_delete=models.PROTECT)
    default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.person} {self.changeorder}"

class TempRecipientsCOPList(models.Model):
    id = models.BigAutoField(primary_key=True)
    person = models.ForeignKey('jobs.ClientEmployees', on_delete=models.PROTECT)
    job = models.ForeignKey('jobs.Jobs', on_delete=models.PROTECT)
    default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.person} {self.job}"

class EWT(models.Model):
    id = models.BigAutoField(primary_key=True)
    change_order = models.ForeignKey(ChangeOrders, on_delete=models.PROTECT)
    week_ending = models.DateField()
    notes = models.CharField(null=True, max_length=2000)
    completed_by = models.CharField(null=True, max_length=150)
    recipient = models.CharField(null=True, max_length=150)

    def __str__(self):
        return f"{self.change_order.job_number} {self.change_order}"

class EWTicket(models.Model):
    id = models.BigAutoField(primary_key=True)
    master = models.ForeignKey(
        TMPricesMaster, on_delete=models.PROTECT, null=True, related_name='ewtmaster')
    EWT = models.ForeignKey(EWT, on_delete=models.PROTECT)
    category = models.CharField(null=True, max_length=50, validators=[
                                validate_tm_category])  # DONT USE # labor, material, equipment, bond, inventory
    employee = models.ForeignKey('employees.Employees', on_delete=models.PROTECT, null=True)
    monday = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    tuesday = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    wednesday = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    thursday = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    friday = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    saturday = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    sunday = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    ot = models.BooleanField(default=False)
    description = models.CharField(null=True, max_length=2000)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    units = models.CharField(null=True, max_length=50)
    custom_employee = models.CharField(max_length=150,null=True,blank=True)

    def __str__(self):
        return f"{self.EWT} {self.master}"

class TMProposal(models.Model):
    id = models.BigAutoField(primary_key=True)
    change_order = models.ForeignKey('changeorder.ChangeOrders', on_delete=models.PROTECT)
    total = models.DecimalField(
        max_digits=8, decimal_places=2, blank=True, null=True)
    notes = models.CharField(null=True, max_length=2000)
    ticket = models.ForeignKey(EWT, on_delete=models.PROTECT, null=True, blank=True)
    date_sent_for_approval = models.DateField(null=True, blank=True)
    date_approved_internally = models.DateField(null=True, blank=True)
    approved_by = models.ForeignKey(
        employees.models.Employees,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_tm_proposals"
    )
    status = models.CharField(
        max_length=50,
        default="Draft"
    )
    week_ending = models.DateField(null=True)
    completed_by = models.CharField(null=True, max_length=150)

    def __str__(self):
        return f"{self.change_order}"

class TMList(models.Model):  # one entry for each line item of t&m bill
    id = models.BigAutoField(primary_key=True)
    change_order = models.ForeignKey('changeorder.ChangeOrders', on_delete=models.PROTECT)
    # painter name, promar 200, etc. Called Item on the price breakdown
    description = models.CharField(null=False, max_length=500)
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    units = models.CharField(null=False, max_length=10)
    rate = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    total = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    category = models.CharField(null=False, max_length=50, validators=[
                                validate_tm_category])  # labor, material, equipment, bond, inventory
    category2 = models.CharField(
        null=False, max_length=200)  # interior latex eg-shell
    proposal = models.ForeignKey(TMProposal, on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.change_order} {self.description}"

class ChangeOrderApprovers(models.Model):
    id = models.BigAutoField(primary_key=True)

    job = models.ForeignKey(
        'jobs.Jobs',
        on_delete=models.CASCADE,
        related_name="changeorder_approvers"
    )

    approver = models.ForeignKey(
        employees.models.Employees,
        on_delete=models.CASCADE
    )

    def __str__(self):
        return f"{self.job.job_number} - {self.approver}"