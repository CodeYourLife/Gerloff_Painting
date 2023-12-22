from django.contrib.auth.decorators import login_required
from changeorder.models import *
from jobs.models import Jobs, JobCharges, ClientEmployees
from employees.models import *
from django.shortcuts import render, redirect
from datetime import date
import json
from django.core.serializers.json import DjangoJSONEncoder
from django_tables2 import RequestConfig
from wallcovering.tables import ChangeOrderTable
from wallcovering.filters import ChangeOrderFilter
import os
import os.path
from django.template.loader import get_template, render_to_string
from xhtml2pdf import pisa
from console.misc import createfolder, getFilesOrFolders
from django.conf import settings
from io import StringIO
from console.misc import Email
from media.utilities import MediaUtilities
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

def print_TMProposal(request, id):
    newproposal = TMProposal.objects.get(id=id)
    changeorder = newproposal.change_order
    laboritems = TMList.objects.filter(change_order=changeorder, category="Labor")
    materialitems = TMList.objects.filter(change_order=changeorder, category="Material")
    equipmentitems = TMList.objects.filter(change_order=changeorder, category="Equipment")
    extraitems = TMList.objects.filter(change_order=changeorder, category="Extras")
    inventory_exists = False
    bond_exists = False
    inventory = []
    bond = []
    if TMList.objects.filter(change_order=changeorder, category="Inventory"):
        inventory_exists = True
        inventory = TMList.objects.get(change_order=changeorder, category="Inventory")
    if TMList.objects.filter(change_order=changeorder, category="Bond"):
        bond = TMList.objects.get(change_order=changeorder, category="Bond")
        bond_exists = True
    ewt = newproposal.ticket

    path = os.path.join(settings.MEDIA_ROOT, "changeorder", str(changeorder.id))
    result_file = open(f"{path}/COP_{changeorder.cop_number}_{date.today()}.pdf", "w+b")
    if request.method == 'POST':
        html = render_to_string("print_TMProposal.html",
                                {'inventory_exists': inventory_exists, 'bond_exists': bond_exists, 'laboritems': laboritems,
                                 'materialitems': materialitems, 'inventory': inventory, 'bond': bond,
                                 'equipmentitems': equipmentitems, 'extraitems': extraitems, 'newproposal': newproposal,
                                 'changeorder': changeorder, 'ewt': ewt})
        pisa.CreatePDF(
            html,
            dest=result_file
        )
        result_file.close()
        Email.sendEmail("COP Proposal", "Please find the TM Proposal attached", ["joe@gerloffpainting.com"],
                        f"{path}/COP_{changeorder.cop_number}_{date.today()}.pdf")


    return render(request, "preview_TMProposal.html",
                  {'inventory_exists': inventory_exists, 'bond_exists': bond_exists, 'laboritems': laboritems,
                   'materialitems': materialitems, 'inventory': inventory, 'bond': bond,
                   'equipmentitems': equipmentitems, 'extraitems': extraitems, 'newproposal': newproposal,
                   'changeorder': changeorder, 'ewt': ewt})


