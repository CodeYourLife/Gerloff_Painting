from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
import json
from django.core.serializers.json import DjangoJSONEncoder
from datetime import date
from .tables import *
from equipment.models import *
from jobs.models import Jobs
from .filters import EquipmentFilter, EquipmentFilter2
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

@login_required(login_url='/accounts/login')
def equipment_remove_from_outgoing_cart(request,id): #status = None, Outgoing, Incoming
    item = Inventory.objects.get(id=id)
    item.batch = None
    item.save()
    return redirect('equipment_batch_outgoing',status='Outgoing')

@login_required(login_url='/accounts/login')
def equipment_remove_from_incoming_cart(request,id): #status = None, Outgoing, Incoming
    item = Inventory.objects.get(id=id)
    item.batch = None
    item.save()
    return redirect('equipment_batch_outgoing',status='Incoming')

@login_required(login_url='/accounts/login')
def equipment_add_to_outgoing(request,id): #status = None, Outgoing, Incoming
    item = Inventory.objects.get(id=id)
    item.batch = "Outgoing"
    item.save()
    return redirect('equipment_batch_outgoing',status='Outgoing')

@login_required(login_url='/accounts/login')
def equipment_add_to_incoming(request,id): #status = None, Outgoing, Incoming
    item = Inventory.objects.get(id=id)
    item.batch = "Incoming"
    item.save()
    return redirect('equipment_batch_outgoing',status='Incoming')

@login_required(login_url='/accounts/login')
def equipment_batch_outgoing(request,status): #status is Outgoing, Incoming
    if request.method == 'POST':
        if status == "Outgoing":
            for x in Inventory.objects.filter(batch = 'Outgoing'):
                x.job_number = Jobs.objects.get(job_number= request.POST['select_job'])
                x.status = "Checked Out"
                x.batch = None
                x.save()
                new_note = InventoryNotes(inventory_item=x, date=date.today(),
                                          user=request.user.first_name + " " + request.user.last_name,
                                          note="Sent to Job -" + request.POST['inventory_notes'],
                                          category="Job", job_number = request.POST['select_job'], job_name = x.job_number.job_name)
                new_note.save()
            for x in Inventory.objects.filter(batch='Incoming'):
                x.batch=None
                x.save()
        else:
            for x in Inventory.objects.filter(batch = 'Incoming'):
                x.job_number = None
                x.status= "Available"
                x.batch = None
                x.save()
                new_note = InventoryNotes(inventory_item=x, date=date.today(),
                                          user=request.user.first_name + " " + request.user.last_name,
                                          note="Returned -" + request.POST['inventory_notes'],
                                          category="Returned")
                new_note.save()
            for x in Inventory.objects.filter(batch='Outgoing'):
                x.batch=None
                x.save()

        return redirect('warehouse_home')
    status=status
    jobs = Jobs.objects.filter(status="Open")
    available_filter = EquipmentFilter(request.GET, queryset = Inventory.objects.filter(status='Available',batch=None))
    if status == 'Outgoing':
        available_filter = EquipmentFilter(request.GET,queryset=Inventory.objects.filter(status='Available', batch=None))
        pending_table = EquipmentTableOutgoing(Inventory.objects.filter(batch = 'Outgoing'))
        available_table = EquipmentTableOutgoing(available_filter.qs)
    else:
        available_filter = EquipmentFilter2(request.GET,queryset=Inventory.objects.filter(status='Checked Out', batch=None))
        pending_table = EquipmentTableOutgoing(Inventory.objects.filter(batch='Incoming'))
        available_table = EquipmentTableIncoming(available_filter.qs)
    has_filter = any(field in request.GET for field in set(available_filter.get_fields()))
    return render(request, "equipment_batch_outgoing.html", {'status':status,'jobs':jobs,'available_filter':available_filter,'has_filter':has_filter,'pending_table':pending_table,'available_table':available_table})

@login_required(login_url='/accounts/login')
def equipment_new(request):
    inventorytype=InventoryType.objects.all()
    inventoryitems1 = json.dumps(list(InventoryItems.objects.values('id','type__id','name').all()), cls=DjangoJSONEncoder)
    inventoryitems2 = json.dumps(list(InventoryItems2.objects.values('id','type__id','name').all()), cls=DjangoJSONEncoder)
    inventoryitems3 = json.dumps(list(InventoryItems3.objects.values('id','type__id','name').all()), cls=DjangoJSONEncoder)
    inventoryitems4 = json.dumps(list(InventoryItems4.objects.values('id','type__id','name').all()), cls=DjangoJSONEncoder)
    vendors = Vendors.objects.filter(category__category='Equipment Supplier')
    if request.method == 'POST':
        if request.POST['purchased_from'] == 'new':
            vendor = Vendors.objects.create(company_name=request.POST['vendor_name'], category=VendorCategory.objects.get(category='Equipment Supplier'))
        else:
            vendor = Vendors.objects.get(id=request.POST['purchased_from'])
        inventory=Inventory.objects.create(item =request.POST['item'],inventory_type=InventoryType.objects.get(id=request.POST['inventory_type0']),purchase_date =request.POST['purchase_date'],purchased_from =vendor,status="Available",number=request.POST['number'],purchase_price=request.POST['purchase_price'],purchased_by=request.POST['purchased_by'],serial_number=request.POST['serial_number'],po_number=request.POST['po_number'],notes=request.POST['notes'])
        createfolder("equipment/" + str(inventory.id))
        if 'is_labeled' in request.POST:
            inventory.is_labeled=True
            inventory.save()
        new_note = InventoryNotes.objects.create(inventory_item=inventory, date=date.today(),
                                  user=request.user.first_name + " " + request.user.last_name,
                                  note="Purchased From " + vendor.company_name + ". " + inventory.notes,
                                  category="Misc")
        return redirect('equipment_page', id=inventory.id)
    return render(request, "equipment_new.html", {'vendors':vendors,'inventorytype':inventorytype,'inventoryitems1':inventoryitems1,'inventoryitems2':inventoryitems2,'inventoryitems3':inventoryitems3,'inventoryitems4':inventoryitems4})

