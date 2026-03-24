
from changeorder.models import *
from changeorder.models import ChangeOrders, EWT, EWTicket, TMPricesMaster
from collections import defaultdict
from console.misc import createfolder, getFilesOrFolders, create_shortcut
from console.misc import Email, get_client_ip, is_internal_ip, create_excel_from_template, get_subfolders, find_post_bid_docs_shortcut, resolve_shortcut, create_folder_shortcut, create_changeorder_shortcut_in_plan_folder
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Case, When, IntegerField
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import get_template, render_to_string
from django.utils.text import get_valid_filename
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django_tables2 import RequestConfig
from employees.models import *
from io import StringIO, BytesIO
from jobs.models import Jobs, JobCharges, ClientEmployees, Email_Errors,JobNotes
from media.utilities import MediaUtilities
from media.utilities import MediaUtilities
from .models import ChangeOrders
from wallcovering.filters import ChangeOrderFilter
from wallcovering.tables import ChangeOrderTable
from xhtml2pdf import pisa
import json
import os
import os.path



def emailed_ticket(request, id):
    send_data = {}
    changeorder = ChangeOrders.objects.get(id=id)
    ewt = EWT.objects.get(change_order=changeorder)
    recipient = ewt.recipient
    send_data['recipient']=recipient

    status = 'NEW'
    try:
        signature = Signature.objects.get(change_order_id=id)
    except:
        signature = None
    laboritems = EWTicket.objects.filter(EWT=ewt).exclude(employee=None, custom_employee=None)
    materials = EWTicket.objects.filter(EWT=ewt, master__category="Material")
    equipment = EWTicket.objects.filter(EWT=ewt, master__category="Equipment")
    sundries = EWTicket.objects.filter(EWT=ewt, master__category="Sundries")
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
                                        user=Employees.objects.get(id=42),
                                        note="Digital Signature Received. Signed by: " + request.POST[
                                            'signatureName'] + ". Comments: " + request.POST['gc_notes'])
        changeorder.is_ticket_signed = True
        changeorder.digital_ticket_signed_date = date.today()
        changeorder.save()
        signature = Signature.objects.filter(change_order_id=id).first()
        # Build folder path
        path = os.path.join(
            settings.MEDIA_ROOT,
            "changeorder",
            f"{changeorder.job_number.job_number} COP #{changeorder.cop_number}"
        )
        # Create folder if it doesn't exist
        os.makedirs(path, exist_ok=True)

        # Build full PDF file path
        file_path = os.path.join(
            path,
            f"Signed_Extra_Work_Ticket_{date.today()}.pdf"
        )
        with open(file_path, "w+b") as result_file:
            html = render_to_string("signed_ticket_pdf.html",
                                {'sundries':sundries,'equipment': equipment, 'materials': materials, 'laboritems': laboritems, 'ewt': ewt,
                                 'changeorder': changeorder, 'signature': signature, 'status': status,'is_emailed_link':True})
            pisa.CreatePDF(
                html,
                dest=result_file,
                link_callback=link_callback
            )
            result_file.close()
        recipients = ["joe@gerloffpainting.com","bridgette@gerloffpainting.com"]
        recipients.append(recipient)
        job_name = changeorder.job_number.job_name
        check_sender = Employees.objects.filter(user=request.user).first() if request.user.is_authenticated else None
        sender = check_sender.email if check_sender else "operations@gerloffpainting.com"
        try:
            Email.sendEmail("Signed Gerloff Painting Ticket", f"The signed ticket is attached for {changeorder.description} - {job_name}", recipients,
                            f"{path}/Signed_Extra_Work_Ticket_{date.today()}.pdf",sender)
            send_data['error_message'] = "The email with the signed ticket was successfully sent!"
        except:
            send_data['error_message'] = "ERROR! The email with the signed ticket was not sent!"
            send_data['email_failed'] = True
        return render(request, "print_ticket3.html", send_data)

    return render(request, "print_ticket.html",
                  {'equipment': equipment, 'materials': materials, 'laboritems': laboritems, 'ewt': ewt,
                   'changeorder': changeorder, 'signature': signature, 'status': status,'sundries':sundries,'is_emailed_link':True})


def email_for_signature(request, id):
    if request.method == 'POST':
        if 'recipient' in request.POST:
            changeorder = ChangeOrders.objects.get(id=id)
            client = changeorder.job_number.client
            name=request.POST['recipient_name']
            phone = request.POST['recipient_phone']
            email = request.POST['recipient_email']
            recipient_id = request.POST['recipient']
            if recipient_id == 'add_new':
                if request.POST['add_recipient_form']:
                    ClientEmployees.objects.create(id=client, name=name, phone=phone, email=email)
            else:
                recipient = ClientEmployees.objects.get(person_pk=recipient_id)
                if request.POST['change_recipient_form']:
                    recipient.name=name
                    recipient.phone=phone
                    recipient.email=email
                    recipient.save()
            email_body = "You have received an extra work ticket from Gerloff Painting.  \nPlease click this link http://www.google.com"
            recipients = ["joe@gerloffpainting.com"]
            recipients.append(email)
            Email_Errors.objects.filter(user=request.user.first_name + " " + request.user.last_name).delete()
            check_sender = Employees.objects.filter(user=request.user).first() if request.user.is_authenticated else None
            sender = check_sender.email if check_sender else "operations@gerloffpainting.com"
            try:
                Email.sendEmail("Extra Work Ticket", email_body, recipients, False,sender)
                message = "The email with the link to the extra work ticket was successfully sent!"
            except:
                message = "ERROR! The email with the extra work ticket failed to send. You will need to try again later."
            Email_Errors.objects.create(user=request.user.first_name + " " + request.user.last_name, error=message,date = date.today())
    return redirect('extra_work_ticket', id=id)


@login_required(login_url='/accounts/login')
def batch_approve_co(request, id):
    changeorder = ChangeOrders.objects.get(id=id)
    selectedjob = changeorder.job_number
    allchangeorders = ChangeOrders.objects.filter(job_number=selectedjob, is_closed=False, is_approved_to_bill=False, date_sent__isnull=False).order_by('id')
    send_data = {}
    send_data['changeorder'] = changeorder
    send_data['selectedjob'] = selectedjob
    send_data['allchangeorders'] = allchangeorders
    send_data['originalcontract'] = selectedjob.contract_amount
    send_data['previous_change_orders'] = selectedjob.approved_co_amount()
    send_data['current_contract_amount'] = selectedjob.current_contract_amount()
    send_data['total_contract_amount'] = changeorder.price + selectedjob.current_contract_amount()
    changeordersjson = allchangeorders.values()
    send_data['changeordersjson'] = json.dumps(list(changeordersjson), cls=DjangoJSONEncoder)
    if request.method == 'POST':
        send_email = False
        gc_number_exists = False
        approved_for_billing = False
        approval_explanation = request.POST['notes']
        if request.POST['gc_number'] != "":
            gc_number_exists = True
            approved_for_billing = True
            gc_number = request.POST['gc_number']
        else:
            if 'approved_for_billing' in request.POST:
                approved_for_billing = True
        email_message = "The following COPs have been approved for billing on {selectedjob.job_number.job_number} {selectedjob.job_number.job_name}. "
        for x in request.POST:
            if x[0:10] == 'select_cop':
                item_number = x[10:len(x)]
                selected_cop = ChangeOrders.objects.get(id=request.POST['select_cop' + item_number])
                selected_cop.is_approved = True
                selected_cop.date_approved = date.today()
                selected_cop.price = request.POST['price' + item_number]
                if gc_number_exists:
                    selected_cop.gc_number = gc_number
                    selected_cop.is_approved_to_bill = True
                    note = "Approved! GC Number: " + str(gc_number) + ". Approved price: " + str(
                        request.POST['price' + item_number])
                elif approved_for_billing:
                    selected_cop.is_approved_to_bill = True
                    selected_cop.approval_explanation = approval_explanation
                    selected_cop.gc_number = "None"
                    note = "Approved for billing, but no GC Number! " + request.POST[
                        'notes'] + ". Approved price: " + str(request.POST['price' + item_number])
                else:
                    note = "Informal approval only! Do not add to SOVs. " + request.POST[
                        'notes'] + ". Approved price: " + str(request.POST['price' + item_number])
                    selected_cop.approval_explanation = approval_explanation
                selected_cop.save()
                if selected_cop.is_approved_to_bill:
                    send_email = True
                    email_message += f"COP {selected_cop.cop_number}-{selected_cop.description}-${selected_cop.price}. "
                ChangeOrderNotes.objects.create(cop_number=selected_cop, date=date.today(),
                                                user=Employees.objects.get(user=request.user), note=note)
                if 'upload_file' in request.FILES:
                    fileitem = request.FILES['upload_file']
                    fn = os.path.basename(fileitem.name)
                    fn2 = os.path.join(settings.MEDIA_ROOT, "changeorder",str(selected_cop.job_number.job_number)+ " COP #" + str(selected_cop.cop_number), fn)
                    open(fn2, 'wb').write(fileitem.file.read())
        if send_email:
            if not gc_number_exists:
                gc_number="None"
            subject = "COP APPROVED FOR BILLING"
            email_message += f" GC# {gc_number}. {request.POST['notes']}"
            recipients= ["bridgette@gerloffpainting.com"]
            check_sender = Employees.objects.filter(user=request.user).first() if request.user.is_authenticated else None
            sender = check_sender.email if check_sender else "operations@gerloffpainting.com"
            try:
                Email.sendEmail(subject, email_message, recipients, False, sender)
                messages.success(request, "Email Sent to Bridgette")
            except:
                messages.error(request,
                    "There was a problem sending the email to Bridgette. Please tell her it is approved.")
        return redirect('extra_work_ticket', id=selected_cop.id)
    return render(request, 'batch_approve_co.html', send_data)


def link_callback(uri, rel):

    if uri.startswith(settings.MEDIA_URL):
        path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
    elif uri.startswith(settings.STATIC_URL):
        path = os.path.join(settings.STATIC_ROOT, uri.replace(settings.STATIC_URL, ""))
    else:
        return uri

    return path

@login_required(login_url='/accounts/login')
def print_TMProposal(request, id):
    send_data={}
    email_send_error = "no"
    newproposal = TMProposal.objects.get(id=id)
    changeorder = newproposal.change_order
    laboritems = TMList.objects.filter(change_order=changeorder, category="Labor")
    materialitems = TMList.objects.filter(change_order=changeorder, category="Material")
    equipmentitems = TMList.objects.filter(change_order=changeorder, category="Equipment")
    sundriesitems = TMList.objects.filter(change_order=changeorder, category="Sundries")
    extraitems = TMList.objects.filter(change_order=changeorder, category="Extras")
    inventory_exists = False
    bond_exists = False
    inventory = []
    bond = []
    foldercontents = []
    try:
        path = os.path.join(settings.MEDIA_ROOT, "changeorder", str(changeorder.job_number.job_number)+ " COP #" + str(changeorder.cop_number))
        foldercontents = os.listdir(path)
        send_data['foldercontents'] = foldercontents
    except Exception as e:
        send_data['no_folder_contents'] = True
    if request.method != 'POST':
        for x in TempRecipients.objects.filter(changeorder=changeorder):
            x.delete()
    if TMList.objects.filter(change_order=changeorder, category="Inventory"):
        inventory_exists = True
        inventory = TMList.objects.get(change_order=changeorder, category="Inventory")
    if TMList.objects.filter(change_order=changeorder, category="Bond"):
        bond = TMList.objects.get(change_order=changeorder, category="Bond")
        bond_exists = True
    ewt = newproposal.ticket
    path = os.path.join(settings.MEDIA_ROOT, "changeorder", str(changeorder.job_number.job_number)+ " COP #" + str(changeorder.cop_number))
    result_file = open(f"{path}/GP COP {changeorder.cop_number} {changeorder.description} {date.today()}.pdf", "w+b")
    if request.method == 'POST':
        for x in request.POST:
            if x[0:11] == 'updateemail':
                person = ClientEmployees.objects.get(person_pk=x[11:len(x)])
                person.email = request.POST['email' + str(person.person_pk)]
                person.save()
            if x[0:6] == 'remove':
                person = ClientEmployees.objects.get(person_pk=x[6:len(x)])
                ClientJobRoles.objects.filter(role="Change Orders", job=changeorder.job_number, employee=person).delete()
            if x[0:10] == 'adddefault':
                person = ClientEmployees.objects.get(person_pk=x[10:len(x)])
                ClientJobRoles.objects.create(role="Change Orders", job=changeorder.job_number, employee=person)
            if x[0:10] == 'tempremove':
                person = ClientEmployees.objects.get(person_pk=x[10:len(x)])
                TempRecipients.objects.filter(changeorder=changeorder, person=person).delete()
            if x[0:7] == 'tempadd':
                if not request.POST.get("addrecipient").isdigit():#checks to see if they are adding a new person to database
                    new_client_name = request.POST.get("addrecipient")  # typed name from dropdown
                    new_client_email = request.POST.get("new_contact_email")
                    person = ClientEmployees.objects.create(id=changeorder.job_number.client, name=new_client_name,
                                                   email=new_client_email)
                else:
                    person = ClientEmployees.objects.get(person_pk=request.POST['addrecipient'])
                TempRecipients.objects.create(person=person, changeorder=changeorder)
            if x[0:10] == 'defaultadd':
                if not request.POST.get("addrecipient").isdigit(): #checks to see if they are adding a new person to database
                    new_client_name = request.POST.get("addrecipient")  # typed name from dropdown
                    new_client_email = request.POST.get("new_contact_email")
                    person = ClientEmployees.objects.create(id=changeorder.job_number.client, name=new_client_name,
                                                   email=new_client_email)
                else:
                    person = ClientEmployees.objects.get(person_pk=request.POST['addrecipient'])
                if not ClientJobRoles.objects.filter(role="Change Orders", job=changeorder.job_number,
                                                     employee=person).exists():
                    ClientJobRoles.objects.create(role="Change Orders", job=changeorder.job_number, employee=person)
                    TempRecipients.objects.create(person=person, changeorder=changeorder)
            if request.POST['status'] == 'Final' or x[0:8] == 'no_email':
                newproposal.status = "Sent"
                newproposal.save()
                changeorder.date_sent = date.today()
                changeorder.save()

                recipients = ["bridgette@gerloffpainting.com"]
                bridgette = Employees.objects.get(first_name="Bridgette", last_name="Clause")
                current_user = Employees.objects.get(user=request.user)
                if bridgette:
                    if current_user != bridgette:
                        if current_user.email:
                            recipients.append(current_user.email)
                for x in request.POST:
                    if x[0:5] == 'email':
                        recipients.append(request.POST[x])
                logo_path = os.path.join(settings.MEDIA_ROOT, "images/logo.png")

                html = render_to_string("print_TMProposal.html",
                                        {'sundriesitems':sundriesitems,'inventory_exists': inventory_exists, 'bond_exists': bond_exists,
                                         'laboritems': laboritems,
                                         'materialitems': materialitems, 'inventory': inventory, 'bond': bond,
                                         'equipmentitems': equipmentitems, 'extraitems': extraitems,
                                         'newproposal': newproposal,
                                         'changeorder': changeorder, 'ewt': ewt, 'logo_path':logo_path})
                pisa.CreatePDF(
                    html,
                    dest=result_file,
                    link_callback=link_callback
                )
                result_file.close()

                if request.POST['status'] == 'Final':
                    Email_Errors.objects.filter(user=request.user.first_name + " " + request.user.last_name).delete()
                    try:
                        files=[]
                        files.append(f"{path}/GP COP {changeorder.cop_number} {changeorder.description} {date.today()}.pdf")
                        files.append(f"{path}/" + request.POST['filename'])
                        email_subject = f"GP COP{changeorder.cop_number}- {changeorder.job_number.job_name}"
                        email_body = f"Please find the T&M Proposal attached for job {changeorder.job_number.job_name}"
                        check_sender = Employees.objects.filter(user=request.user).first() if request.user.is_authenticated else None
                        sender = check_sender.email if check_sender else "operations@gerloffpainting.com"
                        Email.sendEmail2(email_subject, email_body, recipients,files,sender)
                        ChangeOrderNotes.objects.create(cop_number=changeorder, date=date.today(),
                                                        user=Employees.objects.get(user=request.user),
                                                        note=f"COP Sent for ${changeorder.price}. Emailed to {recipients}" )
                        error = "COP was succesfully emailed"
                    except:
                        email_send_error = "yes"
                        ChangeOrderNotes.objects.create(cop_number=changeorder, date=date.today(),
                                                        user=Employees.objects.get(user=request.user),
                                                        note=f"COP Sent for ${changeorder.price}. Attempted to email to {recipients} but failed.")
                        error = "COP FAILED to Email! Please try again later!"
                    Email_Errors.objects.create(user=request.user.first_name + " " + request.user.last_name,
                                                error=error, date=date.today())
                else:
                    ChangeOrderNotes.objects.create(cop_number=changeorder, date=date.today(),
                                                    user=Employees.objects.get(user=request.user),
                                                    note=f"COP Sent for ${changeorder.price}. User decided to send email themself",)
                return redirect('extra_work_ticket', id=changeorder.id)

    extra_contacts = False
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
    for x in ClientEmployees.objects.filter(id=changeorder.job_number.client,is_active=True).order_by('name'):
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
    client_list = sorted(client_list, key=lambda x: x['name'].lower())
    send_data['email_send_error']=email_send_error
    send_data['client_list'] =client_list
    send_data['extra_contacts'] =extra_contacts
    send_data['inventory_exists'] =inventory_exists
    send_data['bond_exists'] =bond_exists
    send_data['laboritems'] =laboritems
    send_data['materialitems']=materialitems
    send_data['inventory'] =inventory
    send_data['bond'] =bond
    send_data['equipmentitems'] =equipmentitems
    send_data['sundriesitems'] = sundriesitems
    send_data['extraitems'] =extraitems
    send_data['newproposal'] =newproposal
    send_data['changeorder'] =changeorder
    send_data['ewt'] =ewt
    return render(request, "preview_TMProposal.html",send_data)


