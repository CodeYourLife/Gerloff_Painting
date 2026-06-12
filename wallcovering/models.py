from django.db import models
from django.apps import apps
from equipment.models import Vendors
import employees.models
from decimal import Decimal

class Wallcovering(models.Model):
    id = models.BigAutoField(primary_key=True)
    job_number = models.ForeignKey('jobs.Jobs', on_delete=models.PROTECT)
    code = models.CharField(null=True, max_length=100,blank=True)
    vendor = models.ForeignKey(Vendors, on_delete=models.PROTECT,null=True)
    pattern = models.CharField(null=True, max_length=2000,blank=True)
    estimated_quantity = models.IntegerField(default=0, blank=True,null=True)
    estimated_unit = models.CharField(null=True, max_length=20, blank=True)
    cut_charge = models.CharField(null=True, max_length=1000, blank=True)
    roll_width = models.CharField(null=True, max_length=50, blank=True)
    vertical_repeat = models.CharField(null=True, max_length=50, blank=True)
    is_random_reverse = models.BooleanField(default=False)
    is_repeat = models.BooleanField(default=False)
    notes = models.CharField(null=True, max_length=2000, blank=True)
    roll_length = models.CharField(null=True, max_length=50, blank=True)
    is_owner_furnished = models.BooleanField(default=False)
    increment_requirement = models.CharField(null=True, max_length=500, blank=True)
    is_void = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.job_number} {self.code}"

    def quantity_ordered(self):
        total = Decimal("0.00")
        for item in OrderItems.objects.filter(wallcovering=self):
            total += item.quantity or Decimal("0.00")
        return total

    def ordered_unit(self):
        item = OrderItems.objects.filter(wallcovering=self).first()
        return item.unit if item else self.estimated_unit

    def quantity_received(self):
        total = Decimal("0.00")
        for item in OrderItems.objects.filter(wallcovering=self):
            total += item.quantity_received()
        return total

    def packages_received(self):
        totalquantity = 0

        for package in Packages.objects.filter(orderitem__wallcovering=self):
            totalquantity += package.quantity_received or 0

        return totalquantity

    def packages_sent(self):
        totalquantity = 0

        for package in Packages.objects.filter(orderitem__wallcovering=self):
            totalquantity += package.total_sent()

        return totalquantity

    def sent_percentage(self):
        received = self.packages_received()
        sent = self.packages_sent()

        if received == 0:
            return 0

        return round((sent / received) * 100)

    def wallcovering_status(self):
        if self.is_owner_furnished:
            return "Owner Furnished"

        ordered = self.quantity_ordered()
        received = self.quantity_received()
        packages_received = self.packages_received()
        packages_sent = self.packages_sent()

        if ordered <= 0:
            return "Not Ordered"

        if received <= 0:
            return "Ordered"

        # PARTIAL RECEIVED + SOME SENT
        if received < ordered and packages_sent > 0:
            return "Received Partial, Sent to Job"

        # FULLY SENT
        if packages_received > 0 and packages_sent >= packages_received:
            return "Sent to Job"

        # PARTIALLY SENT
        if packages_received > 0 and packages_sent > 0:
            return "Partially Sent to Job"

        # PARTIAL RECEIVED
        if received < ordered:
            return "Received Partial"

        return "Received"

    def display_quantity(self):
        if self.quantity_ordered() > 0:
            return f"{self.quantity_ordered():,.2f} {self.ordered_unit() or ''}"

        return f"{self.estimated_quantity:,} {self.estimated_unit or ''}"

    def submittal_status(self):
        if self.is_owner_furnished:
            return "Owner Furnished"

        from submittals.models import SubmittalItems, SubmittalApprovals

        matching_items = SubmittalItems.objects.filter(
            wallcovering_id=self,
            is_no_longer_used=False
        )

        if not matching_items.exists():
            return "Not Submitted"

        linked_approvals = SubmittalApprovals.objects.filter(
            submittalitem__in=matching_items,
            submittal__isnull=False
        )

        unlinked_approvals_exist = SubmittalApprovals.objects.filter(
            submittalitem__in=matching_items,
            submittal__isnull=True
        ).exists()

        items_without_approvals_exist = matching_items.filter(
            submittalapprovals__isnull=True
        ).exists()

        has_submission_problem = (
                unlinked_approvals_exist
                or items_without_approvals_exist
        )

        # Nothing has actually been submitted yet
        if not linked_approvals.exists():
            return "Not Submitted"

        # Some items are submitted, but at least one item still needs to be submitted
        if has_submission_problem:
            return "Partially Submitted"

        # Everything has been submitted and all linked approvals are approved
        if not linked_approvals.exclude(is_approved=True).exists():
            return "Approved"

        # Everything has been submitted, but something is pending/rejected
        return "Submitted"

    def ordering_status(self):
        if self.is_owner_furnished:
            return "Owner Furnished"

        ordered = self.quantity_ordered()
        received = self.quantity_received()

        if ordered <= 0:
            return "Not Ordered"

        if received <= 0:
            return "Ordered"

        if received < ordered:
            return "Partially Received"

        return "Received"

    def sent_status(self):
        if self.is_owner_furnished:
            return "Owner Furnished"

        received = self.packages_received()
        sent = self.packages_sent()

        if received <= 0 or sent <= 0:
            return "Not Sent"

        if sent < received:
            return "Partially Sent"

        return "Sent to Job"


