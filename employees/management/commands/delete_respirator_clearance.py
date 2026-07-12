from django.core.management.base import BaseCommand
from employees.models import *  # Update with your actual app name if needed

class Command(BaseCommand):
    help = 'Deletes all entries in the RespiratorClearance model'

    def handle(self, *args, **kwargs):
        CertificationNotes.objects.all().delete()
        Certifications.objects.all().delete()
        CertificationCategories.objects.all().delete()
        CertificationActionRequired.objects.all().delete()