@login_required(login_url='/accounts/login')
def revise_TM_COP(request, id):
    changeorder = ChangeOrders.objects.get(id=id)

    if request.method == 'POST':
        if 'cancel' in request.POST:
            return redirect('extra_work_ticket', id=changeorder.id)
        material_exists = 0
        changeorder.price = request.POST['final_cost']
        changeorder.date_sent = date.today()
        changeorder.full_description = request.POST['notes']
        changeorder.save()
        ChangeOrderNotes.objects.create(cop_number=changeorder, date=date.today(),
                                        user=Employees.objects.get(user=request.user),
                                        note="Revised COP Sent. Price: $" + request.POST['final_cost'])
        newproposal = TMProposal.objects.get(change_order=changeorder)
        newproposal.total =request.POST['final_cost']
        newproposal.notes = request.POST['notes']
        newproposal.save()
        for x in TMList.objects.filter(proposal=newproposal):
            x.delete()
        for x in request.POST:
            if x[0:10] == 'labor_item':
                temp_number = x[10:len(x)]
                TMList.objects.create(change_order=changeorder, description=request.POST['labor_item' + temp_number],
                                      quantity=request.POST['labor_hours' + temp_number], units="Hours",
                                      rate=request.POST['labor_rate' + temp_number],
                                      total=request.POST['labor_cost' + temp_number],
                                      category="Labor", category2=request.POST['labor_item' + temp_number],
                                      proposal=newproposal)
            if x[0:20] == 'material_description':
                material_exists = 1
                temp_number = x[20:len(x)]
                TMList.objects.create(change_order=changeorder,
                                      description=request.POST['material_description' + temp_number],
                                      quantity=request.POST['material_quantity' + temp_number],
                                      units=request.POST['material_units' + temp_number],
                                      rate=request.POST['material_rate' + temp_number],
                                      total=request.POST['material_cost' + temp_number],
                                      category="Material", category2=request.POST['material_category' + temp_number],
                                      proposal=newproposal)
            if x[0:21] == 'equipment_description':
                temp_number = x[21:len(x)]
                TMList.objects.create(change_order=changeorder,
                                      description=request.POST['equipment_description' + temp_number],
                                      quantity=request.POST['equipment_quantity' + temp_number],
                                      units=request.POST['equipment_units' + temp_number],
                                      rate=request.POST['equipment_rate' + temp_number],
                                      total=request.POST['equipment_cost' + temp_number],
                                      category="Equipment", category2=request.POST['equipment_category' + temp_number],
                                      proposal=newproposal)
            if x[0:20] == 'sundries_description':
                temp_number = x[20:len(x)]
                TMList.objects.create(change_order=changeorder,
                                      description=request.POST['equipment_description' + temp_number],
                                      quantity=request.POST['equipment_quantity' + temp_number],
                                      units=request.POST['equipment_units' + temp_number],
                                      rate=request.POST['equipment_rate' + temp_number],
                                      total=request.POST['equipment_cost' + temp_number],
                                      category="Sundries", category2=request.POST['sundries_category' + temp_number],
                                      proposal=newproposal)
            if x[0:15] == 'extras_category':
                temp_number = x[15:len(x)]
                TMList.objects.create(change_order=changeorder,
                                      description=request.POST['extras_description' + temp_number],
                                      quantity=request.POST['extras_quantity' + temp_number],
                                      units=request.POST['extras_units' + temp_number],
                                      rate=request.POST['extras_rate' + temp_number],
                                      total=request.POST['extras_cost' + temp_number],
                                      category="Extras", category2=request.POST['extras_category' + temp_number],
                                      proposal=newproposal)
        if material_exists == 1:
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
    send_data = {}
    send_data['tmproposal'] = TMProposal.objects.get(change_order=changeorder)

    if EWT.objects.filter(change_order = changeorder).exists():
        ewt = EWT.objects.get(change_order = changeorder)
        send_data['ewt']=ewt
    send_data['change_order']=changeorder
    laboritems = []
    counter = 0
    totallaborcost=0
    for x in TMList.objects.filter(change_order=changeorder,category="Labor").order_by('id'):
        counter += 1
        totallaborcost += x.total
        laboritems.append({'rate': x.rate, 'counter': counter, 'item': x, 'hours': x.quantity, 'cost': x.total})
    materials = []
    counter = 0
    totalmaterialcost=0
    for x in TMList.objects.filter(change_order=changeorder, category="Material").order_by('id'):
        counter += 1
        totalmaterialcost += x.total
        materials.append(
            {'rate': x.rate, 'counter': counter,
             'description': x.description,
             'quantity': x.quantity, 'units': x.units,
             'cost': x.total})
    inventory = TMList.objects.get(change_order=changeorder, category="Inventory").total
    equipment = []
    counter = 0
    totalequipmentcost=0
    for x in TMList.objects.filter(change_order=changeorder, category="Equipment").order_by('id'):
        counter += 1
        totalequipmentcost+= x.total
        equipment.append(
            {'rate': x.rate, 'counter': counter,
             'description': x.description,
             'quantity': x.quantity, 'units': x.units,
             'cost': x.total})
    sundries = []
    counter = 0
    totalsundriescost=0
    for x in TMList.objects.filter(change_order=changeorder, category="Sundries").order_by('id'):
        counter += 1
        totalsundriescost += x.total
        sundries.append(
            {'rate': x.rate, 'counter': counter,
             'description': x.description,
             'quantity': x.quantity, 'units': x.units,
             'cost': x.total})
    extras = []
    counter = 0
    totalextrascost=0
    for x in TMList.objects.filter(change_order=changeorder, category="Extras").order_by('id'):
        counter += 1
        totalextrascost+= x.total
        extras.append(
            {'rate': x.rate, 'counter': counter,
             'description': x.description,
             'quantity': x.quantity, 'units': x.units,
             'cost': x.total})
    bond_rate = 0
    bond_cost = 0
    is_bonded = False
    totalcost=totalmaterialcost+totallaborcost+totalequipmentcost+totalsundriescost+totalextrascost+inventory
    if changeorder.job_number.is_bonded == True:
        bond_rate = TMPricesMaster.objects.get(category='Bond').rate
        bond_cost = bond_rate * totalcost
        totalcost = totalcost + bond_cost
        is_bonded = True
    send_data['is_bonded'] = is_bonded
    send_data['bond_cost'] = int(bond_cost)
    send_data['bond_rate'] = int(bond_rate)
    employees2 = TMPricesMaster.objects.filter(category="Labor").values()
    materials2 = TMPricesMaster.objects.filter(category="Material").values()
    equipment2 = TMPricesMaster.objects.filter(category="Equipment").values()
    sundries2 = TMPricesMaster.objects.filter(category="Sundries").values()
    extras2 = TMPricesMaster.objects.filter(category="Misc").values()
    send_data['employees_json'] = json.dumps(list(employees2), cls=DjangoJSONEncoder)
    send_data['material_json'] = json.dumps(list(materials2), cls=DjangoJSONEncoder)
    send_data['equipment_json'] = json.dumps(list(equipment2), cls=DjangoJSONEncoder)
    send_data['sundries_json'] = json.dumps(list(sundries2), cls=DjangoJSONEncoder)
    send_data['extras_json'] = json.dumps(list(extras2), cls=DjangoJSONEncoder)
    send_data['laborcount']=int(len(laboritems))
    send_data['materialcount'] =int(len(materials))
    send_data['equipmentcount']=int(len(equipment))
    send_data['sundriescount'] = int(len(sundries))
    send_data['extrascount'] =int(len(extras))
    send_data['extras'] = extras
    send_data['totalcost'] =int(totalcost)
    send_data['inventory']=inventory
    send_data['equipment'] =equipment
    send_data['sundries'] = sundries
    send_data['materials']=materials
    send_data['laboritems'] =laboritems
    send_data['changeorder'] = changeorder
    send_data['employees2']=employees2
    send_data['materials2'] =materials2
    send_data['equipment2']=equipment2
    send_data['sundries2'] = sundries2
    send_data['extras2'] =extras2
    send_data['totalmaterialcost'] =int(totalmaterialcost)
    send_data['totallaborcost'] =int(totallaborcost)
    send_data['totalequipmentcost']=int(totalequipmentcost)
    send_data['totalsundriescost'] = int(totalsundriescost)
    send_data['totalextrascost'] =int(totalextrascost)
    return render(request, "revise_TM_COP.html",send_data)

