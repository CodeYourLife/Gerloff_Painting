from console.models import *
import django_tables2 as tables
from console.models import Orders, OrderItems, Packages, WallcoveringDelivery, ReceivedItems, OutgoingWallcovering, OutgoingItem
from django_filters.views import FilterView
from django_tables2.utils import A

class RentalsTable(tables.Table):
    item_description = tables.TemplateColumn('<a href="{% url "rental_page" record.id "YES" %}">{{record.item}}</a>')
    class Meta:
        model=Rentals
        template_name = "django_tables2/bootstrap.html"
        fields = ("job_number", "item_description", "company", "on_rent_date", "off_rent_date",'notes')