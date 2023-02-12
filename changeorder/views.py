
from console.models import *
from django.shortcuts import render, redirect
from datetime import date
import json
from django.core.serializers.json import DjangoJSONEncoder
from django_tables2 import RequestConfig
from wallcovering.tables import ChangeOrderTable
from wallcovering.filters import ChangeOrderFilter
from console.misc import Email

import os
import os.path
# Create your views here.

def price_ewt(request,id):
    changeorder = ChangeOrders.objects.get(id=id)
    ewt = EWT.objects.get(change_order=changeorder)
    equipment = []
    laboritems = []
    materials = []
    extras = []
    totalhours = 0
    totalmaterialcost =0
    totalcost = 0
    counter=0
    for x in TMPricesMaster.objects.filter(category="Labor", ewticket__isnull=False).distinct():
        hours = 0
        for y in EWTicket.objects.filter(EWT=ewt, master=x).exclude(employee=None).order_by('master'):
            hours = hours + y.monday + y.tuesday + y.wednesday + y.thursday + y.friday + y.saturday + y.sunday
        totalhours = totalhours + hours
        cost = hours * x.rate
        totalcost=totalcost+cost
        counter=counter+1
        rate = float(x.rate)
        laboritems.append({'rate':rate,'counter':counter,'item':x,'hours':hours, 'cost':int(cost)})
    counter = 0
    for y in EWTicket.objects.filter(EWT=ewt, master__category="Material").order_by('master'):
        cost = y.quantity * y.master.rate
        totalcost = totalcost + cost
        totalmaterialcost = totalmaterialcost + cost
        counter = counter + 1
        rate = float(y.master.rate)
        materials.append(
            {'rate':rate,'counter':counter,'category': y.master.item, 'description': y.description, 'quantity': y.quantity, 'units': y.units,
             'cost': int(cost)})
    inventory = int(float(totalmaterialcost) * .15)
    totalcost = totalcost + inventory
    counter = 0
    for y in EWTicket.objects.filter(EWT=ewt, master__category="Equipment").order_by('master'):
        cost = y.quantity * y.master.rate
        totalcost = totalcost + cost
        counter = counter + 1
        rate = float(y.master.rate)
        equipment.append(
            {'rate':rate,'counter':counter,'category': y.master.item, 'description': y.description, 'quantity': y.quantity, 'units': y.units,
             'cost': int(cost)})
    days = totalhours /8
    counter=0
    for x in JobCharges.objects.filter(job=changeorder.job_number):
        print("jeses")
        if x.master.unit == "Day":
            cost =days * x.master.rate
            totalcost = totalcost + cost
            counter = counter + 1
            rate = float(x.master.rate)
            extras.append({'rate':rate,'counter':counter,'category': x.master.item, 'quantity': days, 'unit': "Days", 'cost': int(cost)})
        elif x.master.unit == "Hours":
            cost = totalhours * x.master.rate
            totalcost = totalcost + cost
            counter = counter + 1
            rate = float(x.master.rate)
            extras.append({'rate':rate,'counter':counter,'category': x.master.item, 'quantity': totalhours, 'unit': "Hours", 'cost': int(cost)})
        else:
            counter = counter + 1
            rate = float(x.master.rate)
            extras.append({'rate':rate,'counter':counter,'category': x.master.item, 'quantity': 0, 'unit': x.master.unit, 'cost': 0})
    if changeorder.job_number.is_bonded == True:
        counter = counter + 1
        extras.append({'rate':1,'counter':counter,'category':"Bond", 'quantity':1,'unit':"LS",'cost':int(float(totalcost) * .02)})


    employees2 = TMPricesMaster.objects.filter(category="Labor").values()
    materials2 = TMPricesMaster.objects.filter(category="Material").values()
    equipment2 = TMPricesMaster.objects.filter(category="Equipment").values()
    extras2 = TMPricesMaster.objects.filter(category="Misc").values()
    employees_json = json.dumps(list(employees2), cls=DjangoJSONEncoder)
    material_json = json.dumps(list(materials2), cls=DjangoJSONEncoder)
    equipment_json = json.dumps(list(equipment2), cls=DjangoJSONEncoder)
    extras_json = json.dumps(list(extras2), cls=DjangoJSONEncoder)
    print(extras)
    print(extras_json)
    return render(request, "price_ewt.html",
                  {'extras_json':extras_json,'employees_json':employees_json,'material_json':material_json,'equipment_json':equipment_json,'laborcount':int(len(laboritems)),'materialcount':int(len(materials)+1),'equipmentcount':int(len(equipment)),'extrascount':int(len(extras)),'extras':extras,'totalcost':int(totalcost),'inventory':int(inventory),'equipment': equipment, 'materials': materials, 'laboritems': laboritems, 'ewt': ewt,
                   'changeorder': changeorder})

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
    if request.method != 'POST':
        for x in TempRecipients.objects.filter(changeorder=changeorder):
            x.delete()
    if request.method == 'POST':
        for x in request.POST:
            if x[0:11] == 'updateemail':
                person = ClientEmployees.objects.get(person_pk=x[11:len(x)])
                person.email = request.POST['email'+str(person.person_pk)]
                person.save()
            if x[0:6] == 'remove':
                person = ClientEmployees.objects.get(person_pk=x[6:len(x)])
                ClientJobRoles.objects.get(role="Change Orders", job=changeorder.job_number, employee=person).delete()
            if x[0:10] == 'adddefault':
                person = ClientEmployees.objects.get(person_pk=x[10:len(x)])
                ClientJobRoles.objects.create(role="Change Orders", job=changeorder.job_number, employee=person)
            if x[0:10] == 'tempremove':
                person = ClientEmployees.objects.get(person_pk=x[10:len(x)])
                TempRecipients.objects.get(changeorder=changeorder,person=person).delete()
            if x[0:7] == 'tempadd':
                person = ClientEmployees.objects.get(person_pk=request.POST['addrecipient'])
                TempRecipients.objects.create(person=person, changeorder=changeorder)
            if x[0:10] == 'defaultadd':
                person = ClientEmployees.objects.get(person_pk=request.POST['addrecipient'])
                if not ClientJobRoles.objects.filter(role="Change Orders", job=changeorder.job_number, employee=person).exists():
                    ClientJobRoles.objects.create(role="Change Orders", job=changeorder.job_number, employee=person)
                    TempRecipients.objects.create(person=person, changeorder=changeorder)
            if x[0:5] == 'final':
                recipients = ""
                for x in request.POST:
                    if x[0:5] == 'email':
                        if recipients == "":
                            recipients = request.POST[x]
                        else:
                            recipients = recipients + "; " + request.POST[x]
                changeorder.sent_to = recipients
                changeorder.full_description = request.POST['full_description']
                changeorder.price = request.POST['price']
                changeorder.date_sent = date.today()
                changeorder.save()
                ChangeOrderNotes.objects.create(cop_number=changeorder, date=date.today(),
                                                user=request.user.first_name + " " + request.user.last_name,
                                                note="COP Sent. Price: $" + request.POST['price'])
                # Email.sendEmail("Change Order","Test",recipients)
                return redirect('extra_work_ticket', id=id)
    extra_contacts = False
    project_pm = ClientEmployees.objects.get(person_pk=changeorder.job_number.client_Pm.person_pk)
    client_list = []
    if TempRecipients.objects.filter(changeorder=changeorder,default=False).exists():
        if TempRecipients.objects.filter(changeorder=changeorder, default=True).exists():
            TempRecipients.objects.filter(changeorder=changeorder,default=True).delete()
    if not ClientJobRoles.objects.filter(role="Change Orders", job=changeorder.job_number):
        if not TempRecipients.objects.filter(changeorder=changeorder):
            TempRecipients.objects.create(person=project_pm,changeorder=changeorder,default=True)
    else: #means there is a default person
        if not TempRecipients.objects.filter(changeorder=changeorder): #this will add all default as temp recipients if there are no temp recipients
            for x in ClientJobRoles.objects.filter(role="Change Orders", job=changeorder.job_number):
                TempRecipients.objects.create(person=x.employee,changeorder=changeorder)
    for x in ClientEmployees.objects.filter(id=changeorder.job_number.client):
        if ClientJobRoles.objects.filter(role="Change Orders", job=changeorder.job_number, employee=x).exists():
            if TempRecipients.objects.filter(changeorder=changeorder,person=x).exists():
                client_list.append({'person_pk':x.person_pk,'name':x.name,'default':True,'current':True,'email':x.email})
            else:
                extra_contacts = True
                client_list.append({'person_pk': x.person_pk, 'name': x.name, 'default': True, 'current': False,'email':x.email})
        else:
            if TempRecipients.objects.filter(person=x,changeorder=changeorder).exists():
                client_list.append({'person_pk':x.person_pk,'name':x.name,'default':False,'current':True,'email':x.email})
            else:
                extra_contacts = True
                client_list.append({'person_pk': x.person_pk, 'name': x.name, 'default': False, 'current': False,'email':x.email})

    return render(request, "change_order_send.html",
                  {'client_list':client_list,
                   'extra_contacts': extra_contacts,'changeorder': changeorder})



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
