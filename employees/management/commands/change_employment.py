from django.core.management.base import BaseCommand
from employees.models import *  # Update with your actual app name if needed

class Command(BaseCommand):
    help = 'Deletes all entries in the RespiratorClearance model'

    def handle(self, *args, **kwargs):
        for x in Employees.objects.all():
            x.employment_company = Employers.objects.get(id=1)
            x.save()
