# forms.py
from django import forms
from .models import Employees

class EmployeeUploadForm(forms.Form):
    excel_file = forms.FileField()