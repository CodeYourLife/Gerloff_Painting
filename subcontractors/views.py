from console.models import *
from django.shortcuts import render, redirect
import json
from django.core.serializers.json import DjangoJSONEncoder
from datetime import date
from wallcovering.models import Wallcovering
from subcontractors.models import *
from jobs.models import *
from django.contrib.auth.decorators import login_required
from employees.models import *


@login_required(login_url='/accounts/login')
def subcontractor_invoice_new(request, subcontract_id):
    subcontract = Subcontracts.objects.get(id=subcontract_id)
    items = []
    for x in SubcontractItems.objects.filter(subcontract=subcontract):
        totalcost = float(x.total_cost())
        totalbilled = float(x.total_billed())
        totalordered = float(x.SOV_total_ordered)
        quantitybilled = float(x.quantity_billed())
        remainingcost = totalcost - totalbilled
        remainingqnty = totalordered - quantitybilled
        if x.SOV_is_lump_sum == True:
            items.append({'remainingqnty': remainingqnty, 'remainingcost': remainingcost, 'id': x.id,
                          'SOV_description': x.SOV_description, 'SOV_is_lump_sum': x.SOV_is_lump_sum,
                          'SOV_unit': x.SOV_unit, 'SOV_total_ordered': x.SOV_total_ordered, 'SOV_rate': x.SOV_rate,
                          'notes': x.notes, 'quantity_billed': float(x.quantity_billed()),
                          'total_billed': int(x.total_billed()), 'total_cost': int(x.total_cost())})
        else:
            items.append({'remainingqnty': remainingqnty, 'remainingcost': remainingcost, 'id': x.id,
                          'SOV_description': x.SOV_description, 'SOV_is_lump_sum': x.SOV_is_lump_sum,
                          'SOV_unit': x.SOV_unit, 'SOV_total_ordered': x.SOV_total_ordered, 'SOV_rate': x.SOV_rate,
                          'notes': x.notes, 'quantity_billed': int(x.quantity_billed()),
                          'total_billed': int(x.total_billed()), 'total_cost': int(x.total_cost())})
    print(items)
    if SubcontractorInvoice.objects.filter(subcontract=subcontract).exists():
        next_number = SubcontractorInvoice.objects.filter(subcontract=subcontract).latest(
            'pay_app_number').pay_app_number + 1
    else:
        next_number = 1
    if request.method == 'POST':
        if 'subcontract_note' in request.POST:
            invoice = SubcontractorInvoice.objects.create(date=date.today(), pay_app_number=next_number,
                                                          subcontract=subcontract)
            for x in SubcontractItems.objects.filter(subcontract=subcontract):
                if request.POST['quantity' + str(x.id)] != '':
                    SubcontractorInvoiceItem.objects.create(invoice=invoice, sov_item=x,
                                                            quantity=request.POST['quantity' + str(x.id)],
                                                            notes=request.POST['note' + str(x.id)])
                elif request.POST['note' + str(x.id)] != '':
                    SubcontractorInvoiceItem.objects.create(invoice=invoice, sov_item=x, quantity=0,
                                                            notes=request.POST['note' + str(x.id)])
            SubcontractNotes.objects.create(subcontract=subcontract, date=date.today(),
                                            user=Employees.objects.get(user=request.user),
                                            note="New Invoice- " + request.POST['subcontract_note'], invoice=invoice)
            # Email.sendEmail('test', 'test body', 'joe@gerloffpainting.com')
            return redirect('subcontract_invoices', subcontract_id=subcontract_id, item_id='ALL')
    return render(request, "subcontractor_invoice_new.html",
                  {'next_number': next_number, 'items': items, 'subcontract': subcontract})


