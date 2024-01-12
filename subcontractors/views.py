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
import datetime
from console.misc import Email


def portal(request, sub_id, contract_id):
    send_data = {}
    selected_sub = Subcontractors.objects.get(id=sub_id)
    send_data['selected_sub'] = selected_sub
    subcontracts = []
    if contract_id == 'ALL':
        for x in Subcontracts.objects.filter(is_closed=False,
                                             subcontractor=selected_sub):
            total_contract_amount = "$" + f"{int(x.total_contract_amount()):,d}"
            total_billed = "$" + f"{int(x.total_billed()):,d}"
            subcontracts.append({'invoice_ready': x.invoice_ready(), 'invoice_pending': x.invoice_pending(),
                                 'job_name': x.job_number.job_name,
                                 'job_number': x.job_number.job_number,
                                 'subcontractor': x.subcontractor.company, 'subcontractor_id': x.subcontractor.id,
                                 'po_number': x.po_number, 'id': x.id,
                                 'percent_complete': format(x.percent_complete(), ".0%"),
                                 'total_contract_amount': total_contract_amount, 'total_billed': total_billed})
        send_data['subcontracts'] = subcontracts
    else:
        selected_contract = Subcontracts.objects.get(id=contract_id)
        if SubcontractorInvoice.objects.filter(subcontract=selected_contract, is_sent=False).exists():
            send_data['pending_invoices_exist'] = True
        send_data['selected_contract'] = selected_contract
        send_data['invoices'] = SubcontractorInvoice.objects.filter(subcontract=selected_contract)
        items = []
        number_items = 0
        for x in SubcontractItems.objects.filter(subcontract=selected_contract):
            number_items = number_items + 1
            totalcost = float(x.total_cost())
            totalbilled = float(x.total_billed())
            totalordered = float(x.SOV_total_ordered)
            quantitybilled = float(x.quantity_billed())
            remainingcost = totalcost - totalbilled
            remainingqnty = totalordered - quantitybilled
            percentage = (totalbilled / totalcost) * 100
            totalordered = f"{int(x.SOV_total_ordered):,d}"
            items.append({'percentage': str(round(percentage, 2)),
                          'remainingqnty': remainingqnty, 'remainingcost': remainingcost, 'id': x.id,
                          'SOV_description': x.SOV_description, 'SOV_is_lump_sum': x.SOV_is_lump_sum,
                          'SOV_unit': x.SOV_unit, 'SOV_total_ordered': totalordered, 'SOV_rate': x.SOV_rate,
                          'notes': x.notes, 'quantity_billed': float(x.quantity_billed()),
                          'total_billed': int(x.total_billed()), 'total_cost': int(x.total_cost())})
        send_data['items'] = items

    return render(request, "portal.html", send_data)


def connect(request):
    send_data = {}
    if request.method == 'POST':
        send_data = {}
        if 'login_now' in request.POST:
            if Subcontractors.objects.filter(username=request.POST['username']).exists():
                selected_sub = Subcontractors.objects.get(username=request.POST['username'])
                if request.POST['password'] == selected_sub.password:
                    return redirect('portal', sub_id=selected_sub.id, contract_id='ALL')
            else:
                send_data['message'] = "Username or password not valid"
                return render(request, "portal_registration.html", send_data)

        if 'enter_pin' in request.POST:
            send_data['enter_pin'] = True
            return render(request, "portal_registration.html", send_data)
        if 'pin' in request.POST:
            print(request.POST)
            if Subcontractors.objects.filter(pin=request.POST['pin']).exists():
                selected_sub = Subcontractors.objects.get(pin=request.POST['pin'])
                if selected_sub.username:
                    send_data['message'] = "Someone has already registered with that PIN"
                    send_data['enter_pin'] = True
                else:
                    send_data['selected_sub'] = selected_sub
                    send_data['register_now'] = True
            else:
                send_data['message'] = "PIN NOT CORRECT"
                send_data['enter_pin'] = True
            return render(request, "portal_registration.html", send_data)
        if 'new_username' in request.POST:
            if Subcontractors.objects.filter(username=request.POST['new_username']).exists():
                selected_sub = Subcontractors.objects.get(id=request.POST['selected_sub'])
                send_data['message'] = "That Username has already been used"
                send_data['selected_sub'] = selected_sub
                send_data['register_now'] = True
                return render(request, "portal_registration.html", send_data)
            else:
                selected_sub = Subcontractors.objects.get(id=request.POST['selected_sub'])
                selected_sub.username = request.POST['new_username']
                selected_sub.password = request.POST['password']
                selected_sub.save()
                return redirect('portal', sub_id=selected_sub.id, contract_id='ALL')
    return render(request, "portal_registration.html", send_data)


