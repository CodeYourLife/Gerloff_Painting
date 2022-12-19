from console.models import *
import django_tables2 as tables
from console.models import InventoryNotes
import django_filters


class EquipmentNotesFilter(django_filters.FilterSet):
    class Meta:
        model = InventoryNotes
        fields = ['category']