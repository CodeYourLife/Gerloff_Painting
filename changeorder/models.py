from django.db import models
from django.core.exceptions import ValidationError

def validate_tm_category(value):
    if value == "Labor" or value == "Material" or value == "Equipment" or value == "Inventory" or value == "Misc" or value == "Bond":
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

class Signature(models.Model):
    id = models.BigAutoField(primary_key=True)
    type = models.CharField(null=False, max_length=50)
    change_order_id = models.IntegerField(null=False)
    signature = models.CharField(null=False, max_length=10000)
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

    def __str__(self):
        return f"{self.job_number} {self.description}"

    def need_ticket(self):
        if self.is_t_and_m == True:
            if self.is_ticket_signed == False:
                if EWT.objects.filter(change_order=self).exists():
                    return "No"
                else:
                    return "Yes"
            else:
                return "No"
        else:
            return "N/A"

    def need_ticket_signed(self):
        if self.is_t_and_m == True:
            if self.is_ticket_signed == False:
                return "Yes"
            else:
                return "No"
        else:
            return "N/A"


class ChangeOrderNotes(models.Model):
    id = models.BigAutoField(primary_key=True)
    cop_number = models.ForeignKey('changeorder.ChangeOrders', on_delete=models.PROTECT)
    date = models.DateField(null=True, blank=True)
    user = models.CharField(null=True, max_length=20)
    note = models.CharField(null=True, max_length=2000)

class ClientJobRoles(models.Model):
    id = models.BigAutoField(primary_key=True)
    employee = models.ForeignKey(
        'jobs.ClientEmployees', on_delete=models.PROTECT, related_name='roles')
    job = models.ForeignKey('jobs.Jobs', on_delete=models.PROTECT)
    # Submittals, #Change Orders, anything else
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


class EWT(models.Model):
    id = models.BigAutoField(primary_key=True)
    change_order = models.ForeignKey(ChangeOrders, on_delete=models.PROTECT)
    week_ending = models.DateField()
    notes = models.CharField(null=True, max_length=2000)
    completed_by = models.CharField(null=True, max_length=150)

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

    def __str__(self):
        return f"{self.EWT} {self.master}"

class TMProposal(models.Model):
    id = models.BigAutoField(primary_key=True)
    change_order = models.ForeignKey('changeorder.ChangeOrders', on_delete=models.PROTECT)
    total = models.DecimalField(
        max_digits=8, decimal_places=2, blank=True, null=True)
    notes = models.CharField(null=True, max_length=2000)
    ticket = models.ForeignKey(EWT, on_delete=models.PROTECT)

class TMList(models.Model):  # one entry for each line item of t&m bill
    id = models.BigAutoField(primary_key=True)
    change_order = models.ForeignKey('changeorder.ChangeOrders', on_delete=models.PROTECT)
    # painter name, promar 200, etc. Called Item on the price breakdown
    description = models.CharField(null=False, max_length=500)
    quantity = models.DecimalField(
        max_digits=8, decimal_places=2, blank=True, null=True)
    units = models.CharField(null=False, max_length=10)
    rate = models.DecimalField(
        max_digits=8, decimal_places=2, blank=True, null=True)
    total = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, null=True)
    category = models.CharField(null=False, max_length=50, validators=[
                                validate_tm_category])  # labor, material, equipment, bond, inventory
    category2 = models.CharField(
        null=False, max_length=200)  # interior latex eg-shell
    proposal = models.ForeignKey(TMProposal, on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.change_order} {self.item}"
