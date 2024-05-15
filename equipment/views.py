from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
import json
from django.core.serializers.json import DjangoJSONEncoder
from datetime import date
from equipment.tables import *
from equipment.models import *
from jobs.models import Jobs, JobNotes, Email_Errors
from equipment.filters import EquipmentFilter, EquipmentFilter2, EquipmentFilter3
import json
from django.core.serializers.json import DjangoJSONEncoder
from console.misc import createfolder
from django.core.files.storage import FileSystemStorage
import os
import os.path
import csv
from pathlib import Path
from django.conf import settings
from django.http import HttpResponse
from media.utilities import MediaUtilities
from console.misc import Email
from datetime import datetime
from employees.models import *


def complete_pickup(request, pickup):
    send_data = {}
    selected_request = PickupRequest.objects.get(id=pickup)
    if selected_request.completed_notes is None:
        selected_request.completed_notes=" "
    selected_request.save()
    selected_job = selected_request.job_number
    if request.method == 'POST':
        for x in request.POST:
            if x == 'trash_done':
                selected_request.trash_removed = True
                selected_request.completed_notes += " Trash Picked Up \n"
                selected_request.save()
            if x == 'paint_saved':
                selected_request.leftover_paint_saved = True
                selected_request.completed_notes += " Leftover Paint Saved \n"
                selected_request.save()
            if x == 'trash_not_done':
                selected_request.trash_removed = True
                selected_request.completed_notes += "Trash pickup not done. " + str(request.POST['trash_problem_note']) + "\n"
                selected_request.save()
            if x == 'paint_not_saved':
                selected_request.leftover_paint_saved = True
                selected_request.completed_notes += "Leftover Paint Not Saved. " + str(
                    request.POST['paint_saved_note']) + "\n"
                selected_request.save()
            if x[0:8] == 'check_in':
                if selected_request.all_items == True:
                    item = Inventory.objects.get(id=x[8:len(x)])
                    item.job_number = None
                    item.status = "Available"
                    item.batch = None
                    item.save()
                else:
                    item = PickupRequestItems.objects.get(id=x[8:len(x)])
                    item.returned = True
                    item.save()
                    item = item.item
                    item.job_number = None
                    item.status = "Available"
                    item.batch = None
                    item.save()
                selected_request.completed_notes = selected_request.completed_notes + " " + str(
                    item.item) + "- Returned. \n"
                selected_request.save()
                InventoryNotes.objects.create(inventory_item=item, date=date.today(),
                                              user=Employees.objects.get(user=request.user),
                                              note="Returned - requested for pickup by " + str(
                                                  selected_request.requested_by),
                                              category="Returned")
            if x[0:7] == 'missing':
                if selected_request.all_items == True:
                    item = Inventory.objects.get(id=x[7:len(x)])
                else:
                    item = PickupRequestItems.objects.get(id=x[7:len(x)])
                    item.returned = True
                    item.save()
                    item = item.item
                if request.POST['status'] == '1': #missing
                    item.status = "Missing"  # change field
                    item.job_number = None
                    item.service_vendor = None
                    item.assigned_to = None
                    item.save()
                    selected_request.completed_notes = selected_request.completed_notes + "MISSING- " + item.item + " is missing. " + request.POST['notes'] + "\n"
                    selected_request.save()
                    InventoryNotes.objects.create(inventory_item=item, date=date.today(),
                                                  user=Employees.objects.get(user=request.user),
                                                  note="This item was requested to be picked up by: " + str(
                                                      selected_request.requested_by) + ". It is not on the jobsite. " +
                                                       request.POST['notes'],
                                                  category="Missing")
                elif request.POST['status'] == '2':    #still on job
                    print("PUMPKIN2")
                    if selected_request.all_items == True:
                        PickupRequestItems.objects.create(request=selected_request, item=item)
                    selected_request.completed_notes = selected_request.completed_notes + " Didn't pickup " + item.item + " we left it on the job. " + request.POST['notes'] + "\n"
                    selected_request.save()
                    InventoryNotes.objects.create(inventory_item=item, date=date.today(),
                                                  user=Employees.objects.get(user=request.user),
                                                  note="This item was requested to be picked up by: " + str(
                                                      selected_request.requested_by) + ". We left it on the job. " +
                                                       request.POST['notes'],
                                                  category="Misc")
                elif request.POST['status'] == '3':  # different job
                    selected_request.completed_notes = selected_request.completed_notes + " Didn't pickup " + item.item + " it is already on a different job, " + request.POST['current_location'] + ". " + request.POST['notes'] + "\n"
                    selected_request.save()
                    InventoryNotes.objects.create(inventory_item=item, date=date.today(),
                                                  user=Employees.objects.get(user=request.user),
                                                  note="This item was requested to be picked up by: " + str(
                                                      selected_request.requested_by) + ". It was already on a different job, " + request.POST['current_location'] + ". " +
                                                       request.POST['notes'],
                                                  category="Misc")
            if x == 'send_now':
                selected_request.completed_notes = selected_request.completed_notes + " " + request.POST['request_notes']
                selected_request.completed_date = date.today()
                selected_request.is_closed = True
                selected_request.save()
                PickupRequestItems.objects.filter(request=selected_request).delete()
                JobNotes.objects.create(job_number=selected_job,
                                        note="Job Pickup Completed! " + selected_request.completed_notes,
                                        type="auto_misc_note", date=date.today(),
                                        user=Employees.objects.get(user=request.user))
                message = "Jobsite Pickup Completed. \n Job: " + str(selected_request.job_number) + "\n\n" + selected_request.completed_notes
                recipients = ["warehouse@gerloffpainting.com", "joe@gerloffpainting.com"]
                if selected_job.superintendent:
                    if selected_job.superintendent.email:
                        recipients.append(selected_job.superintendent.email)
                    if selected_request.requested_by != selected_job.superintendent:
                        if selected_request.requested_by.email is not None:
                            recipients.append(selected_request.requested_by.email)
                else:
                    if selected_request.requested_by.email is not None:
                        recipients.append(selected_request.requested_by.email)
                Email_Errors.objects.filter(user=request.user.first_name + " " + request.user.last_name).delete()
                try:
                    Email.sendEmail("Pickup Complete! " + selected_job.job_name, message,
                                    recipients, False)
                    message = "Your email about the pickup being complete was sent succesfully"
                except:
                    message = "Error! Your email about the pickup being complete failed to send. Please call them and let them know it was completed."
                Email_Errors.objects.create(user=request.user.first_name + " " + request.user.last_name, error=message,
                                            date=date.today())
                return redirect('warehouse_home')
    items_not_ready = False
    if selected_request.all_items == True:
        selected_items = Inventory.objects.filter(pickuprequested__isnull=True, job_number=selected_request.job_number,is_closed=False)
        if selected_items.exists(): items_not_ready=True
    else:
        selected_items = PickupRequestItems.objects.filter(request=selected_request, returned=False)
        if selected_items.exists(): items_not_ready=True
    send_data['selected_request'] = selected_request
    send_data['selected_items'] = selected_items
    if selected_request.remove_trash:
        if not selected_request.trash_removed:
            items_not_ready=True
            send_data['remove_trash'] = True
    if selected_request.save_leftover_paint:
        if not selected_request.leftover_paint_saved:
            items_not_ready=True
            send_data['save_paint'] = True
    if items_not_ready:
        send_data['items_not_ready'] = True
    return render(request, 'complete_pickup.html', send_data)

