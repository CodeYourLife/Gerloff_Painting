
from console.models import *
from django.shortcuts import render, redirect
from datetime import date
import json
from django.core.serializers.json import DjangoJSONEncoder
# Create your views here.

def extra_work_ticket(request,id):

    if request.method == 'GET':
        changeorder = ChangeOrders.objects.get(id=id)
        notes = ChangeOrderNotes.objects.filter(cop_number=id)
        return render(request, "extra_work_ticket.html", {'changeorder': changeorder, 'notes': notes})
    if request.method == 'POST':
        if request.POST['new_note'] != "":
            changeorder = ChangeOrders.objects.get(id=id)
            changeordernote = ChangeOrderNotes.objects.create(note=request.POST['new_note'],
                                                              cop_number= changeorder, date=date.today(), user="Current User")
            notes = ChangeOrderNotes.objects.filter(cop_number=id)
            return render(request, "extra_work_ticket.html", {'changeorder': changeorder, 'notes': notes})

def process_ewt(request, id):
    employees = Employees.objects.all()
    employees2 = Employees.objects.values()
    changeorder = ChangeOrders.objects.get(id=id)
    materials = TMPricesMaster.objects.filter(category= "Material")
    materials2 = TMPricesMaster.objects.filter(category="Material").values
    employees_json = json.dumps(list(employees2), cls=DjangoJSONEncoder)
    materials_json = json.dumps(list(materials2), cls=DjangoJSONEncoder)
    return render(request, "process_ewt.html", {'materialsjson': materials_json, 'materials': materials,'changeorder': changeorder,'employees': employees, 'employeesjson': employees_json})