@login_required(login_url='/accounts/login')
def subcontract_invoices(request, subcontract_id, item_id):
    subcontract = Subcontracts.objects.get(id=subcontract_id)
    if request.method == 'POST':
        if 'form99' in request.POST:
            selected_invoice = SubcontractorInvoice.objects.get(id=item_id)
            SubcontractNotes.objects.create(subcontract=subcontract, date=date.today(),
                                            user=Employees.objects.get(user=request.user),
                                            note=request.POST['invoice_notes'], invoice=selected_invoice)
            return redirect('subcontract_invoices', subcontract_id=subcontract_id, item_id=item_id)
        if 'form5' in request.POST:
            selected_invoice = SubcontractorInvoice.objects.get(id=item_id)
            invoice = SubcontractorInvoice.objects.get(id=item_id)
            invoicetotal = 0
            for x in SubcontractorInvoiceItem.objects.filter(invoice=selected_invoice):
                invoicetotal = invoicetotal + x.total_cost()
            invoice.final_amount = invoicetotal
            if subcontract.is_retainage == True:
                invoice.retainage = invoicetotal * subcontract.retainage_percentage
            else:
                invoice.retainage = 0
            invoice.is_sent = True
            invoice.save()
            SubcontractNotes.objects.create(subcontract=subcontract, date=date.today(),
                                            user=Employees.objects.get(user=request.user),
                                            note="Invoice " + str(invoice.pay_app_number) + " Approved!",
                                            invoice=selected_invoice)
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
        invoices = SubcontractorInvoice.objects.filter(id=item_id)
        selected_invoice = SubcontractorInvoice.objects.get(id=item_id)
        invoice_items = SubcontractorInvoiceItem.objects.filter(invoice=selected_invoice)
        notes = SubcontractNotes.objects.filter(subcontract=subcontract, invoice=selected_invoice)
        for x in SubcontractItems.objects.filter(subcontract=subcontract):
            totalcost = float(x.total_cost())
            totalbilled = float(x.total_billed())
            totalordered = float(x.SOV_total_ordered)
            quantitybilled = float(x.quantity_billed())
            remainingcost = totalcost - totalbilled
            remainingqnty = totalordered - quantitybilled
            invoiced = SubcontractorInvoiceItem.objects.filter(invoice=selected_invoice, sov_item=x).exists()
            if invoiced:
                if x.SOV_is_lump_sum:
                    special = (float(SubcontractorInvoiceItem.objects.get(invoice=selected_invoice,
                                                                          sov_item=x).quantity) / totalcost) * 100
                    percentage = ((float(SubcontractorInvoiceItem.objects.get(invoice=selected_invoice,
                                                                              sov_item=x).quantity) + totalbilled) / totalcost) * 100
                else:
                    special = int(SubcontractorInvoiceItem.objects.get(invoice=selected_invoice,
                                                                       sov_item=x).quantity) * x.SOV_rate
                    percentage = ((float(SubcontractorInvoiceItem.objects.get(invoice=selected_invoice,
                                                                              sov_item=x).quantity) + quantitybilled) / totalordered) * 100
            else:
                special = 0
                percentage = (totalbilled / totalcost) * 100
            items.append(
                {'percentage': str(round(percentage, 2)), 'special': str(round(special, 2)), 'invoiced': invoiced,
                 'remainingqnty': remainingqnty, 'remainingcost': remainingcost, 'id': x.id,
                 'SOV_description': x.SOV_description, 'SOV_is_lump_sum': x.SOV_is_lump_sum,
                 'SOV_unit': x.SOV_unit, 'SOV_total_ordered': x.SOV_total_ordered, 'SOV_rate': x.SOV_rate,
                 'notes': x.notes, 'quantity_billed': float(x.quantity_billed()),
                 'total_billed': int(x.total_billed()), 'total_cost': int(x.total_cost())})
        return render(request, "subcontract_invoices.html",
                      {'notes': notes, 'items': items, 'invoice_items': invoice_items,
                       'selected_invoice': selected_invoice, 'invoices': invoices, 'subcontract': subcontract})
    return render(request, "subcontract_invoices.html", {'invoices': invoices, 'subcontract': subcontract})