def request_trash_pickup(request, jobnumber):
    send_data={}
    selected_job = Jobs.objects.get(job_number=jobnumber)
    send_data['selected_job']=selected_job
    if PickupRequest.objects.filter(job_number=selected_job, confirmed=False, is_closed=False).exists():
        return redirect('request_pickup',jobnumber=jobnumber,item='ALL',pickup='ALL',status='ALL')
    if PickupRequest.objects.filter(job_number=selected_job, confirmed=True, is_closed=False).exists():
        send_data['pickup_exists']=True
    if request.method == 'POST':
        if 'add_trash_request' in request.POST:
            if PickupRequest.objects.filter(job_number=selected_job, confirmed=True, is_closed=False).exists():
                message = "Request for job: " + str(selected_job.job_name)
                message += " In addition to the requested equipment, please also pickup the trash!"
                if 'save_paint' in request.POST:
                    message += " Please save the leftover paint in our warehouse, until I can review it"
                JobNotes.objects.create(job_number=selected_job,
                                        note=message,
                                        type="auto_misc_note", user=Employees.objects.get(user=request.user),
                                        date=date.today())
                Email_Errors.objects.filter(user=request.user.first_name + " " + request.user.last_name).delete()
                recipients = ["warehouse@gerloffpainting.com"]
                current_user = Employees.objects.get(user=request.user)
                if current_user.email: recipients.append(current_user.email)
                try:
                    Email.sendEmail("Trash Pickup", message, recipients, False)
                    message2 = "Trash Pickup Request was succesfully emailed"
                except:
                    message2 = "Error! Trash Pickup Request failed to email. Please retry later!"
                Email_Errors.objects.create(user=request.user.first_name + " " + request.user.last_name,
                                            error=message2, date=date.today())
                selected_request = PickupRequest.objects.get(job_number=selected_job, confirmed=True, is_closed=False)
                selected_request.remove_trash = True
                selected_request.request_notes = selected_request.request_notes + " Trash Pickup Request Added. " + request.POST['notes']
                if 'save_paint' in request.POST:
                    selected_request.save_leftover_paint=True
                selected_request.save()
                return redirect('job_page', jobnumber=jobnumber)
            else:
                #no existing request
                send_data['new_request'] = True

                send_data['notes'] = request.POST['notes']

                if 'save_paint' in request.POST: send_data['save_paint'] = True
        if 'cancel' in request.POST:
            return redirect('job_page', jobnumber=jobnumber)
        if 'pickup_all_equipment' in request.POST or 'pickup_certain_equipment' in request.POST or 'no_equipment' in request.POST:
            message = "Request for job: " + str(selected_job.job_name) + ". \n"

            new_request= PickupRequest.objects.create(date=date.today(), job_number=selected_job, confirmed=False, request_notes="Trash Pickup Requested- " + str(request.POST['notes'])) + ". \n"

            new_request.remove_trash = True
            if 'save_paint' in request.POST: new_request.save_leftover_paint = True
            if 'pickup_all_equipment' in request.POST:
                new_request.all_items = True

            message += " Please pickup the trash! " + request.POST['notes'] + ". "

            if 'save_paint' in request.POST:
                message += " Please save the leftover paint in our warehouse, until I can review it."
            if 'pickup_all_equipment' in request.POST:
                message += " Please also pickup all the equipment from the jobsite. "
            new_request.save()
            if 'pickup_all_equipment' in request.POST or 'no_equipment' in request.POST:
                new_request.confirmed = True
                new_request.save()
                JobNotes.objects.create(job_number=selected_job,
                                        note=message,
                                        type="auto_misc_note", user=Employees.objects.get(user=request.user),
                                        date=date.today())
                Email_Errors.objects.filter(user=request.user.first_name + " " + request.user.last_name).delete()
                recipients = ["warehouse@gerloffpainting.com"]
                current_user = Employees.objects.get(user=request.user)
                if current_user.email: recipients.append(current_user.email)
                try:
                    Email.sendEmail("Trash Pickup", message, recipients, False)
                    message2 = "Trash Pickup Request was succesfully emailed"
                except:
                    message2 = "Error! Trash Pickup Request failed to email. Please retry later!"
                Email_Errors.objects.create(user=request.user.first_name + " " + request.user.last_name,
                                        error=message2, date=date.today())
                return redirect('job_page', jobnumber=jobnumber)
            return redirect('request_pickup',jobnumber=jobnumber,item='ALL',pickup='ALL',status='ALL')
    return render(request, 'request_trash_pickup.html', send_data)

