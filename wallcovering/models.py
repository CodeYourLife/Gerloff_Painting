from django.db import models
from equipment.models import Vendors



class Wallcovering(models.Model):
    id = models.BigAutoField(primary_key=True)
    job_number = models.ForeignKey('jobs.Jobs', on_delete=models.PROTECT)
    code = models.CharField(null=True, max_length=10)  # wc1, etc.
    vendor = models.ForeignKey(Vendors, on_delete=models.PROTECT)
    pattern = models.CharField(null=True, max_length=2000)
    estimated_quantity = models.IntegerField(default=0, blank=True)
    estimated_unit = models.CharField(null=True, max_length=20, blank=True)
    cut_charge = models.CharField(null=True, max_length=1000, blank=True)
    roll_width = models.CharField(null=True, max_length=50, blank=True)
    vertical_repeat = models.CharField(null=True, max_length=50, blank=True)
    is_random_reverse = models.BooleanField(default=False)
    is_repeat = models.BooleanField(default=False)
    notes = models.CharField(null=True, max_length=2000, blank=True)
    qnty_ordered = models.IntegerField(blank=True, null=True)  # not used
    qnty_received = models.IntegerField(blank=True, null=True)  # not used
    packages_received = models.IntegerField(blank=True, null=True)  # not used
    packages_sent = models.IntegerField(blank=True, null=True)  # not used

    def __str__(self):
        return f"{self.job_number} {self.code}"

    def quantity_ordered(self):
        totalquantity = 0
        for x in OrderItems.objects.filter(wallcovering=self):
            totalquantity = totalquantity + x.quantity
        return totalquantity

    def quantity_received(self):
        totalquantity = 0
        for x in OrderItems.objects.filter(wallcovering=self):
            totalquantity = totalquantity + x.quantity_received()
        return totalquantity

    def packages_received(self):
        totalquantity = 0
        # these are all orders with packages
        for y in models.ForeignObject('jobs.Orders').objects.filter(orderitems2__isnull=False, job_number=self.job_number, orderitems2__wallcovering=self).distinct():
            totalquantity = totalquantity + y.packages_received()
        return totalquantity

    def packages_sent(self):
        totalquantity = 0
        totalquantity = 0
        # these are all orders with packages
        for y in models.ForeignObject('jobs.Orders').objects.filter(orderitems2__isnull=False, job_number=self.job_number, orderitems2__wallcovering=self).distinct():
            totalquantity = totalquantity + y.packages_sent()
        return totalquantity


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

    def __str__(self):
        return f"{self.delivery.order.job_number} {self.contents}"

    def total_sent(self):
        totalquantity = 0
        for x in OutgoingItem.objects.filter(package=self):
            totalquantity = totalquantity+x.quantity_sent
        return totalquantity


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
