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
# Create your views here.

def subcontractor_invoice_new(request,subcontract_id):
    subcontract = Subcontracts.objects.get(id=subcontract_id)
    items = []
    for x in SubcontractItems.objects.filter(subcontract=subcontract):
        totalcost=float(x.total_cost())
        totalbilled=float(x.total_billed())
        totalordered=float(x.SOV_total_ordered)
        quantitybilled=float(x.quantity_billed())
        remainingcost= totalcost-totalbilled
        remainingqnty = totalordered - quantitybilled
        items.append({'remainingqnty':remainingqnty,'remainingcost':remainingcost,'id':x.id,'SOV_description':x.SOV_description,'SOV_is_lump_sum':x.SOV_is_lump_sum,'SOV_unit':x.SOV_unit,'SOV_total_ordered':x.SOV_total_ordered,'SOV_rate':x.SOV_rate,'notes':x.notes,'quantity_billed':int(x.quantity_billed()),'total_billed':int(x.total_billed()),'total_cost':int(x.total_cost())})
    if SubcontractorInvoice.objects.filter(subcontract=subcontract).exists():
        next_number = SubcontractorInvoice.objects.filter(subcontract=subcontract).latest('pay_app_number').pay_app_number + 1
    else:
        next_number = 1
    if request.method == 'POST':
        if 'subcontract_note' in request.POST:
            print(request.POST)
            invoice = SubcontractorInvoice.objects.create(date=date.today(), pay_app_number=next_number, subcontract=subcontract,notes=request.POST['subcontract_note'])
            for x in SubcontractItems.objects.filter(subcontract=subcontract):
                if request.POST['quantity' + str(x.id)] != '':
                    SubcontractorInvoiceItem.objects.create(invoice=invoice, sov_item=x, quantity=request.POST['quantity' + str(x.id)],notes=request.POST['note' + str(x.id)])
            return redirect('subcontract_invoices', subcontract_id=subcontract_id, item_id='ALL')
    return render(request, "subcontractor_invoice_new.html", {'next_number':next_number,'items':items,'subcontract':subcontract})

def subcontract_invoices(request,subcontract_id,item_id):
    subcontract = Subcontracts.objects.get(id=subcontract_id)
    invoices = SubcontractorInvoice.objects.filter(subcontract=subcontract)
    return render(request, "subcontract_invoices.html", {'invoices':invoices,'subcontract':subcontract})


def subcontractor_home(request):

    subcontractors = Subcontractors.objects.filter(subcontract__isnull=False)
    return render(request, "subcontractor_home.html", {'subcontractors':subcontractors})
def subcontract(request,id):
    subcontract= Subcontracts.objects.get(id=id)
    items = SubcontractItems.objects.filter(subcontract=subcontract)
    number_items = items.count()
    if Wallcovering.objects.filter(job_number=subcontract.job_number):
        wallcovering = Wallcovering.objects.filter(job_number=subcontract.job_number)
        wallcovering_json1 = []
        for x in wallcovering:
            wallcovering_json1.append(
                {'id': x.id, 'code': x.code, 'vendor': x.vendor.company_name, 'pattern': x.pattern,
                 'estimated_unit': x.estimated_unit, 'quantity_ordered': int(x.quantity_ordered())})
        wallcovering_json = json.dumps(list(wallcovering_json1), cls=DjangoJSONEncoder)
    if request.method == 'POST':
        print(request.POST)
        if 'edit_existing_item' in request.POST:
            if request.POST['delete_existing_item'] != 'None Selected':
                item = SubcontractItems.objects.get(id=request.POST['delete_existing_item'])
                item.delete()
            elif 'item_edited' in request.POST:
                item = SubcontractItems.objects.get(id=request.POST['item_edited'])
                item.SOV_description=request.POST['SOV_description']
                item.SOV_total_ordered=request.POST['SOV_total_ordered']
                item.SOV_rate=request.POST['SOV_rate']
                item.notes=request.POST['notes']
                item.save()
                return render(request, "subcontract.html",
                              {'number_items': number_items, 'subcontract': subcontract, 'items': items})
            elif request.POST['edit_existing_item'] != 'None Selected':
                item = SubcontractItems.objects.get(id=request.POST['edit_existing_item'])
                if item.invoice_item2.exists():
                    return render(request, "subcontract.html", {'invoiced_already':True,'number_items': number_items, 'subcontract': subcontract, 'items': items,'edit_row':request.POST['edit_existing_item']})
                else:
                    return render(request, "subcontract.html", {'number_items': number_items, 'subcontract': subcontract, 'items': items,'edit_row':request.POST['edit_existing_item']})
            else:
                for x in range(1, int(request.POST['number_items']) + 1):
                    if 'item_type' + str(x) in request.POST:
                        if request.POST['item_type' + str(x)] == "Per Unit":
                            item = SubcontractItems.objects.create(subcontract=subcontract,
                                                                   SOV_description=request.POST[
                                                                       'item_description' + str(x)],
                                                                   SOV_unit=request.POST['item_unit' + str(x)],
                                                                   SOV_total_ordered=request.POST[
                                                                       'item_quantity' + str(x)],
                                                                   SOV_rate=request.POST['item_price' + str(x)],
                                                                   notes=request.POST['item_notes' + str(x)],
                                                                   date=date.today())
                            if request.POST['wallcovering_number' + str(x)] != 'no_wc_selected':
                                item.wallcovering_id = Wallcovering.objects.get(
                                    id=request.POST['wallcovering_number' + str(x)])
                                item.save()
                        else:
                            item = SubcontractItems.objects.create(subcontract=subcontract,
                                                                   SOV_description=request.POST[
                                                                       'item_description' + str(x)],
                                                                   SOV_is_lump_sum=True, SOV_unit="Lump Sum",
                                                                   SOV_total_ordered=request.POST[
                                                                       'item_price' + str(x)],
                                                                   SOV_rate=request.POST['item_price' + str(x)],
                                                                   notes=request.POST['item_notes' + str(x)],
                                                                   date=date.today())
                            if request.POST['wallcovering_number' + str(x)] != 'no_wc_selected':
                                item.wallcovering_id = Wallcovering.objects.get(
                                    id=request.POST['wallcovering_number' + str(x)])
                                item.save()
    return render(request, "subcontract.html", {'wallcovering_json':wallcovering_json,'number_items':number_items,'subcontract':subcontract,'items':items})


