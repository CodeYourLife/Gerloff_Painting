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
    notes = models.CharField(null=True, max_length=2000, blank=True)
    originated_in_management_console =models.BooleanField(default=False)

    def __str__(self):
        return f"{self.job_number} {self.description}"

    def status(self):
        from .models import SubmittalApprovals  # avoids circular import

        has_pending = SubmittalApprovals.objects.filter(
            submittal=self,
            is_approved__isnull=True
        ).exists()

        return "OPEN" if has_pending else "CLOSED"


class SubmittalItems(models.Model):
    id = models.BigAutoField(primary_key=True)
    wallcovering_id = models.ForeignKey(
        Wallcovering, on_delete=models.PROTECT, null=True)
    description = models.CharField(null=True, max_length=250)
    notes = models.CharField(null=True, max_length=2000, blank=True)
    is_no_longer_used = models.BooleanField(default=False)
    job_number = models.ForeignKey(Jobs, on_delete=models.PROTECT,null=True,blank=True)

    def __str__(self):
        return f"{self.job_number} {self.description}"


class SubmittalApprovals(models.Model):
    id = models.BigAutoField(primary_key=True)
    submittal = models.ForeignKey(Submittals, on_delete=models.PROTECT,null=True,blank=True)
    submittalitem = models.ForeignKey(SubmittalItems, on_delete=models.PROTECT)
    is_approved = models.BooleanField(null=True,blank=True)
    notes = models.CharField(null=True, max_length=2000, blank=True)
    quantity = models.IntegerField(default=0)
    date_reviewed = models.DateField(null=True, blank=True)


class SubmittalNotes(models.Model):
    id = models.BigAutoField(primary_key=True)
    submittal = models.ForeignKey(Submittals, on_delete=models.PROTECT,null=True,blank=True)
    date = models.DateField(null=True, blank=True)
    user = models.ForeignKey(employees.models.Employees, on_delete=models.PROTECT)
    note = models.CharField(null=True, max_length=2000)

class SubmittalApprovalNotes(models.Model):#NOT USED
    id = models.BigAutoField(primary_key=True)
    submittal = models.ForeignKey(Submittals, on_delete=models.PROTECT,null=True,blank=True)
    submittalapproval = models.ForeignKey(SubmittalApprovals, on_delete=models.PROTECT,null=True,blank=True)
    date = models.DateField(null=True, blank=True)
    user = models.ForeignKey(employees.models.Employees, on_delete=models.PROTECT)
    note = models.CharField(null=True, max_length=2000)

class SubmittalItemNotes(models.Model):
    id = models.BigAutoField(primary_key=True)
    submittal = models.ForeignKey(Submittals, on_delete=models.PROTECT,null=True,blank=True)
    submittalitem = models.ForeignKey(SubmittalItems, on_delete=models.PROTECT)
    date = models.DateField(null=True, blank=True)
    user = models.ForeignKey(employees.models.Employees, on_delete=models.PROTECT)
    note = models.CharField(null=True, max_length=2000)