@login_required(login_url='/accounts/login')
def price_ewt(request, id):

    changeorder = ChangeOrders.objects.get(id=id)
    ewt = EWT.objects.filter(change_order=changeorder).first()

    def safe_decimal(val):
        try:
            return Decimal(val or "0")
        except:
            return Decimal("0")

    # ==========================================================
    # ======================= POST LOGIC ========================
    # ==========================================================
    if request.method == "POST":

        # ---------------------------
        # Detect Action
        # ---------------------------
        action = None

        if "save_draft" in request.POST:
            action = "save_draft"

        elif "send_for_approval" in request.POST:
            action = "send_for_approval"

        elif "send_to_gc" in request.POST:
            action = "send_to_gc"

        elif "approve" in request.POST:
            action = "approve"

        elif "cancel" in request.POST:
            return redirect("extra_work_ticket", id=changeorder.id)

        # ---------------------------
        # Begin Atomic Transaction
        # ---------------------------
        print(action)
        with transaction.atomic():

            # --------------------------------------------------
            # Update ChangeOrder Base Values
            # --------------------------------------------------
            changeorder.price = request.POST.get("final_cost", 0)
            changeorder.full_description = request.POST.get("notes", "")
            changeorder.save()

            # --------------------------------------------------
            # Get or Create Proposal
            # --------------------------------------------------
            proposal = TMProposal.objects.filter(
                change_order=changeorder
            ).order_by("-id").first()

            if not proposal:
                proposal = TMProposal.objects.create(
                    change_order=changeorder,
                    ticket=ewt,
                    status="Draft",
                )
            date_string = request.POST.get("week_ending", "")
            for fmt in ("%Y-%m-%d", "%B %d, %Y"):
                try:
                    converted_date = datetime.strptime(date_string, fmt).date()
                    proposal.week_ending = converted_date
                except:
                    print("ERROR")
            proposal.completed_by = request.POST.get("completed_by", "")
            proposal.total = request.POST.get("final_cost", 0)
            proposal.notes = request.POST.get("notes", "")
            proposal.save()
            # --------------------------------------------------
            # Rebuild TMList (ALWAYS)
            # --------------------------------------------------
            TMList.objects.filter(proposal=proposal).delete()

            # ==================================================
            # LABOR
            # ==================================================
            for key in request.POST:
                if not key.startswith("labor_item"):
                    continue

                index = key.replace("labor_item", "")

                desc = request.POST.get(f"labor_item{index}", "").strip()
                hours = safe_decimal(request.POST.get(f"labor_hours{index}"))
                rate = safe_decimal(request.POST.get(f"labor_rate{index}"))
                total = safe_decimal(request.POST.get(f"labor_cost{index}"))

                if not desc or hours <= 0 or rate <= 0:
                    continue

                TMList.objects.create(
                    change_order=changeorder,
                    description=desc,
                    quantity=hours,
                    units="Hours",
                    rate=rate,
                    total=total,
                    category="Labor",
                    category2=desc,
                    proposal=proposal
                )

            # ==================================================
            # GENERIC CATEGORY PROCESSOR
            # ==================================================
            def process_category(prefix, category_name):
                for key in request.POST:
                    if not key.startswith(f"{prefix}_description"):
                        continue

                    index = key.replace(f"{prefix}_description", "")

                    desc = request.POST.get(f"{prefix}_description{index}", "").strip()
                    qty = safe_decimal(request.POST.get(f"{prefix}_quantity{index}"))
                    rate = safe_decimal(request.POST.get(f"{prefix}_rate{index}"))
                    total = safe_decimal(request.POST.get(f"{prefix}_cost{index}"))
                    units = request.POST.get(f"{prefix}_units{index}", "")

                    if not desc or qty <= 0 or rate <= 0:
                        continue

                    TMList.objects.create(
                        change_order=changeorder,
                        description=desc,
                        quantity=qty,
                        units=units,
                        rate=rate,
                        total=total,
                        category=category_name,
                        category2=request.POST.get(f"{prefix}_category{index}", desc),
                        proposal=proposal
                    )

            process_category("material", "Material")
            process_category("equipment", "Equipment")
            process_category("sundries", "Sundries")
            process_category("extras", "Extras")

            # ==================================================
            # INVENTORY
            # ==================================================
            inventory_cost = safe_decimal(request.POST.get("inventory_cost"))
            if inventory_cost > 0:
                TMList.objects.create(
                    change_order=changeorder,
                    description="Inventory",
                    quantity=1,
                    units="Lump Sum",
                    rate=1,
                    total=inventory_cost,
                    category="Inventory",
                    category2="Inventory",
                    proposal=proposal
                )

            # ==================================================
            # BOND
            # ==================================================
            bond_cost = safe_decimal(request.POST.get("bond_cost"))
            bond_rate = safe_decimal(request.POST.get("bond_rate"))

            if bond_cost > 0:
                TMList.objects.create(
                    change_order=changeorder,
                    description="Bond",
                    quantity=1,
                    units="Lump Sum",
                    rate=bond_rate,
                    total=bond_cost,
                    category="Bond",
                    category2="Bond",
                    proposal=proposal
                )

            # ==================================================
            # APPLY ACTION
            # ==================================================

            if action == "save_draft":
                if not proposal.status:
                    proposal.status = "Draft"
                    proposal.save()

                ChangeOrderNotes.objects.create(
                    cop_number=changeorder,
                    date=date.today(),
                    user=Employees.objects.get(user=request.user),
                    note=f"Proposal saved as Draft. Price: ${proposal.total}"
                )

                return redirect("extra_work_ticket", id=changeorder.id)

            elif action == "send_for_approval":
                proposal.status = "Pending Approval"
                proposal.date_sent_for_approval = date.today()
                proposal.save()

                ChangeOrderNotes.objects.create(
                    cop_number=changeorder,
                    date=date.today(),
                    user=Employees.objects.get(user=request.user),
                    note=f"T&M Proposal sent to PM for approval. Price: ${proposal.total}"
                )

                return redirect("select_pm_approval", id=changeorder.id)

            elif action == "send_to_gc":
                # moved this code to print_TMProposal
                # proposal.status = "Sent"
                # proposal.save()
                #
                # changeorder.date_sent = date.today()
                # changeorder.save()
                #
                # ChangeOrderNotes.objects.create(
                #     cop_number=changeorder,
                #     date=date.today(),
                #     user=Employees.objects.get(user=request.user),
                #     note=f"COP Sent to GC. Price: ${proposal.total}"
                # )
                return redirect("preview_TMProposal", id=proposal.id)

            elif action == "approve":
                proposal.status = "Approved"
                proposal.date_approved_internally = date.today()
                proposal.approved_by = Employees.objects.get(user=request.user)
                proposal.save()

                ChangeOrderNotes.objects.create(
                    cop_number=changeorder,
                    date=date.today(),
                    user=Employees.objects.get(user=request.user),
                    note=f"COP Approved. Price: ${proposal.total}"
                )

                approval_link = request.build_absolute_uri(
                    reverse('price_ewt', args=[changeorder.id])
                )

                message = f"""
T&M Proposal #{changeorder.cop_number} for {changeorder.job_number} is approved.

Click below to send:
{approval_link}
"""

                recipient_list = ['bridgette@gerloffpainting.com']
                subject = "T&M Proposal Approved"
                check_sender = Employees.objects.filter(user=request.user).first() if request.user.is_authenticated else None
                sender = check_sender.email if check_sender else "operations@gerloffpainting.com"
                try:
                    Email.sendEmail(subject, message, recipient_list, False,sender)
                    messages.success(request, "Email Sent to Bridgette")
                except:
                    messages.error(request,
                        "There was a problem sending the email to Bridgette. Please tell her it is approved.")

                return redirect("extra_work_ticket", id=changeorder.id)
    # ==========================================================
    # ======================= GET LOGIC ========================
    # ==========================================================


    proposal = TMProposal.objects.filter(change_order=changeorder).order_by("-id").first()
    if proposal and TMList.objects.filter(proposal=proposal).exists():
        build_from_proposal = True
    else:
        build_from_proposal = False
    inventory = 0
    equipment = []
    sundries = []
    laboritems = []
    materials = []
    extras = []
    totalhours = 0
    totalmaterialcost = 0
    totallaborcost = 0
    totalequipmentcost = 0
    totalsundriescost = 0
    totalextrascost = 0
    totalcost = 0
    counter = 0
    labor_counter = 0
    material_counter = 0
    equip_counter = 0
    sundries_counter = 0
    extras_counter = 0
    is_bonded = False
    bond_rate = 0
    bond_cost = 0
    if changeorder.job_number.is_bonded == True:
        bond_rate = TMPricesMaster.objects.get(category='Bond').rate
        bond_cost = bond_rate * totalcost
        totalcost = totalcost + bond_cost
        is_bonded = True
    week_ending = None
    completed_by = None
    if build_from_proposal:
        week_ending = proposal.week_ending
        completed_by = proposal.completed_by
        for x in TMList.objects.filter(proposal=proposal).order_by("-id").all():
            if x.category == "Labor":
                labor_counter += 1
                laboritems.append({'rate': x.rate, 'counter': labor_counter, 'item': x.category2, 'hours': x.quantity, 'cost': x.total,'id':""})
                totallaborcost += x.total
                totalcost = totalcost + x.total
            if x.category == "Material":
                material_counter += 1
                totalmaterialcost = totalmaterialcost + x.total
                totalcost = totalcost + x.total
                materials.append(
                    {'rate': x.rate, 'counter': material_counter, 'category': x.category, 'category_id': "",
                     'description': x.description,
                     'quantity': x.quantity, 'units': x.units,
                     'cost': x.total})
            if x.category == "Sundries":
                sundries_counter += 1
                totalsundriescost = totalsundriescost + x.total
                totalcost = totalcost + x.total
                sundries.append(
                    {'rate': x.rate, 'counter': sundries_counter, 'category': x.category, 'category_id': "",
                     'description': x.description,
                     'quantity': x.quantity, 'units': x.units,
                     'cost': x.total})
            if x.category == "Equipment":
                equip_counter += 1
                totalequipmentcost = totalequipmentcost + x.total
                totalcost = totalcost + x.total
                equipment.append(
                    {'rate': x.rate, 'counter': equip_counter, 'category': x.category, 'category_id': "",
                     'description': x.description,
                     'quantity': x.quantity, 'units': x.units,
                     'cost': x.total})
            if x.category == "Extras":
                extras_counter += 1
                totalextrascost = totalextrascost + x.total
                totalcost = totalcost + x.total
                extras.append(
                    {'rate': x.rate, 'counter': extras_counter, 'category': x.category, 'category_id': "",
                     'description': x.description,
                     'quantity': x.quantity, 'units': x.units,
                     'cost': x.total})
        inventory = int(float(totalmaterialcost) * .15)
    elif ewt:
        week_ending = ewt.week_ending
        completed_by = ewt.completed_by
        for x in TMPricesMaster.objects.filter(category="Labor", ewtmaster__isnull=False).distinct():
            if EWTicket.objects.filter(EWT=ewt, master=x).exclude(employee=None, custom_employee=None).exists():
                hours = 0
                for y in EWTicket.objects.filter(EWT=ewt, master=x).exclude(employee=None, custom_employee=None).order_by(
                        'master'):
                    hours = hours + y.monday + y.tuesday + y.wednesday + y.thursday + y.friday + y.saturday + y.sunday
                totalhours = totalhours + hours
                cost = hours * x.rate
                totalcost = totalcost + cost
                counter = counter + 1
                rate = float(x.rate)
                laboritems.append({'rate': rate, 'counter': counter, 'item': x, 'hours': hours, 'cost': int(cost)})
        days = totalhours / 8
        counter = 0
        totallaborcost = totalcost
        for y in EWTicket.objects.filter(EWT=ewt, category="Material").order_by('master'):
            cost=0
            rate =0
            counter = counter + 1
            category = y.category
            category_id = None
            if y.master:
                cost = y.quantity * y.master.rate
                totalcost = totalcost + cost
                totalmaterialcost = totalmaterialcost + cost
                rate = float(y.master.rate)
                category_id = y.master.id
            materials.append(
                {'rate': rate, 'counter': counter, 'category': category, 'category_id': category_id,
                 'description': y.description,
                 'quantity': y.quantity, 'units': y.units,
                 'cost': int(cost)})
        inventory = int(float(totalmaterialcost) * .15)
        totalcost = totalcost + inventory
        totalmaterialcost = totalmaterialcost + inventory
        counter = 0
        for y in EWTicket.objects.filter(EWT=ewt, category="Equipment").order_by('master'):
            cost=0
            rate =0
            counter = counter + 1
            category = y.category
            category_id = None
            if y.master:
                cost = y.quantity * y.master.rate
                totalcost = totalcost + cost
                totalequipmentcost += cost
                rate = float(y.master.rate)
                category_id = y.master.id
            equipment.append(
                {'rate': rate, 'counter': counter, 'category': category, 'category_id': category_id,
                 'description': y.description,
                 'quantity': y.quantity, 'units': y.units,
                 'cost': int(cost)})
        counter = 0
        for y in EWTicket.objects.filter(EWT=ewt, category="Sundries").order_by('master'):
            cost=0
            rate =0
            counter = counter + 1
            category = y.category
            category_id = None
            if y.master:
                cost = y.quantity * y.master.rate
                totalcost = totalcost + cost
                totalsundriescost += cost
                counter = counter + 1
                rate = float(y.master.rate)
                #category = y.master.item
                category_id = y.master.id
            sundries.append(
                {'rate': rate, 'counter': counter, 'category': category, 'category_id': category_id,
                 'description': y.description,
                 'quantity': y.quantity, 'units': y.units,
                 'cost': int(cost)})
    #as of 2/28/26 joe does not this this part is used anywhere. we should add it, for recurring extras that need to go on every change order for a job
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
    #end of part that joe doesn't think is used anywhere


    employees2 = TMPricesMaster.objects.filter(category="Labor").values()
    materials2 = TMPricesMaster.objects.filter(category="Material").values()
    equipment2 = TMPricesMaster.objects.filter(category="Equipment").values()
    sundries2 = TMPricesMaster.objects.filter(category="Sundries").values()
    extras2 = TMPricesMaster.objects.filter(category="Misc").values()
    employees_json = json.dumps(list(employees2), cls=DjangoJSONEncoder)
    material_json = json.dumps(list(materials2), cls=DjangoJSONEncoder)
    equipment_json = json.dumps(list(equipment2), cls=DjangoJSONEncoder)
    sundries_json = json.dumps(list(sundries2), cls=DjangoJSONEncoder)
    extras_json = json.dumps(list(extras2), cls=DjangoJSONEncoder)
    notes = ""
    if ewt:
        notes=ewt.notes
    if proposal:
        notes = proposal.notes

    return render(request, "price_ewt.html",
                  {'week_ending':week_ending,'completed_by':completed_by,'proposal':proposal,'notes': notes, 'is_bonded': is_bonded, 'bond_cost': int(bond_cost), 'bond_rate': bond_rate,
                   'extras_json': extras_json, 'employees_json': employees_json, 'material_json': material_json,
                   'equipment_json': equipment_json, 'sundries_json': sundries_json,'laborcount': int(len(laboritems)),
                   'materialcount': int(len(materials)), 'equipmentcount': int(len(equipment)),'sundriescount': int(len(sundries)),
                   'extrascount': int(len(extras)), 'extras': extras, 'totalcost': int(totalcost),
                   'inventory': int(inventory), 'equipment': equipment, 'sundries': sundries, 'materials': materials,
                   'laboritems': laboritems, 'ewt': ewt,
                   'changeorder': changeorder, 'employees2': employees2, 'materials2': materials2,
                   'equipment2': equipment2, 'sundries2': sundries2,'extras2': extras2,'totalextrascost':totalextrascost, 'totalmaterialcost': int(totalmaterialcost),
                   'totallaborcost': int(totallaborcost), 'totalequipmentcost': int(totalequipmentcost),'totalsundriescost': int(totalsundriescost)})

@login_required(login_url='/accounts/login')
def price_old_ewt(request, id):
    changeorder = ChangeOrders.objects.get(id=id)
    # ewt = EWT.objects.get(change_order=changeorder)
    if request.method == 'POST':
        if 'cancel' in request.POST:
            return redirect('extra_work_ticket', id=changeorder.id)
        material_exists = 0
        changeorder.price = request.POST['final_cost']
        changeorder.date_sent = date.today()
        changeorder.full_description = request.POST['notes']
        changeorder.save()
        ChangeOrderNotes.objects.create(cop_number=changeorder, date=date.today(),
                                        user=Employees.objects.get(user=request.user),
                                        note="COP Sent. Price: $" + request.POST['final_cost'])
        ewt=EWT.objects.create(change_order=changeorder, week_ending=request.POST['week_ending_date'],
                           notes="Paper Ticket", completed_by=request.POST['completed_by'])
        newproposal = TMProposal.objects.create(change_order=changeorder, total=request.POST['final_cost'],
                                                notes=request.POST['notes'],ticket=ewt)

        for x in request.POST:
            if x[0:10] == 'labor_item':
                temp_number = x[10:len(x)]
                TMList.objects.create(change_order=changeorder, description=request.POST['labor_item' + temp_number],
                                      quantity=request.POST['labor_hours' + temp_number], units="Hours",
                                      rate=request.POST['labor_rate' + temp_number],
                                      total=request.POST['labor_cost' + temp_number],
                                      category="Labor", category2=request.POST['labor_item' + temp_number],
                                      proposal=newproposal)
            if x[0:20] == 'material_description':
                material_exists = 1
                temp_number = x[20:len(x)]
                TMList.objects.create(change_order=changeorder,
                                      description=request.POST['material_description' + temp_number],
                                      quantity=request.POST['material_quantity' + temp_number],
                                      units=request.POST['material_units' + temp_number],
                                      rate=request.POST['material_rate' + temp_number],
                                      total=request.POST['material_cost' + temp_number],
                                      category="Material", category2=request.POST['material_category' + temp_number],
                                      proposal=newproposal)
            if x[0:21] == 'equipment_description':
                temp_number = x[21:len(x)]
                TMList.objects.create(change_order=changeorder,
                                      description=request.POST['equipment_description' + temp_number],
                                      quantity=request.POST['equipment_quantity' + temp_number],
                                      units=request.POST['equipment_units' + temp_number],
                                      rate=request.POST['equipment_rate' + temp_number],
                                      total=request.POST['equipment_cost' + temp_number],
                                      category="Equipment", category2=request.POST['equipment_category' + temp_number],
                                      proposal=newproposal)
            if x[0:20] == 'sundries_description':
                temp_number = x[20:len(x)]
                TMList.objects.create(change_order=changeorder,
                                      description=request.POST['sundries_description' + temp_number],
                                      quantity=request.POST['sundries_quantity' + temp_number],
                                      units=request.POST['sundries_units' + temp_number],
                                      rate=request.POST['sundries_rate' + temp_number],
                                      total=request.POST['sundries_cost' + temp_number],
                                      category="Sundries", category2=request.POST['sundries_category' + temp_number],
                                      proposal=newproposal)
            if x[0:15] == 'extras_category':
                temp_number = x[15:len(x)]
                TMList.objects.create(change_order=changeorder,
                                      description=request.POST['extras_description' + temp_number],
                                      quantity=request.POST['extras_quantity' + temp_number],
                                      units=request.POST['extras_units' + temp_number],
                                      rate=request.POST['extras_rate' + temp_number],
                                      total=request.POST['extras_cost' + temp_number],
                                      category="Extras", category2=request.POST['extras_category' + temp_number],
                                      proposal=newproposal)
        if material_exists == 1:
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
    sundries = []
    laboritems = []
    materials = []
    extras = []
    totalhours = 0
    totalmaterialcost = 0
    totallaborcost = 0
    totalequipmentcost = 0
    totalsundriescost = 0
    totalcost = 0
    counter = 0
    is_bonded = False
    days = 0
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
    sundries2 = TMPricesMaster.objects.filter(category="Sundries").values()
    extras2 = TMPricesMaster.objects.filter(category="Misc").values()
    employees_json = json.dumps(list(employees2), cls=DjangoJSONEncoder)
    material_json = json.dumps(list(materials2), cls=DjangoJSONEncoder)
    equipment_json = json.dumps(list(equipment2), cls=DjangoJSONEncoder)
    sundries_json = json.dumps(list(sundries2), cls=DjangoJSONEncoder)
    extras_json = json.dumps(list(extras2), cls=DjangoJSONEncoder)
    inventory = 0
    return render(request, "price_old_ewt.html",
                  {'is_bonded': is_bonded, 'bond_cost': int(bond_cost), 'bond_rate': bond_rate,
                   'extras_json': extras_json, 'employees_json': employees_json, 'material_json': material_json,
                   'equipment_json': equipment_json, 'laborcount': int(len(laboritems)),
                   'materialcount': int(len(materials)), 'equipmentcount': int(len(equipment)),
                   'extrascount': int(len(extras)), 'extras': extras, 'totalcost': int(totalcost),
                   'inventory': int(inventory), 'equipment': equipment, 'materials': materials,
                   'laboritems': laboritems, 'changeorder': changeorder, 'totalmaterialcost': int(totalmaterialcost),
                   'totallaborcost': int(totallaborcost), 'totalequipmentcost': int(totalequipmentcost),'sundries_json': sundries_json,'sundriescount': int(len(sundries)),'sundries': sundries,'totalsundriescost': int(totalsundriescost)})