def price_ewt(request, id):
    changeorder = ChangeOrders.objects.get(id=id)
    ewt = EWT.objects.get(change_order=changeorder)
    if request.method == 'POST':
        changeorder.price = request.POST['final_cost']
        changeorder.date_sent = date.today()
        changeorder.full_description = ewt.notes + " " + request.POST['notes']
        changeorder.save()
        ChangeOrderNotes.objects.create(cop_number=changeorder, date=date.today(),
                                        user=Employees.objects.get(user=request.user),
                                        note="COP Sent. Price: $" + request.POST['final_cost'])
        newproposal = TMProposal.objects.create(change_order=changeorder, total=request.POST['final_cost'],
                                                notes=request.POST['notes'], ticket=ewt)
        print(request.POST)
        for x in range(1, int(request.POST['hidden_labor']) + 1):
            TMList.objects.create(change_order=changeorder, description=request.POST['labor_item' + str(x)],
                                  quantity=request.POST['labor_hours' + str(x)], units="Hours",
                                  rate=request.POST['labor_rate' + str(x)], total=request.POST['labor_cost' + str(x)],
                                  category="Labor", category2=request.POST['labor_item' + str(x)], proposal=newproposal)
        for x in range(1, int(request.POST['hidden_material']) + 1):
            TMList.objects.create(change_order=changeorder, description=request.POST['material_description' + str(x)],
                                  quantity=request.POST['material_quantity' + str(x)],
                                  units=request.POST['material_units' + str(x)],
                                  rate=request.POST['material_rate' + str(x)],
                                  total=request.POST['material_cost' + str(x)],
                                  category="Material", category2=request.POST['material_category' + str(x)],
                                  proposal=newproposal)
        for x in range(1, int(request.POST['hidden_equipment']) + 1):
            TMList.objects.create(change_order=changeorder, description=request.POST['equipment_description' + str(x)],
                                  quantity=request.POST['equipment_quantity' + str(x)],
                                  units=request.POST['equipment_units' + str(x)],
                                  rate=request.POST['equipment_rate' + str(x)],
                                  total=request.POST['equipment_cost' + str(x)],
                                  category="Equipment", category2=request.POST['equipment_category' + str(x)],
                                  proposal=newproposal)
        for x in range(1, int(request.POST['hidden_extras']) + 1):
            extras = TMList.objects.create(change_order=changeorder,
                                           description=request.POST['extras_category' + str(x)],
                                           quantity=request.POST['extras_quantity' + str(x)],
                                           units=request.POST['extras_units' + str(x)],
                                           rate=request.POST['extras_rate' + str(x)],
                                           total=request.POST['extras_cost' + str(x)],
                                           category="Extras", category2=request.POST['extras_category' + str(x)],
                                           proposal=newproposal)
            if 'extras_description' + str(x) in request.POST:
                extras.description = request.POST['extras_description' + str(x)]
                extras.save()
        if 'inventory_cost' in request.POST:
            TMList.objects.create(change_order=changeorder, description="Inventory",
                                  quantity="1",
                                  units="Lump Sum",
                                  rate="1", total=request.POST['inventory_cost'],
                                  category="Inventory", category2="Inventory",
                                  proposal=newproposal)
        if 'bond_cost' in request.POST:
            TMList.objects.create(change_order=changeorder, description="Bond",
                                  quantity="1",
                                  units="Lump Sum",
                                  rate=request.POST['bond_rate'], total=request.POST['bond_cost'],
                                  category="Bond", category2="Bond",
                                  proposal=newproposal)
        return redirect('preview_TMProposal', id=newproposal.id)
    equipment = []
    laboritems = []
    materials = []
    extras = []
    totalhours = 0
    totalmaterialcost = 0
    totalcost = 0
    counter = 0
    is_bonded = False
    for x in TMPricesMaster.objects.filter(category="Labor", ewtmaster__isnull=False).distinct():
        hours = 0
        for y in EWTicket.objects.filter(EWT=ewt, master=x).exclude(employee=None).order_by('master'):
            hours = hours + y.monday + y.tuesday + y.wednesday + y.thursday + y.friday + y.saturday + y.sunday
        totalhours = totalhours + hours
        cost = hours * x.rate
        totalcost = totalcost + cost
        counter = counter + 1
        rate = float(x.rate)
        laboritems.append({'rate': rate, 'counter': counter, 'item': x, 'hours': hours, 'cost': int(cost)})
    days = totalhours / 8
    counter = 0
    for y in EWTicket.objects.filter(EWT=ewt, master__category="Material").order_by('master'):
        cost = y.quantity * y.master.rate
        totalcost = totalcost + cost
        totalmaterialcost = totalmaterialcost + cost
        counter = counter + 1
        rate = float(y.master.rate)
        materials.append(
            {'rate': rate, 'counter': counter, 'category': y.master.item, 'description': y.description,
             'quantity': y.quantity, 'units': y.units,
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
            {'rate': rate, 'counter': counter, 'category': y.master.item, 'description': y.description,
             'quantity': y.quantity, 'units': y.units,
             'cost': int(cost)})
    counter = 0
    for x in JobCharges.objects.filter(job=changeorder.job_number):
        if x.master.unit == "Day":
            cost = days * x.master.rate
            totalcost = totalcost + cost
            counter = counter + 1
            rate = float(x.master.rate)
            extras.append(
                {'rate': rate, 'counter': counter, 'category': x.master.item, 'quantity': days, 'unit': "Days",
                 'cost': int(cost)})
        elif x.master.unit == "Hours":
            cost = totalhours * x.master.rate
            totalcost = totalcost + cost
            counter = counter + 1
            rate = float(x.master.rate)
            extras.append(
                {'rate': rate, 'counter': counter, 'category': x.master.item, 'quantity': totalhours, 'unit': "Hours",
                 'cost': int(cost)})
        else:
            counter = counter + 1
            rate = float(x.master.rate)
            extras.append(
                {'rate': rate, 'counter': counter, 'category': x.master.item, 'quantity': 0, 'unit': x.master.unit,
                 'cost': 0})

    bond_rate = 0
    bond_cost = 0
    if changeorder.job_number.is_bonded == True:
        bond_rate = TMPricesMaster.objects.get(category='Bond').rate
        bond_cost = bond_rate * totalcost
        totalcost = totalcost + bond_cost
        is_bonded = True

    employees2 = TMPricesMaster.objects.filter(category="Labor").values()
    materials2 = TMPricesMaster.objects.filter(category="Material").values()
    equipment2 = TMPricesMaster.objects.filter(category="Equipment").values()
    extras2 = TMPricesMaster.objects.filter(category="Misc").values()
    employees_json = json.dumps(list(employees2), cls=DjangoJSONEncoder)
    material_json = json.dumps(list(materials2), cls=DjangoJSONEncoder)
    equipment_json = json.dumps(list(equipment2), cls=DjangoJSONEncoder)
    extras_json = json.dumps(list(extras2), cls=DjangoJSONEncoder)

    return render(request, "price_ewt.html",
                  {'notes': ewt.notes, 'is_bonded': is_bonded, 'bond_cost': int(bond_cost), 'bond_rate': bond_rate,
                   'extras_json': extras_json, 'employees_json': employees_json, 'material_json': material_json,
                   'equipment_json': equipment_json, 'laborcount': int(len(laboritems)),
                   'materialcount': int(len(materials)), 'equipmentcount': int(len(equipment)),
                   'extrascount': int(len(extras)), 'extras': extras, 'totalcost': int(totalcost),
                   'inventory': int(inventory), 'equipment': equipment, 'materials': materials,
                   'laboritems': laboritems, 'ewt': ewt,
                   'changeorder': changeorder})


def print_ticket(request, id, status):
    # status = 'OLD' paper.  status = 'NEW' digital signature
    changeorder = ChangeOrders.objects.get(id=id)
    ewt = EWT.objects.get(change_order=changeorder)
    try:
        signature = Signature.objects.get(change_order_id=id)
    except:
        signature = None
    laboritems = EWTicket.objects.filter(EWT=ewt).exclude(employee=None)
    materials = EWTicket.objects.filter(EWT=ewt, master__category="Material")
    equipment = EWTicket.objects.filter(EWT=ewt, master__category="Equipment")
    if status == 'OLD':
        ChangeOrderNotes.objects.create(cop_number=changeorder, date=date.today(),
                                        user=Employees.objects.get(user=request.user),
                                        note="Ticket Printed for Wet Signature")
        changeorder.is_printed = True
        changeorder.save()
    if request.method == 'POST':
        signatureValue = request.POST['signatureValue']
        nameValue = request.POST['signatureName']
        comments = request.POST['gc_notes']
        if signature is None:
            Signature.objects.create(change_order_id=id, type="changeorder", name=nameValue, signature=signatureValue,
                                     date=date.today(), notes=comments)
        else:
            Signature.objects.update(change_order_id=id, type="changeorder", name=nameValue, signature=signatureValue,
                                     date=date.today(), notes=comments)
        ChangeOrderNotes.objects.create(cop_number=changeorder, date=date.today(),
                                        user=Employees.objects.get(user=request.user),
                                        note="Digital Signature Received. Signed by: " + request.POST[
                                            'signatureName'] + ". Comments: " + request.POST['gc_notes'])
        signature = Signature.objects.get(change_order_id=id)
        path = os.path.join(settings.MEDIA_ROOT, "changeorder", str(changeorder.id))
        result_file = open(f"{path}/{id}_change_order_{date.today()}.pdf", "w+b")
        changeorder.is_ticket_signed = True
        changeorder.save()
        html = render_to_string("print_ticket.html",
                                {'equipment': equipment, 'materials': materials, 'laboritems': laboritems, 'ewt': ewt,
                                 'changeorder': changeorder, 'signature': signature, 'status': status})
        pisa.CreatePDF(
            html,
            dest=result_file
        )
        result_file.close()
    return render(request, "print_ticket.html",
                  {'equipment': equipment, 'materials': materials, 'laboritems': laboritems, 'ewt': ewt,
                   'changeorder': changeorder, 'signature': signature, 'status': status})


@login_required(login_url='/accounts/login')
def view_ewt(request, id):
    changeorder = ChangeOrders.objects.get(id=id)
    employees = Employees.objects.all()
    employees2 = Employees.objects.values()
    materials = TMPricesMaster.objects.filter(category="Material")
    materials2 = TMPricesMaster.objects.filter(category="Material").values()
    equipment = TMPricesMaster.objects.filter(category="Equipment").values()
    employees_json = json.dumps(list(employees2), cls=DjangoJSONEncoder)
    materials_json = json.dumps(list(materials2), cls=DjangoJSONEncoder)
    equipment_json = json.dumps(list(equipment), cls=DjangoJSONEncoder)
    return render(request, "process_ewt.html",
                  {'equipment': equipment, 'equipmentjson': equipment_json, 'materialsjson': materials_json,
                   'materials': materials, 'changeorder': changeorder, 'employees': employees,
                   'employeesjson': employees_json})


@login_required(login_url='/accounts/login')
def change_order_send(request, id):
    changeorder = ChangeOrders.objects.get(id=id)
    if request.method != 'POST':
        for x in TempRecipients.objects.filter(changeorder=changeorder):
            x.delete()
    if request.method == 'POST':
        for x in request.POST:
            if x[0:11] == 'updateemail':
                person = ClientEmployees.objects.get(person_pk=x[11:len(x)])
                person.email = request.POST['email' + str(person.person_pk)]
                person.save()
            if x[0:6] == 'remove':
                person = ClientEmployees.objects.get(person_pk=x[6:len(x)])
                ClientJobRoles.objects.get(role="Change Orders", job=changeorder.job_number, employee=person).delete()
            if x[0:10] == 'adddefault':
                person = ClientEmployees.objects.get(person_pk=x[10:len(x)])
                ClientJobRoles.objects.create(role="Change Orders", job=changeorder.job_number, employee=person)
            if x[0:10] == 'tempremove':
                person = ClientEmployees.objects.get(person_pk=x[10:len(x)])
                TempRecipients.objects.get(changeorder=changeorder, person=person).delete()
            if x[0:7] == 'tempadd':
                person = ClientEmployees.objects.get(person_pk=request.POST['addrecipient'])
                TempRecipients.objects.create(person=person, changeorder=changeorder)
            if x[0:10] == 'defaultadd':
                person = ClientEmployees.objects.get(person_pk=request.POST['addrecipient'])
                if not ClientJobRoles.objects.filter(role="Change Orders", job=changeorder.job_number,
                                                     employee=person).exists():
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
                                                user=Employees.objects.get(user=request.user),
                                                note="COP Sent. Price: $" + request.POST['price'])
                # Email.sendEmail("Change Order","Test",recipients)
                return redirect('extra_work_ticket', id=id)
    extra_contacts = False
    print(changeorder.job_number.client_Pm)
    project_pm = ClientEmployees.objects.get(person_pk=changeorder.job_number.client_Pm.person_pk)
    client_list = []
    if TempRecipients.objects.filter(changeorder=changeorder, default=False).exists():
        if TempRecipients.objects.filter(changeorder=changeorder, default=True).exists():
            TempRecipients.objects.filter(changeorder=changeorder, default=True).delete()
    if not ClientJobRoles.objects.filter(role="Change Orders", job=changeorder.job_number):
        if not TempRecipients.objects.filter(changeorder=changeorder):
            TempRecipients.objects.create(person=project_pm, changeorder=changeorder, default=True)
    else:  # means there is a default person
        if not TempRecipients.objects.filter(
                changeorder=changeorder):  # this will add all default as temp recipients if there are no temp recipients
            for x in ClientJobRoles.objects.filter(role="Change Orders", job=changeorder.job_number):
                TempRecipients.objects.create(person=x.employee, changeorder=changeorder)
    for x in ClientEmployees.objects.filter(id=changeorder.job_number.client):
        if ClientJobRoles.objects.filter(role="Change Orders", job=changeorder.job_number, employee=x).exists():
            if TempRecipients.objects.filter(changeorder=changeorder, person=x).exists():
                client_list.append(
                    {'person_pk': x.person_pk, 'name': x.name, 'default': True, 'current': True, 'email': x.email})
            else:
                extra_contacts = True
                client_list.append(
                    {'person_pk': x.person_pk, 'name': x.name, 'default': True, 'current': False, 'email': x.email})
        else:
            if TempRecipients.objects.filter(person=x, changeorder=changeorder).exists():
                client_list.append(
                    {'person_pk': x.person_pk, 'name': x.name, 'default': False, 'current': True, 'email': x.email})
            else:
                extra_contacts = True
                client_list.append(
                    {'person_pk': x.person_pk, 'name': x.name, 'default': False, 'current': False, 'email': x.email})

    return render(request, "change_order_send.html",
                  {'client_list': client_list,
                   'extra_contacts': extra_contacts, 'changeorder': changeorder})