@login_required(login_url='/accounts/login')
def subcontractor_home(request):
    if request.method == 'POST':
        subcontractor = Subcontractors.objects.get(id=request.POST['subcontractor_id'])
        subcontractor.contact = request.POST['contact']
        subcontractor.phone = request.POST['phone']
        subcontractor.email = request.POST['email']
        subcontractor.notes = request.POST['notes']
        if 'is_inactive' in request.POST:
            subcontractor.is_inactive = True
        subcontractor.save()
        if request.POST['insurance'] != "":
            subcontractor.insurance_expire_date = request.POST['insurance']
            subcontractor.save()
        if 'go_back_to_subcontracts' in request.POST:
            return redirect('subcontracts_home')
        if 'go_back_to_subcontract' in request.POST:
            return redirect('subcontract', id=request.POST['go_back_to_subcontract'])
        return redirect('subcontractor_home')
    send_data = {}
    subcontractors = []
    for x in Subcontractors.objects.filter(is_inactive=False):
        subcontractors.append({'id': x.id, 'company': x.company, 'active_contracts': x.active_contracts()})
    send_data['subcontractors'] = subcontractors
    return render(request, "subcontractor_home.html", send_data)


@login_required(login_url='/accounts/login')
def subcontract(request, id):
    send_data = {}
    subcontract = Subcontracts.objects.get(id=id)
    items = []
    number_items = 0
    for x in SubcontractItems.objects.filter(subcontract=subcontract):
        number_items = number_items + 1
        totalcost = float(x.total_cost())
        totalbilled = float(x.total_billed())
        totalordered = float(x.SOV_total_ordered)
        quantitybilled = float(x.quantity_billed())
        remainingcost = totalcost - totalbilled
        remainingqnty = totalordered - quantitybilled
        percentage = (totalbilled / totalcost) * 100
        items.append({'percentage': str(round(percentage, 2)),
                      'remainingqnty': remainingqnty, 'remainingcost': remainingcost, 'id': x.id,
                      'SOV_description': x.SOV_description, 'SOV_is_lump_sum': x.SOV_is_lump_sum,
                      'SOV_unit': x.SOV_unit, 'SOV_total_ordered': x.SOV_total_ordered, 'SOV_rate': x.SOV_rate,
                      'notes': x.notes, 'quantity_billed': float(x.quantity_billed()),
                      'total_billed': int(x.total_billed()), 'total_cost': int(x.total_cost())})
    send_data['items'] = items
    send_data['number_items'] = number_items
    send_data['notes'] = SubcontractNotes.objects.filter(subcontract=subcontract)
    if Wallcovering.objects.filter(job_number=subcontract.job_number):
        wallcovering = Wallcovering.objects.filter(job_number=subcontract.job_number)
        print("Wallcovering")
        print(wallcovering)
        wallcovering_json1 = []
        for x in wallcovering:
            wallcovering_json1.append(
                {'id': x.id, 'code': x.code, 'vendor': x.vendor.company_name, 'pattern': x.pattern,
                 'estimated_unit': x.estimated_unit, 'quantity_ordered': int(x.quantity_ordered())})
        send_data['wallcovering_json'] = json.dumps(list(wallcovering_json1), cls=DjangoJSONEncoder)
    if request.method == 'POST':
        if 'change_header' in request.POST:
            subcontract.po_number = request.POST['po_number']
            subcontract.date = request.POST['issued_date']
            if 'is_retainage' in request.POST:
                subcontract.is_retainage = True
            else:
                subcontract.is_retainage = False
            subcontract.retainage_percentage = request.POST['retainage_percentage']
            if 'is_closed' in request.POST:
                subcontract.is_closed = True
            else:
                subcontract.is_closed = False
            subcontract.save()
            return redirect("subcontract", subcontract.id)
        if 'edit_now' in request.POST:
            send_data['edit_row'] = request.POST['edit_existing_item']
            if request.POST['edit_existing_item'] != 'None Selected':
                item = SubcontractItems.objects.get(id=request.POST['edit_existing_item'])
                if item.invoice_item2.exists():
                    send_data['invoiced_already'] = True
        if 'save_now' in request.POST:
            item = SubcontractItems.objects.get(id=request.POST['item_edited'])
            item.SOV_description = request.POST['SOV_description']
            if 'SOV_total_ordered' in request.POST: item.SOV_total_ordered = request.POST['SOV_total_ordered']
            if 'SOV_rate' in request.POST: item.SOV_rate = request.POST['SOV_rate']
            item.notes = request.POST['notes']
            item.save()
            return redirect("subcontract", subcontract.id)
        if 'delete_now' in request.POST:
            item = SubcontractItems.objects.get(id=request.POST['delete_existing_item'])
            item.delete()
            return redirect("subcontract", subcontract.id)
        if 'added_row' in request.POST:
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
                        if 'wallcovering_number' + str(x) in request.POST:
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
                        if 'wallcovering_number' + str(x) in request.POST:
                            if request.POST['wallcovering_number' + str(x)] != 'no_wc_selected':
                                item.wallcovering_id = Wallcovering.objects.get(
                                    id=request.POST['wallcovering_number' + str(x)])
                                item.save()
            return redirect("subcontract", subcontract.id)
        if 'new_note' in request.POST:
            SubcontractNotes.objects.create(subcontract=subcontract, date=date.today(),
                                            user=Employees.objects.get(user=request.user),
                                            note=request.POST['new_note'])
            send_data['notes'] = SubcontractNotes.objects.filter(subcontract=subcontract)
            return redirect("subcontract", subcontract.id)
    subcontract = Subcontracts.objects.get(id=id)
    send_data['subcontract'] = subcontract
    send_data['percent_complete'] = format(subcontract.percent_complete(), ".0%")
    send_data['total_contract'] = "{:,}".format(int(subcontract.total_contract_amount()))
    send_data['total_billed'] = "{:,}".format(int(subcontract.total_billed()))
    send_data['subcontract_date'] = str(subcontract.date)
    return render(request, "subcontract.html", send_data)