@login_required(login_url='/accounts/login')
def subcontractor_invoice_new(request, subcontract_id):
    today = datetime.date.today()
    friday = today + datetime.timedelta((4 - today.weekday()) % 7)
    if today.weekday() == 4 or today.weekday() == 3 or today.weekday() == 2: friday = friday + timedelta(7)
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
    if SubcontractorInvoice.objects.filter(subcontract=subcontract).exists():
        next_number = SubcontractorInvoice.objects.filter(subcontract=subcontract).latest(
            'pay_app_number').pay_app_number + 1
    else:
        next_number = 1
    if request.method == 'POST':
        if 'subcontract_note' in request.POST:
            invoice_total = 0
            invoice = SubcontractorInvoice.objects.create(date=date.today(), pay_app_number=next_number,
                                                          subcontract=subcontract, pay_date=friday)
            for x in SubcontractItems.objects.filter(subcontract=subcontract):
                if request.POST['quantity' + str(x.id)] != '':
                    SubcontractorInvoiceItem.objects.create(invoice=invoice, sov_item=x,
                                                            quantity=request.POST['quantity' + str(x.id)],
                                                            notes=request.POST['note' + str(x.id)])
                    SubcontractorOriginalInvoiceItem.objects.create(invoice=invoice, sov_item=x,
                                                                    quantity=request.POST['quantity' + str(x.id)],
                                                                    notes=request.POST['note' + str(x.id)])
                # elif request.POST['note' + str(x.id)] != '':
                #     SubcontractorInvoiceItem.objects.create(invoice=invoice, sov_item=x, quantity=0,
                #                                             notes=request.POST['note' + str(x.id)])
                #     SubcontractorOriginalInvoiceItem.objects.create(invoice=invoice, sov_item=x,
                #                                                     quantity=request.POST['quantity' + str(x.id)],
                #                                                     notes=request.POST['note' + str(x.id)])
            SubcontractNotes.objects.create(subcontract=subcontract, date=date.today(),
                                            user=Employees.objects.get(user=request.user),
                                            note="New Invoice- " + request.POST['subcontract_note'], invoice=invoice)
            # Email.sendEmail('test', 'test body', 'joe@gerloffpainting.com')

            for x in SubcontractorInvoiceItem.objects.filter(invoice=invoice):
                invoice_total += x.total_cost()
            invoice.final_amount = invoice_total
            if subcontract.is_retainage == True:
                invoice.retainage = invoice_total * subcontract.retainage_percentage
            else:
                invoice.retainage = 0

            # invoice.final_amount = invoice_total
            # if invoice.subcontract.is_retainage: invoice.retainage = float(invoice_total) * float(.1)
            invoice.save()
            InvoiceApprovals.objects.create(employee=Employees.objects.get(id=22), invoice=invoice)
            InvoiceApprovals.objects.create(employee=Employees.objects.get(id=18), invoice=invoice)
            if subcontract.job_number.superintendent:
                if subcontract.job_number.superintendent != Employees.objects.get(id=22):
                    InvoiceApprovals.objects.create(employee=subcontract.job_number.superintendent, invoice=invoice)
            return redirect('subcontract_invoices', subcontract_id=subcontract_id, item_id='ALL')
    return render(request, "subcontractor_invoice_new.html",
                  {'next_number': next_number, 'items': items, 'subcontract': subcontract})


