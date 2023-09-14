from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(Subcontracts)
admin.site.register(Subcontractors)
admin.site.register(SubcontractItems)
admin.site.register(SubcontractorInvoice)
admin.site.register(SubcontractorInvoiceItem)
admin.site.register(SubcontractNotes)