@login_required(login_url='/accounts/login')
def print_ticket(request, id, status):
    # status = 'OLD' paper.  status = 'NEW' digital signature
    changeorder = ChangeOrders.objects.get(id=id)
    ewt = EWT.objects.get(change_order=changeorder)
    try:
        signature = Signature.objects.get(change_order_id=id)
    except:
        signature = None
    laboritems = EWTicket.objects.filter(EWT=ewt).exclude(employee=None, custom_employee=None)
    # materials = EWTicket.objects.filter(EWT=ewt, master__category="Material")
    # equipment = EWTicket.objects.filter(EWT=ewt, master__category="Equipment")
    # sundries = EWTicket.objects.filter(EWT=ewt, master__category="Sundries")
    materials = EWTicket.objects.filter(EWT=ewt, category="Material")
    equipment = EWTicket.objects.filter(EWT=ewt, category="Equipment")
    sundries = EWTicket.objects.filter(EWT=ewt, category="Sundries")
    if status == 'OLD':
        ChangeOrderNotes.objects.create(cop_number=changeorder, date=date.today(),
                                        user=Employees.objects.get(user=request.user),
                                        note="Ticket Printed for Wet Signature")
        changeorder.is_printed = True
        changeorder.save()
        path = os.path.join(
            settings.MEDIA_ROOT,
            "changeorder",
            f"{changeorder.job_number.job_number} COP #{changeorder.cop_number}"
        )
        # Create folder if it doesn't exist
        os.makedirs(path, exist_ok=True)

        # Build full PDF file path
        filepath = os.path.join(
            path,
            f"Unsigned Extra_Work Ticket {date.today()}.pdf"
        )
        with open(filepath, "w+b") as result_file:
            html = render_to_string("signed_ticket_pdf.html",
                                    {'sundries':sundries,'equipment': equipment, 'materials': materials, 'laboritems': laboritems, 'ewt': ewt,
                                     'changeorder': changeorder, 'signature': signature, 'status': status,'is_emailed_link':True})

            pisa.CreatePDF(
                html,
                dest=result_file,
                link_callback=link_callback
            )
            result_file.close()

        return redirect('extra_work_ticket', id=id)
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
        changeorder.is_ticket_signed = True
        changeorder.digital_ticket_signed_date = date.today()
        changeorder.save()
        signature = Signature.objects.get(change_order_id=id)
        # Build folder path
        path = os.path.join(
            settings.MEDIA_ROOT,
            "changeorder",
            f"{changeorder.job_number.job_number} COP #{changeorder.cop_number}"
        )
        # Create folder if it doesn't exist
        os.makedirs(path, exist_ok=True)

        # Build full PDF file path
        file_path = os.path.join(
            path,
            f"Signed_Extra_Work_Ticket_{date.today()}.pdf"
        )
        with open(file_path, "w+b") as result_file:
            html = render_to_string("signed_ticket_pdf.html",
                                {'sundries':sundries,'equipment': equipment, 'materials': materials, 'laboritems': laboritems, 'ewt': ewt,
                                 'changeorder': changeorder, 'signature': signature, 'status': status,'is_emailed_link':True})
        # Create PDF
            pisa.CreatePDF(
                html,
                dest=result_file,
                link_callback=link_callback
            )
            result_file.close()
        # with open(file_path, "w+b") as result_file:
        #     pisa.CreatePDF(html, dest=result_file)
        return redirect('email_signed_ticket', changeorder=changeorder.id)

    return render(request, "print_ticket.html",
                  {'sundries':sundries,'equipment': equipment, 'materials': materials, 'laboritems': laboritems, 'ewt': ewt,
                   'changeorder': changeorder, 'signature': signature, 'status': status})


@login_required(login_url='/accounts/login')
def email_signed_ticket(request, changeorder):
    send_data = {}
    changeorder = ChangeOrders.objects.get(id=changeorder)
    send_data['changeorder'] = changeorder
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
                ClientJobRoles.objects.filter(role="Extra Work Tickets", job=changeorder.job_number,
                                           employee=person).delete()
            if x[0:10] == 'adddefault':
                person = ClientEmployees.objects.get(person_pk=x[10:len(x)])
                ClientJobRoles.objects.create(role="Extra Work Tickets", job=changeorder.job_number, employee=person)
            if x[0:10] == 'tempremove':
                person = ClientEmployees.objects.get(person_pk=x[10:len(x)])
                TempRecipients.objects.filter(changeorder=changeorder, person=person).delete()
            if x[0:7] == 'tempadd':
                if not request.POST.get("addrecipient").isdigit():#checks to see if they are adding a new person to database
                    new_client_name = request.POST.get("addrecipient")  # typed name from dropdown
                    new_client_email = request.POST.get("new_contact_email")
                    person = ClientEmployees.objects.create(id=changeorder.job_number.client, name=new_client_name,
                                                   email=new_client_email)
                else:
                    person = ClientEmployees.objects.get(person_pk=request.POST['addrecipient'])
                TempRecipients.objects.create(person=person, changeorder=changeorder)
            if x[0:10] == 'defaultadd':
                if not request.POST.get("addrecipient").isdigit(): #checks to see if they are adding a new person to database
                    new_client_name = request.POST.get("addrecipient")  # typed name from dropdown
                    new_client_email = request.POST.get("new_contact_email")
                    person = ClientEmployees.objects.create(id=changeorder.job_number.client, name=new_client_name,
                                                   email=new_client_email)
                else:
                    person = ClientEmployees.objects.get(person_pk=request.POST['addrecipient'])
                if not ClientJobRoles.objects.filter(role="Extra Work Tickets", job=changeorder.job_number,
                                                     employee=person).exists():
                    ClientJobRoles.objects.create(role="Extra Work Tickets", job=changeorder.job_number,
                                                  employee=person)
                    TempRecipients.objects.create(person=person, changeorder=changeorder)
            if x[0:5] == 'final':
                recipients = ["bridgette@gerloffpainting.com"]
                bridgette = Employees.objects.get(first_name="Bridgette", last_name="Clause")
                current_user = Employees.objects.get(user=request.user)
                if bridgette:
                    if current_user != bridgette:
                        if current_user.email:
                            recipients.append(current_user.email)
                else:
                    recipients.append(current_user.email)
                if x == 'final1':
                    for y in request.POST:
                        if y[0:5] == 'email':
                            recipients.append(request.POST[y])
                ChangeOrderNotes.objects.create(cop_number=changeorder, date=date.today(),
                                                user=current_user,
                                                note="Signed Ticket emailed to " + str(recipients))
                path = os.path.join(settings.MEDIA_ROOT, "changeorder", str(changeorder.job_number.job_number)+ " COP #" + str(changeorder.cop_number))
                job_name = changeorder.job_number.job_name
                check_sender = Employees.objects.filter(user=request.user).first() if request.user.is_authenticated else None
                sender = check_sender.email if check_sender else "operations@gerloffpainting.com"
                try:
                    Email.sendEmail(f"Signed Ticket {job_name}", f"Please find the Signed Extra Work Ticket attached for {job_name}", recipients,
                                    f"{path}/Signed_Extra_Work_Ticket_{date.today()}.pdf",sender)
                    success = True
                except:
                    success = False
                return redirect('extra_work_ticket', id=changeorder.id)
    extra_contacts = False
    project_pm = ClientEmployees.objects.get(person_pk=changeorder.job_number.client_Pm.person_pk)
    client_list = []
    if TempRecipients.objects.filter(changeorder=changeorder, default=False).exists():
        if TempRecipients.objects.filter(changeorder=changeorder, default=True).exists():
            TempRecipients.objects.filter(changeorder=changeorder, default=True).delete()
    if not ClientJobRoles.objects.filter(role="Extra Work Tickets", job=changeorder.job_number):
        if not TempRecipients.objects.filter(changeorder=changeorder):
            TempRecipients.objects.create(person=project_pm, changeorder=changeorder, default=True)
    else:  # means there is a default person
        if not TempRecipients.objects.filter(
                changeorder=changeorder):  # this will add all default as temp recipients if there are no temp recipients
            for x in ClientJobRoles.objects.filter(role="Extra Work Tickets", job=changeorder.job_number):
                TempRecipients.objects.create(person=x.employee, changeorder=changeorder)
    for x in ClientEmployees.objects.filter(id=changeorder.job_number.client,is_active=True).order_by('name'):
        if ClientJobRoles.objects.filter(role="Extra Work Tickets", job=changeorder.job_number, employee=x).exists():
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
    client_list = sorted(client_list, key=lambda x: x['name'].lower())
    return render(request, "signed_ticket_send.html", {'client_list': client_list,
                                                       'extra_contacts': extra_contacts, 'changeorder': changeorder})


@login_required(login_url='/accounts/login')
def view_ewt(request, id):
    changeorder = ChangeOrders.objects.get(id=id)
    employees = Employees.objects.all()
    employees2 = Employees.objects.values()
    materials = TMPricesMaster.objects.filter(category="Material")
    materials2 = TMPricesMaster.objects.filter(category="Material").values()
    equipment = TMPricesMaster.objects.filter(category="Equipment").values()
    sundries = TMPricesMaster.objects.filter(category="Sundries").values()
    employees_json = json.dumps(list(employees2), cls=DjangoJSONEncoder)
    materials_json = json.dumps(list(materials2), cls=DjangoJSONEncoder)
    equipment_json = json.dumps(list(equipment), cls=DjangoJSONEncoder)
    sundries_json = json.dumps(list(sundries), cls=DjangoJSONEncoder)
    return render(request, "process_ewt.html",
                  {'sundries':sundries,'sundriesjson':sundries_json,'equipment': equipment, 'equipmentjson': equipment_json, 'materialsjson': materials_json,
                   'materials': materials, 'changeorder': changeorder, 'employees': employees,
                   'employeesjson': employees_json})

def get_or_create_contact(add_value,email, client):
    print("HERE")
    if not add_value:
        return None

    # EXISTING CONTACT
    if add_value.isdigit():
        return ClientEmployees.objects.get(person_pk=add_value)

    # NEW CONTACT (typed name)
    name = add_value.strip()
    email = email

    if not email:
        return None  # JS should prevent this anyway

    # # Prevent duplicate by email
    # existing = ClientEmployees.objects.filter(email=email).first()
    # if existing:
    #     return existing

    # Create new contact
    new_person = ClientEmployees.objects.create(
        name=name,
        email=email,
        id=client
    )

    return new_person

@login_required(login_url='/accounts/login')
def change_order_send(request, id):

    changeorder = ChangeOrders.objects.get(id=id)

    # --------------------------------------------------
    # Reset temp recipients if not POST
    # --------------------------------------------------
    if request.method != 'POST':
        TempRecipients.objects.filter(changeorder=changeorder).delete()

    # ==================================================
    # POST HANDLING
    # ==================================================
    if request.method == 'POST':
        # -----------------------------
        # Always update description
        # -----------------------------
        changeorder.full_description = request.POST.get('full_description', '')
        raw_price = request.POST.get('price', '').replace(',', '').strip()
        bond_amount = None
        price = None  # default

        try:
            parsed_price = Decimal(raw_price)

            if parsed_price > 0:
                changeorder.price_before_bond = parsed_price.quantize(
                    Decimal("0.01"),
                    rounding=ROUND_HALF_UP)
                if changeorder.job_number.is_bonded:
                    bond_amount = parsed_price * Decimal("0.02")
                    parsed_price = parsed_price + bond_amount
                price = parsed_price.quantize(Decimal("0.01"),rounding=ROUND_HALF_UP)
                changeorder.price = price
        except (InvalidOperation, TypeError):
            pass  # ignore invalid price for now

        changeorder.save()
        # -----------------------------
        # Button Flags
        # -----------------------------
        is_final = 'final' in request.POST
        is_myself = 'myself' in request.POST

        # ==================================================
        # 1️⃣ UPDATE EMAILS
        # ==================================================
        for key in request.POST:
            if key.startswith('updateemail'):
                person_pk = key.replace('updateemail', '')
                person = ClientEmployees.objects.get(person_pk=person_pk)
                person.email = request.POST.get(f'email{person_pk}')
                person.save()

        # ==================================================
        # 2️⃣ REMOVE DEFAULT ROLE
        # ==================================================
        for key in request.POST:
            if key.startswith('remove'):
                person_pk = key.replace('remove', '')
                person = ClientEmployees.objects.get(person_pk=person_pk)
                ClientJobRoles.objects.filter(
                    role="Change Orders",
                    job=changeorder.job_number,
                    employee=person
                ).delete()

        # ==================================================
        # 3️⃣ ADD DEFAULT ROLE
        # ==================================================
        add_value = request.POST.get("addrecipient", "").strip()
        new_email = request.POST.get("new_contact_email", "").strip()
        client = changeorder.job_number.client
        for key in request.POST:
            if key.startswith('adddefault'):
                #add new or grab existing
                person_pk = key.replace("adddefault", "")
                person = ClientEmployees.objects.get(person_pk=person_pk)
                ClientJobRoles.objects.get_or_create(
                    role="Change Orders",
                    job=changeorder.job_number,
                    employee=person
                )

        # ==================================================
        # 4️⃣ TEMP REMOVE
        # ==================================================
        for key in request.POST:
            if key.startswith('tempremove'):
                person_pk = key.replace('tempremove', '')
                person = ClientEmployees.objects.get(person_pk=person_pk)
                TempRecipients.objects.filter(
                    changeorder=changeorder,
                    person=person
                ).delete()

        # ==================================================
        # 5️⃣ TEMP ADD
        # ==================================================
        if 'tempadd' in request.POST:
            # add new or grab existing
            person = get_or_create_contact(add_value, new_email, client)
            TempRecipients.objects.get_or_create(
                person=person,
                changeorder=changeorder
            )

        # ==================================================
        # 6️⃣ DEFAULT ADD
        # ==================================================
        if any(key.startswith('defaultadd') for key in request.POST):
            # add new or grab existing
            person = get_or_create_contact(add_value, new_email, client)
            ClientJobRoles.objects.get_or_create(
                role="Change Orders",
                job=changeorder.job_number,
                employee=person
            )

            TempRecipients.objects.get_or_create(
                person=person,
                changeorder=changeorder
            )

        # ==================================================
        # 7️⃣ FINAL / MYSELF (Generate Proposal)
        # ==================================================
        if is_final or is_myself:
            if price is None:
                messages.error(request, "Please enter a valid price before creating or sending the proposal.")
                return redirect('change_order_send', id=id)
            # -----------------------------
            # Build PDF
            # -----------------------------
            logo_path = os.path.join(settings.MEDIA_ROOT, "images/logo.png")
            path = os.path.join(
                settings.MEDIA_ROOT,
                "changeorder",
                f"{changeorder.job_number.job_number} COP #{changeorder.cop_number}"
            )

            os.makedirs(path, exist_ok=True)

            filename = f"GP COP {changeorder.cop_number} {changeorder.description} {date.today()}.pdf"
            filepath = os.path.join(path, filename)

            with open(filepath, "w+b") as result_file:

                html = render_to_string(
                    "print_proposal.html",
                    {
                        'bond_amount':bond_amount,'changeorder': changeorder,
                        'full_description': request.POST.get('full_description'),
                        'price': request.POST.get('price'),
                        'date': date.today(), 'logo_path':logo_path
                    }
                )

                # pisa.CreatePDF(html, dest=result_file)
                pisa.CreatePDF(
                    html,
                    dest=result_file,
                    link_callback=link_callback
                )
                result_file.close()
            # -----------------------------
            # Save pricing + sent date
            # -----------------------------

            changeorder.date_sent = date.today()
            changeorder.save()

            current_user = Employees.objects.get(user=request.user)

            # ==================================================
            # FINAL → SEND EMAIL
            # ==================================================
            if is_final:

                recipients = {
                    "bridgette@gerloffpainting.com",
                    "joe@gerloffpainting.com"
                }

                if current_user.email:
                    recipients.add(current_user.email.lower())

                for key, value in request.POST.items():
                    if key.startswith('email') and value:
                        recipients.add(value.lower())

                recipients = list(recipients)

                changeorder.sent_to = recipients
                changeorder.save()
                subject = f"GP COP{changeorder.cop_number}- {changeorder.job_number.job_name}"
                body = f"Please see the attached change order for {changeorder.job_number}. Gerloff Painting COP #{changeorder.cop_number} - {changeorder.description}"
                Email_Errors.objects.filter(
                    user=f"{request.user.first_name} {request.user.last_name}"
                ).delete()
                check_sender = Employees.objects.filter(user=request.user).first() if request.user.is_authenticated else None
                sender = check_sender.email if check_sender else "operations@gerloffpainting.com"
                try:
                    Email.sendEmail(
                        subject,
                        body,
                        recipients,
                        filepath,
                        sender
                    )

                    ChangeOrderNotes.objects.create(
                        cop_number=changeorder,
                        date=date.today(),
                        user=current_user,
                        note=f"COP Sent. Price: ${price}. Sent to {recipients}"
                    )

                    message = "Change Order Proposal was successfully emailed"

                except Exception:
                    message = "Error! Change Order Proposal failed to email."

                    ChangeOrderNotes.objects.create(
                        cop_number=changeorder,
                        date=date.today(),
                        user=current_user,
                        note=f"COP Sent. Price: ${price}. Sent to {recipients}. EMAIL FAILED."
                    )

                Email_Errors.objects.create(
                    user=f"{request.user.first_name} {request.user.last_name}",
                    error=message,
                    date=date.today()
                )

            # ==================================================
            # MYSELF → JUST CREATE
            # ==================================================
            else:
                ChangeOrderNotes.objects.create(
                    cop_number=changeorder,
                    date=date.today(),
                    user=current_user,
                    note=f"COP Created. User will email manually. Price: ${price}"
                )

            return redirect('extra_work_ticket', id=id)

    # ==================================================
    # EXISTING CLIENT LIST LOGIC (UNCHANGED)
    # ==================================================

    extra_contacts = False
    project_pm = ClientEmployees.objects.get(
        person_pk=changeorder.job_number.client_Pm.person_pk
    )

    client_list = []

    if TempRecipients.objects.filter(changeorder=changeorder, default=False).exists():
        if TempRecipients.objects.filter(changeorder=changeorder, default=True).exists():
            TempRecipients.objects.filter(changeorder=changeorder, default=True).delete()

    if not ClientJobRoles.objects.filter(
        role="Change Orders",
        job=changeorder.job_number
    ):
        if not TempRecipients.objects.filter(changeorder=changeorder):
            TempRecipients.objects.create(
                person=project_pm,
                changeorder=changeorder,
                default=True
            )
    else:
        if not TempRecipients.objects.filter(changeorder=changeorder):
            for role in ClientJobRoles.objects.filter(
                role="Change Orders",
                job=changeorder.job_number
            ):
                TempRecipients.objects.create(
                    person=role.employee,
                    changeorder=changeorder
                )

    for employee in ClientEmployees.objects.filter(id=changeorder.job_number.client,is_active=True).order_by('name'):

        has_default = ClientJobRoles.objects.filter(
            role="Change Orders",
            job=changeorder.job_number,
            employee=employee
        ).exists()

        is_temp = TempRecipients.objects.filter(
            changeorder=changeorder,
            person=employee
        ).exists()

        if has_default and is_temp:
            client_list.append({'person_pk': employee.person_pk, 'name': employee.name, 'default': True, 'current': True, 'email': employee.email})
        elif has_default:
            extra_contacts = True
            client_list.append({'person_pk': employee.person_pk, 'name': employee.name, 'default': True, 'current': False, 'email': employee.email})
        elif is_temp:
            client_list.append({'person_pk': employee.person_pk, 'name': employee.name, 'default': False, 'current': True, 'email': employee.email})
        else:
            extra_contacts = True
            client_list.append({'person_pk': employee.person_pk, 'name': employee.name, 'default': False, 'current': False, 'email': employee.email})

    return render(
        request,
        "change_order_send.html",
        {
            'client_list': client_list,
            'extra_contacts': extra_contacts,
            'changeorder': changeorder
        }
    )