def portal_invoice_new(request, subcontract_id):
    today = datetime.date.today()
    friday = today + datetime.timedelta((4 - today.weekday()) % 7)
    if today.weekday() == 4 or today.weekday() == 3 or today.weekday() == 2: friday = friday + timedelta(7)
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
    if SubcontractorInvoice.objects.filter(subcontract=subcontract).exists():
        next_number = SubcontractorInvoice.objects.filter(subcontract=subcontract).latest(
            'pay_app_number').pay_app_number + 1
    else:
        next_number = 1
    if request.method == 'POST':
        if 'subcontract_note' in request.POST:
            invoice_total = 0
            invoice = SubcontractorInvoice.objects.create(date=date.today(), pay_app_number=next_number,
                                                          subcontract=subcontract, pay_date=friday)
            for x in SubcontractItems.objects.filter(subcontract=subcontract):
                if request.POST['quantity' + str(x.id)] != '':
                    SubcontractorInvoiceItem.objects.create(invoice=invoice, sov_item=x,
                                                            quantity=request.POST['quantity' + str(x.id)],
                                                            notes=request.POST['note' + str(x.id)])
                    SubcontractorOriginalInvoiceItem.objects.create(invoice=invoice, sov_item=x,
                                                                    quantity=request.POST['quantity' + str(x.id)],
                                                                    notes=request.POST['note' + str(x.id)])
                    # if x.SOV_is_lump_sum:
                    #     invoice_total += float(request.POST['quantity' + str(x.id)])
                    # else:
                    #     invoice_total += float(request.POST['quantity' + str(x.id)]) * x.SOV_rate
                elif request.POST['note' + str(x.id)] != '':
                    SubcontractorInvoiceItem.objects.create(invoice=invoice, sov_item=x, quantity=0,
                                                            notes=request.POST['note' + str(x.id)])
                    SubcontractorOriginalInvoiceItem.objects.create(invoice=invoice, sov_item=x,
                                                                    quantity=request.POST['quantity' + str(x.id)],
                                                                    notes=request.POST['note' + str(x.id)])
            SubcontractNotes.objects.create(subcontract=subcontract, date=date.today(),
                                            user=Employees.objects.get(id=42),
                                            note="New Invoice From Portal- " + request.POST['subcontract_note'],
                                            invoice=invoice)
            for x in SubcontractorInvoiceItem.objects.filter(invoice=invoice):
                invoice_total += x.total_cost()
            invoice.final_amount = invoice_total
            if subcontract.is_retainage == True:
                invoice.retainage = invoice_total * subcontract.retainage_percentage
            else:
                invoice.retainage = 0
            # # Email.sendEmail('test', 'test body', 'joe@gerloffpainting.com')
            # invoice.final_amount = invoice_total
            # if invoice.subcontract.is_retainage: invoice.retainage = float(invoice_total) * float(.1)
            invoice.save()
            # 22 is victor.18 is gene.
            InvoiceApprovals.objects.create(employee=Employees.objects.get(id=22), invoice=invoice)
            InvoiceApprovals.objects.create(employee=Employees.objects.get(id=18), invoice=invoice)
            if subcontract.job_number.superintendent:
                if subcontract.job_number.superintendent != Employees.objects.get(id=22):
                    InvoiceApprovals.objects.create(employee=subcontract.job_number.superintendent, invoice=invoice)
            email_body = "New Invoice Entered For " + str(subcontract.subcontractor.company) + "\n Job: " + str(
                subcontract.job_number.job_name)
            Email.sendEmail("New invoice", email_body,
                            ['admin2@gerloffpainting.com', 'joe@gerloffpainting.com', 'bridgette@gerloffpainting.com'],
                            False)
            return redirect('portal', sub_id=subcontract.subcontractor.id, contract_id=subcontract_id)
    return render(request, "portal_invoice_new.html",
                  {'friday': friday, 'next_number': next_number, 'items': items, 'subcontract': subcontract})