def request_pickup(request, jobnumber, item, pickup, status):
    # item either ALL or ID
    # Pickup either 'ADD' or ID or 'ALL' or 'CHANGE' or 'ITEMADD' or 'ITEMREMOVE'
    # status either 'ALL' or 'CHANGE' or 'ADD' or 'REVISE'
    selected_job = Jobs.objects.get(job_number=jobnumber)
    send_data = {}

    if status == 'REVISE':
        if 'revise' in request.POST:
            selected_request = PickupRequest.objects.get(id=pickup)
            selected_request.confirmed = False
            selected_request.request_notes = selected_request.request_notes + "\n Revised! \n"
            selected_request.save()
        else:
            return redirect("equipment_home")
    if PickupRequest.objects.filter(job_number=selected_job, confirmed=True, is_closed=False, all_items=True).exists():
        status = "CHECK"
        selected_request = PickupRequest.objects.get(job_number=selected_job, confirmed=True, is_closed=False, all_items=True)
        if selected_request.remove_trash:
            send_data['remove_trash'] = True
            if selected_request.save_leftover_paint:
                send_data['save_paint'] = True
        send_data['existing_request_all'] = selected_request
    elif PickupRequest.objects.filter(job_number=selected_job, confirmed=True, is_closed=False).exists():
        status = "CHECK"
        selected_request = PickupRequest.objects.get(job_number=selected_job, confirmed=True, is_closed=False)
        if selected_request.remove_trash:
            send_data['remove_trash'] = True
            if selected_request.save_leftover_paint:
                send_data['save_paint'] = True
        send_data['existing_request'] = selected_request
        send_data['existing_request_items'] = PickupRequestItems.objects.filter(request=selected_request)

    if pickup == 'ALL':
        PickupRequestItems.objects.filter(request__confirmed=False).exclude(request__date=date.today()).delete()
        PickupRequest.objects.filter(confirmed=False).exclude(date=date.today()).delete()
        if PickupRequest.objects.filter(job_number=selected_job, confirmed=False):
            pickup = PickupRequest.objects.get(job_number=selected_job, confirmed=False).id
            selected_request = PickupRequest.objects.get(job_number=selected_job, confirmed=False)
            if selected_request.remove_trash:
                send_data['remove_trash'] = True
                if selected_request.save_leftover_paint:
                    send_data['save_paint'] = True
    if pickup == 'ALL' and status == 'ALL' and item != 'ALL':
        selected_request = PickupRequest.objects.create(date=date.today(), job_number=selected_job, confirmed=False,request_notes=" ")
        pickup = selected_request.id
        PickupRequestItems.objects.create(request=selected_request, item=Inventory.objects.get(id=item))
    if item != 'ALL':
        if status == 'ITEMREMOVE':
            selected_item = PickupRequestItems.objects.get(id=item).item
        else:
            selected_item = Inventory.objects.get(id=item)
        send_data['selected_item'] = selected_item
    send_data['all_items'] = Inventory.objects.filter(job_number=jobnumber,is_closed=False)
    if pickup != 'ALL':
        selected_request = PickupRequest.objects.get(id=pickup)
        send_data['selected_request'] = selected_request
        if selected_request.remove_trash:
            send_data['remove_trash'] = True
            if selected_request.save_leftover_paint:
                send_data['save_paint'] = True
    if status == 'ITEMADD': PickupRequestItems.objects.create(request=selected_request, item=selected_item)
    if status == 'ITEMREMOVE': PickupRequestItems.objects.get(id=item).delete()
    if request.method == 'POST':
        if status == 'ADD':
            selected_request = PickupRequest.objects.create(date=date.today(), job_number=selected_job, confirmed=False,request_notes=" ")
            send_data['selected_request'] = selected_request
            if 'all_items' in request.POST:
                selected_request.all_items = True
            elif item != 'ALL':
                PickupRequestItems.objects.create(request=selected_request, item=selected_item)
        if 'change_to_all_items' in request.POST:
            selected_request.all_items = True
            selected_request.save()
            for x in PickupRequestItems.objects.filter(request=selected_request):
                x.delete()
        if 'change_to_certain_items' in request.POST:
            selected_request.all_items = False
            selected_request.save()
        selected_request.remove_trash = False
        selected_request.save_leftover_paint = False
        if 'remove_trash' in request.POST:
            selected_request.remove_trash = True
            send_data['remove_trash']=True
        if 'save_paint' in request.POST:
            selected_request.save_leftover_paint = True
            send_data['save_paint'] =True
        selected_request.save()
        if 'send_now' in request.POST:
            selected_request.confirmed = True
            selected_request.requested_by = Employees.objects.get(user=request.user)
            message = "Pickup Request For Job: " + selected_job.job_name + ".\n"
            selected_request.remove_trash = False
            selected_request.save_leftover_paint = False
            if 'remove_trash' in request.POST:
                selected_request.remove_trash = True
                message += " Remove all trash."
            if 'save_paint' in request.POST:
                selected_request.save_leftover_paint = True
                message += " Save leftover paint in our warehouse until i can review. "
            selected_request.save()
            if selected_request.all_items == True:
                if selected_request.request_notes is None:
                    selected_request.request_notes = ""
                    selected_request.save()
                selected_request.request_notes = selected_request.request_notes + " Pickup All Items. " + request.POST[
                    'request_notes']
                selected_request.save()
                message = message + ". Please pickup all items. \n"
            else:
                tempnote = ". Please pickup the following items: \n"
                message = message + ". Please pickup the following items: \n\n"
                for x in PickupRequestItems.objects.filter(request=selected_request):
                    InventoryNotes.objects.create(inventory_item=x.item, date=date.today(),
                                                  user=Employees.objects.get(user=request.user),
                                                  note="Requested for pickup by " + str(
                                                      selected_request.requested_by),
                                                  category="Misc",job_number=selected_job.job_number,job_name=selected_job.job_name)
                    if x.item.number:
                        tempnote = tempnote + "#:" + x.item.number + "- " + x.item.item + ". \n"
                        message = message + "#:" + x.item.number + "- " + x.item.item + ". \n"
                    else:
                        tempnote = tempnote + "#:N/A- " + x.item.item + ". \n"
                        message = message + "#:N/A- " + x.item.item + ". \n"
                selected_request.request_notes = selected_request.request_notes + tempnote + "\n" + request.POST[
                    'request_notes'] + ". "
                selected_request.save()
            message = message + "\n Requested by: " + str(selected_request.requested_by) + "\n\n" + request.POST[
                'request_notes'] + ". "
            recipients = ["warehouse@gerloffpainting.com", "joe@gerloffpainting.com"]
            if selected_job.superintendent:
                if selected_job.superintendent.email:
                    recipients.append(selected_job.superintendent.email)
                if selected_request.requested_by != selected_job.superintendent:
                    if selected_request.requested_by.email is not None:
                        recipients.append(selected_request.requested_by.email)
            Email_Errors.objects.filter(user=request.user.first_name + " " + request.user.last_name).delete()
            try:
                Email.sendEmail("Pickup Request! " + selected_job.job_name, message,
                                recipients, False)

                message2 = "Your email requesting a pickup was sent succesfully!"
            except:
                message2 = "ERROR! Your pickup request was not sent. Please call the warehouse."
            Email_Errors.objects.create(user=request.user.first_name + " " + request.user.last_name, error=message2,

                                        date=date.today())
            JobNotes.objects.create(job_number=selected_job,
                                    note=message,
                                    type="auto_misc_note", user=Employees.objects.get(user=request.user), date=date.today())
            if selected_job: return redirect('job_page', jobnumber=selected_job.job_number)
            else: return redirect('warehouse_home')


    if pickup != 'ALL': send_data['selected_items'] = PickupRequestItems.objects.filter(request=selected_request)
    send_data['equipment'] = Inventory.objects.filter(job_number=selected_job,is_closed=False)
    send_data['selected_job'] = selected_job
    send_data['available_items'] = Inventory.objects.filter(job_number=selected_job, pickuprequested__isnull=True,is_closed=False)
    return render(request, 'request_pickup.html', send_data)



