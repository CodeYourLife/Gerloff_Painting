from console.models import *
import django_tables2 as tables
from console.models import InventoryNotes
from django_filters.views import FilterView

class EquipmentNotesTable(tables.Table, FilterView):
    class Meta:
        model = InventoryNotes
        template_name = "django_tables2/bootstrap.html"
        fields = ("date", "user", "note", "job_name")