@login_required(login_url='/accounts/login')
def subcontract_invoices(request, subcontract_id, item_id):
    send_data = {}
    subcontract = Subcontracts.objects.get(id=subcontract_id)
    send_data['subcontract'] = subcontract
    if request.method == 'POST':
        if 'edit_invoice' in request.POST:
            send_data['edit_now'] = True
        if 'other_approver' in request.POST:
            send_data['other_approve'] = InvoiceApprovals.objects.get(id=request.POST['other_approver'])
        if 'invoice_notes' in request.POST:
            selected_invoice = SubcontractorInvoice.objects.get(id=item_id)
            SubcontractNotes.objects.create(subcontract=subcontract, date=date.today(),
                                            user=Employees.objects.get(user=request.user),
                                            note=request.POST['invoice_notes'], invoice=selected_invoice)
            return redirect('subcontract_invoices', subcontract_id=subcontract_id, item_id=item_id)
        if 'reject_notes' in request.POST:
            selected_invoice = SubcontractorInvoice.objects.get(id=item_id)
            invoice = SubcontractorInvoice.objects.get(id=item_id)
            approvers = InvoiceApprovals.objects.filter(invoice=selected_invoice)
            current_employee = Employees.objects.get(user=request.user)
            if 'approved' in request.POST:
                invoicetotal = 0
                for x in SubcontractorInvoiceItem.objects.filter(invoice=selected_invoice):
                    invoicetotal = invoicetotal + x.total_cost()
                invoice.final_amount = invoicetotal
                approved = True
                if 'is_other_approver_id' in request.POST:
                    other_approval = InvoiceApprovals.objects.get(id=request.POST['is_other_approver_id'])
                    current_employee = other_approval.employee
                    note = "Invoice " + str(invoice.pay_app_number) + " Approved! On behalf of " + str(current_employee)
                else:
                    note = "Invoice " + str(invoice.pay_app_number) + " Approved!"
                for x in approvers:
                    if x.employee == current_employee:
                        x.is_approved = True
                        x.made_changes = False
                        x.date = date.today()
                        x.is_reviewed = True
                        x.save()
                    elif x.is_approved == False:
                        approved = False
                if approved == True: invoice.is_sent = True
                invoice.save()
                current_employee = Employees.objects.get(user=request.user)
                SubcontractNotes.objects.create(subcontract=subcontract, date=date.today(),
                                                user=current_employee,
                                                note=note,
                                                invoice=selected_invoice)
            else:  # rejected
                if 'is_other_approver_id' in request.POST:
                    other_approval = InvoiceApprovals.objects.get(id=request.POST['is_other_approver_id'])
                    current_employee = Employees.objects.get(id=other_approval.employee.id)

                    note = "Invoice " + str(
                        invoice.pay_app_number) + " Rejected! On behalf of: " + str(current_employee) + ". " + \
                           request.POST[
                               'reject_notes']
                else:
                    note = "Invoice " + str(
                        invoice.pay_app_number) + " Rejected! " + request.POST[
                               'reject_notes']
                for x in approvers:
                    if x.employee == current_employee:
                        x.is_approved = False
                        x.made_changes = False
                        x.date = date.today()
                        x.is_reviewed = True
                        x.save()
                current_employee = Employees.objects.get(user=request.user)
                SubcontractNotes.objects.create(subcontract=subcontract, date=date.today(),
                                                user=current_employee,
                                                note=note,
                                                invoice=selected_invoice)
                email_body = selected_invoice.subcontract.subcontractor.company + " invoice for " + selected_invoice.subcontract.job_number.job_name + " has been rejected by " + current_employee.first_name + ". " + \
                             request.POST['reject_notes']
                Email.sendEmail("Invoice Rejected", email_body,
                                ['admin2@gerloffpainting.com', 'joe@gerloffpainting.com', 'bridgette@gerloffpainting.com'], False)
            return redirect('subcontract_invoices', subcontract_id=subcontract_id, item_id=item_id)
        if 'form5' in request.POST:  # approved
            selected_invoice = SubcontractorInvoice.objects.get(id=item_id)
            invoice = SubcontractorInvoice.objects.get(id=item_id)
            invoicetotal = 0
            for x in SubcontractorInvoiceItem.objects.filter(invoice=selected_invoice):
                invoicetotal = invoicetotal + x.total_cost()
            invoice.final_amount = invoicetotal
            approvers = InvoiceApprovals.objects.filter(invoice=selected_invoice)
            approved = True
            current_employee = Employees.objects.get(user=request.user)
            if 'is_other_approver_id' in request.POST:
                other_approval = InvoiceApprovals.objects.get(id=request.POST['is_other_approver_id'])
                current_employee = Employees.objects.get(id=other_approval.employee.id)
                note = "Invoice " + str(invoice.pay_app_number) + " Approved! On behalf of " + str(current_employee)
            else:
                note = "Invoice " + str(invoice.pay_app_number) + " Approved!"
            for x in approvers:
                if x.employee == current_employee:
                    x.is_approved = True
                    x.made_changes = False
                    x.date = date.today()
                    x.is_reviewed = True
                    x.save()
                elif x.is_approved == False:
                    approved = False
            if approved == True:
                invoice.is_sent = True
                email_body = selected_invoice.subcontract.subcontractor.company + " invoice for " + selected_invoice.subcontract.job_number.job_name + " has been approved."
                Email.sendEmail("Invoice Approved", email_body,
                                ['admin2@gerloffpainting.com', 'joe@gerloffpainting.com', 'bridgette@gerloffpainting.com'], False)
            invoice.save()
            current_employee = Employees.objects.get(user=request.user)
            SubcontractNotes.objects.create(subcontract=subcontract, date=date.today(),
                                            user=current_employee,
                                            note=note,
                                            invoice=selected_invoice)
            return redirect('subcontract_invoices', subcontract_id=subcontract_id, item_id=item_id)
        if 'change_notes' in request.POST:  # approved with changes
            selected_invoice = SubcontractorInvoice.objects.get(id=item_id)
            invoice = SubcontractorInvoice.objects.get(id=item_id)
            invoicetotal = 0
            note2=""
            for x in SubcontractItems.objects.filter(subcontract=subcontract):
                if request.POST['quantity' + str(x.id)] != '':
                    if SubcontractorInvoiceItem.objects.filter(invoice=invoice, sov_item=x).exists():
                        item = SubcontractorInvoiceItem.objects.get(invoice=invoice, sov_item=x)
                        if item.quantity != request.POST['quantity' + str(x.id)]:
                            note2 += x.SOV_description + "- changed from " + str(item.quantity) + " to " + str(request.POST['quantity' + str(x.id)]) + ". "
                        item.quantity = request.POST['quantity' + str(x.id)]
                        item.notes = request.POST['note' + str(x.id)]
                        item.save()
                    else:
                        SubcontractorInvoiceItem.objects.create(invoice=invoice, sov_item=x,
                                                                quantity=request.POST['quantity' + str(x.id)],
                                                                notes=request.POST['note' + str(x.id)])
                        note2 += x.SOV_description + "- added to invoice. Quantity: " + str(request.POST['quantity' + str(x.id)]) + ". "
                else:
                    if SubcontractorInvoiceItem.objects.filter(invoice=invoice, sov_item=x).exists():
                        item = SubcontractorInvoiceItem.objects.get(invoice=invoice, sov_item=x)
                        if item.quantity != 0:
                            note2 += x.SOV_description + "- changed from " + str(item.quantity) + " to 0. "
                        item.quantity = 0
                        item.notes = request.POST['note' + str(x.id)]
                        item.save()
            for x in SubcontractorInvoiceItem.objects.filter(invoice=selected_invoice):
                invoicetotal = invoicetotal + x.total_cost()
            invoice.final_amount = invoicetotal
            invoice.retainage = request.POST['this_retainage']
            approvers = InvoiceApprovals.objects.filter(invoice=selected_invoice)
            approved = True
            current_employee = Employees.objects.get(user=request.user)
            invoice.save()
            if 'is_other_approver_id' in request.POST:
                other_approval = InvoiceApprovals.objects.get(id=request.POST['is_other_approver_id'])
                current_employee = Employees.objects.get(id=other_approval.employee.id)
                note = "Invoice " + str(invoice.pay_app_number) + " Approved - Made Changes! On behalf of " + str(
                    current_employee) + ". " + note2 + ". " + request.POST['change_notes']
            elif 'editing_now' in request.POST:
                note = "Invoice " + str(invoice.pay_app_number) + " Edited. " + note2 + ". " + request.POST[
                    'change_notes']
            else:
                note = "Invoice " + str(invoice.pay_app_number) + " Approved - Made Changes! " + note2 + ". " + request.POST[
                    'change_notes']
            if 'editing_now' not in request.POST:
                for x in approvers:
                    if x.employee == current_employee:
                        x.is_approved = True
                        x.made_changes = True
                        x.date = date.today()
                        x.is_reviewed = True
                        x.save()
                    elif x.is_approved == False:
                        approved = False
                if approved == True:
                    email_body = selected_invoice.subcontract.subcontractor.company + " invoice for " + selected_invoice.subcontract.job_number.job_name + " has been approved."
                    Email.sendEmail("Invoice Approved", email_body,
                                    ['admin2@gerloffpainting.com', 'joe@gerloffpainting.com', 'bridgette@gerloffpainting.com'], False)
                    invoice.is_sent = True
            invoice.save()
            current_employee = Employees.objects.get(user=request.user)
            SubcontractNotes.objects.create(subcontract=subcontract, date=date.today(),
                                            user=current_employee,
                                            note=note,
                                            invoice=selected_invoice)
            return redirect('subcontract_invoices', subcontract_id=subcontract_id, item_id=item_id)
    if item_id == 'ALL':
        invoices = SubcontractorInvoice.objects.filter(subcontract=subcontract)
        send_data['invoices'] = invoices
    else:
        items = []
        invoices = SubcontractorInvoice.objects.filter(id=item_id)
        send_data['invoices'] = invoices
        selected_invoice = SubcontractorInvoice.objects.get(id=item_id)
        send_data['selected_invoice'] = selected_invoice
        invoice_items = SubcontractorInvoiceItem.objects.filter(invoice=selected_invoice)
        send_data['invoice_items'] = invoice_items
        notes = SubcontractNotes.objects.filter(subcontract=subcontract, invoice=selected_invoice)
        send_data['notes'] = notes
        other_retainage=0
        previously_billed=0
        for x in SubcontractorInvoice.objects.filter(subcontract=subcontract).exclude(id=item_id):
            if x.retainage: other_retainage += x.retainage
            if x.final_amount: previously_billed += x.final_amount
        send_data['previously_billed'] = previously_billed
        send_data['total_billed'] = previously_billed + selected_invoice.final_amount
        send_data['other_retainage'] = other_retainage
        send_data['total_retainage'] = other_retainage + selected_invoice.retainage
        send_data['total_contract'] = subcontract.total_contract_amount()
        if InvoiceApprovals.objects.filter(employee=Employees.objects.get(user=request.user), invoice=selected_invoice,
                                           is_approved=False).exists():
            send_data['me_approve'] = True
        elif InvoiceApprovals.objects.filter(invoice=selected_invoice, is_approved=False).exists():
            send_data['other_approvers'] = InvoiceApprovals.objects.filter(invoice=selected_invoice, is_approved=False)
        approvalcheck = InvoiceApprovals.objects.filter(invoice=selected_invoice, is_approved=True)
        if not approvalcheck:
            send_data['no_approvals_yet'] = True
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
            send_data['items'] = items
        return render(request, "subcontract_invoices.html", send_data)
    return render(request, "subcontract_invoices.html", send_data)