@login_required(login_url='/accounts/login')
def get_directory_contents(request, id, value):
    file_path = os.path.join(settings.MEDIA_ROOT, "equipment", str(id), os.path.basename(value))
    if os.path.exists(file_path):
        name = value.split('.')[0]
        mimetype = value.split('.')[1]
        with open(file_path, 'rb') as fh:
            return HttpResponse(fh.read(), headers={'Content-Type': f'image/{mimetype}','Content-Disposition': f'attachment; filename="{name}.{mimetype}"'})

@login_required(login_url='/accounts/login')
def equipment_page(request, id):
    inventory = Inventory.objects.get(id=id)
    table = EquipmentNotesTable(InventoryNotes.objects.filter(inventory_item=inventory))
    employees = Employees.objects.filter(active=True)
    vendors = Vendors.objects.filter(category__category="Equipment Repair")
    path = os.path.join(settings.MEDIA_ROOT, "equipment", str(inventory.id))
    foldercontents =  os.listdir(path)
    if request.method == 'POST':
        if 'apply_filter' in request.POST:
            table = EquipmentNotesTable(InventoryNotes.objects.filter(inventory_item=inventory, category=request.POST['select_category']))
        if 'clear_filter' in request.POST:
            table = EquipmentNotesTable(InventoryNotes.objects.filter(inventory_item=inventory))
        if 'returned' in request.POST:
            if inventory.assigned_to != None:
                inventory.status = "Checked Out"
            else:
                inventory.status = "Available"  # change field
            inventory.date_returned = date.today()
            inventory.job_number = None
            inventory.service_vendor = None
            inventory.save()  # this will update only
            new_note = InventoryNotes(inventory_item=inventory, date=date.today(), user=request.user.first_name + " " + request.user.last_name, note="Returned -" + request.POST['returned_notes'],
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
                                          user=request.user.first_name + " " + request.user.last_name,
                                          note="No longer assigned to employee. " + inventory.assigned_to.first_name + " " + inventory.assigned_to.last_name + ". " +
                                               request.POST['returned_notes'],
                                          category="Employee")
            else:
                new_note = InventoryNotes(inventory_item=inventory, date=date.today(), user=request.user.first_name + " " + request.user.last_name, note="No longer assigned to employee. " + inventory.assigned_to.first_name + " " + inventory.assigned_to.last_name + ". " + request.POST['returned_notes'],
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
            new_note = InventoryNotes(inventory_item=inventory, date=date.today(), user=request.user.first_name + " " + request.user.last_name, note="Missing -" + request.POST['missing_notes'],
                                      category="Missing")
            new_note.save()
        if 'select_job' in request.POST:
            inventory.job_number = Jobs.objects.get(job_number = request.POST['select_job'])
            inventory.service_vendor = None
            inventory.status= "Checked Out"
            inventory.date_out = date.today()
            inventory.date_returned = None
            inventory.save()
            new_note = InventoryNotes(inventory_item=inventory, date=date.today(), user= request.user.first_name + " " + request.user.last_name, note="New Job -" + request.POST['job_notes'],
                                      category="Job", job_name = Jobs.objects.get(job_number = request.POST['select_job']).job_name, job_number = request.POST['select_job'] )
            new_note.save()
        if 'equipment_note' in request.POST:
            new_note = InventoryNotes(inventory_item=inventory, date=date.today(), user=request.user.first_name + " " + request.user.last_name,
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
                                          user=request.user.first_name + " " + request.user.last_name,
                                          note="In Service -" + request.POST['service_notes'],
                                          category="Service",
                                          job_name= Vendors.objects.get(id=request.POST['select_service']).company_name)
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
                                      user=request.user.first_name + " " + request.user.last_name,
                                      note="Assigned to Employee -" + inventory.assigned_to.first_name + " " + inventory.assigned_to.last_name + ". " + request.POST['job_notes'],
                                      category="Employee",)
            new_note.save()
        if 'upload_file' in request.FILES:
            fileitem = request.FILES['upload_file']
            fn = os.path.basename(fileitem.name)
            print(settings.MEDIA_ROOT)
            fn2 = os.path.join(settings.MEDIA_ROOT, "equipment", str(inventory.id), fn)
            open(fn2, 'wb').write(fileitem.file.read())

    jobs = Jobs.objects.all()
    return render(request, "equipment_page.html", {'employees':employees,'jobs': jobs,'inventories': inventory, "table": table, "vendors": vendors, "foldercontents":foldercontents})

@login_required(login_url='/accounts/login')
def equipment_home(request):
    inventories = Inventory.objects.all()
    return render(request, "equipment_home.html", {'inventories': inventories})



        