@login_required(login_url='/accounts/login')
def subcontractor(request, id):
    response = redirect('/')
    return response


@login_required(login_url='/accounts/login')
def subcontractor_new(request):
    if request.method == 'POST':
        print(request.POST['insurance_expire_date'])
        signed = False
        if 'is_signed_labor_agreement' in request.POST:
            signed = True
        new_sub = Subcontractors.objects.create(company=request.POST['subcontractor'], contact=request.POST['contact'],
                                                phone=request.POST['phone'], email=request.POST['email'],
                                                is_signed_labor_agreement=signed, notes=request.POST['notes'])
        new_sub.save()
        return redirect('subcontractor', id=new_sub.id)
    return render(request, "subcontractor_new.html")


@login_required(login_url='/accounts/login')
def subcontracts_new(request):
    send_data = {}
    send_data['subcontractors'] = Subcontractors.objects.all()
    if request.method == 'POST':
        if 'form1' in request.POST:
            selectedjob = Jobs.objects.get(job_number=request.POST['select_job'])
            send_data['selectedjob'] = selectedjob
            if Wallcovering.objects.filter(job_number__job_number=request.POST['select_job']):
                wallcovering = Wallcovering.objects.filter(job_number__job_number=request.POST['select_job'])
                wallcovering_json1 = []
                for x in wallcovering:
                    wallcovering_json1.append(
                        {'id': x.id, 'code': x.code, 'vendor': x.vendor.company_name, 'pattern': x.pattern,
                         'estimated_unit': x.estimated_unit, 'quantity_ordered': int(x.quantity_ordered())})
                send_data['wallcovering_json'] = json.dumps(list(wallcovering_json1), cls=DjangoJSONEncoder)
            else:
                send_data['wallcovering_json'] = 'None'
            return render(request, "subcontracts_new.html", send_data)
        else:
            subcontract1 = Subcontracts.objects.create(
                job_number=Jobs.objects.get(job_number=request.POST['selected_job']),
                subcontractor=Subcontractors.objects.get(id=request.POST['select_subcontractor']),
                po_number=request.POST['po_number'], date=date.today(), retainage_percentage=0, is_retainage=False)
            SubcontractNotes.objects.create(subcontract=subcontract1, date=date.today(),
                                            user=Employees.objects.get(user=request.user),
                                            note="New Contract- " + request.POST['subcontract_notes'])
            if 'is_retainage' in request.POST:
                subcontract1.is_retainage = True
                subcontract1.retainage_percentage = request.POST['retainage_amt']
                subcontract1.save()
            for x in range(1, int(request.POST['number_items']) + 1):
                if 'item_type' + str(x) in request.POST:
                    if request.POST['item_type' + str(x)] == "Per Unit":
                        item = SubcontractItems.objects.create(subcontract=subcontract1, SOV_description=request.POST[
                            'item_description' + str(x)], SOV_unit=request.POST['item_unit' + str(x)],
                                                               SOV_total_ordered=request.POST['item_quantity' + str(x)],
                                                               SOV_rate=request.POST['item_price' + str(x)],
                                                               notes=request.POST['item_notes' + str(x)],
                                                               date=date.today())
                        if 'wallcovering_number' + str(x) in request.POST:
                            if request.POST['wallcovering_number' + str(x)] != 'no_wc_selected':
                                item.wallcovering_id = Wallcovering.objects.get(
                                    id=request.POST['wallcovering_number' + str(x)])
                                item.save()
                    else:
                        item = SubcontractItems.objects.create(subcontract=subcontract1, SOV_description=request.POST[
                            'item_description' + str(x)], SOV_is_lump_sum=True, SOV_unit="Lump Sum",
                                                               SOV_total_ordered=request.POST['item_price' + str(x)],
                                                               SOV_rate=request.POST['item_price' + str(x)],
                                                               notes=request.POST['item_notes' + str(x)],
                                                               date=date.today())
                        if 'wallcovering_number' + str(x) in request.POST:
                            if request.POST['wallcovering_number' + str(x)] != 'no_wc_selected':
                                item.wallcovering_id = Wallcovering.objects.get(
                                    id=request.POST['wallcovering_number' + str(x)])
                                item.save()
            return redirect('subcontract', id=subcontract1.id)
    send_data['selectedjob'] = 'ALL'
    if request.method == 'GET':
        if 'search_job' in request.GET:
            send_data['jobs'] = Jobs.objects.filter(job_name__icontains=request.GET['search_job'])
        else:
            send_data['jobs'] = Jobs.objects.filter(status='Open')
    else:
        send_data['jobs'] = Jobs.objects.filter(status='Open')
    return render(request, "subcontracts_new.html", send_data)


@login_required(login_url='/accounts/login')
def subcontracts_home(request):
    if request.method == 'POST':
        print(request.POST)
        if request.POST['subcontract_id'] != "":
            return redirect('subcontract', id=request.POST['subcontract_id'])
        if request.POST['job_number'] != "":
            return redirect('job_page', jobnumber=request.POST['job_number'])
    subcontracts = []
    for x in Subcontracts.objects.filter(is_closed=False):  # str(format(x.percent_complete(),".0%"))
        subcontracts.append({'job_name': x.job_number.job_name, 'job_number': x.job_number.job_number,
                             'subcontractor': x.subcontractor.company, 'subcontractor_id': x.subcontractor.id,
                             'po_number': x.po_number, 'id': x.id,
                             'percent_complete': format(x.percent_complete(), ".0%")})
    return render(request, "subcontracts_home.html", {'subcontracts': subcontracts})