@login_required(login_url='/accounts/login')
def subcontractor_home(request):
    if request.method == 'POST':
        subcontractor = Subcontractors.objects.get(id=request.POST['subcontractor_id'])
        if 'contact' in request.POST:
            subcontractor.contact = request.POST['contact']
            subcontractor.phone = request.POST['phone']
            subcontractor.email = request.POST['email']
            subcontractor.notes = request.POST['notes']
        if 'is_inactive' in request.POST:
            subcontractor.is_inactive = True
        subcontractor.save()
        if 'insurance' in request.POST:
            if request.POST['insurance'] != "":
                subcontractor.insurance_expire_date = request.POST['insurance']
            if request.POST['w9_form_date'] != "":
                subcontractor.w9_form_date = request.POST['w9_form_date']
            if request.POST['business_license_expiration_date'] != "":
                subcontractor.business_license_expiration_date = request.POST['business_license_expiration_date']
            if 'has_workers_comp' in request.POST: subcontractor.has_workers_comp = True
            else: subcontractor.has_workers_comp = False
            if 'has_auto_insurance' in request.POST: subcontractor.has_auto_insurance = True
            else: subcontractor.has_auto_insurance = False
            if 'has_w9_form' in request.POST: subcontractor.has_w9_form = True
            else: subcontractor.has_w9_form = False
            if 'has_business_license' in request.POST: subcontractor.has_business_license = True
            else: subcontractor.has_business_license = False
            if 'is_signed_labor_agreement' in request.POST: subcontractor.is_signed_labor_agreement = True
            else: subcontractor.is_signed_labor_agreement = False
        subcontractor.save()
        if 'go_back_to_subcontracts' in request.POST:
            return redirect('subcontracts_home')
        if 'go_back_to_subcontract' in request.POST:
            return redirect('subcontract', id=request.POST['go_back_to_subcontract'])
        return redirect('subcontractor_home')
    send_data = {}
    subcontractors = []
    for x in Subcontractors.objects.filter(is_inactive=False):
        subcontractors.append({'id': x.id, 'company': x.company, 'active_contracts': x.active_contracts(),
                               'pending_invoices': x.pending_invoices()})
    send_data['subcontractors'] = subcontractors
    send_data['subcontractor_count'] = Subcontractors.objects.filter(is_inactive=False).count()
    send_data['contracts_count'] = Subcontracts.objects.filter(is_closed=False).count()
    send_data['approvals_count'] = SubcontractorInvoice.objects.filter(is_sent=False).count()
    send_data['approved'] = SubcontractorInvoice.objects.filter(is_sent=True, processed=False)
    send_data['approved_count'] = SubcontractorInvoice.objects.filter(is_sent=True, processed=False).count()
    all_invoices = []
    for x in SubcontractorInvoice.objects.filter(is_sent=False):
        all_invoices.append({'contract_id': x.subcontract.id, 'id': x.id, 'job_name': x.subcontract.job_number.job_name,
                             'company': x.subcontract.subcontractor, 'amount': x.final_amount,
                             'approvals_needed': x.approvals_needed(), 'pay_date': x.pay_date,
                             'number': x.pay_app_number})
    send_data['all_invoices'] = all_invoices
    my_invoices = []
    my_approvals_count = 0
    for x in SubcontractorInvoice.objects.filter(is_sent=False):
        if InvoiceApprovals.objects.filter(invoice=x, employee=Employees.objects.get(user=request.user),
                                           is_approved=False).exists():
            my_approvals_count += 1
            my_invoices.append(
                {'contract_id': x.subcontract.id, 'id': x.id, 'job_name': x.subcontract.job_number.job_name,
                 'company': x.subcontract.subcontractor, 'amount': x.final_amount,
                 'approvals_needed': x.approvals_needed(), 'pay_date': x.pay_date, 'number': x.pay_app_number})
    send_data['my_approvals_count'] = my_approvals_count
    send_data['my_invoices'] = my_invoices
    return render(request, "subcontractor_home.html", send_data)


