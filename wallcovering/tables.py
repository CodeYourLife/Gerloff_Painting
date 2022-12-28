from console.models import *
import django_tables2 as tables
from console.models import *
from django_filters.views import FilterView
from django_tables2.utils import A



class WallcoveringPriceTable(tables.Table):
    class Meta:
            model = WallcoveringPricing
            template_name = "django_tables2/bootstrap.html"
            fields = ("quote_date", "min_yards", "price", "unit", "note")

class OutgoingWallcoveringTable(tables.Table):
    edit = tables.TemplateColumn('<a href="{% url "job_page" record.outgoing_event.job_number.job_number %}">TEST</a>')

    class Meta:
            model = OutgoingItem
            template_name = "django_tables2/bootstrap.html"
            fields = ("edit", "outgoing_event.job_number.job_name", "outgoing_event.delivered_by", "outgoing_event.notes","package.type", "package.contents", "description","quantity_sent","edit_col")


class OrdersTable(tables.Table):
    class Meta:
        model = OrderItems
        template_name = "django_tables2/bootstrap.html"
        fields = ('order__date_ordered','item_description','quantity', 'unit', 'item_notes')

class ReceivedTable(tables.Table):
    class Meta:
        model = ReceivedItems
        template_name = "django_tables2/bootstrap.html"
        fields = ('order_item__item_description','wallcovering_delivery__date','quantity' )


class PackagesTable(tables.Table):
    class Meta:
        model = Packages
        template_name = "django_tables2/bootstrap.html"
        fields = ('delivery__date', 'type', 'contents', 'quantity_received', 'notes')

class JobDeliveriesTable(tables.Table):
    class Meta:
        model = OutgoingItem
        template_name = "django_tables2/bootstrap.html"
        fields = ('outgoing_event__date', 'package__type', 'package__contents', 'description', 'quantity_sent', 'outgoing_event__notes')