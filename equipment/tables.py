from console.models import *
import django_tables2 as tables
from console.models import InventoryNotes, WallcoveringPricing
from django_filters.views import FilterView

class EquipmentNotesTable(tables.Table, FilterView):
    class Meta:
        model = InventoryNotes
        template_name = "django_tables2/bootstrap.html"
        fields = ("date", "user", "note", "job_name")



class EquipmentTable(tables.Table):
    class Meta:
        model = Inventory
        template_name = "django_tables2/bootstrap.html"
        fields = ("job_number.job_name", "inventory_type.type", "item")