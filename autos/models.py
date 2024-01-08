from django.db import models
from employees.models import *

# Create your models here.
class Vehicle(models.Model):
    current_driver = models.ForeignKey(Employees, on_delete=models.PROTECT)
    vin_number = models.CharField(max_length=2000, null=True, blank=True)
    date_purchased = models.DateField()
    mileage = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    notes = models.CharField(max_length=2000, null=True, blank=True)

class VehicleMaintenance(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT)
    description = models.CharField(max_length=2000, null=True, blank=True)
    date_completed = models.DateField()
    mileage_increment = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    notes = models.CharField(max_length=2000, null=True, blank=True)

class RequiredMaintenance(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT)
    maintenance_type = models.CharField(max_length=2000, null=True, blank=True)
    maintenance_frequency = models.CharField(max_length=2000, null=True, blank=True)

class VehicleNotes(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT)
    date = models.DateField(null=True, blank=True)
    user = models.ForeignKey('employees.Employees', on_delete=models.PROTECT)
    note = models.CharField(null=True, max_length=2000)