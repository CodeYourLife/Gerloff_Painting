from django.db import models
from django.core.exceptions import ValidationError
from equipment.models import Vendors, VendorContact
import employees.models
from datetime import date

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
	requested_off_rent = models.BooleanField(default=False)
	def __str__(self):
		return f"{self.job_number} {self.item}"


	def next_period(self):
		if self.off_rent_date:
			return ""
		else:
			today = date.today()
			daysonrent = (today - self.on_rent_date).days + 1
			print(daysonrent)
			while daysonrent > 28:
				daysonrent -= 28
			if daysonrent >2 and daysonrent < 8:
				return str("Another Week Starts in " + str(8- daysonrent) + " Days")
			if daysonrent >7 and daysonrent < 15:
				return str("Another Week Starts in " + str(15- daysonrent) + " Days")
			elif daysonrent > 14 and daysonrent < 29:
				return str("Another Month Starts in " + str(29 - daysonrent) + " Days")
			else: return ""

	def current_duration(self):
		if self.off_rent_date:
			daysonrent = (self.off_rent_date - self.on_rent_date).days + 1
		else:
			today = date.today()
			daysonrent = (today - self.on_rent_date).days + 1
		months= 0
		duration = ""
		while daysonrent > 28:
			months += 1
			duration = str(str(months) + " Months ")
			daysonrent -= 28
		if daysonrent < 3:
			return str(duration + str(daysonrent) + " Days ")
		elif daysonrent < 8:
			return str(duration + "1 Week ")
		elif daysonrent < 10:
			return str(duration + "1 Week " + str(daysonrent -7) + " Days")
		elif daysonrent < 15:
			return str(duration + "2 Weeks ")
		elif daysonrent < 17:
			return str(duration + "2 Weeks " + str(daysonrent-14) + " Days")
		else:
			months += 1
			return str(str(months) + " Months")

	def colorize(self):
		if self.off_rent_date:
			return False
		else:
			today = date.today()
			daysonrent = (today - self.on_rent_date).days + 1
			print(daysonrent)
			while daysonrent > 28:
				daysonrent -= 28
			if daysonrent > 14 and daysonrent < 29:
				remaining = 29 - daysonrent
				if remaining <6:
					return True
				else:
					return False
			else: return False


	def colorize(self):
		if self.off_rent_date:
			return False
		else:
			today = date.today()
			daysonrent = (today - self.on_rent_date).days + 1
			print(daysonrent)
			while daysonrent > 28:
				daysonrent -= 28
			if daysonrent > 14 and daysonrent < 29:
				remaining = 29 - daysonrent
				if remaining <6:
					return True
				else:
					return False
			else: return False


class RentalNotes(models.Model):
    id = models.BigAutoField(primary_key=True)
    rental = models.ForeignKey(Rentals, on_delete=models.PROTECT)
    date = models.DateField(null=True, blank=True)
    user = models.ForeignKey(employees.models.Employees, on_delete=models.PROTECT)
    note = models.CharField(null=True, max_length=2000)
