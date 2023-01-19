from django.utils import timezone
from django.views import generic
from django.views.generic import ListView
from console.models import *
from django.contrib.auth.models import User, auth
from django.shortcuts import render, redirect
from json import dumps
import json
from django.core.serializers.json import DjangoJSONEncoder
from datetime import date
from django_tables2 import SingleTableView
from .tables import *
from console.models import InventoryNotes
from .filters import EquipmentNotesFilter, EquipmentFilter, EquipmentFilter2
import json
from django.core.serializers.json import DjangoJSONEncoder
# Create your views here.

def equipment_remove_from_outgoing_cart(request,id): #status = None, Outgoing, Incoming
    item = Inventory.objects.get(id=id)
    item.batch = None
    item.save()
    return redirect('equipment_batch_outgoing',status='Outgoing')

def equipment_remove_from_incoming_cart(request,id): #status = None, Outgoing, Incoming
    item = Inventory.objects.get(id=id)
    item.batch = None
    item.save()
    return redirect('equipment_batch_outgoing',status='Incoming')

def equipment_add_to_outgoing(request,id): #status = None, Outgoing, Incoming
    item = Inventory.objects.get(id=id)
    item.batch = "Outgoing"
    item.save()
    return redirect('equipment_batch_outgoing',status='Outgoing')

def equipment_add_to_incoming(request,id): #status = None, Outgoing, Incoming
    item = Inventory.objects.get(id=id)
    item.batch = "Incoming"
    item.save()
    return redirect('equipment_batch_outgoing',status='Incoming')

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
        inventory=Inventory.objects.latest('id')
        if 'is_labeled' in request.POST:
            inventory.is_labeled=True
            inventory.save()
        new_note = InventoryNotes(inventory_item=inventory, date=date.today(),
                                  user=request.user.first_name + " " + request.user.last_name,
                                  note="Purchased From " + vendor.company_name + ". " + inventory.notes,
                                  category="Misc")
        new_note.save()
        return redirect('equipment_page', id=inventory.id)
    return render(request, "equipment_new.html", {'vendors':vendors,'inventorytype':inventorytype,'inventoryitems1':inventoryitems1,'inventoryitems2':inventoryitems2,'inventoryitems3':inventoryitems3,'inventoryitems4':inventoryitems4})

def equipment_page(request, id):
    inventory = Inventory.objects.get(id=id)
    table = EquipmentNotesTable(InventoryNotes.objects.filter(inventory_item=inventory))
    vendors = Vendors.objects.all()
    if request.method == 'POST':
        print(request.POST)
        if 'select_category' in request.POST:
            table = EquipmentNotesTable(InventoryNotes.objects.filter(inventory_item=inventory, category=request.POST['select_category']))
        if 'returned' in request.POST:
            inventory.status = "Available"  # change field
            inventory.date_returned = date.today()
            inventory.job_number = None
            inventory.vendor = None
            inventory.save()  # this will update only
            new_note = InventoryNotes(inventory_item=inventory, date=date.today(), user=request.user.first_name + " " + request.user.last_name, note="Returned -" + request.POST['returned_notes'],
                                      category="Returned")
            new_note.save()

        if 'missing' in request.POST:
            print(request.POST['missing_notes'])
            inventory.status = "Missing"  # change field
            inventory.job_number = None
            inventory.vendor = None
            inventory.save()
            new_note = InventoryNotes(inventory_item=inventory, date=date.today(), user=request.user.first_name + " " + request.user.last_name, note="Missing -" + request.POST['missing_notes'],
                                      category="Missing")
            new_note.save()
        if 'select_job' in request.POST:
            print(request.POST['select_job'])
            inventory.job_number = Jobs.objects.get(job_number = request.POST['select_job'])
            inventory.vendor = None
            inventory.status= "Checked Out"
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
                print(request.POST['select_service'])
                inventory.service_vendor = Vendors.objects.get(id=request.POST['select_service'])
                print(inventory.service_vendor.company_name)
                inventory.job_number = None
                inventory.status = "Service"
                inventory.save()
                new_note = InventoryNotes(inventory_item=inventory, date=date.today(),
                                          user=request.user.first_name + " " + request.user.last_name,
                                          note="In Service -" + request.POST['service_notes'],
                                          category="Service",
                                          job_name= Vendors.objects.get(id=request.POST['select_service']).company_name)
                new_note.save()


    jobs = Jobs.objects.all()
    return render(request, "equipment_page.html", {'jobs': jobs,'inventories': inventory, "table": table, "vendors": vendors})

def equipment_home(request):
    inventories = Inventory.objects.all()
    return render(request, "equipment_home.html", {'inventories': inventories})
