from django.utils import timezone
from django.views import generic
from django.views.generic import ListView
from console.models import *
from django.contrib.auth.models import User, auth
from django.shortcuts import render, redirect
from json import dumps
import json
from django.core.serializers.json import DjangoJSONEncoder
from datetime import date
from django_tables2 import SingleTableView
from .tables import EquipmentNotesTable
from console.models import InventoryNotes
from .filters import EquipmentNotesFilter
# Create your views here.

def equipment_page(request, id):
    inventory = Inventory.objects.get(id=id)
    table = EquipmentNotesTable(InventoryNotes.objects.filter(inventory_item=inventory))
    if request.method == 'POST':
        print(request.POST)
        if 'select_category' in request.POST:
            table = EquipmentNotesTable(InventoryNotes.objects.filter(inventory_item=inventory, category=request.POST['select_category']))
        if 'returned' in request.POST:
            inventory.status = "Available"  # change field
            inventory.date_returned = date.today()
            inventory.job_number = None
            inventory.save()  # this will update only
            new_note = InventoryNotes(inventory_item=inventory, date=date.today(), user=request.user.first_name + " " + request.user.last_name, note="Returned -" + request.POST['returned_notes'],
                                      category="Returned")
            new_note.save()

        if 'missing' in request.POST:
            print("MISSING")
            new_note = InventoryNotes(inventory_item=inventory, date=date.today(), user=request.user.first_name + " " + request.user.last_name, note="Missing -" + request.POST['missing_notes'],
                                      category="Missing")
            new_note.save()
        if 'select_job' in request.POST:
            print(request.POST['select_job'])
            inventory.job_number = Jobs.objects.get(job_number = request.POST['select_job'])
            inventory.save()
            new_note = InventoryNotes(inventory_item=inventory, date=date.today(), user= request.user.first_name + " " + request.user.last_name, note="New Job -" + request.POST['job_notes'],
                                      category="Job", job_name = Jobs.objects.get(job_number = request.POST['select_job']).job_name, job_number = request.POST['select_job'] )
            new_note.save()
        if 'equipment_note' in request.POST:
            new_note = InventoryNotes(inventory_item=inventory, date=date.today(), user=request.user.first_name + " " + request.user.last_name,
                                      note=request.POST['equipment_note'],
                                      category="Misc")
            new_note.save()


    jobs = Jobs.objects.all()
    return render(request, "equipment_page.html", {'jobs': jobs,'inventories': inventory, "table": table})
