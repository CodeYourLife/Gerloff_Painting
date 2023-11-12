
from console.models import *
from django.shortcuts import render, redirect
import json
from django.core.serializers.json import DjangoJSONEncoder
from datetime import date
from wallcovering.models import Wallcovering
from subcontractors.models import *
from jobs.models import *
from django.contrib.auth.decorators import login_required

@login_required(login_url='/accounts/login')
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
        if x.SOV_is_lump_sum == True:
            items.append({'remainingqnty': remainingqnty, 'remainingcost': remainingcost, 'id': x.id,
                          'SOV_description': x.SOV_description, 'SOV_is_lump_sum': x.SOV_is_lump_sum,
                          'SOV_unit': x.SOV_unit, 'SOV_total_ordered': x.SOV_total_ordered, 'SOV_rate': x.SOV_rate,
                          'notes': x.notes, 'quantity_billed': float(x.quantity_billed()),
                          'total_billed': int(x.total_billed()), 'total_cost': int(x.total_cost())})
        else:
            items.append({'remainingqnty':remainingqnty,'remainingcost':remainingcost,'id':x.id,'SOV_description':x.SOV_description,'SOV_is_lump_sum':x.SOV_is_lump_sum,'SOV_unit':x.SOV_unit,'SOV_total_ordered':x.SOV_total_ordered,'SOV_rate':x.SOV_rate,'notes':x.notes,'quantity_billed':int(x.quantity_billed()),'total_billed':int(x.total_billed()),'total_cost':int(x.total_cost())})
    print(items)
    if SubcontractorInvoice.objects.filter(subcontract=subcontract).exists():
        next_number = SubcontractorInvoice.objects.filter(subcontract=subcontract).latest('pay_app_number').pay_app_number + 1
    else:
        next_number = 1
    if request.method == 'POST':
        if 'subcontract_note' in request.POST:
            invoice = SubcontractorInvoice.objects.create(date=date.today(), pay_app_number=next_number, subcontract=subcontract)
            for x in SubcontractItems.objects.filter(subcontract=subcontract):
                if request.POST['quantity' + str(x.id)] != '':
                    SubcontractorInvoiceItem.objects.create(invoice=invoice, sov_item=x, quantity=request.POST['quantity' + str(x.id)],notes=request.POST['note' + str(x.id)])
                elif request.POST['note' + str(x.id)] != '':
                    SubcontractorInvoiceItem.objects.create(invoice=invoice, sov_item=x, quantity=0,notes=request.POST['note' + str(x.id)])
            SubcontractNotes.objects.create(subcontract=subcontract, date =date.today(), user=Employees.objects.get(user=request.user),note = "New Invoice- " + request.POST['subcontract_note'],invoice = invoice)
            # Email.sendEmail('test', 'test body', 'joe@gerloffpainting.com')
            return redirect('subcontract_invoices', subcontract_id=subcontract_id, item_id='ALL')
    return render(request, "subcontractor_invoice_new.html", {'next_number':next_number,'items':items,'subcontract':subcontract})