@login_required(login_url='/accounts/login')
def change_order_new(request, jobnumber):
    send_data={}
    if request.method == 'POST':
        if 'select_job' in request.POST:
            selected_job = Jobs.objects.get(job_number=request.POST['select_job'])
            return render(request, "change_order_new.html", {'selected_job': selected_job})
        else:
            t_and_m = False
            if 'is_t_and_m' in request.POST:
                t_and_m = True
            if ChangeOrders.objects.filter(job_number=Jobs.objects.get(job_number=jobnumber)):
                last_cop = ChangeOrders.objects.filter(job_number=Jobs.objects.get(job_number=jobnumber)).order_by(
                    'cop_number').last()
                next_cop = last_cop.cop_number + 1
            else:
                next_cop = 1
            changeorder = ChangeOrders.objects.create(job_number=Jobs.objects.get(job_number=jobnumber),
                                                      is_t_and_m=t_and_m, description=request.POST['description'],
                                                      cop_number=next_cop, notes=request.POST['notes'])
            # directory = changeorder.id
            # parent_dir = "C:/Trinity/ChangeOrder"
            # path = os.path.join(parent_dir, str(directory))
            try:
                createfolder("changeorder/" + str(changeorder.id))
            except OSError as error:
                print(error)
            if changeorder.is_t_and_m == True:
                note = ChangeOrderNotes.objects.create(cop_number=changeorder, date=date.today(),
                                                       user=Employees.objects.get(user=request.user),
                                                       note="T&M COP Added. " + request.POST['notes'])
            else:
                note = ChangeOrderNotes.objects.create(cop_number=changeorder, date=date.today(),
                                                       user=Employees.objects.get(user=request.user),
                                                       note="COP Added. " + request.POST['notes'])
            return redirect('extra_work_ticket', id=changeorder.id)
    else:
        if jobnumber == 'ALL':
            if request.method == 'GET':
                if 'search_job' in request.GET:
                    send_data['jobs'] = Jobs.objects.filter(job_name__icontains=request.GET['search_job'])
                else:
                    send_data['jobs'] = Jobs.objects.filter(is_closed=False)
            else:
                send_data['jobs'] = Jobs.objects.filter(is_closed=False)
        else:
            send_data['selected_job'] = Jobs.objects.get(job_number=jobnumber)
        return render(request, "change_order_new.html", send_data)