def update_equipment(request, id):
    item = Inventory.objects.get(id=id)
    if request.method == 'POST':
        if 'is_labeled' in request.POST:
            item.is_labeled = True
        else:
            item.is_labeled = False
        if 'needs_label' in request.POST:
            item.needs_label = True
        else:
            item.needs_label = False
        if request.POST['select_vendor'] == 'add_new':
            item.purchased_from = Vendors.objects.create(company_name=request.POST['new_vendor'],
                                                         category=VendorCategory.objects.get(
                                                             category='Equipment Supplier'))
        elif request.POST['select_vendor'] != 'please_select':
            item.purchased_from = Vendors.objects.get(id=request.POST['select_vendor'])
        item.number = request.POST['number']
        item.purchase_date = request.POST['purchase_date']
        item.purchase_price = request.POST['purchase_price']
        item.purchased_by = request.POST['purchased_by']
        item.serial_number = request.POST['serial_number']
        item.po_number = request.POST['po_number']
        item.item = request.POST['item']
        item.notes = request.POST['notes']
        item.inventory_type = InventoryType.objects.get(id=request.POST['inventory_type0'])
        item.save()
        return redirect('equipment_page', id=id)
    send_data = {}
    send_data['item'] = item
    send_data['inventorytypes'] = InventoryType.objects.all()
    send_data['vendors'] = Vendors.objects.filter(category__category='Equipment Supplier')
    send_data['format_date'] = item.purchase_date.strftime("%Y-%m-%d")
    return render(request, "equipment_update.html", send_data)