@login_required(login_url='/accounts/login')
def subcontract_invoices(request,subcontract_id,item_id):
    subcontract = Subcontracts.objects.get(id=subcontract_id)
    if request.method == 'POST':
        if 'form99' in request.POST:
            selected_invoice = SubcontractorInvoice.objects.get(id=item_id)
            SubcontractNotes.objects.create(subcontract=subcontract, date=date.today(),
                                            user=Employees.objects.get(user=request.user),
                                            note=request.POST['invoice_notes'],invoice=selected_invoice)
            return redirect('subcontract_invoices', subcontract_id=subcontract_id, item_id=item_id)
        if 'form5' in request.POST:
            selected_invoice = SubcontractorInvoice.objects.get(id=item_id)
            invoice = SubcontractorInvoice.objects.get(id=item_id)
            invoicetotal = 0
            for x in SubcontractorInvoiceItem.objects.filter(invoice=selected_invoice):
                invoicetotal = invoicetotal + x.total_cost()
            invoice.final_amount=invoicetotal
            if subcontract.is_retainage == True:
                invoice.retainage = invoicetotal * subcontract.retainage_percentage
            else:
                invoice.retainage =0
            invoice.is_sent = True
            invoice.save()
            SubcontractNotes.objects.create(subcontract=subcontract, date=date.today(),
                                            user=Employees.objects.get(user=request.user),
                                            note="Invoice " + str(invoice.pay_app_number) + " Approved!",invoice=selected_invoice)
            return redirect('subcontract_invoices', subcontract_id=subcontract_id, item_id=item_id)
        if 'form6' in request.POST:
            selected_invoice = SubcontractorInvoice.objects.get(id=item_id)
            invoice = SubcontractorInvoice.objects.get(id=item_id)
            print(request.POST)
            for x in SubcontractItems.objects.filter(subcontract=subcontract):
                if request.POST['quantity' + str(x.id)] != '':
                    if SubcontractorInvoiceItem.objects.filter(invoice=invoice, sov_item=x).exists():
                        item = SubcontractorInvoiceItem.objects.get(invoice=invoice, sov_item=x)
                        item.quantity = request.POST['quantity' + str(x.id)]
                        item.notes = request.POST['note' + str(x.id)]
                        item.save()
                    else:
                        SubcontractorInvoiceItem.objects.create(invoice=invoice, sov_item=x,
                                                                quantity=request.POST['quantity' + str(x.id)],
                                                                notes=request.POST['note' + str(x.id)])
                elif request.POST['note' + str(x.id)] != '':
                    SubcontractorInvoiceItem.objects.create(invoice=invoice, sov_item=x,
                                                            quantity=0,
                                                            notes=request.POST['note' + str(x.id)])
            return redirect('subcontract_invoices', subcontract_id=subcontract_id, item_id=item_id)
    if item_id == 'ALL':
        invoices = SubcontractorInvoice.objects.filter(subcontract=subcontract)
    else:
        items = []
        invoices = SubcontractorInvoice.objects.filter(id= item_id)
        selected_invoice = SubcontractorInvoice.objects.get(id= item_id)
        invoice_items = SubcontractorInvoiceItem.objects.filter(invoice=selected_invoice)
        notes = SubcontractNotes.objects.filter(subcontract=subcontract,invoice=selected_invoice)
        for x in SubcontractItems.objects.filter(subcontract=subcontract):
            totalcost = float(x.total_cost())
            totalbilled = float(x.total_billed())
            totalordered = float(x.SOV_total_ordered)
            quantitybilled = float(x.quantity_billed())
            remainingcost = totalcost - totalbilled
            remainingqnty = totalordered - quantitybilled
            invoiced = SubcontractorInvoiceItem.objects.filter(invoice=selected_invoice,sov_item=x).exists()
            if invoiced:
                if x.SOV_is_lump_sum:
                    special =  (float(SubcontractorInvoiceItem.objects.get(invoice=selected_invoice,sov_item=x).quantity) / totalcost)*100
                    percentage = ((float(SubcontractorInvoiceItem.objects.get(invoice=selected_invoice,sov_item=x).quantity) + totalbilled) / totalcost)*100
                else:
                    special = int(SubcontractorInvoiceItem.objects.get(invoice=selected_invoice,sov_item=x).quantity) * x.SOV_rate
                    percentage = ((float(SubcontractorInvoiceItem.objects.get(invoice=selected_invoice,
                                                                             sov_item=x).quantity) + quantitybilled) / totalordered)*100
            else:
                special =0
                percentage = (totalbilled / totalcost)*100
            items.append({'percentage':str(round(percentage, 2)),'special':str(round(special, 2)),'invoiced':invoiced,'remainingqnty': remainingqnty, 'remainingcost': remainingcost, 'id': x.id,
                          'SOV_description': x.SOV_description, 'SOV_is_lump_sum': x.SOV_is_lump_sum,
                          'SOV_unit': x.SOV_unit, 'SOV_total_ordered': x.SOV_total_ordered, 'SOV_rate': x.SOV_rate,
                          'notes': x.notes, 'quantity_billed': float(x.quantity_billed()),
                          'total_billed': int(x.total_billed()), 'total_cost': int(x.total_cost())})
        return render(request, "subcontract_invoices.html", {'notes':notes,'items':items,'invoice_items':invoice_items,'selected_invoice':selected_invoice,'invoices': invoices, 'subcontract': subcontract})
    return render(request, "subcontract_invoices.html", {'invoices':invoices,'subcontract':subcontract})


