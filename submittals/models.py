from django.db import models
from jobs.models import Jobs
from wallcovering.models import Wallcovering
import employees.models


class Submittals(models.Model):
    id = models.BigAutoField(primary_key=True)
    job_number = models.ForeignKey(Jobs, on_delete=models.PROTECT)
    description = models.CharField(null=True, max_length=2000)
    submittal_number = models.IntegerField(default=0)
    date_sent = models.DateField(null=True, blank=True)
    date_returned = models.DateField(null=True, blank=True)
    is_closed = models.BooleanField(default=False)
    notes = models.CharField(null=True, max_length=2000, blank=True)
    status = models.CharField(null=True, max_length=20)

    def __str__(self):
        return f"{self.job_number} {self.description}"


class SubmittalItems(models.Model):
    id = models.BigAutoField(primary_key=True)
    submittal = models.ForeignKey(Submittals, on_delete=models.PROTECT)
    wallcovering_id = models.ForeignKey(
        Wallcovering, on_delete=models.PROTECT, null=True)
    description = models.CharField(null=True, max_length=250)
    quantity = models.IntegerField(default=0)
    is_closed = models.BooleanField(default=False)
    notes = models.CharField(null=True, max_length=2000, blank=True)

    def __str__(self):
        return f"{self.submittal} {self.description}"

class SubmittalNotes(models.Model):
    id = models.BigAutoField(primary_key=True)
    submittal = models.ForeignKey(Submittals, on_delete=models.PROTECT)
    date = models.DateField(null=True, blank=True)
    user = models.ForeignKey(employees.models.Employees, on_delete=models.PROTECT)
    note = models.CharField(null=True, max_length=2000)