@login_required(login_url='/accounts/login')
def equipment_remove_from_outgoing_cart(request, id):  # status = None, Outgoing, Incoming
    item = Inventory.objects.get(id=id)
    item.batch = None
    item.save()
    return redirect('equipment_batch_outgoing', status='Outgoing')


@login_required(login_url='/accounts/login')
def equipment_remove_from_incoming_cart(request, id):  # status = None, Outgoing, Incoming
    item = Inventory.objects.get(id=id)
    item.batch = None
    item.save()
    return redirect('equipment_batch_outgoing', status='Incoming')


@login_required(login_url='/accounts/login')
def equipment_add_to_outgoing(request, id):  # status = None, Outgoing, Incoming
    item = Inventory.objects.get(id=id)
    item.batch = "Outgoing"
    item.save()
    return redirect('equipment_batch_outgoing', status='Outgoing')


@login_required(login_url='/accounts/login')
def equipment_add_to_incoming(request, id):  # status = None, Outgoing, Incoming
    item = Inventory.objects.get(id=id)
    item.batch = "Incoming"
    item.save()
    return redirect('equipment_batch_outgoing', status='Incoming')


@login_required(login_url='/accounts/login')
def equipment_batch_outgoing(request, status):  # status is Outgoing, Incoming
    jobs = Jobs.objects.filter(is_closed=False)
    if request.method == 'POST':
        if 'filter_job_name' in request.POST:
            jobs = Jobs.objects.filter(is_closed=False, job_name__icontains=request.POST['filter_job_name'])
        else:
            if status == "Outgoing":
                for x in Inventory.objects.filter(batch='Outgoing',is_closed=False):
                    x.job_number = Jobs.objects.get(job_number=request.POST['select_job'])
                    x.status = "Checked Out"
                    x.batch = None
                    x.save()
                    new_note = InventoryNotes.objects.create(inventory_item=x, date=date.today(),
                                                             user=Employees.objects.get(user=request.user),
                                                             note="Sent to Job -" + request.POST['inventory_notes'],
                                                             category="Job", job_number=request.POST['select_job'],
                                                             job_name=x.job_number.job_name)
                    new_note.save()
                for x in Inventory.objects.filter(batch='Incoming',is_closed=False):
                    x.batch = None
                    x.save()
            else:
                for x in Inventory.objects.filter(batch='Incoming',is_closed=False):
                    x.job_number = None
                    x.status = "Available"
                    x.batch = None
                    x.save()
                    new_note = InventoryNotes.objects.create(inventory_item=x, date=date.today(),
                                                             user=Employees.objects.get(user=request.user),
                                                             note="Returned -" + request.POST['inventory_notes'],
                                                             category="Returned")
                    new_note.save()
                for x in Inventory.objects.filter(batch='Outgoing',is_closed=False):
                    x.batch = None
                    x.save()
            return redirect('warehouse_home')
    status = status
    available_filter = EquipmentFilter(request.GET, queryset=Inventory.objects.filter(status='Available', batch=None,is_closed=False))
    if status == 'Outgoing':
        available_filter = EquipmentFilter(request.GET,
                                           queryset=Inventory.objects.filter(status='Available', batch=None,is_closed=False))
        pending_table = EquipmentTableOutgoing(Inventory.objects.filter(batch='Outgoing',is_closed=False))
        available_table = EquipmentTableOutgoing(available_filter.qs)
    else:
        available_filter = EquipmentFilter2(request.GET,
                                            queryset=Inventory.objects.filter(status='Checked Out', batch=None,is_closed=False))
        pending_table = EquipmentTableOutgoing(Inventory.objects.filter(batch='Incoming',is_closed=False))
        available_table = EquipmentTableIncoming(available_filter.qs)
    has_filter = any(field in request.GET for field in set(available_filter.get_fields()))
    send_data = {}
    send_data['status'] = status
    send_data['jobs'] = jobs
    send_data['available_filter'] = available_filter
    send_data['has_filter'] = has_filter
    send_data['pending_table'] = pending_table
    send_data['available_table'] = available_table
    return render(request, "equipment_batch_outgoing.html", send_data)


