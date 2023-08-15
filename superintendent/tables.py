import django_tables2 as tables
from console.models import Jobs

class JobsTable(tables.Table):
    class Meta:
        model = Jobs
        template_name = "django_tables2/bootstrap.html"
        fields = ("job_name","job_number", "superintendent.last_name")