@login_required(login_url='/accounts/login')
def change_order_new_select(request):
    send_data = {}
    send_data['jobs'] = Jobs.objects.filter(is_closed=False).order_by('job_name')
    if request.method == 'POST':
        if 'select_job' in request.POST:
            selectedjob = Jobs.objects.get(job_number=request.POST['select_job'])
            return redirect('change_order_new',selectedjob.job_number)
    return render(request, "change_order_new_select.html", send_data)

@login_required(login_url='/accounts/login')
def change_order_new(request, jobnumber):
    send_data = {}
    selected_job = Jobs.objects.get(job_number=jobnumber)
    send_data['selected_job'] = selected_job
    if request.method == 'GET':
        if 'search1' in request.GET: send_data['search1_exists'] = request.GET['search1']  # Needs Ticket
        if 'search2' in request.GET: send_data['search2_exists'] = request.GET['search2']  # super
        if 'search3' in request.GET: send_data['search3_exists'] = request.GET['search3']  # Awaiting Approval
        if 'search4' in request.GET: send_data['search4_exists'] = request.GET['search4']  # Approved
        if 'search5' in request.GET: send_data['search5_exists'] = request.GET['search5']  # Show T&M Only
        if 'search6' in request.GET: send_data['search6_exists'] = request.GET['search6']  # Include Voided
        if 'search7' in request.GET: send_data['search7_exists'] = request.GET['search7']  # Needs to be Sent
    if 'search6' in request.GET:
        search_cos = ChangeOrderFilter(request.GET, queryset=ChangeOrders.objects.filter(job_number=selected_job))
    else:
        search_cos = ChangeOrderFilter(request.GET, queryset=ChangeOrders.objects.filter(is_closed=False,
                                                                                         job_number=selected_job))

    changeorders = search_cos.qs.order_by('id')
    # changeorders = search_cos
    send_data['changeorders'] = changeorders
    if request.method == 'POST':
            t_and_m = False
            if 'is_t_and_m' in request.POST:
                t_and_m = True
            if changeorders:
                last_cop = changeorders.order_by('cop_number').last()
                next_cop = last_cop.cop_number + 1
            else:
                next_cop = 1
            changeorder = ChangeOrders.objects.create(job_number=Jobs.objects.get(job_number=jobnumber),
                                                      is_t_and_m=t_and_m, description=request.POST['description'],
                                                      cop_number=next_cop, notes=request.POST['notes'])
            try:
                #createfolder("changeorder/" + str(changeorder.job_number.job_number)+ " COP #" + str(changeorder.cop_number))
                createfolder("changeorder/" + str(changeorder.job_number.job_number) + " COP #" + str(changeorder.cop_number))
            except OSError as error:
                messages.error(request,
                               "Folder Not Made - Tell Joe")
            try:
                new_file = create_excel_from_template(
                    template_name="Change Order Takeoff.xlsm",
                    destination_subfolder=os.path.join("changeorder", str(changeorder.job_number.job_number)+ " COP #" + str(changeorder.cop_number)),
                    new_filename=f"Change Order {next_cop} Takeoff.xlsm",
                )
            except:
                Email_Errors.objects.create(user=request.user.first_name + " " + request.user.last_name, error="Change Order Takeoff Not Made",date = date.today())
            if changeorder.is_t_and_m == True:
                note = ChangeOrderNotes.objects.create(cop_number=changeorder, date=date.today(),
                                                       user=Employees.objects.get(user=request.user),
                                                       note="T&M COP Added. " + request.POST['notes'])
            else:
                note = ChangeOrderNotes.objects.create(cop_number=changeorder, date=date.today(),
                                                       user=Employees.objects.get(user=request.user),
                                                       note="COP Added. " + request.POST['notes'])
            # CREATE LINK IN MANAGEMENT CONSOLE DELETED ON 2/26/26
            # parent_dir = settings.MEDIA_ROOT
            # trinity_folder = os.path.join(parent_dir, "changeorder/" + str(changeorder.job_number.job_number) + " COP #" + str(changeorder.cop_number))
            # os.makedirs(trinity_folder, exist_ok=True)
            #
            # # 2️⃣ Build network folder path
            # BASE_JOBS_PATH = r"\\gp2022\company\jobs\open jobs"
            # if os.path.exists(BASE_JOBS_PATH):
            #     job_folder_name = (
            #             f"{changeorder.job_number.job_number} "
            #             f"{changeorder.job_number.job_name}\\Contract & Billings\\Change Order Proposals"
            #         )
            #     job_folder = os.path.join(BASE_JOBS_PATH, job_folder_name)
            # if os.path.exists(job_folder):
            #     changeorder_folder_name = (
            #         f"GP COP {changeorder.cop_number} {changeorder.description}"
            #     )
            #
            #     changeorder_folder = os.path.join(
            #         BASE_JOBS_PATH,
            #         job_folder_name,
            #         changeorder_folder_name
            #     )
            #
            #     # 3️⃣ If network folder exists
            #     if os.path.exists(changeorder_folder):
            #         shortcut_name = "Shortcut to MC.lnk"
            #         shortcut_path = os.path.join(trinity_folder, shortcut_name)
            #         create_shortcut(shortcut_path, changeorder_folder)
            #         shortcut_name = "Shortcut to Trinity.lnk"
            #         shortcut_path = os.path.join(changeorder_folder, shortcut_name)
            #
            #     else:
            #         # If network folder does NOT exist,
            #         # create shortcut inside Trinity folder instead
            #         shortcut_name = f"{changeorder_folder_name}.lnk"
            #         shortcut_path = os.path.join(job_folder, shortcut_name)
            #
            #     # 4️⃣ Create the shortcut from MC to Trinity
            #     create_shortcut(shortcut_path, os.path.abspath(trinity_folder))
            # else:
            #     print("GP2022 share not accessible")

            return redirect('extra_work_ticket', id=changeorder.id)
    return render(request, "change_order_new.html", send_data)


@login_required(login_url='/accounts/login')
def change_order_home(request):
    send_data = {}
    if request.method == 'GET':
        if 'search1' in request.GET: send_data['search1_exists'] = request.GET['search1']  # Needs Ticket
        if 'search2' in request.GET: send_data['search2_exists'] = request.GET['search2']  # super
        if 'search3' in request.GET: send_data['search3_exists'] = request.GET['search3']  # Awaiting Approval
        if 'search4' in request.GET: send_data['search4_exists'] = request.GET['search4']  # Approved
        if 'search5' in request.GET: send_data['search5_exists'] = request.GET['search5']  # Show T&M Only
        if 'search6' in request.GET: send_data['search6_exists'] = request.GET['search6']  # Include Voided
        if 'search7' in request.GET: send_data['search7_exists'] = request.GET['search7']  # Needs to be Sent
    if 'search6' in request.GET:
        search_cos = ChangeOrderFilter(request.GET, queryset=ChangeOrders.objects.filter(job_number__is_closed=False))
    else:
        search_cos = ChangeOrderFilter(request.GET, queryset=ChangeOrders.objects.filter(is_closed=False,
                                                                                         job_number__is_closed=False))
    changeorders = search_cos.qs.order_by('id')
    send_data['supers'] = Employees.objects.filter(job_title__description="Superintendent", active=True)
    # changeorders = []
    # for x in search_cos.qs.order_by('job_number', 'id'):
    #     status = "Not Sent"
    #     color = "beige"
    #     if x.is_approved:
    #         if x.is_approved_to_bill:
    #             status = "Approved"
    #             color = "none"
    #         else:
    #             status = "Informal Approval"
    #             color = "yellow"
    #     elif x.date_sent:
    #         status = "Sent to GC"
    #         color = "yellow"
    #     else:
    #         if x.is_t_and_m == True:
    #             if x.is_ticket_signed == True:
    #                 tmproposal = TMProposal.objects.filter(change_order=x).first()
    #                 if tmproposal:
    #                     if tmproposal.date_sent_for_approval:
    #                         status="PM Review"
    #                         color = "beige"
    #                     else:
    #                         status="Proposal in Progress"
    #                         color = "beige"
    #                 else:
    #                     status = "Ticket Signed"
    #                     color = "beige"
    #             else:
    #                 if x.need_ticket() == True and x.is_printed == False:
    #                     status = "Ticket Not Completed"
    #                     color = "red"
    #                 else:
    #                     status = "Ticket Not Signed"
    #                     color = "red"
    #     price = None
    #     if x.price: price = "{:,}".format(int(x.price))
    #
    #     changeorders.append(
    #         {'color':color,'is_t_and_m': x.is_t_and_m, 'job_name': x.job_number.job_name, 'job_number': x.job_number.job_number,
    #          'cop_number': x.cop_number, 'description': x.description, 'status': status, 'id': x.id,
    #          'date_sent': x.date_sent, 'date_approved': x.date_approved, 'is_approved': x.is_approved,
    #          'gc_number': x.gc_number, 'price': price})

    send_data['changeorders'] = changeorders
    # send_data['changeorders'] = search_cos.qs.order_by('job_number', 'cop_number')
    return render(request, "change_order_home.html", send_data)


@login_required(login_url='/accounts/login')
def change_order_email(request, jobnumber):
    send_data={}
    return render(request, "change_order_email.html", send_data)