@login_required(login_url='/accounts/login')
def equipment_new(request):
    inventorytype = InventoryType.objects.all()
    inventoryitems1 = json.dumps(list(InventoryItems.objects.values('id', 'type__id', 'name').all()),
                                 cls=DjangoJSONEncoder)
    inventoryitems2 = json.dumps(list(InventoryItems2.objects.values('id', 'type__id', 'name').all()),
                                 cls=DjangoJSONEncoder)
    inventoryitems3 = json.dumps(list(InventoryItems3.objects.values('id', 'type__id', 'name').all()),
                                 cls=DjangoJSONEncoder)
    inventoryitems4 = json.dumps(list(InventoryItems4.objects.values('id', 'type__id', 'name').all()),
                                 cls=DjangoJSONEncoder)
    vendors = Vendors.objects.filter(category__category='Equipment Supplier')
    if request.method == 'POST':
        inventory = Inventory.objects.create(item=request.POST['item'], inventory_type=InventoryType.objects.get(
            id=request.POST['inventory_type0']), purchase_date=request.POST['purchase_date'],
                                             status="Available", number=request.POST['number'],
                                             purchase_price=request.POST['purchase_price'],
                                             purchased_by=request.POST['purchased_by'],
                                             serial_number=request.POST['serial_number'],
                                             po_number=request.POST['po_number'], notes=request.POST['notes'])
        if request.POST['select_vendor'] == 'add_new':
            inventory.purchased_from = Vendors.objects.create(company_name=request.POST['new_vendor'],
                                                              category=VendorCategory.objects.get(
                                                                  category='Equipment Supplier'))
            vendor = inventory.purchased_from.company_name
        elif request.POST['select_vendor'] != 'please_select':
            inventory.purchased_from = Vendors.objects.get(id=request.POST['select_vendor'])
            vendor = inventory.purchased_from.company_name
        else:
            vendor = "?"
        createfolder("equipment/" + str(inventory.id))
        if 'is_labeled' in request.POST:
            inventory.is_labeled = True
        inventory.save()
        InventoryNotes.objects.create(inventory_item=inventory, date=date.today(),
                                      user=Employees.objects.get(user=request.user),
                                      note="Purchased From " + vendor + ". " + inventory.notes,
                                      category="Misc")
        return redirect('equipment_page', id=inventory.id)
    return render(request, "equipment_new.html",
                  {'vendors': vendors, 'inventorytype': inventorytype, 'inventoryitems1': inventoryitems1,
                   'inventoryitems2': inventoryitems2, 'inventoryitems3': inventoryitems3,
                   'inventoryitems4': inventoryitems4})


