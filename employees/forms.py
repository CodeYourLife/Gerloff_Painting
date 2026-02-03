# forms.py
from django import forms
from .models import Employees
from jobs.models import JobsiteSafetyInspection, Jobs, InspectionStatus


class EmployeeUploadForm(forms.Form):
    excel_file = forms.FileField()

class SiriusUploadForm(forms.Form):
    excel_file = forms.FileField()

class ClockSharkUploadForm(forms.Form):
    excel_file = forms.FileField()

class ToolboxTalksUploadForm(forms.Form):
    excel_file = forms.FileField()

class JobsiteSafetyInspectionForm(forms.ModelForm):
    class Meta:
        model = JobsiteSafetyInspection
        exclude = ["inspector", "inspection_date", "created_at"]
        widgets = {
            field: forms.RadioSelect
            for field in [
                "housekeeping", "walkways_clear", "wet_paint_signs",
                "proper_uniforms", "floor_protection", "proper_lighting",
                "ladders", "scaffolding", "aerial_lifts", "fall_protection",
                "ppe", "respirators", "eye_protection", "hand_protection",
                "hard_hats", "hearing_protection", "heat_cold_stress",
                "first_aid_kit", "paint_storage", "flammables", "sds",
                "ventilation", "lead_containment", "silica_control",
                "overspray", "power_tools", "extension_cords",
                "electrical_safety", "overhead_work", "traffic_control",
                "signage", "fire_extinguishers", "weather_conditions",
                "spray_equipment"
            ]
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Only show ACTIVE jobs
        self.fields["job"].queryset = Jobs.objects.filter(is_closed=False).order_by("job_name")
        self.fields["job"].label = "Select Job"

        for name, field in self.fields.items():
            if isinstance(field.widget, forms.RadioSelect):
                field.initial = InspectionStatus.NOT_OBSERVED
                field.required = False  # belt + suspenders