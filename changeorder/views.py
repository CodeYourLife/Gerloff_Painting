
from console.models import *
from django.shortcuts import render, redirect
from datetime import date
import json
from django.core.serializers.json import DjangoJSONEncoder
from django_tables2 import RequestConfig
from wallcovering.tables import ChangeOrderTable
from wallcovering.filters import ChangeOrderFilter
import jinja2
import pdfkit
import os
import os.path
# Create your views here.

def print_ticket(request,id):
    changeorder = ChangeOrders.objects.get(id=id)
    ewt = EWT.objects.get(change_order=changeorder)
    laboritems = EWTicket.objects.filter(EWT=ewt).exclude(employee=None)
    materials = EWTicket.objects.filter(EWT=ewt,master__category="Material")
    equipment = EWTicket.objects.filter(EWT=ewt, master__category="Equipment")
    if request.method == 'POST':
        print("HI")
    return render(request, "print_ticket.html", {'equipment':equipment,'materials':materials,'laboritems':laboritems,'ewt':ewt,'changeorder':changeorder})


def view_ewt(request,id):
    changeorder = ChangeOrders.objects.get(id=id)
    employees = Employees.objects.all()
    employees2 = Employees.objects.values()
    materials = TMPricesMaster.objects.filter(category= "Material")
    materials2 = TMPricesMaster.objects.filter(category="Material").values()
    equipment = TMPricesMaster.objects.filter(category="Equipment").values()
    employees_json = json.dumps(list(employees2), cls=DjangoJSONEncoder)
    materials_json = json.dumps(list(materials2), cls=DjangoJSONEncoder)
    equipment_json = json.dumps(list(equipment), cls=DjangoJSONEncoder)
    return render(request, "process_ewt.html", {'equipment':equipment,'equipmentjson':equipment_json,'materialsjson': materials_json, 'materials': materials,'changeorder': changeorder,'employees': employees, 'employeesjson': employees_json})

