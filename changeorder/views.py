
from console.models import *
from django.shortcuts import render, redirect
from datetime import date
import json
from django.core.serializers.json import DjangoJSONEncoder
from django_tables2 import RequestConfig
from wallcovering.tables import ChangeOrderTable
from wallcovering.filters import ChangeOrderFilter

# Create your views here.
def change_order_send(request,id):
    changeorder = ChangeOrders.objects.get(id=id)
    if request.method == 'POST':

        if request.POST['add_submittal_contact'] != 'None':
            ClientJobRoles.objects.create(job =changeorder.job_number, employee = ClientEmployees.objects.get(person_pk=request.POST['add_submittal_contact']),role="Change Orders")
            return redirect('change_order_send', id=id)
        elif request.POST['remove_submittal_contact'] != 'None':
            employee = ClientEmployees.objects.get(person_pk=request.POST['remove_submittal_contact'])
            job=changeorder.job_number
            for x in ClientJobRoles.objects.filter(employee=employee, job=job, role="Change Orders"):
                x.delete()
            return redirect('change_order_send', id=id)
        else:
            changeorder.date_sent=date.today()
            changeorder.price=request.POST['price']
            changeorder.full_description = request.POST['full_description']
            changeorder.is_t_and_m = False
            changeorder.save()
            ChangeOrderNotes.objects.create(cop_number=changeorder, date=date.today(), user=request.user.first_name + " " + request.user.last_name, note="COP Sent. Price: $" + request.POST['price'])
            return redirect('extra_work_ticket', id=id)
    allcontacts = ClientEmployees.objects.filter(id=changeorder.job_number.client)
    allcontacts_json = json.dumps(list(ClientEmployees.objects.filter(id=changeorder.job_number.client).values('person_pk','name')), cls=DjangoJSONEncoder)
    if ClientJobRoles.objects.filter(job=changeorder.job_number,role="Change Orders"):
        co_contacts_exist = "Yes"
        co_contacts = ClientEmployees.objects.filter(roles__role="Change Orders")
        co_contacts_json = json.dumps(list(ClientEmployees.objects.filter(roles__role="Change Orders").values('person_pk','name')))
        return render(request, "change_order_send.html",
                      {'co_contacts_json': co_contacts_json, 'allcontacts_json': allcontacts_json,
                       'changeorder': changeorder,'co_contacts_exist':co_contacts_exist,'allcontacts':allcontacts})
    else:
        co_contacts_exist = "None"
        return render(request, "change_order_send.html", {'allcontacts_json': allcontacts_json, 'changeorder': changeorder,'co_contacts_exist':co_contacts_exist,'allcontacts':allcontacts})

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
    ticket_needed = changeorder.need_ticket()
    notes = ChangeOrderNotes.objects.filter(cop_number=id)
    if request.method == 'GET':
        return render(request, "extra_work_ticket.html", {'ticket_needed':ticket_needed,'changeorder': changeorder, 'notes': notes})
    if request.method == 'POST':
        if 'submit_form4' in request.POST:
            changeorder.is_closed = True
            changeorder.save()
            ChangeOrderNotes.objects.create(cop_number=changeorder, date=date.today(),
                                            user=request.user.first_name + " " + request.user.last_name,
                                            note="VOIDED - " + request.POST['void_notes'])
            return redirect('extra_work_ticket', id=id)
        if 'submit_form1' in request.POST:
            changeorder.is_approved = True
            changeorder.date_approved = date.today()
            changeorder.gc_number = request.POST['gc_number']
            if 'is_approved_to_bill' in request.POST:
                changeorder.is_approved_to_bill = True
            changeorder.price = request.POST['approved_price']
            changeorder.save()
            ChangeOrderNotes.objects.create(cop_number=changeorder, date=date.today(),
                                            user=request.user.first_name + " " + request.user.last_name,
                                            note="COP Approved. Price: $" + request.POST['approved_price'] + " -" + request.POST['approval_note'])
            return redirect('extra_work_ticket', id=id)
        if 'submit_form3' in request.POST:
            if 'no_tm' in request.POST:
                if changeorder.is_t_and_m == True:
                    changeorder.is_t_and_m=False
                else:
                    changeorder.is_t_and_m = True
                    changeorder.price = 0
                    changeorder.date_sent = None
                    changeorder.is_ticket_signed=False
                changeorder.save()
                if changeorder.is_t_and_m == True:
                    changeordernote = ChangeOrderNotes.objects.create(note="Changed to T&M: " + request.POST['no_tm_notes'],cop_number= changeorder, date=date.today(), user=request.user.first_name + " " + request.user.last_name)
                else:
                    changeordernote = ChangeOrderNotes.objects.create(
                        note="No Longer T&M: " + request.POST['no_tm_notes'], cop_number=changeorder, date=date.today(),
                        user=request.user.first_name + " " + request.user.last_name)
        if 'submit_form2' in request.POST:
            if request.POST['new_note'] != "":
                changeordernote = ChangeOrderNotes.objects.create(note=request.POST['new_note'],
                                                                  cop_number= changeorder, date=date.today(), user=request.user.first_name + " " + request.user.last_name)
        notes = ChangeOrderNotes.objects.filter(cop_number=id)
        return render(request, "extra_work_ticket.html", {'ticket_needed':ticket_needed,'changeorder': changeorder, 'notes': notes})


def process_ewt(request, id):
    if request.method == 'POST':
        print("HERE")
    employees = Employees.objects.all()
    employees2 = Employees.objects.values()
    changeorder = ChangeOrders.objects.get(id=id)
    materials = TMPricesMaster.objects.filter(category= "Material")
    materials2 = TMPricesMaster.objects.filter(category="Material").values()
    equipment = TMPricesMaster.objects.filter(category="Equipment").values()
    employees_json = json.dumps(list(employees2), cls=DjangoJSONEncoder)
    materials_json = json.dumps(list(materials2), cls=DjangoJSONEncoder)
    equipment_json = json.dumps(list(equipment), cls=DjangoJSONEncoder)
    return render(request, "process_ewt.html", {'equipment':equipment,'equipmentjson':equipment_json,'materialsjson': materials_json, 'materials': materials,'changeorder': changeorder,'employees': employees, 'employeesjson': employees_json})
