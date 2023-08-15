from django.db import models
from django.core.exceptions import ValidationError
from jobs.models import Jobs
from equipment.models import Vendors


class Rentals(models.Model):
	id = models.BigAutoField(primary_key=True)
	company = models.ForeignKey(Vendors, on_delete=models.PROTECT, null=True, blank=True)
	item = models.CharField(null=True, max_length=250)
	purchase_order = models.CharField(null=True, max_length=250,blank=True)
	on_rent_date = models.DateField(null=True, blank=True)
	off_rent_date = models.DateField(null=True, blank=True)
	off_rent_number = models.CharField(null=True, max_length=250, blank=True)
	notes = models.CharField(null=True, max_length=2000)
	job_number = models.ForeignKey(Jobs, on_delete=models.PROTECT)
	day_price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
	week_price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
	month_price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
	is_closed = models.BooleanField(default=False) #once accounting has invoiced
	def __str__(self):
		return f"{self.job_number} {self.item}"