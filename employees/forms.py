# forms.py
from django import forms
from .models import Employees

class EmployeeUploadForm(forms.Form):
    excel_file = forms.FileField()

class SiriusUploadForm(forms.Form):
    excel_file = forms.FileField()

class ClockSharkUploadForm(forms.Form):
    excel_file = forms.FileField()

class ToolboxTalksUploadForm(forms.Form):
    excel_file = forms.FileField()