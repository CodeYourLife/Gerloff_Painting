from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(Subcontracts)
admin.site.register(Subcontractors)
admin.site.register(SubcontractItems)
admin.site.register(SubcontractorInvoice)
admin.site.register(SubcontractorInvoiceItem)
admin.site.register(SubcontractNotes)
admin.site.register(Standard_Approvers)
admin.site.register(InvoiceApprovals)
admin.site.register(SubcontractorPayments)
admin.site.register(SubcontractorOriginalInvoiceItem)
admin.site.register(SubcontractorEmployeeDelegation)


@admin.register(SubcontractorRespiratorClearance)
class SubcontractorRespiratorClearanceAdmin(admin.ModelAdmin):
    list_display = (
        "subcontractor",
        "employee_display_name",
        "date_created",
        "date_completed",
        "approved_for_use",
        "date_expires",
    )
    list_filter = ("approved_for_use", "subcontractor")
    search_fields = ("employee__name", "employee_name", "subcontractor__company")
