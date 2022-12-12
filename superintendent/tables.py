import django_tables2 as tables
from console.models import Jobs, Inventory, InventoryType

class JobsTable(tables.Table):
    class Meta:
        model = Jobs
        template_name = "django_tables2/bootstrap.html"
        fields = ("job_name","job_number", "superintendent.last_name")


class EquipmentTable(tables.Table):
    class Meta:
        model = Inventory
        template_name = "django_tables2/bootstrap.html"
        fields = ("job_number.job_name", "inventory_type.type", "item")