@login_required(login_url='/accounts/login')
def change_order_home(request):
    send_data = {}
    print(request.GET)
    if request.method == 'GET':
        if 'search1' in request.GET: send_data['search1_exists'] = request.GET['search1']  # Needs Ticket
        if 'search2' in request.GET: send_data['search2_exists'] = request.GET['search2']  # super
        if 'search3' in request.GET: send_data['search3_exists'] = request.GET['search3']  # Awaiting Approval
        if 'search4' in request.GET: send_data['search4_exists'] = request.GET['search4']  # Approved
        if 'search5' in request.GET: send_data['search5_exists'] = request.GET['search5']  # Show T&M Only
        if 'search6' in request.GET: send_data['search6_exists'] = request.GET['search6']  # Include Voided
        if 'search7' in request.GET: send_data['search7_exists'] = request.GET['search7']  # Needs to be Sent
    if 'search6' in request.GET:
        search_cos = ChangeOrderFilter(request.GET, queryset=ChangeOrders.objects.filter())
    else:
        search_cos = ChangeOrderFilter(request.GET, queryset=ChangeOrders.objects.filter(is_closed=False))
    changeorders =[]
    for x in search_cos.qs.order_by('job_number', 'cop_number'):
        status=""
        if x.is_t_and_m == True:
            if x.is_ticket_signed == True:
                status="Ticket Signed"
            else:
                if x.need_ticket == False and x.is_printed == False:
                    status="Ticket Not Completed"
                else:
                    status = "Ticket Not Signed"
        price = None
        if x.price: price = "{:,}".format(int(x.price))
        changeorders.append({'job_name':x.job_number.job_name,'job_number':x.job_number.job_number,'cop_number':x.cop_number,'description':x.description,'status':status,'id':x.id,'date_sent':x.date_sent,'date_approved':x.date_approved,'is_approved':x.is_approved,'gc_number':x.gc_number,'price':price})
    send_data['changeorders'] = changeorders
    # send_data['changeorders'] = search_cos.qs.order_by('job_number', 'cop_number')
    return render(request, "change_order_home.html",send_data)


