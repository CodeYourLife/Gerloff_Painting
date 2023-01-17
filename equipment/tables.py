from console.models import *
import django_tables2 as tables
from console.models import InventoryNotes, WallcoveringPricing
from django_filters.views import FilterView
from .filters import EquipmentFilter

class JobsTable(tables.Table):
    jobnumber = tables.TemplateColumn('<a href="{% url "job_page" record.job_number %}">{{record.job_number}}</a>')
    startdate = tables.TemplateColumn('<a href="{% url "change_start_date" record.job_number "jobpage" %}">{{record.start_date}}</a>')
    class Meta:
        model = Jobs
        template_name = "django_tables2/bootstrap.html"
        fields = ("jobnumber", "job_name","startdate","client","estimator","superintendent","contract_amount","address","city","state")
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

class EquipmentTableOutgoing(tables.Table):
    add_to_cart= tables.TemplateColumn("""{% if record.batch == None %}<a href="{% url 'equipment_add_to_outgoing' record.id %}">Add to Cart</a>{% else %}<a href="{% url 'equipment_remove_from_outgoing_cart' record.id %}">Remove from Cart</a>{% endif %}""")

    class Meta:
        model = Inventory
        template_name = "django_tables2/bootstrap.html"
        fields = ("inventory_type.type", "item", "number", "add_to_cart","notes")

class EquipmentTableIncoming(tables.Table):
    add_to_cart= tables.TemplateColumn("""{% if record.batch == None %}<a href="{% url 'equipment_add_to_incoming' id=record.id %}">Add to Cart</a>{% else %}<a href="{% url 'equipment_remove_from_incoming_cart' id=record.id status=None %}">Remove from Cart</a>{% endif %}""")

    class Meta:
        model = Inventory
        template_name = "django_tables2/bootstrap.html"
        fields = ("job_number__job_name","inventory_type.type", "item", "number", "add_to_cart","notes")