@login_required(login_url='/accounts/login')
def extra_work_ticket(request, id):

    send_data = {}
    full_name = request.user.first_name + " " + request.user.last_name
    errors = Email_Errors.objects.filter(user=full_name)
    if errors.exists():
        send_data['error_message'] = errors.last().error
    errors.delete()
    changeorder = ChangeOrders.objects.get(id=id)
    send_data['changeorder'] = changeorder

    job = changeorder.job_number
    #---send plan folders to select from, to create shortcuts to those folders --#
    # REMOVED 2/26/26
    # BASE_JOBS_PATH = r"\\gp2022\company\jobs\open jobs"
    # job_folder_name = f"{changeorder.job_number.job_number} {changeorder.job_number.job_name} "
    # plans_folder = os.path.join(BASE_JOBS_PATH, job_folder_name, "plans")
    # lnk_path = find_post_bid_docs_shortcut(plans_folder)
    # post_bid_docs_target = None
    # if lnk_path:
    #     post_bid_docs_target = resolve_shortcut(lnk_path)
    # if post_bid_docs_target and os.path.isdir(post_bid_docs_target):
    #     send_data['post_bid_doc_folders'] = get_subfolders(post_bid_docs_target)
    # else:
    #     send_data['post_bid_doc_folders'] = []


    if request.method == 'POST':
        if "create_post_bid_doc_shortcuts" in request.POST:
            return redirect('extra_work_ticket', id=id)
        if 'price_already_sent' in request.POST:
            changeorder.date_sent = date.today()
            changeorder.price = request.POST['price_already_sent']
            changeorder.save()
            note_text = request.POST.get('price_note')
            if note_text:
                ChangeOrderNotes.objects.create(
                    cop_number=changeorder,
                    date=date.today(),
                    user=Employees.objects.get(user=request.user),
                    note=f"Manual Price Sent Outside of Trinity. ${changeorder.price}. {note_text}"
                )

        # Shortcut creation removed 2/26/26
        #     selected_folders = request.POST.getlist("folders")
        #     changeorder_folder = os.path.join(
        #         settings.MEDIA_ROOT,
        #         "changeorder",
        #         str(changeorder.job_number.job_number)+ " COP #" + str(changeorder.cop_number),
        #     )
        #     shortcut_base_dir = changeorder_folder
        #     for folder_path in selected_folders:
        #         folder_path = os.path.normpath(folder_path)
        #         if not folder_path.startswith(post_bid_docs_target):
        #             send_data['error_message'] = "Cant Find Post Bid Docs"
        #         else:
        #             # 1️⃣ Shortcut IN change order folder → plan folder
        #             try:
        #                 create_folder_shortcut(
        #                     target_folder=folder_path,
        #                     shortcut_dir=shortcut_base_dir,
        #                 )
        #                 # 2️⃣ Shortcut IN plan folder → change order folder
        #                 create_changeorder_shortcut_in_plan_folder(
        #                     plan_folder=folder_path,
        #                     changeorder_folder=changeorder_folder,
        #                     changeorder_id=changeorder.id,
        #                 )
        #                 send_data['error_message'] = "Shortcuts to Change Order and Plans Succesfully Created"
        #             except Exception as e:
        #                 print(e)
        #                 send_data['error_message'] = "Failed to Create Shortcuts"

        #i dont think this exists anymore
        # if 'windows_explorer' in request.POST:
        #     os.startfile(path)
        if 'recipient' in request.POST:
            client = changeorder.job_number.client
            name=request.POST['recipient_name']
            phone = request.POST['recipient_phone']
            email = request.POST['recipient_email']
            recipient_id = request.POST['recipient']
            if recipient_id == 'add_new':
                if request.POST['add_recipient_form'] == "Yes":
                    ClientEmployees.objects.create(id=client, name=name, phone=phone, email=email)
            else:
                recipient = ClientEmployees.objects.get(person_pk=recipient_id)
                if request.POST['change_recipient_form'] == "Yes":
                    recipient.name=name
                    recipient.phone=phone
                    recipient.email=email
                    recipient.save()
            job_name = changeorder.job_number.job_name
            approval_link = request.build_absolute_uri(
                reverse('emailed_ticket', args=[changeorder.id])
            )

            email_body = (
                f"You have received an extra work ticket from Gerloff Painting "
                f"for {changeorder.description} at {job_name}.\n\n"
                f"Please click this link to view the ticket:\n"
                f"{approval_link}"
            )
            recipients = ["joe@gerloffpainting.com"]
            recipients.append(email)
            check_sender = Employees.objects.filter(user=request.user).first() if request.user.is_authenticated else None
            sender = check_sender.email if check_sender else "operations@gerloffpainting.com"
            try:
                Email.sendEmail("Extra Work Ticket", email_body, recipients, False,sender)
                send_data['error_message'] = "The email with the link to the extra work ticket was successfully sent!"
                ewt = EWT.objects.get(change_order=changeorder)
                ewt.recipient = email
                ewt.save()
                ChangeOrderNotes.objects.create(note="Ticket Emailed To: " + str(email),
                                                cop_number=changeorder, date=date.today(),
                                                user=Employees.objects.get(user=request.user))
            except Exception as e:
                print(e)
                send_data['error_message'] = "ERROR! The email with the extra work ticket failed to send. Please try again later. "
        if 'selected_file' in request.POST:
            return MediaUtilities().getDirectoryContents(id, request.POST['selected_file'], 'changeorder')
        if 'oldform' in request.POST:
            ChangeOrderNotes.objects.create(cop_number=changeorder, date=date.today(),
                                            user=Employees.objects.get(user=request.user),
                                            note="Blank Ticket Printed")
            changeorder.is_old_form_printed = True
            changeorder.save()
        if 'new_note' in request.POST:
            ChangeOrderNotes.objects.create(note=request.POST['new_note'],
                                            cop_number=changeorder, date=date.today(),
                                            user=Employees.objects.get(user=request.user))
        if 'upload_file2' in request.FILES:
            fileitem = request.FILES['upload_file2']
            short_year = date.today().strftime("%y")
            short_mth = date.today().strftime("%m")
            short_day = date.today().strftime("%d")
            short_date = short_year + "-" + short_mth + "-" + short_day
            extension = fileitem.name.split(".")[1]
            fn = os.path.basename(short_date + " Signed EWT." + extension)
            fn2 = os.path.join(settings.MEDIA_ROOT, "changeorder", str(changeorder.job_number.job_number)+ " COP #" + str(changeorder.cop_number), fn)
            #changed per chatgpt
            #open(fn2, 'wb').write(fileitem.file.read())
            os.makedirs(os.path.dirname(fn2), exist_ok=True)
            with open(fn2, 'wb') as f:
                for chunk in fileitem.chunks():
                    f.write(chunk)
            try:
                path = os.path.join(settings.MEDIA_ROOT, "changeorder", str(changeorder.job_number.job_number)+ " COP #" + str(changeorder.cop_number))
                foldercontents = os.listdir(path)
                send_data['foldercontents'] = foldercontents
            except Exception as e:
                print('no folder contents')
            changeorder.is_ticket_signed = True
            changeorder.date_signed = date.today()
            changeorder.save()
            ChangeOrderNotes.objects.create(note="Paper Ticket Signed and Uploaded",
                                            cop_number=changeorder, date=date.today(),
                                            user=Employees.objects.get(user=request.user))
        if 'upload_file' in request.FILES:
            fileitem = request.FILES['upload_file']
            fn = os.path.basename(fileitem.name)
            fn2 = os.path.join(settings.MEDIA_ROOT, "changeorder", str(changeorder.job_number.job_number)+ " COP #" + str(changeorder.cop_number), fn)
            open(fn2, 'wb').write(fileitem.file.read())
            try:
                path = os.path.join(settings.MEDIA_ROOT, "changeorder", str(changeorder.job_number.job_number)+ " COP #" + str(changeorder.cop_number))
                foldercontents = os.listdir(path)
                send_data['foldercontents'] = foldercontents
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
        if 'void_notes' in request.POST:
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
            message = "Change Order " + str(changeorder.cop_number) + " Approved!\n"
            message += str(changeorder.job_number.job_number) + " - " + str(changeorder.job_number.job_name) + "\n"
            message += "GC# " + str(changeorder.gc_number)
            check_sender = Employees.objects.filter(user=request.user).first() if request.user.is_authenticated else None
            sender = check_sender.email if check_sender else "operations@gerloffpainting.com"
            try:
                Email.sendEmail("Change Order Approved", message, recipients, False,sender)
                success = True
            except:
                success = False
            return redirect('extra_work_ticket', id=id)
        if 'no_tm_notes' in request.POST:
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
        return redirect('extra_work_ticket', id=id)
    send_data['client_list']= ClientEmployees.objects.filter(id=changeorder.job_number.client,is_active=True).order_by('name')
    send_data['client_list_json'] = json.dumps(list(ClientEmployees.objects.filter(id=changeorder.job_number.client,is_active=True).order_by('name').values()), cls=DjangoJSONEncoder)
    ticket_needed = changeorder.need_ticket()
    send_data['ticket_needed'] = ticket_needed
    client_ip = get_client_ip(request)
    can_open_folder = is_internal_ip(client_ip)
    send_data['can_open_folder'] = can_open_folder
    send_data['formals'] = job.formals()
    send_data['approved'] = ChangeOrders.objects.filter(job_number=job, is_approved=True, is_closed=False)
    send_data['pending'] = ChangeOrders.objects.filter(job_number=job, is_approved=False, is_closed=False)
    ewt = EWT.objects.filter(change_order=changeorder).first()
    if ewt:
        send_data['EWT'] = ewt
    tmproposal = []
    foldercontents = []
    file_count = 0
    try:
        path = os.path.join(settings.MEDIA_ROOT, "changeorder", str(changeorder.job_number.job_number)+ " COP #" + str(changeorder.cop_number))
        foldercontents = os.listdir(path)
        send_data['foldercontents'] = foldercontents
        file_count = len(foldercontents)
    except Exception as e:
        send_data['no_folder_contents'] = True
    send_data['folder_path'] = rf"\\gp-webserver\trinity\changeorder\{changeorder.job_number.job_number} COP #{changeorder.cop_number}"
    if changeorder.originated_in_management_console:
        send_data['mc_folder_path'] = rf"\\gp2022\company\jobs\open jobs\{job.job_number} {job.job_name}\Contract & Billings\Change Order Proposals\GP COP {changeorder.cop_number} {changeorder.description}"
    send_data['file_count'] = file_count
    tmproposal = TMProposal.objects.filter(change_order=changeorder).first()
    if tmproposal:
        send_data['tmproposal'] = tmproposal
    notes = ChangeOrderNotes.objects.filter(cop_number=id).order_by('id')
    total_notes = notes.count()
    if total_notes > 4:
        older_notes = notes[:total_notes - 4]
        latest_notes = notes[total_notes - 4:]
    else:
        older_notes = []
        latest_notes = notes
    send_data['older_notes'] = older_notes
    send_data['latest_notes'] = latest_notes
    status = ""
    send_status = ""
    send_data['ticket_status_class'] = "status-gray"
    send_data['send_status_class'] = "status-gray"
    if changeorder.is_approved:
        if changeorder.is_approved_to_bill:
            send_status = f"Approved For Billing- GC#{changeorder.gc_number}"
            send_data['send_status_class'] = "status-success"
        else:
            send_status = "Informally Approved"
            send_data['send_status_class'] = "status-success"
    elif changeorder.date_sent:
        send_status = f"Sent Price of ${changeorder.price} on {changeorder.date_sent}"
        send_data['send_status_class'] = "status-info"
    else:
        send_status = "Change Order Not Sent Yet"
        send_data['send_status_class'] = "status-danger"
    if changeorder.is_t_and_m:
        if changeorder.is_ticket_signed:
            send_data['ticket_status_class'] = "status-gray"
            if changeorder.digital_ticket_signed_date:
                status = f"Digital Ticket Signed on {changeorder.digital_ticket_signed_date}"
            else:
                status = "Ticket Signed. "
            if tmproposal:
                status += ". Proposal Status: " + tmproposal.status
            else:
                status += ". Proposal Status: Not Processed Yet"
        else:
            send_data['ticket_status_class'] = "status-warning"
            if changeorder.is_old_form_printed:
                status = "Blank Ticket Printed. "
            if ewt:
                ewt = ewt
                if ewt.recipient:
                    status = status + f". Digital Ticket Emailed To {ewt.recipient}. "
                else:
                    status = status + ". Digital Ticket Entered. "
            if changeorder.is_printed:
                status = status + ". Printed Digital T&M Entries for Wet Signature. "
            if not ewt:
                status = "No Ticket Has Been Completed Yet"
                send_data['ticket_status_class'] = "status-danger"

    send_data['status'] = status
    send_data['send_status'] = send_status
    return render(request, "extra_work_ticket.html", send_data)


def getChangeorderFolder(request):
    changeorder = ChangeOrders.objects.get(id=request.GET['id'])
    filesOrFolders = getFilesOrFolders("changeorder", str(changeorder.job_number.job_number)+ " COP #" + str(changeorder.cop_number))
    return HttpResponse(json.dumps(filesOrFolders))


@csrf_exempt
def downloadFile(request):
    return MediaUtilities().getDirectoryContents(str(request.GET['id']), str(request.GET['name']), 'changeorder')


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
        changeorder = ChangeOrders.objects.get(id=request.GET['id'])
        fn2 = os.path.join(settings.MEDIA_ROOT, "changeorder", str(changeorder.job_number.job_number)+ " COP #" + str(changeorder.cop_number), fn)
        open(fn2, 'wb').write(request.FILES['file'].read())
    except Exception as e:
        print('cannot write to folder', e)
    return HttpResponse(json.dumps('{"name": ' + name + ' }'))


@login_required(login_url='/accounts/login')
def process_ewt(request, id): #THIS IS GETTING REPLACED WITH EWT_CREATE
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
            ot2 = []
            for x in range(0, len(ot)):
                if ot[x] == 'checked':
                    ot2.append('checked')
                    position = len(ot2) - 2
                    ot2.pop(position)
                else:
                    ot2.append('notchecked')

            for x in range(0, len(answer)):
                if ot2[x] != 'notchecked':
                    master = TMPricesMaster.objects.get(item='Painter Hours OT')
                    new_ewt = EWTicket.objects.create(master=master, EWT=ewt, monday=float(monday[x]),
                                                      tuesday=float(tuesday[x]),
                                                      wednesday=float(wednesday[x]),
                                                      thursday=float(thursday[x]),
                                                      friday=float(friday[x]),
                                                      saturday=float(saturday[x]),
                                                      sunday=float(sunday[x]), ot=True)
                else:
                    master = TMPricesMaster.objects.get(item='Painter Hours')
                    new_ewt = EWTicket.objects.create(master=master, EWT=ewt, monday=float(monday[x]),
                                                      tuesday=float(tuesday[x]),
                                                      wednesday=float(wednesday[x]),
                                                      thursday=float(thursday[x]),
                                                      friday=float(friday[x]),
                                                      saturday=float(saturday[x]),
                                                      sunday=float(sunday[x]), ot=False)
                if answer[x][0:7] == 'painter':
                    new_ewt.custom_employee = answer[x][7:len(answer[x])]
                else:
                    if Employees.objects.filter(id=answer[x]).exists():
                        new_ewt.employee = Employees.objects.get(id=answer[x])
                new_ewt.save()

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
        if 'existing_sundries' in request.POST:
            answer = request.POST.getlist('existing_sundries')
            description = request.POST.getlist('sundries_description')
            quantity = request.POST.getlist('sundries_quantity')
            units = request.POST.getlist('sundries_units')
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
                        new_ewt = EWTicket.objects.create(master=master, EWT=ewt,
                                                          monday=float(request.POST['monday' + str(x)]),
                                                          tuesday=float(request.POST['tuesday' + str(x)]),
                                                          wednesday=float(request.POST['wednesday' + str(x)]),
                                                          thursday=float(request.POST['thursday' + str(x)]),
                                                          friday=float(request.POST['friday' + str(x)]),
                                                          saturday=float(request.POST['saturday' + str(x)]),
                                                          sunday=float(request.POST['sunday' + str(x)]), ot=True)

                    else:
                        master = TMPricesMaster.objects.get(item='Painter Hours')
                        new_ewt = EWTicket.objects.create(master=master, EWT=ewt,
                                                          monday=float(request.POST['monday' + str(x)]),
                                                          tuesday=float(request.POST['tuesday' + str(x)]),
                                                          wednesday=float(request.POST['wednesday' + str(x)]),
                                                          thursday=float(request.POST['thursday' + str(x)]),
                                                          friday=float(request.POST['friday' + str(x)]),
                                                          saturday=float(request.POST['saturday' + str(x)]),
                                                          sunday=float(request.POST['sunday' + str(x)]), ot=False)
                    if request.POST['painter_dropdown' + str(x)][0:7] == 'painter':
                        new_ewt.custom_employee = request.POST['painter_dropdown' + str(x)][
                                                  7:len(request.POST['painter_dropdown' + str(x)])]
                    else:
                        if Employees.objects.filter(id=request.POST['painter_dropdown' + str(x)]).exists():
                            new_ewt.employee = Employees.objects.get(id=request.POST['painter_dropdown' + str(x)])
                    new_ewt.save()
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
        if request.POST['number_sundries'] != 0:
            for x in range(1, int(request.POST['number_sundries']) + 1):
                if 'select_sundries' + str(x) in request.POST:
                    master = TMPricesMaster.objects.get(id=request.POST['select_sundries' + str(x)])
                    EWTicket.objects.create(master=master, EWT=ewt,
                                            description=request.POST['sundries_description' + str(x)],
                                            quantity=request.POST['sundries_quantity' + str(x)],
                                            units=request.POST['sundries_units' + str(x)])
        return redirect('extra_work_ticket', id=id)
    employees = Employees.objects.filter(active=True,job_title__description="Painter").all()
    employees2 = Employees.objects.filter(active=True,job_title__description="Painter").values()
    materials = TMPricesMaster.objects.filter(category="Material")
    materials2 = TMPricesMaster.objects.filter(category="Material").values()
    equipment = TMPricesMaster.objects.filter(category="Equipment").values()
    employees_json = json.dumps(list(employees2), cls=DjangoJSONEncoder)
    materials_json = json.dumps(list(materials2), cls=DjangoJSONEncoder)
    equipment_json = json.dumps(list(equipment), cls=DjangoJSONEncoder)
    sundries = TMPricesMaster.objects.filter(category="Sundries").values()
    sundries_json = json.dumps(list(sundries), cls=DjangoJSONEncoder)
    send_data = {}
    send_data['equipment']=equipment
    send_data['equipmentjson'] = equipment_json
    send_data['materialsjson'] = materials_json
    send_data['materials'] = materials
    send_data['changeorder'] = changeorder
    send_data['employees'] = employees
    send_data['employeesjson'] = employees_json
    send_data['sundries'] = sundries
    send_data['sundriesjson'] = sundries_json
    if EWT.objects.filter(change_order=changeorder).exists():
        ewt = EWT.objects.get(change_order=changeorder)
        send_data['ewt'] = ewt
        adjust_date = ewt.week_ending.strftime("%Y-%m-%d")
        send_data['ewtdate'] = adjust_date
        if EWTicket.objects.filter(EWT=ewt, master__category="Labor").exists():
            laboritems = EWTicket.objects.filter(EWT=ewt, master__category="Labor").values()
            send_data['row_counter'] = EWTicket.objects.filter(EWT=ewt, master__category="Labor").count()
            # laboritems = json.dumps(list(laboritems1), cls=DjangoJSONEncoder)
            send_data['laboritems'] = laboritems
        if EWTicket.objects.filter(EWT=ewt, master__category="Material").exists():
            materialitems = EWTicket.objects.filter(EWT=ewt, master__category="Material").values()
            send_data['material_row_counter'] = EWTicket.objects.filter(EWT=ewt, master__category="Material").count()
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
            send_data['equipment_row_counter'] = EWTicket.objects.filter(EWT=ewt, master__category="Equipment").count()
            # equipmentitems = json.dumps(list(equipmentitems1), cls=DjangoJSONEncoder)
            send_data['equipmentitems'] = equipmentitems
        if EWTicket.objects.filter(EWT=ewt, master__category="Sundries").exists():
            sundriesitems = EWTicket.objects.filter(EWT=ewt, master__category="Sundries").values()
            send_data['sundries_row_counter'] = EWTicket.objects.filter(EWT=ewt, master__category="Sundries").count()
            send_data['sundriesitems'] = sundriesitems
        if EWTicket.objects.filter(EWT=ewt, master__category="Bond").exists():
            bond = EWTicket.objects.filter(EWT=ewt, master__category="Bond").values
            # bond = json.dumps(list(bond1), cls=DjangoJSONEncoder)
            send_data['bond'] = bond
    else:
        adjust_date = date.today().strftime("%Y-%m-%d")
        send_data['ewtdate'] = adjust_date
    return render(request, "process_ewt.html", send_data)