@login_required(login_url='/accounts/login')
def subcontract(request, id):
    send_data = {}
    subcontract = Subcontracts.objects.get(id=id)
    send_data['invoices'] = SubcontractorInvoice.objects.filter(subcontract=subcontract).order_by('id')
    items = []
    number_items = 0
    for x in SubcontractItems.objects.filter(subcontract=subcontract).order_by('id'):
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
    send_data['total_billed'] = subcontract.total_billed()
    send_data['total_contract']=subcontract.total_contract_amount()
    send_data['total_retainage'] =subcontract.total_retainage()
    send_data['total_pending'] = subcontract.total_pending_amount()
    send_data['total_billed_and_pending'] = float(subcontract.total_pending_amount())+float(subcontract.total_billed())
    send_data['total_retainage_pending'] = subcontract.total_retainage_pending()
    send_data['final_retainage'] = float(subcontract.total_retainage_pending())+float(subcontract.total_retainage())
    if subcontract.invoice_pending(): send_data['is_invoice_pending']=True
    if Wallcovering.objects.filter(job_number=subcontract.job_number):
        wallcovering = Wallcovering.objects.filter(job_number=subcontract.job_number)
        wallcovering_json1 = []
        for x in wallcovering:
            wallcovering_json1.append(
                {'id': x.id, 'code': x.code, 'vendor': x.vendor.company_name, 'pattern': x.pattern,
                 'estimated_unit': x.estimated_unit, 'quantity_ordered': int(x.quantity_ordered())})
        send_data['wallcovering_json'] = json.dumps(list(wallcovering_json1), cls=DjangoJSONEncoder)
    if request.method == 'POST':
        if 'retainage_released' in request.POST:
            today = datetime.date.today()
            friday = today + datetime.timedelta((4 - today.weekday()) % 7)
            if SubcontractorInvoice.objects.filter(subcontract=subcontract).exists():
                next_number = SubcontractorInvoice.objects.filter(subcontract=subcontract).latest(
                    'pay_app_number').pay_app_number + 1
            else:
                next_number = 1
            if today.weekday() == 4 or today.weekday() == 3 or today.weekday() == 2: friday = friday + timedelta(7)
            invoice = SubcontractorInvoice.objects.create(date=date.today(), pay_app_number=next_number,
                                                          subcontract=subcontract, pay_date=friday,final_amount=0,retainage=0-float(request.POST['retainage_released']),notes=request.POST['new_note'])
            SubcontractNotes.objects.create(subcontract=subcontract, date=date.today(),
                                            user=Employees.objects.get(user=request.user),
                                            note="Retainage released- " + request.POST['new_note'], invoice=invoice)
            InvoiceApprovals.objects.create(employee=Employees.objects.get(id=22), invoice=invoice)
            InvoiceApprovals.objects.create(employee=Employees.objects.get(id=18), invoice=invoice)
            if subcontract.job_number.superintendent != Employees.objects.get(id=22):
                InvoiceApprovals.objects.create(employee=subcontract.job_number.superintendent, invoice=invoice)
            return redirect('subcontract',id=id)
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
            if request.POST['po_number'] == "":
                nextPO = PurchaseOrderNumber.objects.get(id=1)
                po_number = "TR" + str(nextPO.next_po_number)
                nextPO.next_po_number += 1
                nextPO.save()
            else:
                po_number = request.POST['po_number']
            subcontract1 = Subcontracts.objects.create(
                job_number=Jobs.objects.get(job_number=request.POST['selected_job']),
                subcontractor=Subcontractors.objects.get(id=request.POST['select_subcontractor']),
                po_number=po_number, date=date.today(), retainage_percentage=0, is_retainage=False)
            SubcontractNotes.objects.create(subcontract=subcontract1, date=date.today(),
                                            user=Employees.objects.get(user=request.user),
                                            note="New Contract- " + request.POST['subcontract_notes'])
            message = "New Subcontract for " + subcontract1.subcontractor.company + "\n Job: " + subcontract1.job_number.job_name + "\n PO #: " + subcontract1.po_number
            Email.sendEmail("New Subcontract", message, ['joe@gerloffpainting.com', 'admin2@gerloffpainting.com', 'bridgette@gerloffpainting.com'],
                            False)
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
            send_data['jobs'] = Jobs.objects.filter(is_closed=False)
    else:
        send_data['jobs'] = Jobs.objects.filter(is_closed=False)

    return render(request, "subcontracts_new.html", send_data)


