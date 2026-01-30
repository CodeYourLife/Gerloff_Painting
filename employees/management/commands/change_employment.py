from django.core.management.base import BaseCommand
from employees.models import *  # Update with your actual app name if needed
from subcontractors.models import *
class Command(BaseCommand):
    help = 'Deletes all entries in the RespiratorClearance model'

    def handle(self, *args, **kwargs):
        print("here")
        for x in SubcontractorInvoice.objects.all():
            job = x.subcontract.job_number
            job.is_active=True
            job.save()
