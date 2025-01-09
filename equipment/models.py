from django.db import models
from django.core.exceptions import ValidationError
from employees.models import Employees


def validate_inventory_notes(value):
    if value == "Returned" or value == "Missing" or value == "Job" or value == "Service" or value == "Misc" or value == "Employee":
        return value
    else:
        raise ValidationError(
            "Category must be Returned, Missing, Job, Service, Employee, or Misc")


class VendorCategory(models.Model):  # Equipment Rental, Wallcovering Supplier
    id = models.BigAutoField(primary_key=True)
    category = models.CharField(null=True, max_length=250)

    def __str__(self):
        return f"{self.category}"


class Vendors(models.Model):
    id = models.BigAutoField(primary_key=True)
    company_name = models.CharField(null=True, max_length=250)
    category = models.ForeignKey(
        VendorCategory, on_delete=models.PROTECT, null=True, blank=True)
    company_phone = models.CharField(null=True, max_length=20, blank=True)
    company_email = models.EmailField(null=True, blank=True)

    def __str__(self):
        return f"{self.company_name}-{self.category.category}"


class VendorContact(models.Model):
    id = models.BigAutoField(primary_key=True)
    company = models.ForeignKey(
        Vendors, on_delete=models.PROTECT, null=True, blank=True)
    name = models.CharField(null=True, max_length=250)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(null=True, max_length=20)

    def __str__(self):
        return f"{self.company} {self.name}"


class InventoryType(models.Model):
    id = models.BigAutoField(primary_key=True)
    type = models.CharField(null=True, max_length=50)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.type}"


class InventoryItems(models.Model):
    id = models.BigAutoField(primary_key=True)
    type = models.ForeignKey(InventoryType, on_delete=models.PROTECT)
    name = models.CharField(null=True, max_length=100)

    def __str__(self):
        return f"{self.type} {self.name}"


class InventoryItems2(models.Model):
    id = models.BigAutoField(primary_key=True)
    type = models.ForeignKey(InventoryItems, on_delete=models.PROTECT)
    name = models.CharField(null=True, max_length=100)

    def __str__(self):
        return f"{self.type} {self.name}"


class InventoryItems3(models.Model):
    id = models.BigAutoField(primary_key=True)
    type = models.ForeignKey(InventoryItems2, on_delete=models.PROTECT)
    name = models.CharField(null=True, max_length=100)

    def __str__(self):
        return f"{self.type} {self.name}"


class InventoryItems4(models.Model):
    id = models.BigAutoField(primary_key=True)
    type = models.ForeignKey(InventoryItems3, on_delete=models.PROTECT)
    name = models.CharField(null=True, max_length=100)

    def __str__(self):
        return f"{self.type} {self.name}"


class Inventory(models.Model):
    id = models.BigAutoField(primary_key=True)
    number = models.CharField(null=True, max_length=50, blank=True)
    item = models.CharField(null=True, max_length=2000)
    inventory_type = models.ForeignKey(InventoryType, on_delete=models.PROTECT)
    storage_location = models.CharField(null=True, max_length=50, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    purchase_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    purchased_from = models.ForeignKey(
        Vendors, on_delete=models.PROTECT, blank=True, null=True, related_name='inventory1')
    purchased_by = models.CharField(null=True, max_length=250, blank=True)
    serial_number = models.CharField(null=True, max_length=250, blank=True)
    po_number = models.CharField(null=True, max_length=250, blank=True)
    is_labeled = models.BooleanField(default=False)
    # Checked Out, Missing, Available, Service
    status = models.CharField(null=True, max_length=250, blank=True)
    date_out = models.DateField(null=True, blank=True)
    date_returned = models.DateField(null=True, blank=True)
    job_number = models.ForeignKey(
        'jobs.Jobs', on_delete=models.PROTECT, blank=True, null=True)
    # job_number is the foreign key to the job number in Jobs
    notes = models.CharField(null=True, max_length=2000, blank=True)
    service_vendor = models.ForeignKey(
        Vendors, on_delete=models.PROTECT, blank=True, null=True, related_name='inventory2')
    batch = models.CharField(null=True, max_length=50,
                             blank=True)  # outgoing or incoming
    assigned_to = models.ForeignKey(
        Employees, on_delete=models.PROTECT, blank=True, null=True)
    needs_label = models.BooleanField(default=True)
    is_closed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.id} {self.inventory_type} {self.item}"


class InventoryNotes(models.Model):
    id = models.BigAutoField(primary_key=True)
    inventory_item = models.ForeignKey(Inventory, on_delete=models.PROTECT)
    date = models.DateField(null=True, blank=True)
    user = models.ForeignKey('employees.Employees', on_delete=models.PROTECT)
    note = models.CharField(null=True, max_length=2000)
    category = models.CharField(null=True, max_length=2000, validators=[
        validate_inventory_notes])  # newjob, service, misc, returned
    job_number = models.CharField(null=True, max_length=5, blank=True)
    # either job name, or service vendor
    job_name = models.CharField(null=True, max_length=2000, blank=True)


class BatchInventory(models.Model):
    id = models.BigAutoField(primary_key=True)
    job_number = models.ForeignKey(
        'jobs.Jobs', on_delete=models.PROTECT, related_name='batch1')
    date = models.DateField(null=True, blank=True)
    status = models.CharField(null=True, max_length=50)  # incoming or outgoing
    # true means it is the latest one
    current = models.BooleanField(default=False)


class PickupRequest(models.Model):
    id = models.BigAutoField(primary_key=True)
    date = models.DateField()
    job_number = models.ForeignKey('jobs.Jobs', on_delete=models.PROTECT)
    request_notes = models.CharField(null=True, blank=True,max_length=10000)
    completed_notes = models.CharField(null=True, blank=True,max_length=10000)
    completed_date = models.DateField(null=True, blank=True)
    is_closed = models.BooleanField(default=False)
    all_items = models.BooleanField(default=False)
    confirmed = models.BooleanField(default=False)
    requested_by = models.ForeignKey('employees.Employees', on_delete=models.PROTECT,null=True, blank=True)
    remove_trash = models.BooleanField(default=False)
    trash_removed = models.BooleanField(default=False)
    save_leftover_paint = models.BooleanField(default=False)
    leftover_paint_saved = models.BooleanField(default=False)


class PickupRequestItems(models.Model):
    id = models.BigAutoField(primary_key=True)
    request = models.ForeignKey('PickupRequest', on_delete=models.PROTECT)
    item = models.ForeignKey('Inventory', on_delete=models.PROTECT,related_name='pickuprequested')
    returned = models.BooleanField(default=False)


class BatchInventoryItems(models.Model):
    id = models.BigAutoField(primary_key=True)
    batchinventory = models.ForeignKey(
        BatchInventory, on_delete=models.PROTECT, related_name='batchitem1')
    inventory = models.ForeignKey(Inventory, on_delete=models.PROTECT, related_name='batchitem2')


