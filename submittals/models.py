from django.db import models
from jobs.models import Jobs
from wallcovering.models import Wallcovering
import employees.models
from django.db.models import Q, Max, Count

BOOKING_CREATED_NOTE = "Created at Booking"


def clear_booking_created_note(submittal_item, save=True):
    if (submittal_item.notes or "").strip() != BOOKING_CREATED_NOTE:
        return False

    submittal_item.notes = ""
    if save:
        submittal_item.save(update_fields=["notes"])

    return True


def delete_empty_booking_paint_submittal(new_submittal_item):
    if "paint" not in (new_submittal_item.description or "").lower():
        return 0

    booking_items = SubmittalItems.objects.filter(
        job_number=new_submittal_item.job_number,
        description="Paint Submittal",
        notes=BOOKING_CREATED_NOTE,
    ).exclude(
        id=new_submittal_item.id
    ).exclude(
        submittalapprovals__submittal__isnull=False
    ).distinct()

    deleted_count = 0

    for booking_item in booking_items:
        SubmittalItemNotes.objects.filter(submittalitem=booking_item).delete()
        SubmittalApprovals.objects.filter(
            submittalitem=booking_item,
            submittal__isnull=True,
        ).delete()
        booking_item.delete()
        deleted_count += 1

    return deleted_count


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
            is_approved__isnull=True,
            submittalitem__is_no_longer_used=False  # 👈 exclude “No Longer Used”
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

    def status(self):
        if self.is_no_longer_used:
            return "No Longer Used"
        else:
            approvals = SubmittalApprovals.objects.filter(
                submittalitem=self
            ).order_by('id')

            has_problem = approvals.filter(
                Q(submittal__isnull=True) | Q(is_approved__isnull=True)
            ).exists()

            if not approvals.exists():
                return "Submittal Required"

            elif has_problem:
                return "Not Approved"

            elif approvals.filter(is_approved=True).exists():
                return "Approved"

            else:
                return "Check Status"

class SubmittalApprovals(models.Model):
    id = models.BigAutoField(primary_key=True)
    submittal = models.ForeignKey(Submittals, on_delete=models.PROTECT,null=True,blank=True)
    submittalitem = models.ForeignKey(SubmittalItems, on_delete=models.PROTECT)
    is_approved = models.BooleanField(null=True,blank=True)
    notes = models.CharField(null=True, max_length=2000, blank=True)#reviewer notes
    quantity = models.IntegerField(default=0)
    date_reviewed = models.DateField(null=True, blank=True)
    item_notes = models.CharField(null=True, max_length=2000, blank=True)#item submitted


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
