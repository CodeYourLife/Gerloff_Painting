from console.models import *
import django_tables2 as tables
from console.models import Orders, OrderItems, Packages, WallcoveringDelivery, ReceivedItems, OutgoingWallcovering, OutgoingItem
from django_filters.views import FilterView
from django_tables2.utils import A

from .filters import OrderItemsFilter



class WallcoveringPriceTable(tables.Table):
    class Meta:
            model = WallcoveringPricing
            template_name = "django_tables2/bootstrap.html"
            fields = ("quote_date", "min_yards", "price", "unit", "note")

class OutgoingWallcoveringTable(tables.Table):
    edit = tables.TemplateColumn('<a href="{% url "job_page" record.outgoing_event.job_number.job_number %}">{{record.outgoing_event.date}}</a>', verbose_name="Date")

    class Meta:
            model = OutgoingItem
            template_name = "django_tables2/bootstrap.html"
            fields = ("edit", "outgoing_event.job_number.job_name", "outgoing_event.delivered_by", "outgoing_event.notes","package.type", "package.contents", "description","quantity_sent")


class OrderItemsTable(tables.Table):
    edit = tables.TemplateColumn('<a href="{% url "wallcovering_order" record.order.id %}">{{record.order.date_ordered}}</a>')
    receive = tables.TemplateColumn('<a href="{% url "wallcovering_receive" record.order.id %}">Receive Now</a>')

    class Meta:
        model = OrderItems
        template_name = "django_tables2/bootstrap.html"
        fields = ('edit','item_description','quantity', 'quantity_received','unit', 'item_notes','receive')

class OrdersTable(tables.Table):
    po_link= tables.TemplateColumn('<a href="{% url "wallcovering_order" record.id %}">{{record.po_number}}</a>', verbose_name="PO Number")

    class Meta:
        model = Orders
        template_name = "django_tables2/bootstrap.html"
        fields = ('po_link', 'job_number', 'vendor', 'description', 'date_ordered', 'notes')

class CombinedOrdersTable(tables.Table):
    ponumber = tables.TemplateColumn('<a href="{% url "wallcovering_order" record.order.id %}">{{record.order.po_number}}</a>')
    jobnumber = tables.TemplateColumn('<a href="{% url "job_page" record.order.job_number.job_number %}">{{record.order.job_number}}</a>')
    order__packages_received = tables.Column(verbose_name= 'Packages Received')
    order__packages_sent = tables.Column(verbose_name='Packages Sent')
    class Meta:
        model = OrderItems
        template_name = "django_tables2/bootstrap.html"
        fields = ('jobnumber','ponumber', 'order.date_ordered', 'item_description', 'quantity', 'unit','quantity_received')
        filterset_class = OrderItemsFilter


class ReceivedTable(tables.Table):
    send_to_job = tables.TemplateColumn(
        '<a href="{% url "wallcovering_send" record.order_item.order.job_number.job_number %}">Send to Job</a>')
    class Meta:
        model = ReceivedItems
        template_name = "django_tables2/bootstrap.html"
        fields = ('wallcovering_delivery__order__job_number','order_item__item_description','wallcovering_delivery__date','quantity','order_item__unit', 'wallcovering_delivery__notes','send_to_job' )


class PackagesTable(tables.Table):
    send = tables.TemplateColumn('<a href="{% url "wallcovering_send" record.delivery.order.job_number.job_number %}">Send Now</a>')
    class Meta:
        model = Packages
        template_name = "django_tables2/bootstrap.html"
        fields = ('delivery__date', 'type', 'contents', 'quantity_received', 'total_sent', 'notes','send')

class JobDeliveriesTable(tables.Table):
    class Meta:
        model = OutgoingItem
        template_name = "django_tables2/bootstrap.html"
        fields = ('outgoing_event__date', 'package__type', 'package__contents', 'description', 'quantity_sent', 'outgoing_event__notes')


class WallcoveringPatternsTable(tables.Table):
    codelink = tables.TemplateColumn('<a href="{% url "wallcovering_pattern" record.id %}">{{record.code}}</a>')
    class Meta:
        model = OutgoingItem
        template_name = "django_tables2/bootstrap.html"
        fields = ('job_number','codelink','vendor','pattern','quantity_ordered','quantity_received','packages_received','packages_sent')