@login_required(login_url='/accounts/login')
def get_directory_contents(request, id, value, app):
    print(value)
    return MediaUtilities().getDirectoryContents(id, value, app)


@login_required(login_url='/accounts/login')
def equipment_page(request, id):
    inventory = Inventory.objects.get(id=id)
    table = InventoryNotes.objects.filter(inventory_item=inventory).order_by('date')
    employees = Employees.objects.filter(active=True)
    vendors = Vendors.objects.filter(category__category="Equipment Repair")
    path = os.path.join(settings.MEDIA_ROOT, "equipment", str(inventory.id))
    foldercontents = os.listdir(path)
    folder_count=0
    for x in os.listdir(path):
        if os.path.isfile(os.path.join(path, x)):
            folder_count += 1
    jobs = Jobs.objects.filter(is_closed=False).order_by('job_name')
    if request.method == 'POST':
        if 'selected_file' in request.POST:
            print(request.POST['selected_file'])
            return MediaUtilities().getDirectoryContents(id, request.POST['selected_file'], 'equipment')
        if 'search_job' in request.POST:
            jobs = Jobs.objects.filter(is_closed=False, job_name__icontains=request.POST['search_job']).order_by(
                'job_name')
        if 'apply_filter' in request.POST:
            table = InventoryNotes.objects.filter(inventory_item=inventory, category=request.POST['select_category']).order_by('date')
        if 'clear_filter' in request.POST:
            table = InventoryNotes.objects.filter(inventory_item=inventory).order_by('date')
        if 'returned' in request.POST:
            if inventory.assigned_to != None:
                inventory.status = "Checked Out"
            else:
                inventory.status = "Available"  # change field
            inventory.date_returned = date.today()
            inventory.job_number = None
            inventory.service_vendor = None
            inventory.save()  # this will update only
            new_note = InventoryNotes(inventory_item=inventory, date=date.today(),
                                      user=Employees.objects.get(user=request.user),
                                      note="Returned -" + request.POST['returned_notes'],
                                      category="Returned")
            new_note.save()
        if 'returned_employee' in request.POST:
            if inventory.job_number != None:
                inventory.status = "Checked Out"
            elif inventory.service_vendor != None:
                inventory.status = "Service"
            else:
                inventory.status = "Available"  # change field
                inventory.date_returned = date.today()
            if inventory.job_number != None or inventory.service_vendor != None:
                new_note = InventoryNotes(inventory_item=inventory, date=date.today(),
                                          user=Employees.objects.get(user=request.user),
                                          note="No longer assigned to employee. " + inventory.assigned_to.first_name + " " + inventory.assigned_to.last_name + ". " +
                                               request.POST['returned_notes'],
                                          category="Employee")
            else:
                new_note = InventoryNotes(inventory_item=inventory, date=date.today(),
                                          user=Employees.objects.get(user=request.user),
                                          note="No longer assigned to employee. " + inventory.assigned_to.first_name + " " + inventory.assigned_to.last_name + ". " +
                                               request.POST['returned_notes'],
                                          category="Returned")
            new_note.save()
            inventory.assigned_to = None
            inventory.save()  # this will update only

        if 'missing' in request.POST:
            inventory.status = "Missing"  # change field
            inventory.job_number = None
            inventory.service_vendor = None
            inventory.assigned_to = None
            inventory.save()
            new_note = InventoryNotes(inventory_item=inventory, date=date.today(),
                                      user=Employees.objects.get(user=request.user),
                                      note="Missing -" + request.POST['missing_notes'],
                                      category="Missing")
            new_note.save()
        if 'select_job' in request.POST:
            inventory.job_number = Jobs.objects.get(job_number=request.POST['select_job'])
            inventory.service_vendor = None
            inventory.status = "Checked Out"
            inventory.date_out = date.today()
            inventory.date_returned = None
            inventory.save()
            new_note = InventoryNotes(inventory_item=inventory, date=date.today(),
                                      user=Employees.objects.get(user=request.user),
                                      note="New Job -" + request.POST['job_notes'],
                                      category="Job",
                                      job_name=Jobs.objects.get(job_number=request.POST['select_job']).job_name,
                                      job_number=request.POST['select_job'])
            new_note.save()
        if 'equipment_note' in request.POST:
            new_note = InventoryNotes(inventory_item=inventory, date=date.today(),
                                      user=Employees.objects.get(user=request.user),
                                      note=request.POST['equipment_note'],
                                      category="Misc")
            new_note.save()

        if 'select_service' in request.POST:
            inventory.service_vendor = Vendors.objects.get(id=request.POST['select_service'])
            inventory.job_number = None
            inventory.status = "Service"
            inventory.date_out = date.today()
            inventory.date_returned = None
            inventory.save()
            new_note = InventoryNotes(inventory_item=inventory, date=date.today(),
                                      user=Employees.objects.get(user=request.user),
                                      note="In Service -" + request.POST['service_notes'],
                                      category="Service",
                                      job_name=Vendors.objects.get(id=request.POST['select_service']).company_name)
            new_note.save()

        if 'select_employee' in request.POST:
            inventory.assigned_to = Employees.objects.get(id=request.POST['select_employee'])
            if inventory.status != "Service":
                inventory.status = "Checked Out"
            if inventory.job_number == None and inventory.service_vendor == None:
                inventory.date_out = date.today()
                inventory.date_returned = None
            inventory.save()
            new_note = InventoryNotes(inventory_item=inventory, date=date.today(),
                                      user=Employees.objects.get(user=request.user),
                                      note="Assigned to Employee -" + inventory.assigned_to.first_name + " " + inventory.assigned_to.last_name + ". " +
                                           request.POST['job_notes'],
                                      category="Employee", )
            new_note.save()
        if 'upload_file' in request.FILES:
            fileitem = request.FILES['upload_file']
            custom_name = request.POST['file_name']
            short_year = date.today().strftime("%y")
            short_mth = date.today().strftime("%m")
            short_day = date.today().strftime("%d")
            short_date = short_year + "-" + short_mth + "-" + short_day
            extension = fileitem.name.split(".")[1]
            fn = os.path.basename(short_date + " " + custom_name + "." + extension)
            fn2 = os.path.join(settings.MEDIA_ROOT, "equipment", str(inventory.id), fn)
            open(fn2, 'wb').write(fileitem.file.read())
            foldercontents = os.listdir(path)
            folder_count = 0
            for x in os.listdir(path):
                if os.path.isfile(os.path.join(path, x)):
                    folder_count += 1
    return render(request, "equipment_page.html",
                  {'employees': employees, 'jobs': jobs, 'inventories': inventory, "table": table, "vendors": vendors,
                   "foldercontents": foldercontents,'folder_count':folder_count})


@login_required(login_url='/accounts/login')
def equipment_home(request):
    send_data={}
    if request.method == 'GET':
        if 'available_filter' in request.GET: send_data['available_filter'] = True
        if 'checked_out_filter' in request.GET: send_data['checked_out_filter'] = True
        if 'missing_filter' in request.GET: send_data['missing_filter'] = True
        if 'ladders_filter' in request.GET: send_data['ladders_filter'] = True
        if 'equipment_filter' in request.GET: send_data['equipment_filter'] = True
        if 'other_filter' in request.GET: send_data['other_filter'] = True
    search_equipment = EquipmentFilter3(request.GET, queryset=Inventory.objects.filter(is_closed=False))
    send_data['search_equipment'] = search_equipment
    send_data['inventories'] = search_equipment.qs
    # for inventory in inventories:
    #     inventory.item = inventory.item.strip()
    #     if inventory.service_vendor is not None:
    #         inventory.service_vendor.company_name = inventory.service_vendor.company_name.strip()
    return render(request, "equipment_home.html", send_data)
