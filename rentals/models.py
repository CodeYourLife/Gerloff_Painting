from django.db import models
from django.core.exceptions import ValidationError
from equipment.models import Vendors, VendorContact


class Rentals(models.Model):
	id = models.BigAutoField(primary_key=True)
	company = models.ForeignKey(Vendors, on_delete=models.PROTECT, null=True, blank=True)
	item = models.CharField(null=True, max_length=250)
	purchase_order = models.CharField(null=True, max_length=250,blank=True)
	on_rent_date = models.DateField(null=True, blank=True)
	off_rent_date = models.DateField(null=True, blank=True)
	off_rent_number = models.CharField(null=True, max_length=250, blank=True)
	notes = models.CharField(null=True, max_length=2000, blank=True)
	job_number = models.ForeignKey('jobs.Jobs', on_delete=models.PROTECT)
	day_price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
	week_price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
	month_price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
	is_closed = models.BooleanField(default=False) #once accounting has invoiced
	rep = models.ForeignKey(VendorContact, on_delete=models.PROTECT, null=True, blank=True)
	def __str__(self):
		return f"{self.job_number} {self.item}"


class RentalNotes(models.Model):
    id = models.BigAutoField(primary_key=True)
    rental = models.ForeignKey(Rentals, on_delete=models.PROTECT)
    date = models.DateField(null=True, blank=True)
    user = models.CharField(null=True, max_length=50)
    note = models.CharField(null=True, max_length=2000)