@login_required(login_url='/accounts/login')
def extra_work_ticket(request, id):
    send_data={}
    changeorder = ChangeOrders.objects.get(id=id)
    send_data['changeorder'] = changeorder
    ticket_needed = changeorder.need_ticket()
    send_data['ticket_needed']= ticket_needed
    notes = ChangeOrderNotes.objects.filter(cop_number=id)
    send_data['notes']=notes
    tmproposal = []
    foldercontents = []
    try:
        path = os.path.join(settings.MEDIA_ROOT, "changeorder", str(changeorder.id))
        foldercontents = os.listdir(path)
        send_data['foldercontents']= foldercontents
    except Exception as e:
        send_data['no_folder_contents']=True

    if TMProposal.objects.filter(change_order=changeorder):
        tmproposal = TMProposal.objects.get(change_order=changeorder)
    send_data['tmproposal'] = tmproposal
    if request.method == 'GET':
        return render(request, "extra_work_ticket.html",send_data)
    if request.method == 'POST':
        if 'new_note' in request.POST:
            ChangeOrderNotes.objects.create(note=request.POST['new_note'],
                                            cop_number=changeorder, date=date.today(),
                                            user=Employees.objects.get(user=request.user))
        if 'upload_file' in request.FILES:
            fileitem = request.FILES['upload_file']
            fn = os.path.basename(fileitem.name)
            fn2 = os.path.join(settings.MEDIA_ROOT, "changeorder", str(changeorder.id), fn)
            open(fn2, 'wb').write(fileitem.file.read())
            try:
                path = os.path.join(settings.MEDIA_ROOT, "changeorder", str(changeorder.id))
                foldercontents = os.listdir(path)
            except Exception as e:
                print('no folder contents')
        if 'view_proposal' in request.POST:
            print("NEED TO DO")
        if 'signed' in request.POST:
            changeorder.is_ticket_signed = True
            changeorder.date_signed = date.today()
            changeorder.save()
            ChangeOrderNotes.objects.create(cop_number=changeorder, date=date.today(),
                                            user=Employees.objects.get(user=request.user),
                                            note="Ticket Signed - " + request.POST['signed_notes'])
        if 'submit_form4' in request.POST:
            if changeorder.is_closed == True:
                changeorder.is_closed = False
                note = "RE-OPENED - " + request.POST['void_notes']
            else:
                changeorder.is_closed = True
                note = "VOIDED - " + request.POST['void_notes']
            changeorder.save()
            ChangeOrderNotes.objects.create(cop_number=changeorder, date=date.today(),
                                            user=Employees.objects.get(user=request.user),
                                            note=note)
            return redirect('extra_work_ticket', id=id)
        if 'submit_form1' in request.POST:
            changeorder.is_approved = True
            changeorder.date_approved = date.today()
            if request.POST['gc_number'] != '':
                changeorder.gc_number = request.POST['gc_number']
            if 'is_approved_to_bill' in request.POST:
                changeorder.is_approved_to_bill = True
            changeorder.price = request.POST['approved_price']
            changeorder.save()
            ChangeOrderNotes.objects.create(cop_number=changeorder, date=date.today(),
                                            user=Employees.objects.get(user=request.user),
                                            note="COP Approved. Price: $" + request.POST['approved_price'] + " -" +
                                                 request.POST['approval_note'])
            return redirect('extra_work_ticket', id=id)
        if 'submit_form3' in request.POST:
            if 'no_tm' in request.POST:
                print("WWHY IS IT GOING HERE")
                if changeorder.is_t_and_m == True:
                    changeorder.is_t_and_m = False
                else:
                    changeorder.is_t_and_m = True
                    changeorder.price = 0
                    changeorder.date_sent = None
                    changeorder.is_ticket_signed = False
                changeorder.save()
                if changeorder.is_t_and_m == True:
                    changeordernote = ChangeOrderNotes.objects.create(
                        note="Changed to T&M: " + request.POST['no_tm_notes'], cop_number=changeorder,
                        date=date.today(), user=Employees.objects.get(user=request.user))
                else:
                    changeordernote = ChangeOrderNotes.objects.create(
                        note="No Longer T&M: " + request.POST['no_tm_notes'], cop_number=changeorder, date=date.today(),
                        user=Employees.objects.get(user=request.user))
        notes = ChangeOrderNotes.objects.filter(cop_number=id)
        send_data['notes']=ChangeOrderNotes.objects.filter(cop_number=id)
        return render(request, "extra_work_ticket.html",send_data)