@login_required(login_url='/accounts/login')
def subcontracts_home(request):
    if request.method == 'POST':
        if request.POST['subcontract_id'] != "":
            return redirect('subcontract', id=request.POST['subcontract_id'])
        if request.POST['job_number'] != "":
            return redirect('job_page', jobnumber=request.POST['job_number'])
    subcontracts = []
    for x in Subcontracts.objects.filter(is_closed=False):  # str(format(x.percent_complete(),".0%"))
        subcontracts.append({'job_name': x.job_number.job_name, 'job_number': x.job_number.job_number,
                             'subcontractor': x.subcontractor.company, 'subcontractor_id': x.subcontractor.id,
                             'po_number': x.po_number, 'id': x.id, 'retainage': x.total_retainage(),
                             'percent_complete': format(x.percent_complete(), ".0%")})
    return render(request, "subcontracts_home.html", {'subcontracts': subcontracts})


def subcontractor_payments(request):
    send_data = {}
    send_data['payments'] = SubcontractorPayments.objects.all().order_by('date')
    if request.method == 'POST':
        if 'new_payment' in request.POST:
            return redirect('new_subcontractor_payment')
    return render(request, "subcontractor_payments.html", send_data)


def new_subcontractor_payment(request):
    send_data = {}
    if request.method == 'POST':
        send_data['selected_sub'] = request.POST['select_subcontractor']
        selected_sub = Subcontractors.objects.get(id=request.POST['select_subcontractor'])
        if 'check_number' in request.POST:
            if InvoiceBatch.objects.filter(invoice__subcontract__subcontractor=selected_sub, invoice__is_sent=True,
                                           invoice__processed=False).exists():
                payment = SubcontractorPayments.objects.create(subcontractor=selected_sub,
                                                               date=request.POST['pay_date'],
                                                               check_number=request.POST['check_number'],
                                                               final_amount=request.POST['final_amount'],
                                                               notes=request.POST['note'])
                for x in InvoiceBatch.objects.filter(invoice__subcontract__subcontractor=selected_sub,
                                                     invoice__is_sent=True, invoice__processed=False):
                    selected_invoice = x.invoice
                    selected_invoice.processed = True
                    selected_invoice.payment = payment
                    selected_invoice.save()
                    SubcontractNotes.objects.create(subcontract=selected_invoice.subcontract, date=date.today(),
                                                    user=Employees.objects.get(user=request.user),
                                                    note="Invoice Paid on " + str(request.POST['pay_date']) + ". " +
                                                         request.POST['note'],
                                                    invoice=selected_invoice)
                InvoiceBatch.objects.all().delete()

            return redirect('subcontractor_payments')
        if 'selected_invoice' in request.POST:
            InvoiceBatch.objects.create(invoice=SubcontractorInvoice.objects.get(id=request.POST['selected_invoice']))
        if 'remove_invoice' in request.POST:
            InvoiceBatch.objects.get(id=request.POST['remove_invoice']).delete()
        invoices = []
        for x in SubcontractorInvoice.objects.filter(subcontract__subcontractor=selected_sub, is_sent=True,
                                                     processed=False, batch__isnull=True):
            invoices.append(
                {'total': x.final_amount, 'retainage': x.retainage, 'id': x.id, 'pay_app_number': x.pay_app_number,
                 'job_name': x.subcontract.job_number.job_name, 'amount': x.final_amount - x.retainage,
                 'pay_date': x.pay_date})
        send_data['invoices'] = invoices
        selected_invoices = []
        final_amount = 0
        for x in InvoiceBatch.objects.filter(invoice__subcontract__subcontractor=selected_sub, invoice__is_sent=True,
                                             invoice__processed=False):
            selected_invoices.append({'total': x.invoice.final_amount, 'retainage': x.invoice.retainage, 'id': x.id,
                                      'pay_app_number': x.invoice.pay_app_number,
                                      'job_name': x.invoice.subcontract.job_number.job_name,
                                      'amount': x.invoice.final_amount - x.invoice.retainage,
                                      'pay_date': x.invoice.pay_date})
            final_amount += x.invoice.final_amount - x.invoice.retainage
        send_data['final_amount'] = final_amount
        send_data['selected_invoices'] = selected_invoices
        return render(request, "new_subcontractor_payment.html", send_data)
    else:
        InvoiceBatch.objects.all().delete()
    subcontractors = []
    for x in Subcontractors.objects.all():
        if x.needs_payment() == True:
            print(x.company)
            subcontractors.append({'id': x.id, 'company': x.company})
    send_data['subcontractors'] = subcontractors
    return render(request, "new_subcontractor_payment.html", send_data)