def change_order_send(request,id):
    changeorder = ChangeOrders.objects.get(id=id)
    if request.method == 'POST':
        print(request.POST)
    available_contacts = []
    co_contacts = []
    found_contacts = False
    extra_contacts = False
    pm_is_available = False
    available = False
    project_pm = ClientEmployees.objects.get(person_pk=changeorder.job_number.client_Pm.person_pk)
    for x in ClientEmployees.objects.filter(id=changeorder.job_number.client):
        if ClientJobRoles.objects.filter(role="Change Orders", job=changeorder.job_number, employee=x).exists():
            co_contacts.append(x)
            found_contacts = True
        else:
            available = True
            if x == project_pm:
                pm_is_available = True
            else:
                available_contacts.append(x)
                extra_contacts = True
    return render(request, "change_order_send.html",
                  {'available': available, 'pm_is_available': pm_is_available, 'project_pm': project_pm,
                   'extra_contacts': extra_contacts, 'found_contacts': found_contacts,
                   'available_contacts': available_contacts, 'co_contacts': co_contacts, 'changeorder': changeorder})

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
            directory = changeorder.id
            parent_dir = "C:/Trinity/ChangeOrder"
            path = os.path.join(parent_dir, str(directory))
            try:
                os.mkdir(path)
            except OSError as error:
                print(error)
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
        if 'open_folder' in request.POST:
            path = "C:/trinity/changeorder/" + str(changeorder.id)
            path = os.path.realpath(path)
            os.startfile(path)
        if 'signed' in request.POST:
            print("NEED TO DO THIS PART")
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
    changeorder = ChangeOrders.objects.get(id=id)
    if request.method == 'POST':

        if EWT.objects.filter(change_order=changeorder).exists():
            EWT.objects.get(change_order=changeorder).delete()
        ewt= EWT.objects.create(change_order=changeorder,week_ending = request.POST['date_week_ending'], notes=request.POST['ticket_description'],completed_by=request.user.first_name + " " + request.user.last_name)
        ChangeOrderNotes.objects.create(cop_number=changeorder,date = date.today(), user = request.user.first_name + " " + request.user.last_name,note = "Extra Work Ticket Added")
        if request.POST['number_painters'] != 0:
            for x in range (1,int(request.POST['number_painters'])+1):
                if 'painter_dropdown' + str(x) in request.POST:
                    hours=0
                    if request.POST['monday' + str(x)] != '':
                        hours=hours+int(request.POST['monday' + str(x)])
                    if request.POST['tuesday' + str(x)] != '':
                        hours = hours + int(request.POST['tuesday' + str(x)])
                    if request.POST['wednesday' + str(x)] != '':
                        hours = hours + int(request.POST['wednesday' + str(x)])
                    if request.POST['thursday' + str(x)] != '':
                        hours = hours + int(request.POST['thursday' + str(x)])
                    if request.POST['friday' + str(x)] != '':
                        hours = hours + int(request.POST['friday' + str(x)])
                    if request.POST['saturday' + str(x)] != '':
                        hours = hours + int(request.POST['saturday' + str(x)])
                    if request.POST['sunday' + str(x)] != '':
                        hours = hours + int(request.POST['sunday' + str(x)])
                    if request.POST['is_overtime' + str(x)] != 'notchecked':
                        master=TMPricesMaster.objects.get(item='Painter Hours OT')
                        EWTicket.objects.create(master = master,EWT=ewt,employee=Employees.objects.get(id=request.POST['painter_dropdown' + str(x)]),monday=float(request.POST['monday'+ str(x)]),tuesday=float(request.POST['tuesday'+ str(x)]),wednesday=float(request.POST['wednesday'+ str(x)]),thursday=float(request.POST['thursday'+ str(x)]),friday=float(request.POST['friday'+ str(x)]),saturday=float(request.POST['saturday'+ str(x)]),sunday=float(request.POST['sunday'+ str(x)]),ot = True)
                    else:
                        master = TMPricesMaster.objects.get(item='Painter Hours')
                        EWTicket.objects.create(master=master, EWT=ewt, employee=Employees.objects.get(id=request.POST['painter_dropdown' + str(x)]), monday=float(request.POST['monday' + str(x)]),
                                                               tuesday=float(request.POST['tuesday' + str(x)]),
                                                               wednesday=float(request.POST['wednesday' + str(x)]),
                                                               thursday=float(request.POST['thursday' + str(x)]),
                                                               friday=float(request.POST['friday' + str(x)]),
                                                               saturday=float(request.POST['saturday' + str(x)]),
                                                               sunday=float(request.POST['sunday' + str(x)]), ot=False)
        if request.POST['number_materials'] != 0:
            for x in range(1, int(request.POST['number_materials']) + 1):
                if 'select_material' + str(x) in request.POST:
                    master = TMPricesMaster.objects.get(id=request.POST['select_material' + str(x)])
                    EWTicket.objects.create(master=master, EWT = ewt, description = request.POST['description' + str(x)], quantity = request.POST['quantity' + str(x)], units = request.POST['units' + str(x)])
        if request.POST['number_equipment'] != 0:
            for x in range(1, int(request.POST['number_equipment']) + 1):
                if 'select_equipment' + str(x) in request.POST:
                    master = TMPricesMaster.objects.get(id=request.POST['select_equipment' + str(x)])
                    EWTicket.objects.create(master=master, EWT = ewt, description = request.POST['equipment_description' + str(x)], quantity = request.POST['equipment_quantity' + str(x)], units = request.POST['equipment_units' + str(x)])



        return redirect('change_order_home')
    employees = Employees.objects.all()
    employees2 = Employees.objects.values()
    materials = TMPricesMaster.objects.filter(category= "Material")
    materials2 = TMPricesMaster.objects.filter(category="Material").values()
    equipment = TMPricesMaster.objects.filter(category="Equipment").values()
    employees_json = json.dumps(list(employees2), cls=DjangoJSONEncoder)
    materials_json = json.dumps(list(materials2), cls=DjangoJSONEncoder)
    equipment_json = json.dumps(list(equipment), cls=DjangoJSONEncoder)
    return render(request, "process_ewt.html", {'equipment':equipment,'equipmentjson':equipment_json,'materialsjson': materials_json, 'materials': materials,'changeorder': changeorder,'employees': employees, 'employeesjson': employees_json})
