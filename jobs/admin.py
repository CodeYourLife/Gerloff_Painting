from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(Jobs)
admin.site.register(JobNumbers)
admin.site.register(JobNotes)
admin.site.register(Orders)
admin.site.register(OrderItems)
admin.site.register(Clients)
admin.site.register(ClientEmployees)
admin.site.register(Estimates)
admin.site.register(Plans)
admin.site.register(JobCharges)
admin.site.register(ClockSharkErrors)
admin.site.register(SiriusHours)

@admin.register(ClockSharkTimeEntry)
class ClockSharkTimeEntryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "job",
        "job_name",
        "employee_first_name",
        "employee_last_name",
        "clock_in",
        "clock_out",
        "hours",

    )

    list_filter = (
        "job",
    )

    search_fields = (
        "employee_first_name",
        "employee_last_name",
        "job__name",
    )

    ordering = ("-clock_in",)

    readonly_fields = (
        "clockshark_id",
        "clock_in",
        "clock_out",
        "hours",
    )

    fieldsets = (
        ("Job", {
            "fields": ("job","job_name"),
        }),
        ("Employee", {
            "fields": (
                "employee_first_name",
                "employee_last_name",
            ),
        }),
        ("Time", {
            "fields": (
                "clock_in",
                "clock_out",
                "hours",
            ),
        }),
        ("System", {
            "fields": ("clockshark_id",),
        }),
    )