@login_required(login_url='/accounts/login')
def get_directory_contents(request, id, value, app):
    return MediaUtilities().getDirectoryContents(id, value, app)


def upload_changeorder_file(request, changeorder_id):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    changeorder = get_object_or_404(ChangeOrders, id=changeorder_id)

    if not request.FILES:
        return JsonResponse({"error": "No files received"}, status=400)

    # Build folder path
    folder_path = os.path.join(
        settings.MEDIA_ROOT,
        "changeorder",
        f"{changeorder.job_number.job_number} COP #{changeorder.cop_number}"
    )

    os.makedirs(folder_path, exist_ok=True)

    for uploaded_file in request.FILES.getlist("upload_file"):
        filename = get_valid_filename(uploaded_file.name)
        file_path = os.path.join(folder_path, filename)

        with open(file_path, "wb+") as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

    return JsonResponse({"success": True})

def safe_decimal(value):
    try:
        return Decimal(value)
    except (InvalidOperation, TypeError):
        return Decimal("0")

@transaction.atomic
def ewt_create(request, changeorder_id):

    change_order = get_object_or_404(ChangeOrders, id=changeorder_id)

    # --------------------------------------------------
    # GET REQUEST
    # --------------------------------------------------
    if request.method == "GET":

        context = {
            "change_order": change_order,
            "tm_materials": TMPricesMaster.objects.filter(category="Material"),
            "tm_equipment": TMPricesMaster.objects.filter(category="Equipment"),
            "tm_sundries": TMPricesMaster.objects.filter(category="Sundries"),
            "employees": Employees.objects.filter(active=True,job_title__description="Painter").order_by("first_name"),
        }

        return render(request, "ewt_create.html", context)

    # --------------------------------------------------
    # POST REQUEST
    # --------------------------------------------------
    if request.method == "POST":

        # --------------------------------------------------
        # 1️⃣ Create EWT Header
        # --------------------------------------------------
        ewt = EWT.objects.create(
            change_order=change_order,
            week_ending=request.POST.get("week_ending"),
            notes=request.POST.get("notes"),
            completed_by=request.user.get_full_name()
                if request.user.is_authenticated else "",
        )

        ChangeOrderNotes.objects.create(cop_number=change_order, date=date.today(),
                                        user=Employees.objects.get(user=request.user),
                                        note="Extra Work Ticket Added")

        # --------------------------------------------------
        # 2️⃣ LABOR
        # --------------------------------------------------

        painter_count = int(request.POST.get("painter_count", 0))

        # Fetch masters safely once
        try:
            regular_master = TMPricesMaster.objects.get(item="Painter Hours")
        except TMPricesMaster.DoesNotExist:
            regular_master = None

        try:
            ot_master = TMPricesMaster.objects.get(item="Painter Hours OT")
        except TMPricesMaster.DoesNotExist:
            ot_master = None

        for i in range(1, painter_count + 1):

            employee_id = request.POST.get(f"employee_{i}")
            custom_employee = request.POST.get(f"custom_employee_{i}")
            regular_exists = request.POST.get(f"regular_exists_{i}") == "1"
            ot_exists = request.POST.get(f"ot_exists_{i}") == "1"

            # Collect daily hours safely
            reg_days = {}
            ot_days = {}

            total_regular = Decimal("0")
            total_ot = Decimal("0")

            for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
                reg_val = safe_decimal(request.POST.get(f"reg_{day}_{i}"))
                ot_val = safe_decimal(request.POST.get(f"ot_{day}_{i}"))

                reg_days[day] = reg_val or Decimal("0")
                ot_days[day] = ot_val or Decimal("0")

                total_regular += reg_days[day]
                total_ot += ot_days[day]

            # Skip completely empty painter rows
            if total_regular == 0 and total_ot == 0:
                continue

            # Safe employee lookup
            employee_obj = None
            if employee_id:
                try:
                    employee_obj = Employees.objects.get(id=employee_id)
                except Employees.DoesNotExist:
                    employee_obj = None

            # ---------------------------
            # Regular Hours Entry
            # ---------------------------
            if total_regular > 0 and regular_master:
                EWTicket.objects.create(
                    EWT=ewt,
                    master=regular_master,
                    category=regular_master.category,
                    employee=employee_obj,
                    custom_employee=custom_employee,
                    monday=reg_days["monday"],
                    tuesday=reg_days["tuesday"],
                    wednesday=reg_days["wednesday"],
                    thursday=reg_days["thursday"],
                    friday=reg_days["friday"],
                    saturday=reg_days["saturday"],
                    sunday=reg_days["sunday"],
                    ot=False,
                    units=regular_master.unit,
                    description=regular_master.item
                )

            # ---------------------------
            # OT Hours Entry
            # ---------------------------
            if total_ot > 0 and ot_master:
                EWTicket.objects.create(
                    EWT=ewt,
                    master=ot_master,
                    category=ot_master.category,
                    employee=employee_obj,
                    custom_employee=custom_employee,
                    monday=ot_days["monday"],
                    tuesday=ot_days["tuesday"],
                    wednesday=ot_days["wednesday"],
                    thursday=ot_days["thursday"],
                    friday=ot_days["friday"],
                    saturday=ot_days["saturday"],
                    sunday=ot_days["sunday"],
                    ot=True,
                    units=ot_master.unit,
                    description=ot_master.item
                )

        # --------------------------------------------------
        # 3️⃣ MATERIALS
        # --------------------------------------------------

        material_count = int(request.POST.get("material_count", 0))

        for i in range(1, material_count + 1):

            master_id = request.POST.get(f"material_master_{i}")
            desc = (request.POST.get(f"material_description_{i}") or "").strip()
            qty_raw = request.POST.get(f"material_quantity_{i}")
            units_raw = request.POST.get(f"material_units_{i}")

            qty = safe_decimal(qty_raw)

            # Skip completely empty rows
            if not qty or not desc:
                continue

            master = None
            category = None
            units = None

            # 🔹 If linked to TMPricesMaster
            if master_id and master_id != "new":

                try:
                    master = TMPricesMaster.objects.get(id=master_id)
                    category = master.category
                    units = master.unit
                except TMPricesMaster.DoesNotExist:
                    continue  # invalid master id — skip safely

            # 🔹 If Add New selected
            else:
                units = (units_raw or "").strip()

            EWTicket.objects.create(
                EWT=ewt,
                master=master,
                category="Material",
                description=desc,
                quantity=qty,
                units=units
            )

        # --------------------------------------------------
        # 4️⃣ EQUIPMENT
        # --------------------------------------------------

        equipment_count = int(request.POST.get("equipment_count", 0))

        for i in range(1, equipment_count + 1):

            master_id = request.POST.get(f"equipment_master_{i}")
            desc = (request.POST.get(f"equipment_description_{i}") or "").strip()
            qty_raw = request.POST.get(f"equipment_quantity_{i}")
            units_raw = request.POST.get(f"equipment_units_{i}")

            qty = safe_decimal(qty_raw)

            if not qty or not desc:
                continue

            master = None
            units = None

            if master_id and master_id != "new":

                try:
                    master = TMPricesMaster.objects.get(id=master_id)
                    units = master.unit
                except TMPricesMaster.DoesNotExist:
                    continue
            else:
                units = (units_raw or "").strip()

            EWTicket.objects.create(
                EWT=ewt,
                master=master,
                category="Equipment",  # 🔥 ALWAYS set category
                description=desc,
                quantity=qty,
                units=units
            )
        # --------------------------------
        # 5️⃣ SUNDRIES
        # --------------------------------
        sundries_count = int(request.POST.get("sundries_count", 0))

        for i in range(1, sundries_count + 1):

            master_id = request.POST.get(f"sundries_master_{i}")
            desc = (request.POST.get(f"sundries_description_{i}") or "").strip()
            qty_raw = request.POST.get(f"sundries_quantity_{i}")
            units_raw = request.POST.get(f"sundries_units_{i}")

            qty = safe_decimal(qty_raw)

            if not qty or not desc:
                continue

            master = None
            units = None

            if master_id and master_id != "new":
                try:
                    master = TMPricesMaster.objects.get(id=master_id)
                    units = master.unit
                except TMPricesMaster.DoesNotExist:
                    continue
            else:
                units = (units_raw or "").strip()

            EWTicket.objects.create(
                EWT=ewt,
                master=master,
                category="Sundries",  # 🔥 always set manually
                description=desc,
                quantity=qty,
                units=units
            )

        return redirect("extra_work_ticket", id=change_order.id)


def ewt_edit(request, changeorder_id):

    change_order = get_object_or_404(ChangeOrders, id=changeorder_id)
    ewt = get_object_or_404(EWT, change_order=change_order)

    # =====================================================
    # POST — UPDATE + REBUILD
    # =====================================================
    def safe_decimal(value):
        try:
            return Decimal(value or "0")
        except:
            return Decimal("0")

    if request.method == "POST":
        with transaction.atomic():

            # --------------------------------------------------
            # 1️⃣ Update EWT Header (do NOT recreate header)
            # --------------------------------------------------
            ewt.week_ending = request.POST.get("week_ending")
            ewt.notes = request.POST.get("notes")
            ewt.completed_by = (
                request.user.get_full_name() if request.user.is_authenticated else ""
            )
            ewt.save()

            # Optional: add a note that it was edited
            try:
                ChangeOrderNotes.objects.create(
                    cop_number=change_order,
                    date=date.today(),
                    user=Employees.objects.get(user=request.user),
                    note="Extra Work Ticket Updated",
                )
            except:
                pass

            # --------------------------------------------------
            # 2️⃣ Delete existing ticket rows and rebuild
            # --------------------------------------------------
            EWTicket.objects.filter(EWT=ewt).delete()

            days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

            # --------------------------------------------------
            # 3️⃣ LABOR (match create behavior: use masters + totals)
            # --------------------------------------------------
            painter_count = int(request.POST.get("painter_count", 0))

            # Fetch masters once
            regular_master = TMPricesMaster.objects.filter(item="Painter Hours").first()
            ot_master = TMPricesMaster.objects.filter(item="Painter Hours OT").first()

            for i in range(1, painter_count + 1):

                employee_id = request.POST.get(f"employee_{i}")
                custom_employee = request.POST.get(f"custom_employee_{i}")

                # Collect daily hours + totals
                reg_days = {}
                ot_days = {}
                total_regular = Decimal("0")
                total_ot = Decimal("0")

                for day in days:
                    reg_val = safe_decimal(request.POST.get(f"reg_{day}_{i}"))
                    ot_val = safe_decimal(request.POST.get(f"ot_{day}_{i}"))

                    reg_days[day] = reg_val
                    ot_days[day] = ot_val

                    total_regular += reg_val
                    total_ot += ot_val

                # Skip fully empty painter row
                if total_regular == 0 and total_ot == 0:
                    continue

                # Safe employee lookup
                employee_obj = None
                if employee_id:
                    employee_obj = Employees.objects.filter(id=employee_id).first()

                # Regular entry
                if total_regular > 0 and regular_master:
                    EWTicket.objects.create(
                        EWT=ewt,
                        master=regular_master,
                        category=regular_master.category or "Labor",
                        employee=employee_obj,
                        custom_employee=custom_employee,
                        monday=reg_days["monday"],
                        tuesday=reg_days["tuesday"],
                        wednesday=reg_days["wednesday"],
                        thursday=reg_days["thursday"],
                        friday=reg_days["friday"],
                        saturday=reg_days["saturday"],
                        sunday=reg_days["sunday"],
                        ot=False,
                        units=regular_master.unit,
                        description=regular_master.item,
                    )

                # OT entry
                if total_ot > 0 and ot_master:
                    EWTicket.objects.create(
                        EWT=ewt,
                        master=ot_master,
                        category=ot_master.category or "Labor",
                        employee=employee_obj,
                        custom_employee=custom_employee,
                        monday=ot_days["monday"],
                        tuesday=ot_days["tuesday"],
                        wednesday=ot_days["wednesday"],
                        thursday=ot_days["thursday"],
                        friday=ot_days["friday"],
                        saturday=ot_days["saturday"],
                        sunday=ot_days["sunday"],
                        ot=True,
                        units=ot_master.unit,
                        description=ot_master.item,
                    )

            # --------------------------------------------------
            # 4️⃣ MATERIALS (match create behavior: master vs new)
            # --------------------------------------------------
            material_count = int(request.POST.get("material_count", 0))

            for i in range(1, material_count + 1):
                master_id = request.POST.get(f"material_master_{i}")
                desc = (request.POST.get(f"material_description_{i}") or "").strip()
                qty = safe_decimal(request.POST.get(f"material_quantity_{i}"))
                units_raw = (request.POST.get(f"material_units_{i}") or "").strip()

                # Skip empty rows
                if qty <= 0 or not desc:
                    continue

                master = None
                units = None

                if master_id and master_id != "new":
                    master = TMPricesMaster.objects.filter(id=master_id).first()
                    if not master:
                        continue
                    units = master.unit
                else:
                    units = units_raw  # allow custom units

                EWTicket.objects.create(
                    EWT=ewt,
                    master=master,
                    category="Material",
                    description=desc,
                    quantity=qty,
                    units=units,
                )

            # --------------------------------------------------
            # 5️⃣ EQUIPMENT
            # --------------------------------------------------
            equipment_count = int(request.POST.get("equipment_count", 0))

            for i in range(1, equipment_count + 1):
                master_id = request.POST.get(f"equipment_master_{i}")
                desc = (request.POST.get(f"equipment_description_{i}") or "").strip()
                qty = safe_decimal(request.POST.get(f"equipment_quantity_{i}"))
                units_raw = (request.POST.get(f"equipment_units_{i}") or "").strip()

                if qty <= 0 or not desc:
                    continue

                master = None
                units = None

                if master_id and master_id != "new":
                    master = TMPricesMaster.objects.filter(id=master_id).first()
                    if not master:
                        continue
                    units = master.unit
                else:
                    units = units_raw

                EWTicket.objects.create(
                    EWT=ewt,
                    master=master,
                    category="Equipment",
                    description=desc,
                    quantity=qty,
                    units=units,
                )

            # --------------------------------------------------
            # 6️⃣ SUNDRIES
            # --------------------------------------------------
            sundries_count = int(request.POST.get("sundries_count", 0))

            for i in range(1, sundries_count + 1):
                master_id = request.POST.get(f"sundries_master_{i}")
                desc = (request.POST.get(f"sundries_description_{i}") or "").strip()
                qty = safe_decimal(request.POST.get(f"sundries_quantity_{i}"))
                units_raw = (request.POST.get(f"sundries_units_{i}") or "").strip()

                if qty <= 0 or not desc:
                    continue

                master = None
                units = None

                if master_id and master_id != "new":
                    master = TMPricesMaster.objects.filter(id=master_id).first()
                    if not master:
                        continue
                    units = master.unit
                else:
                    units = units_raw

                EWTicket.objects.create(
                    EWT=ewt,
                    master=master,
                    category="Sundries",
                    description=desc,
                    quantity=qty,
                    units=units,
                )

        return redirect("extra_work_ticket", id=change_order.id)

    # =====================================================
    # GET — BUILD DATA FOR TEMPLATE
    # =====================================================

    tickets = EWTicket.objects.filter(EWT=ewt)

    # ---------------- GROUP LABOR ----------------
    labor_map = {}

    for t in tickets.filter(category="Labor"):

        key = (t.employee.id if t.employee else None, t.custom_employee)

        if key not in labor_map:
            labor_map[key] = {
                "employee": t.employee,
                "custom_employee": t.custom_employee,
                "regular": None,
                "ot": None
            }

        day_data = {
            "monday": t.monday,
            "tuesday": t.tuesday,
            "wednesday": t.wednesday,
            "thursday": t.thursday,
            "friday": t.friday,
            "saturday": t.saturday,
            "sunday": t.sunday,
        }

        if t.ot:
            labor_map[key]["ot"] = day_data
        else:
            labor_map[key]["regular"] = day_data

    labor_list = list(labor_map.values())
    labor_count = len(labor_list)

    # ---------------- SIMPLE LISTS ----------------
    materials = tickets.filter(category="Material")
    equipment = tickets.filter(category="Equipment")
    sundries = tickets.filter(category="Sundries")

    # ---------------- COUNTS ----------------
    material_count = materials.count()
    equipment_count = equipment.count()
    sundries_count = sundries.count()

    return render(request, "ewt_edit.html", {
        "ewt": ewt,
        "change_order": change_order,
        "labor_list": labor_list,
        "labor_count": labor_count,
        "materials": materials,
        "equipment": equipment,
        "sundries": sundries,
        "material_count": material_count,
        "equipment_count": equipment_count,
        "sundries_count": sundries_count,
        "tm_materials": TMPricesMaster.objects.filter(category="Material"),
        "tm_equipment": TMPricesMaster.objects.filter(category="Equipment"),
        "tm_sundries": TMPricesMaster.objects.filter(category="Sundries"),
        "employees": Employees.objects.filter(active=True),
    })