def getChangeorderFolder(request):
    filesOrFolders = getFilesOrFolders("changeorder", str(request.GET['id']))
    return HttpResponse(json.dumps(filesOrFolders))


@csrf_exempt
def downloadFile(request):
    return MediaUtilities().getDirectoryContents(str(request.GET['id']), str(request.GET['name']), 'changeorder')

@csrf_exempt
def downloadFile(request):
    return MediaUtilities().getDirectoryContents(str(request.GET['id']), str(request.GET['name']), 'changeorder')

@csrf_exempt
def uploadFile(request):
    name = ''
    try:
        fn = os.path.basename(request.FILES['file'].name)
        name = request.FILES['file'].name
        fn2 = os.path.join(settings.MEDIA_ROOT, "changeorder", str(request.POST['id']), fn)
        open(fn2, 'wb').write(request.FILES['file'].read())
    except Exception as e:
        print('cannot write to folder', e)
    return HttpResponse(json.dumps('{"name": ' + name + ' }'))

@login_required(login_url='/accounts/login')
def process_ewt(request, id):
    changeorder = ChangeOrders.objects.get(id=id)
    if request.method == 'POST':
        if EWT.objects.filter(change_order=changeorder).exists():
            ewt = EWT.objects.get(change_order=changeorder)
            TMProposal.objects.filter(ticket=ewt).delete()
            # if EWTicket.objects.filter(EWT=ewt).exists():
            EWTicket.objects.filter(EWT=ewt).delete()
            EWT.objects.get(change_order=changeorder).delete()
        ewt = EWT.objects.create(change_order=changeorder, week_ending=request.POST['date_week_ending'],
                                 notes=request.POST['ticket_description'],
                                 completed_by=request.user.first_name + " " + request.user.last_name)
        ChangeOrderNotes.objects.create(cop_number=changeorder, date=date.today(),
                                        user=Employees.objects.get(user=request.user),
                                        note="Extra Work Ticket Added")
        if 'existing_painter' in request.POST:
            answer = request.POST.getlist('existing_painter')
            tuesday = request.POST.getlist('tuesday')
            wednesday = request.POST.getlist('wednesday')
            thursday = request.POST.getlist('thursday')
            friday = request.POST.getlist('friday')
            saturday = request.POST.getlist('saturday')
            sunday = request.POST.getlist('sunday')
            monday = request.POST.getlist('monday')
            ot = request.POST.getlist('is_overtime')
            for x in range(0, len(answer)):
                if ot[x] != 'notchecked':
                    master = TMPricesMaster.objects.get(item='Painter Hours OT')
                    EWTicket.objects.create(master=master, EWT=ewt, employee=Employees.objects.get(
                        id=answer[x]), monday=float(monday[x]),
                                            tuesday=float(tuesday[x]),
                                            wednesday=float(wednesday[x]),
                                            thursday=float(thursday[x]),
                                            friday=float(friday[x]),
                                            saturday=float(saturday[x]),
                                            sunday=float(sunday[x]), ot=True)
                else:
                    master = TMPricesMaster.objects.get(item='Painter Hours')
                    EWTicket.objects.create(master=master, EWT=ewt, employee=Employees.objects.get(
                        id=answer[x]), monday=float(monday[x]),
                                            tuesday=float(tuesday[x]),
                                            wednesday=float(wednesday[x]),
                                            thursday=float(thursday[x]),
                                            friday=float(friday[x]),
                                            saturday=float(saturday[x]),
                                            sunday=float(sunday[x]), ot=False)
        if 'existing_material' in request.POST:
            answer = request.POST.getlist('existing_material')
            description = request.POST.getlist('description')
            quantity = request.POST.getlist('quantity')
            units = request.POST.getlist('units')
            for x in range(0, len(answer)):
                master = TMPricesMaster.objects.get(id=answer[x])
                EWTicket.objects.create(master=master, EWT=ewt, description=description[x],
                                        quantity=quantity[x],
                                        units=units[x])
        if 'existing_equipment' in request.POST:
            answer = request.POST.getlist('existing_equipment')
            description = request.POST.getlist('equip_description')
            quantity = request.POST.getlist('equip_quantity')
            units = request.POST.getlist('equip_units')
            for x in range(0, len(answer)):
                master = TMPricesMaster.objects.get(id=answer[x])
                EWTicket.objects.create(master=master, EWT=ewt, description=description[x],
                                        quantity=quantity[x],
                                        units=units[x])
        if request.POST['number_painters'] != 0:
            for x in range(1, int(request.POST['number_painters']) + 1):
                if 'painter_dropdown' + str(x) in request.POST:
                    hours = 0
                    if request.POST['monday' + str(x)] != '':
                        hours = hours + int(request.POST['monday' + str(x)])
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
                        master = TMPricesMaster.objects.get(item='Painter Hours OT')
                        EWTicket.objects.create(master=master, EWT=ewt, employee=Employees.objects.get(
                            id=request.POST['painter_dropdown' + str(x)]),
                                                monday=float(request.POST['monday' + str(x)]),
                                                tuesday=float(request.POST['tuesday' + str(x)]),
                                                wednesday=float(request.POST['wednesday' + str(x)]),
                                                thursday=float(request.POST['thursday' + str(x)]),
                                                friday=float(request.POST['friday' + str(x)]),
                                                saturday=float(request.POST['saturday' + str(x)]),
                                                sunday=float(request.POST['sunday' + str(x)]), ot=True)
                    else:
                        master = TMPricesMaster.objects.get(item='Painter Hours')
                        EWTicket.objects.create(master=master, EWT=ewt, employee=Employees.objects.get(
                            id=request.POST['painter_dropdown' + str(x)]),
                                                monday=float(request.POST['monday' + str(x)]),
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
                    EWTicket.objects.create(master=master, EWT=ewt, description=request.POST['description' + str(x)],
                                            quantity=request.POST['quantity' + str(x)],
                                            units=request.POST['units' + str(x)])
        if request.POST['number_equipment'] != 0:
            for x in range(1, int(request.POST['number_equipment']) + 1):
                if 'select_equipment' + str(x) in request.POST:
                    master = TMPricesMaster.objects.get(id=request.POST['select_equipment' + str(x)])
                    EWTicket.objects.create(master=master, EWT=ewt,
                                            description=request.POST['equipment_description' + str(x)],
                                            quantity=request.POST['equipment_quantity' + str(x)],
                                            units=request.POST['equipment_units' + str(x)])
        return redirect('change_order_home')
    employees = Employees.objects.all()
    employees2 = Employees.objects.values()
    materials = TMPricesMaster.objects.filter(category="Material")
    materials2 = TMPricesMaster.objects.filter(category="Material").values()
    equipment = TMPricesMaster.objects.filter(category="Equipment").values()
    employees_json = json.dumps(list(employees2), cls=DjangoJSONEncoder)
    materials_json = json.dumps(list(materials2), cls=DjangoJSONEncoder)
    equipment_json = json.dumps(list(equipment), cls=DjangoJSONEncoder)
    send_data = {'equipment': equipment, 'equipmentjson': equipment_json, 'materialsjson': materials_json,
                 'materials': materials, 'changeorder': changeorder, 'employees': employees,
                 'employeesjson': employees_json}
    if EWT.objects.filter(change_order=changeorder).exists():
        ewt = EWT.objects.get(change_order=changeorder)
        send_data['ewt'] = ewt
        adjust_date = ewt.week_ending.strftime("%Y-%m-%d")
        send_data['ewtdate'] = adjust_date
        if EWTicket.objects.filter(EWT=ewt, master__category="Labor").exists():
            laboritems = EWTicket.objects.filter(EWT=ewt, master__category="Labor").values()
            # laboritems = json.dumps(list(laboritems1), cls=DjangoJSONEncoder)
            send_data['laboritems'] = laboritems
        if EWTicket.objects.filter(EWT=ewt, master__category="Material").exists():
            materialitems = EWTicket.objects.filter(EWT=ewt, master__category="Material").values()
            # materialitems = json.dumps(list(materialitems1), cls=DjangoJSONEncoder)
            send_data['materialitems'] = materialitems
            inventory = EWTicket.objects.filter(EWT=ewt, master__category="Inventory")
            # inventory = json.dumps(list(inventory1), cls=DjangoJSONEncoder)
            send_data['inventory'] = inventory
        if EWTicket.objects.filter(EWT=ewt, master__category="Extras").exists():
            extraitems = EWTicket.objects.filter(EWT=ewt, master__category="Extra").values()
            # extraitems = json.dumps(list(extraitems1), cls=DjangoJSONEncoder)
            send_data['extraitems'] = extraitems
        if EWTicket.objects.filter(EWT=ewt, master__category="Equipment").exists():
            equipmentitems = EWTicket.objects.filter(EWT=ewt, master__category="Equipment").values()
            # equipmentitems = json.dumps(list(equipmentitems1), cls=DjangoJSONEncoder)
            send_data['equipmentitems'] = equipmentitems
        if EWTicket.objects.filter(EWT=ewt, master__category="Bond").exists():
            bond = EWTicket.objects.filter(EWT=ewt, master__category="Bond").values
            # bond = json.dumps(list(bond1), cls=DjangoJSONEncoder)
            send_data['bond'] = bond

    return render(request, "process_ewt.html", send_data)

@login_required(login_url='/accounts/login')
def get_directory_contents(request, id, value,app):
    return MediaUtilities().getDirectoryContents(id, value, app)