def subcontractor(request,id):
    response = redirect('/')
    return response


def subcontractor_new(request):
    if request.method == 'POST':
        signed = False
        if 'is_signed_labor_agreement' in request.POST:
            signed = True
        new_sub = Subcontractors.objects.create(company= request.POST['subcontractor'], contact= request.POST['contact'], phone= request.POST['phone'], email= request.POST['email'], is_signed_labor_agreement= signed,notes= request.POST['notes'])
        return redirect('subcontractor', id=new_sub.id)
    return render(request, "subcontractor_new.html")


def subcontracts_new(request):
    subcontractors = Subcontractors.objects.filter()
    if request.method == 'POST':
        if 'form1' in request.POST:
            selectedjob = Jobs.objects.get(job_number=request.POST['select_job'])
            if Wallcovering.objects.filter(job_number__job_number=request.POST['select_job']):
                wallcovering = Wallcovering.objects.filter(job_number__job_number=request.POST['select_job'])
                wallcovering_json1 = []
                for x in wallcovering:
                    wallcovering_json1.append({'id':x.id,'code':x.code,'vendor':x.vendor.company_name,'pattern':x.pattern,'estimated_unit':x.estimated_unit,'quantity_ordered':int(x.quantity_ordered())})
                wallcovering_json = json.dumps(list(wallcovering_json1), cls=DjangoJSONEncoder)
            else:
                wallcovering_json = 'None'
            return render(request, "subcontracts_new.html", {'wallcovering_json':wallcovering_json,'selectedjob': selectedjob, 'subcontractors': subcontractors})
        else:
            subcontract1 = Subcontracts.objects.create(job_number=Jobs.objects.get(job_number=request.POST['selected_job']),subcontractor=Subcontractors.objects.get(id=request.POST['select_subcontractor']),po_number=request.POST['po_number'],notes=request.POST['subcontract_notes'],date=date.today())
            for x in range(1,int(request.POST['number_items'])+1):
                if 'item_type' + str(x) in request.POST:
                    if request.POST['item_type' + str(x)] == "Per Unit":
                        item = SubcontractItems.objects.create(subcontract=subcontract1,SOV_description=request.POST['item_description'+ str(x)],SOV_unit=request.POST['item_unit'+ str(x)],SOV_total_ordered=request.POST['item_quantity'+ str(x)],SOV_rate =request.POST['item_price'+ str(x)],notes=request.POST['item_notes'+ str(x)],date=date.today())
                        if request.POST['wallcovering_number'+ str(x)] != 'no_wc_selected':
                            item.wallcovering_id = Wallcovering.objects.get(id=request.POST['wallcovering_number' + str(x)])
                            item.save()
                    else:
                        item = SubcontractItems.objects.create(subcontract=subcontract1, SOV_description=request.POST['item_description' + str(x)],SOV_is_lump_sum = True, SOV_unit = "Lump Sum", SOV_total_ordered =request.POST['item_price'+ str(x)],SOV_rate =request.POST['item_price'+ str(x)],notes=request.POST['item_notes'+ str(x)],date=date.today())
                        if request.POST['wallcovering_number'+ str(x)] != 'no_wc_selected':
                            item.wallcovering_id = Wallcovering.objects.get(id=request.POST['wallcovering_number' + str(x)])
                            item.save()
            return redirect('subcontract', id=subcontract1.id)

    selectedjob = 'ALL'
    jobs = Jobs.objects.filter(status='Open')
    return render(request, "subcontracts_new.html",{'selectedjob': selectedjob,'jobs':jobs,'subcontractors':subcontractors})


def subcontracts_home(request):
    subcontracts = Subcontracts.objects.filter(is_closed=False)
    return render(request, "subcontracts_home.html", {'subcontracts':subcontracts})
