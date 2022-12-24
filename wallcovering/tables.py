from console.models import *
import django_tables2 as tables
from console.models import *
from django_filters.views import FilterView




class WallcoveringPriceTable(tables.Table):
    class Meta:
            model = WallcoveringPricing
            template_name = "django_tables2/bootstrap.html"
            fields = ("quote_date", "min_yards", "price", "unit", "note")

class OutgoingWallcoveringTable(tables.Table):
    class Meta:
            model = OutgoingItem
            template_name = "django_tables2/bootstrap.html"
            fields = ("outgoing_event.job_number.job_name", "outgoing_event.delivered_by", "outgoing_event.notes","package.type", "package.contents", "description","quantity_sent")