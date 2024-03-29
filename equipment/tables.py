import django_tables2 as tables
from jobs.models import Jobs
from equipment.models import Inventory, InventoryNotes
from django_filters.views import FilterView


class JobsTable(tables.Table):
    jobname = tables.TemplateColumn('<a href="{% url "job_page" record.job_number %}">{{record.job_name}}</a>')
    startdate = tables.TemplateColumn('<a href="{% url "change_start_date" record.job_number "jobpage" "ALL" "ALL" %}">{{record.start_date}}</a>')
    super = tables.TemplateColumn(
            '{% if record.superintendent is None %}<a href="{% url "change_gpsuper" record.job_number "jobpage" %}">Click to Assign</a>{% else %}<a href="{% url "change_gpsuper" record.job_number "jobpage" %}">{{record.superintendent}}</a>{% endif %}')
    class Meta:
        model = Jobs
        template_name = "django_tables2/bootstrap.html"
        attrs = {'class': 'table table-sm'}
        fields = ("job_number", "jobname","start_date","startdate","client","super","contract_amount","city","state")
    def before_render(self,request):
        self.columns.hide('start_date')
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
    itemlink = tables.TemplateColumn('<a href="{% url "equipment_page" record.id %}">{{record.number}}</a>', verbose_name="GP Number")
    class Meta:
        model = Inventory
        template_name = "django_tables2/bootstrap.html"
        fields = ("inventory_type.type", "item", "itemlink", "add_to_cart","notes")

class EquipmentTableIncoming(tables.Table):
    add_to_cart= tables.TemplateColumn("""{% if record.batch == None %}<a href="{% url 'equipment_add_to_incoming' id=record.id %}">Add to Cart</a>{% else %}<a href="{% url 'equipment_remove_from_incoming_cart' id=record.id status=None %}">Remove from Cart</a>{% endif %}""")

    class Meta:
        model = Inventory
        template_name = "django_tables2/bootstrap.html"
        fields = ("job_number__job_name","inventory_type.type", "item", "number", "add_to_cart","notes")