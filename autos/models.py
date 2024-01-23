from django.db import models
from employees.models import *
import datetime
import datetime


# Create your models here.
class Vehicle(models.Model):
    current_driver = models.ForeignKey(Employees, on_delete=models.PROTECT, null=True, blank=True)
    vin_number = models.CharField(max_length=2000, null=True, blank=True)
    date_purchased = models.DateField(default=datetime.date.today)
    mileage = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    mileage_date = models.DateField(default=datetime.date.today)
    notes = models.CharField(max_length=2000, null=True, blank=True)
    in_service = models.BooleanField(default=False)
    current_service_location = models.CharField(max_length=2000, null=True, blank=True)
    is_sold = models.BooleanField(default=False)
    date_sold = models.DateField(null=True,blank=True)

    def oil_change_needed_miles(self):
        if RequiredMaintenance.objects.filter(vehicle=self, maintenance_type="Oil Change").exists():
            oil_change_requirements = RequiredMaintenance.objects.get(vehicle=self, maintenance_type="Oil Change")
            if oil_change_requirements.frequency_odometer:
                frequency = oil_change_requirements.frequency_odometer
                last_oil_change_miles = 0
                for x in VehicleMaintenance.objects.filter(vehicle=self,
                                                           required_maintenance_item=oil_change_requirements):
                    if x.mileage > last_oil_change_miles: last_oil_change_miles = x.mileage
                if self.mileage - last_oil_change_miles > frequency:
                    return True
                else:
                    return False
            else:
                return False
        else:
            return False

    def need_odometer(self):
        lapse = date.today() - self.mileage_date
        if lapse > 60:  # meaning they haven't updated the mileage in 60 days
            return True
        else:
            return False


class RequiredMaintenance(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT)
    maintenance_type = models.CharField(max_length=2000, null=True, blank=True)
    frequency_odometer = models.IntegerField(null=True, blank=True)
    frequency_months = models.IntegerField(null=True, blank=True)


class VehicleMaintenance(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT)
    required_maintenance_item = models.ForeignKey(RequiredMaintenance, on_delete=models.PROTECT, blank=True, null=True)
    description = models.CharField(max_length=2000, null=True, blank=True)
    date_completed = models.DateField()
    mileage = models.IntegerField()
    notes = models.CharField(max_length=2000, null=True, blank=True)
    vendor = models.CharField(max_length=2000, null=True, blank=True)


class VehicleNotes(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT)
    date = models.DateField()
    user = models.ForeignKey('employees.Employees', on_delete=models.PROTECT)
    note = models.CharField(max_length=2000)