@login_required(login_url='/accounts/login')
def subcontractor_home(request):
    subcontractors = Subcontractors.objects.filter(subcontract__isnull=False)
    return render(request, "subcontractor_home.html", {'subcontractors':subcontractors})


@login_required(login_url='/accounts/login')
def subcontract(request,id):
    subcontract= Subcontracts.objects.get(id=id)
    items = []
    number_items =0
    for x in SubcontractItems.objects.filter(subcontract=subcontract):
        number_items = number_items + 1
        totalcost = float(x.total_cost())
        totalbilled = float(x.total_billed())
        totalordered = float(x.SOV_total_ordered)
        quantitybilled = float(x.quantity_billed())
        remainingcost = totalcost - totalbilled
        remainingqnty = totalordered - quantitybilled
        percentage = (totalbilled / totalcost)*100
        items.append({'percentage': str(round(percentage, 2)),
                      'remainingqnty': remainingqnty, 'remainingcost': remainingcost, 'id': x.id,
                      'SOV_description': x.SOV_description, 'SOV_is_lump_sum': x.SOV_is_lump_sum,
                      'SOV_unit': x.SOV_unit, 'SOV_total_ordered': x.SOV_total_ordered, 'SOV_rate': x.SOV_rate,
                      'notes': x.notes, 'quantity_billed': float(x.quantity_billed()),
                      'total_billed': int(x.total_billed()), 'total_cost': int(x.total_cost())})

    notes = SubcontractNotes.objects.filter(subcontract=subcontract)
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
                              {'notes':notes,'number_items': number_items, 'subcontract': subcontract, 'items': items})
            elif request.POST['edit_existing_item'] != 'None Selected':
                item = SubcontractItems.objects.get(id=request.POST['edit_existing_item'])
                if item.invoice_item2.exists():
                    return render(request, "subcontract.html", {'notes':notes,'invoiced_already':True,'number_items': number_items, 'subcontract': subcontract, 'items': items,'edit_row':request.POST['edit_existing_item']})
                else:
                    return render(request, "subcontract.html", {'notes':notes,'number_items': number_items, 'subcontract': subcontract, 'items': items,'edit_row':request.POST['edit_existing_item']})
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
        else:
            if 'form1' in request.POST:
                subcontract.po_number=request.POST['po_number']
                print(request.POST)
                if request.POST['subcontract_notes'] != '':
                    SubcontractNotes.objects.create(subcontract=subcontract, date=date.today(), user=Employees.objects.get(user=request.user),note = request.POST['subcontract_notes'])
                    notes = SubcontractNotes.objects.filter(subcontract=subcontract)
    return render(request, "subcontract.html", {'notes':notes,'wallcovering_json':wallcovering_json,'number_items':number_items,'subcontract':subcontract,'items':items})


@login_required(login_url='/accounts/login')
def subcontractor(request,id):
    response = redirect('/')
    return response


@login_required(login_url='/accounts/login')
def subcontractor_new(request):
    if request.method == 'POST':
        signed = False
        if 'is_signed_labor_agreement' in request.POST:
            signed = True
        new_sub = Subcontractors.objects.create(company= request.POST['subcontractor'], contact= request.POST['contact'], phone= request.POST['phone'], email= request.POST['email'], is_signed_labor_agreement= signed,notes= request.POST['notes'])
        return redirect('subcontractor', id=new_sub.id)
    return render(request, "subcontractor_new.html")


@login_required(login_url='/accounts/login')
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
            subcontract1 = Subcontracts.objects.create(job_number=Jobs.objects.get(job_number=request.POST['selected_job']),subcontractor=Subcontractors.objects.get(id=request.POST['select_subcontractor']),po_number=request.POST['po_number'], date=date.today(),retainage_percentage=0, is_retainage = False)
            SubcontractNotes.objects.create(subcontract=subcontract1, date =date.today(), user=Employees.objects.get(user=request.user),note = "New Contract- " + request.POST['subcontract_notes'])
            if 'is_retainage' in request.POST:
                subcontract1.is_retainage = True
                subcontract1.retainage_percentage = request.POST['retainage_amt']
                subcontract1.save()
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


@login_required(login_url='/accounts/login')
def subcontracts_home(request):
    subcontracts = Subcontracts.objects.filter(is_closed=False)
    return render(request, "subcontracts_home.html", {'subcontracts':subcontracts})
