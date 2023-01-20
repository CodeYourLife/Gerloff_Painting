
from console.models import *
from django.shortcuts import render, redirect
from datetime import date
import json
from django.core.serializers.json import DjangoJSONEncoder
from django_tables2 import RequestConfig
from wallcovering.tables import ChangeOrderTable
from wallcovering.filters import ChangeOrderFilter
# Create your views here.

def change_order_new(request,jobnumber):
    if request.method == 'POST':
        if 'select_job' in request.POST:
            selected_job = Jobs.objects.get(job_number=request.POST['select_job'])
            return render(request, "change_order_new.html", {'selected_job': selected_job})
        else:
            t_and_m = False
            if 'is_t_and_m' in request.POST:
                t_and_m = True
            if ChangeOrders.objects.filter(job_number=Jobs.objects.get(job_number=jobnumber)):
                last_cop = ChangeOrders.objects.filter(job_number=Jobs.objects.get(job_number=jobnumber)).order_by('cop_number').last()
                next_cop = last_cop.cop_number + 1
            else:
                next_cop = 1
            changeorder = ChangeOrders.objects.create(job_number=Jobs.objects.get(job_number=jobnumber), is_t_and_m=t_and_m, description= request.POST['description'],cop_number=next_cop)
            print(request.user)
            if changeorder.is_t_and_m == True:
                note = ChangeOrderNotes.objects.create(cop_number=changeorder,date=date.today(),user=request.user.first_name + " " + request.user.last_name,note ="T&M COP Added. " + request.POST['notes'])
            else:
                note = ChangeOrderNotes.objects.create(cop_number=changeorder, date=date.today(),
                                                       user=request.user.first_name + " " + request.user.last_name,
                                                       note="COP Added. " + request.POST['notes'])
            return redirect('extra_work_ticket',id=changeorder.id)
    else:
        jobs=Jobs.objects.filter(status="Open")
        return render(request, "change_order_new.html",{'jobs':jobs})


def change_order_home(request):
    all_orders = ChangeOrderFilter(request.GET, queryset =ChangeOrders.objects.filter(is_closed=False))
    table = ChangeOrderTable(all_orders.qs)
    has_filter = any(field in request.GET for field in set(all_orders.get_fields()))
    RequestConfig(request).configure(table)
    return render(request, "change_order_home.html", {'table': table,'all_orders':all_orders,'has_filter':has_filter})


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
