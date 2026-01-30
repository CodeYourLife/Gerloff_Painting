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
admin.site.register(ClockSharkJobMap)

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

    list_filter = ("job",)

    search_fields = (
        "employee_first_name",
        "employee_last_name",
        "job__job_name",
        "job_name"
    )

    ordering = ("-clock_in",)

    readonly_fields = ("hours",)

    fieldsets = (
        ("Job", {
            "fields": ("job", "job_name"),
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
            "fields": ("clockshark_id", "lunch", "hours_adjust_note"),
        }),
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "job":
            kwargs["queryset"] = Jobs.objects.filter(is_closed=False).order_by('job_name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        # First save the object normally
        super().save_model(request, obj, form, change)

        # If admin selected a job, create mapping
        if obj.job and obj.job_name:
            ClockSharkJobMap.objects.update_or_create(
                clockshark_job_name=obj.job_name,
                defaults={"job": obj.job},
            )

            # Backfill existing orphaned entries
            for entry in ClockSharkTimeEntry.objects.filter(
                job__isnull=True,
                job_name=obj.job_name,
            ):
                entry.job = obj.job
                entry.save()   # ✅ NOW save() runs