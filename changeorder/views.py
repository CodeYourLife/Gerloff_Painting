
from console.models import *
from django.shortcuts import render, redirect
from datetime import date
import json
from django.core.serializers.json import DjangoJSONEncoder
from wallcovering.tables import ChangeOrderTable
# Create your views here.

def change_order_new(request,jobnumber):
    if jobnumber == 'ALL':
        jobs=Jobs.objects.filter(status="Open")
        return render(request, "change_order_new.html",{'jobs':jobs})
    else:
        jobs=Jobs.objects.filter(job_number=jobnumber)

    return render(request, "change_order_new.html")
def change_order_home(request):
    table = ChangeOrderTable(ChangeOrders.objects.filter(is_closed=False))
    return render(request, "change_order_home.html", {'table':table})


def extra_work_ticket(request,id):
    changeorder = ChangeOrders.objects.get(id=id)
    notes = ChangeOrderNotes.objects.filter(cop_number=id)
    if request.method == 'GET':
        return render(request, "extra_work_ticket.html", {'changeorder': changeorder, 'notes': notes})
    if request.method == 'POST':
        if 'no_tm' in request.POST:
            if changeorder.is_t_and_m == True:
                changeorder.is_t_and_m=False
            else:
                changeorder.is_t_and_m = True
            changeorder.save()
            if 'no_tm_notes' in request.POST:
                if changeorder.is_t_and_m == True:
                    changeordernote = ChangeOrderNotes.objects.create(note="Changed to T&M: " + request.POST['no_tm_notes'],cop_number= changeorder, date=date.today(), user=request.user.first_name + " " + request.user.last_name)
                else:
                    changeordernote = ChangeOrderNotes.objects.create(
                        note="No Longer T&M: " + request.POST['no_tm_notes'], cop_number=changeorder, date=date.today(),
                        user=request.user.first_name + " " + request.user.last_name)
        if 'new_note' in request.POST:
            if request.POST['new_note'] != "":
                changeordernote = ChangeOrderNotes.objects.create(note=request.POST['new_note'],
                                                                  cop_number= changeorder, date=date.today(), user="Current User")
        notes = ChangeOrderNotes.objects.filter(cop_number=id)
        return render(request, "extra_work_ticket.html", {'changeorder': changeorder, 'notes': notes})


def process_ewt(request, id):
    employees = Employees.objects.all()
    employees2 = Employees.objects.values()
    changeorder = ChangeOrders.objects.get(id=id)
    materials = TMPricesMaster.objects.filter(category= "Material")
    materials2 = TMPricesMaster.objects.filter(category="Material").values()
    employees_json = json.dumps(list(employees2), cls=DjangoJSONEncoder)
    materials_json = json.dumps(list(materials2), cls=DjangoJSONEncoder)
    return render(request, "process_ewt.html", {'materialsjson': materials_json, 'materials': materials,'changeorder': changeorder,'employees': employees, 'employeesjson': employees_json})