def get_approver_for_job(job):
    obj = ChangeOrderApprovers.objects.filter(job=job).first()
    return obj.approver if obj else None

def set_default_approver_for_job(job, employee):

    obj, created = ChangeOrderApprovers.objects.update_or_create(
        job=job,
        defaults={
            "approver": employee
        }
    )

    return obj

def select_pm_approval(request, id):

    changeorder = get_object_or_404(ChangeOrders, id=id)
    job = changeorder.job_number

    non_painters = Employees.objects.filter(
        active=True
    ).exclude(
        job_title__description__icontains="Painter"
    )

    # -------------------------------------
    # Determine Default Approver
    # -------------------------------------
    default_approver = get_approver_for_job(job)
    non_painters = list(non_painters.order_by("first_name"))

    if default_approver:
        # Move default to front manually
        non_painters = sorted(
            non_painters,
            key=lambda x: x.id != default_approver.id
        )
    # if default_approver:
    #     non_painters = non_painters.annotate(
    #         is_default=Case(
    #             When(id=default_approver.id, then=0),
    #             default=1,
    #             output_field=IntegerField()
    #         )
    #     ).order_by("is_default", "first_name")
    # else:
    #     non_painters = non_painters.order_by("first_name")
    # If no default, fall back to Victor Riley
    victor = Employees.objects.filter(
        first_name="Victor",
        last_name="Riley"
    ).first()

    selected_approver_id = None

    if default_approver:
        selected_approver_id = int(default_approver.id)
    elif victor:
        selected_approver_id = int(victor.id)


    # if default_approver:
    #     selected_approver_id = default_approver.id
    # elif victor:
    #     selected_approver_id = victor.id

    # -------------------------------------
    # POST
    # -------------------------------------
    if request.method == "POST":

        approver_id = request.POST.get("approver")
        proposal = TMProposal.objects.filter(change_order=changeorder).last()

        # -----------------------------------------
        # HANDLE DEFAULT APPROVER BUTTONS
        # -----------------------------------------
        if "make_default" in request.POST and approver_id:
            pm = Employees.objects.get(id=approver_id)

            set_default_approver_for_job(job, pm)

            messages.success(request, f"{pm.first_name} is now the default approver for this job.")
            return redirect("select_pm_approval", id=changeorder.id)

        if "change_default" in request.POST and approver_id:
            pm = Employees.objects.get(id=approver_id)

            set_default_approver_for_job(job, pm)

            messages.success(request, f"Default approver updated to {pm.first_name}.")
            return redirect("select_pm_approval", id=changeorder.id)
        if proposal and approver_id:

            proposal.date_sent_for_approval = date.today()
            proposal.status = "Pending Approval"
            proposal.save()

            pm = Employees.objects.get(id=approver_id)

            approval_link = request.build_absolute_uri(
                reverse("price_ewt", args=[changeorder.id])
            )

            message = f"""
A T&M Proposal is ready for your review.

Change Order #{changeorder.cop_number}

Click below to review and approve:
{approval_link}
"""

            recipient_list = [pm.email]
            subject = "T&M Proposal Ready for Review"
            check_sender = Employees.objects.filter(user=request.user).first() if request.user.is_authenticated else None
            sender = check_sender.email if check_sender else "operations@gerloffpainting.com"
            try:
                Email.sendEmail(subject, message, recipient_list, False,sender)
                messages.success(request, "Email Sent to Approver")
            except:
                messages.error(
                    request,
                    "There was a problem sending the notification to the approver."
                )

        return redirect("extra_work_ticket", id=changeorder.id)

    return render(request, "select_pm_approval.html", {
        "changeorder": changeorder,
        "employees": non_painters,
        "default_approver": default_approver,
        "selected_approver_id": selected_approver_id,
    })

def send_cop_report(request,job_number):
    job = Jobs.objects.filter(job_number=job_number).first()
    raw_changeorders = ChangeOrders.objects.filter(
        job_number=job,
        is_closed=False
    ).order_by("id")

    changeorders = []

    for co in raw_changeorders:
        status = co.status()

        is_approved = status == "Approved"
        is_sent = status in ["Sent to GC", "Informal Approval", "Approved"]
        is_not_sent = not is_sent

        default_checked = is_sent and not is_approved

        changeorders.append({
            "id": co.id,
            "cop_number": co.cop_number,
            "description": co.description,
            "status": status,
            "price": co.price,
            "is_approved": is_approved,
            "is_sent": is_sent,
            "is_not_sent": is_not_sent,
            "default_checked": default_checked,
        })

    # --------------------------------------------------
    # Reset temp recipients if not POST
    # --------------------------------------------------
    if request.method != 'POST':
        TempRecipientsCOPList.objects.filter(job=job).delete()

    # ==================================================
    # POST HANDLING
    # ==================================================
    if request.method == 'POST':

        # -----------------------------
        # Button Flags
        # -----------------------------
        is_final = 'final' in request.POST
        is_myself = 'myself' in request.POST

        # ==================================================
        # 1️⃣ UPDATE EMAILS
        # ==================================================
        for key in request.POST:
            if key.startswith('updateemail'):
                person_pk = key.replace('updateemail', '')
                person = ClientEmployees.objects.get(person_pk=person_pk)
                person.email = request.POST.get(f'email{person_pk}')
                person.save()

        # ==================================================
        # 2️⃣ REMOVE DEFAULT ROLE
        # ==================================================
        for key in request.POST:
            if key.startswith('remove'):
                person_pk = key.replace('remove', '')
                person = ClientEmployees.objects.get(person_pk=person_pk)
                ClientJobRoles.objects.filter(
                    role="Change Orders",
                    job=job,
                    employee=person
                ).delete()

        # ==================================================
        # 3️⃣ ADD DEFAULT ROLE
        # ==================================================
        add_value = request.POST.get("addrecipient", "").strip()
        new_email = request.POST.get("new_contact_email", "").strip()
        client = job.client
        for key in request.POST:
            if key.startswith('adddefault'):
                # add new or grab existing
                person_pk = key.replace("adddefault", "")
                person = ClientEmployees.objects.get(person_pk=person_pk)
                ClientJobRoles.objects.get_or_create(
                    role="Change Orders",
                    job=job,
                    employee=person
                )

        # ==================================================
        # 4️⃣ TEMP REMOVE
        # ==================================================
        for key in request.POST:
            if key.startswith('tempremove'):
                person_pk = key.replace('tempremove', '')
                person = ClientEmployees.objects.get(person_pk=person_pk)
                TempRecipientsCOPList.objects.filter(
                    job=job,
                    person=person
                ).delete()

        # ==================================================
        # 5️⃣ TEMP ADD
        # ==================================================
        if 'tempadd' in request.POST:
            # add new or grab existing
            person = get_or_create_contact(add_value, new_email, client)
            TempRecipientsCOPList.objects.get_or_create(
                person=person,
                job=job
            )

        # ==================================================
        # 6️⃣ DEFAULT ADD
        # ==================================================
        if any(key.startswith('defaultadd') for key in request.POST):
            # add new or grab existing
            person = get_or_create_contact(add_value, new_email, client)
            ClientJobRoles.objects.get_or_create(
                role="Change Orders",
                job=job,
                employee=person
            )

            TempRecipientsCOPList.objects.get_or_create(
                person=person,
                job=job
            )

        # ==================================================
        # 7️⃣ FINAL / MYSELF (Generate Proposal)
        # ==================================================
        if is_final or is_myself:
            selected_ids = request.POST.getlist("selected_changeorders")

            if selected_ids:
                changeorders = ChangeOrders.objects.filter(
                    id__in=selected_ids,
                    job_number=job,
                    is_closed=False
                ).order_by("id")
            else:
                changeorders = ChangeOrders.objects.none()


            # -----------------------------
            # Build PDF
            # -----------------------------

            logo_path = os.path.join(settings.MEDIA_ROOT, "images/logo.png")
            filepath = os.path.join(
                settings.MEDIA_ROOT,
                "temp",
                f"Gerloff Painting COP Report {job.job_name}.pdf"
            )
            with open(filepath, "w+b") as result_file:

                html = render_to_string(
                    "cop_report_pdf.html",
                    {
                        "job": job,
                        "changeorders": changeorders,
                        "today": date.today(),
                        "logo_path": logo_path
                    }
                )

                # pisa.CreatePDF(html, dest=result_file)
                pisa.CreatePDF(
                    html,
                    dest=result_file,
                    link_callback=link_callback
                )
                result_file.close()
            # -----------------------------
            # Save pricing + sent date
            # -----------------------------
            current_user = Employees.objects.get(user=request.user)

            # ==================================================
            # FINAL → SEND EMAIL
            # ==================================================

            recipients = {}
            if current_user.email:
                recipients ={current_user.email.lower()}
            else:
                recipients = {"bridgette@gerloffpainting.com"}
            if is_final:
                recipients.add("bridgette@gerloffpainting.com")
                recipients.add("joe@gerloffpainting.com")
                for key, value in request.POST.items():
                    if key.startswith('email') and value:
                        recipients.add(value.lower())
            recipients = list(recipients)
            subject = f"Change Orders - {job.job_name}"
            body = f"Attached is the current Change Order report for {job.job_number}. Please advise on approval status."
            check_sender = Employees.objects.filter(user=request.user).first() if request.user.is_authenticated else None
            sender = check_sender.email if check_sender else "operations@gerloffpainting.com"
            try:
                Email.sendEmail(
                    subject,
                    body,
                    recipients,
                    filepath,
                    sender
                )
                JobNotes.objects.create(
                    job_number=job,
                    note=f"Change Order Log sent to was sent to {recipients}",
                    type = "auto_co_note",
                    user = current_user,
                    date = date.today()
                )
                messages.success(request, "COP Report sent")

            except Exception:
                messages.error(request,"Email Not Sent.  Please Try Again Later")

            return redirect('change_order_new', job.job_number)

    # ==================================================
    # EXISTING CLIENT LIST LOGIC (UNCHANGED)
    # ==================================================

    extra_contacts = False
    project_pm = ClientEmployees.objects.get(
        person_pk=job.client_Pm.person_pk
    )

    client_list = []

    if TempRecipientsCOPList.objects.filter(job=job, default=False).exists():
        if TempRecipientsCOPList.objects.filter(job=job, default=True).exists():
            TempRecipientsCOPList.objects.filter(job=job, default=True).delete()

    if not ClientJobRoles.objects.filter(
            role="Change Orders",
            job=job
    ):
        if not TempRecipientsCOPList.objects.filter(job=job):
            TempRecipientsCOPList.objects.create(
                person=project_pm,
                job=job,
                default=True
            )
    else:
        if not TempRecipientsCOPList.objects.filter(job=job):
            for role in ClientJobRoles.objects.filter(
                    role="Change Orders",
                    job=job
            ):
                TempRecipientsCOPList.objects.create(
                    person=role.employee,
                    job=job
                )

    for employee in ClientEmployees.objects.filter(id=job.client, is_active=True).order_by('name'):

        has_default = ClientJobRoles.objects.filter(
            role="Change Orders",
            job=job,
            employee=employee
        ).exists()

        is_temp = TempRecipientsCOPList.objects.filter(
            job=job,
            person=employee
        ).exists()

        if has_default and is_temp:
            client_list.append(
                {'person_pk': employee.person_pk, 'name': employee.name, 'default': True, 'current': True,
                 'email': employee.email})
        elif has_default:
            extra_contacts = True
            client_list.append(
                {'person_pk': employee.person_pk, 'name': employee.name, 'default': True, 'current': False,
                 'email': employee.email})
        elif is_temp:
            client_list.append(
                {'person_pk': employee.person_pk, 'name': employee.name, 'default': False, 'current': True,
                 'email': employee.email})
        else:
            extra_contacts = True
            client_list.append(
                {'person_pk': employee.person_pk, 'name': employee.name, 'default': False, 'current': False,
                 'email': employee.email})

    return render(
        request,
        "send_cop_report.html",
        {
            'client_list': client_list,
            'extra_contacts': extra_contacts,
            'job': job,
            'changeorders':changeorders,
        }
    )