class WallcoveringPricing(models.Model):
    id = models.BigAutoField(primary_key=True)
    wallcovering = models.ForeignKey(Wallcovering, on_delete=models.PROTECT)
    quote_date = models.DateField()
    min_yards = models.IntegerField(blank=True, null=True)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    unit = models.CharField(null=True, max_length=50, blank=True)
    note = models.CharField(null=True, max_length=2000, blank=True)


class OrderItems(models.Model):  # usually just one of these per order
    id = models.BigAutoField(primary_key=True)
    order = models.ForeignKey(
        'jobs.Orders', on_delete=models.PROTECT, related_name='orderitems2')
    wallcovering = models.ForeignKey(
        Wallcovering, on_delete=models.PROTECT, related_name='orderitems1', null=True, blank=True)
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True, verbose_name='Quantity Ordered')
    unit = models.CharField(null=True, max_length=10)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    item_description = models.CharField(null=True, max_length=100)
    item_notes = models.CharField(null=True, max_length=1000, blank=True)
    is_satisfied = models.BooleanField(default=False)  # all has been received
    link_to_wallcovering = models.ForeignKey(
        Wallcovering, on_delete=models.PROTECT, related_name='linked_orderitems', null=True, blank=True)

    def __str__(self):
        return f"{self.item_description}"

    def quantity_received(self):
        totalquantity = 0
        for x in ReceivedItems.objects.filter(order_item=self):
            totalquantity = totalquantity+x.quantity
        return totalquantity


# one instance when receiving material. actual items listed below
class WallcoveringDelivery(models.Model):
    id = models.BigAutoField(primary_key=True)
    order = models.ForeignKey(
        'jobs.Orders', on_delete=models.PROTECT, related_name="foreign_wallcoveringdelivery")
    date = models.DateField(null=True, blank=True)
    notes = models.CharField(null=True, max_length=2000,
                             blank=True)  # box, bolt, bucket

    def __str__(self):
        return f"{self.date} {self.order.job_number}"


class ReceivedItems(models.Model):
    id = models.BigAutoField(primary_key=True)
    wallcovering_delivery = models.ForeignKey(
        WallcoveringDelivery, on_delete=models.PROTECT, related_name="foreign_receiveditems1")
    order_item = models.ForeignKey(
        OrderItems, on_delete=models.PROTECT, related_name="foreign_receiveditems2")  # j-trim
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return f"{self.wallcovering_delivery.date} {self.order_item.item_description}"


class Packages(models.Model):
    id = models.BigAutoField(primary_key=True)
    delivery = models.ForeignKey(
        WallcoveringDelivery, on_delete=models.PROTECT, related_name="foreign_packages")
    type = models.CharField(null=True, max_length=200)  # box, bolt, bucket
    # Wallprotection, FRP glue,
    contents = models.CharField(null=True, max_length=2000)
    quantity_received = models.IntegerField(
        default=0, verbose_name='Packages Received')  # 3
    notes = models.CharField(null=True, max_length=2000, blank=True)
    orderitem = models.ForeignKey(
        OrderItems, on_delete=models.PROTECT, related_name="packages")

    def __str__(self):
        return f"{self.delivery.order.job_number} {self.contents}"

    def total_sent(self):
        totalquantity = 0
        for x in OutgoingItem.objects.filter(package=self):
            totalquantity = totalquantity+x.quantity_sent
        return totalquantity

    def quantity_remaining(self):
        return (self.quantity_received or 0) - self.total_sent()


class OutgoingWallcovering(models.Model):
    id = models.BigAutoField(primary_key=True)
    job_number = models.ForeignKey(
        'jobs.Jobs', on_delete=models.PROTECT, blank=True, null=True)
    delivered_by = models.CharField(null=True, max_length=200)
    notes = models.CharField(null=True, max_length=2000)
    date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.job_number} {self.date}"


class OutgoingItem(models.Model):
    id = models.BigAutoField(primary_key=True)
    outgoing_event = models.ForeignKey(
        OutgoingWallcovering, on_delete=models.PROTECT)
    package = models.ForeignKey(Packages, on_delete=models.PROTECT)
    description = models.CharField(null=True, max_length=200)
    quantity_sent = models.IntegerField(
        default=0, verbose_name='Packages Sent to Job')

    def __str__(self):
        return f"{self.description}"

class WallcoveringNotes(models.Model):
    id = models.BigAutoField(primary_key=True)
    pattern = models.ForeignKey('Wallcovering', on_delete=models.PROTECT)
    order = models.ForeignKey('OrderItems', on_delete=models.PROTECT,null=True, blank=True)
    receipt = models.ForeignKey('WallcoveringDelivery', on_delete=models.PROTECT, null=True, blank=True)
    sent = models.ForeignKey('OutgoingWallcovering', on_delete=models.PROTECT, null=True, blank=True)
    date = models.DateField(null=True, blank=True)
    user = models.ForeignKey(employees.models.Employees, on_delete=models.PROTECT)
    note = models.CharField(null=True, max_length=2000)