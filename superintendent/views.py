from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from rentals.models import Rentals
from datetime import date, timedelta
from employees.models import Employees
from jobs.models import Jobs, JobNotes, ClientEmployees
from changeorder.models import ChangeOrders
from equipment.models import *
from console.models import *
from subcontractors.models import *
from django.db.models import Q
from equipment.filters import JobsFilter2
from django.http import HttpResponse
from jobs.JobMisc import start_date_change, gerloff_super_change, open_dropbox, dropbox3, dropbox2
import json
from django.shortcuts import render, redirect


def super_ajax(request):
    if request.is_ajax():
        if 'payment_id' in request.GET:
            send_data = {}
            payment = SubcontractorPayments.objects.get(id=request.GET['payment_id'])
            invoices = []
            for x in SubcontractorInvoice.objects.filter(payment=payment):
                invoices.append({'contract_id':x.subcontract.id,'id':x.id,'job':x.subcontract.job_number.job_name,'number':x.pay_app_number,'amount':str(x.final_amount-x.retainage)})
            send_data['invoices']=invoices
            return HttpResponse(json.dumps(send_data))
        if 'invoice_id' in request.GET:
            send_data = {}
            selected_invoice = SubcontractorInvoice.objects.get(id=request.GET['invoice_id'])
            send_data['invoice_number'] = str(selected_invoice.pay_app_number)
            sovs = []
            for x in SubcontractItems.objects.filter(subcontract=selected_invoice.subcontract):
                if SubcontractorInvoiceItem.objects.filter(invoice=selected_invoice,sov_item=x).exists():
                    final_item = SubcontractorInvoiceItem.objects.get(invoice=selected_invoice,sov_item=x)
                    final_quantity = f"{int(final_item.quantity):,d}"
                else:
                    final_quantity = 0
                if SubcontractorOriginalInvoiceItem.objects.filter(invoice=selected_invoice,sov_item=x).exists():
                    original_item = SubcontractorOriginalInvoiceItem.objects.get(invoice=selected_invoice,sov_item=x)
                    original_quantity = f"{int(original_item.quantity):,d}"
                else:
                    original_quantity = 0
                sovs.append({'item': x.SOV_description, 'billed': final_quantity,'unit': str(x.SOV_unit), 'original': original_quantity})
            if selected_invoice.original_retainage_amount:
                sovs.append({'item': "Retainage", 'billed': f"{int(0-selected_invoice.retainage):,d}",'unit': "Lump Sum", 'original': f"{int(0-selected_invoice.original_retainage_amount):,d}"})
            else:
                sovs.append({'item': "Retainage", 'billed': f"{int(0-selected_invoice.retainage):,d}", 'unit': "Lump Sum",
                             'original': f"{int(0):,d}"})
            notes = []
            for x in SubcontractNotes.objects.filter(invoice=selected_invoice):
                notes.append({'date':str(x.date),'user':str(x.user),'note':x.note})
            send_data['notes']=notes
            # for x in SubcontractorInvoiceItem.objects.filter(invoice=selected_invoice):
            #     sovs.append({'item': x.sov_item.SOV_description, 'quantity': f"{int(x.quantity):,d}",
            #                  'unit': str(x.sov_item.SOV_unit)})
            # orig_sovs = []
            # for x in SubcontractorOriginalInvoiceItem.objects.filter(invoice=selected_invoice):
            #     orig_sovs.append(
            #         {'item': x.sov_item.SOV_description, 'quantity': str(x.quantity), 'unit': str(x.sov_item.SOV_unit)})
            send_data['sovs'] = sovs
            # send_data['orig_sovs'] = orig_sovs
            return HttpResponse(json.dumps(send_data))
        if 'pending_invoices' in request.GET:
            send_data = {}
            subcontractor = Subcontractors.objects.get(id=request.GET['subcontractor_id'])
            invoices = SubcontractorInvoice.objects.filter(subcontract__subcontractor=subcontractor, is_sent=False)
            pending_invoices = []
            send_data['company'] = subcontractor.company
            for x in invoices:
                pending_invoices.append(
                    {'job_number': x.subcontract.job_number.job_number, 'job_name': x.subcontract.job_number.job_name,
                     'pay_app_number': x.pay_app_number,
                     'date': str(x.pay_date), 'id': x.id, 'subcontract_id': x.subcontract.id})
            send_data['pending_invoices'] = pending_invoices
            return HttpResponse(json.dumps(send_data))
        if 'pending_approvals' in request.GET:
            send_data = {}
            selected_invoice = SubcontractorInvoice.objects.get(id=request.GET['selected_invoice_id'])
            approvals_needed = InvoiceApprovals.objects.filter(invoice=selected_invoice)
            approval_status = []
            for x in approvals_needed:
                if x.is_approved:
                    approved="YES"
                    if x.made_changes:
                        changes = "YES"
                    else:
                        changes = "NO"
                else:
                    if x.is_reviewed:
                        approved="REJECTED"
                        changes=""
                    else:
                        approved="NO"
                        changes=""
                approval_status.append(
                    {'employee': x.employee.first_name, 'approved': approved, 'changes': changes})
            send_data['approval_status'] = approval_status
            return HttpResponse(json.dumps(send_data))
        if 'active_contracts' in request.GET:
            send_data = {}
            subcontractor = Subcontractors.objects.get(id=request.GET['subcontractor_id'])
            contracts = Subcontracts.objects.filter(subcontractor=subcontractor, is_closed=False)
            active_contracts = []
            send_data['company'] = subcontractor.company
            for x in contracts:
                active_contracts.append(
                    {'job_number': x.job_number.job_number, 'job_name': x.job_number.job_name, 'po_number': x.po_number,
                     'date': str(x.date), 'id': x.id, 'percent_complete': str(format(x.percent_complete(), ".0%"))})
            send_data['active_contracts'] = active_contracts
            return HttpResponse(json.dumps(send_data))
        if 'subcontractor_id' in request.GET:
            subcontractor = Subcontractors.objects.get(id=request.GET['subcontractor_id'])
            send_data = {}
            send_data['company'] = subcontractor.company
            send_data['id'] = subcontractor.id
            approvers = []
            for x in Subcontractor_Approvers.objects.filter(subcontractor=subcontractor):
                if x.employee:
                    approvers.append({'id': x.id, 'approver': str(x.employee)})
                if x.job_description:
                    approvers.append({'id': x.id, 'approver': str(x.job_description)})
            # employees = []
            # for x in Employees.objects.all():
            #     employees.append({'name':str(x)})
            # send_data['employees']=employees
            send_data['approvers'] = approvers
            if subcontractor.contact: send_data['contact'] = subcontractor.contact
            if subcontractor.phone: send_data['phone'] = subcontractor.phone
            if subcontractor.email: send_data['email'] = subcontractor.email
            if subcontractor.insurance_expire_date: send_data['insurance'] = str(subcontractor.insurance_expire_date)
            if subcontractor.notes: send_data['notes'] = subcontractor.notes
            if subcontractor.business_license_expiration_date: send_data['business_license_expiration_date'] = str(subcontractor.business_license_expiration_date)
            if subcontractor.w9_form_date: send_data['w9_form_date'] = str(subcontractor.w9_form_date)
            if subcontractor.has_workers_comp: send_data['has_workers_comp'] = subcontractor.has_workers_comp
            if subcontractor.has_auto_insurance: send_data['has_auto_insurance'] = subcontractor.has_auto_insurance
            if subcontractor.has_business_license: send_data['has_business_license'] = subcontractor.has_business_license
            if subcontractor.has_w9_form: send_data['has_w9_form'] = subcontractor.has_w9_form
            if subcontractor.is_signed_labor_agreement: send_data['is_signed_labor_agreement'] = True
            return HttpResponse(json.dumps(send_data))
        if 'dropbox' in request.GET:
            # dropbox2()
            # dropbox2 was old code to get an authorization code
            # print(dropbox3())
            # dropbox3 was to get refresh code from authorization code. i put this refresh code into the open_dropbox() function
            # return HttpResponse()
            return HttpResponse(open_dropbox(request.GET['job_number'], request.user))
        if 'client_employee_id' in request.GET:
            person = ClientEmployees.objects.get(person_pk=request.GET['client_employee_id'])
            data_details = {'phone': person.phone, 'email': person.email, 'name': person.name}
            return HttpResponse(json.dumps(data_details))
        if 'select_super' in request.GET:
            job = Jobs.objects.get(job_number=request.GET['job_number'])
            super = Employees.objects.get(id=request.GET['select_super'])
            email_sent = gerloff_super_change(job, super, Employees.objects.get(user=request.user))
            send_data = {}
            send_data['email_sent']=email_sent
            send_data['super_first_name']=super.first_name
            return HttpResponse(json.dumps(send_data))
        if 'build_notes' in request.GET:
            job = Jobs.objects.get(job_number=request.GET['job_number'])
            job_notes = JobNotes.objects.filter(Q(type="auto_start_date_note") | Q(type="employee_note"),
                                                job_number=job)
            send_data={}
            send_data['job_name']=job.job_name
            send_data['start_date'] = job.start_date.strftime("%Y-%m-%d")
            notes = []
            for x in job_notes:
                notes.append({'note': x.note, 'user': str(x.user),
                              'date': str(x.date)})
            send_data['notes']=notes
            data_details = {'notes': notes}
            return HttpResponse(json.dumps(send_data))
        elif 'filter_type' in request.GET:
            return redirect('super_home', super=request.GET['selected_super'])
        else:

            job = Jobs.objects.get(job_number=request.GET['job_number'])
            if job.is_active == True:
                if request.GET['is_active'] == "true":
                    status = 3
                else:
                    status = 2
            else:
                if request.GET['is_active'] == "true":
                    status = 1
                else:
                    status = 3
            if str(job.start_date) != str(request.GET['start_date']):
                datechange = True
            else:
                datechange = False
            if request.GET['notify'] == "true":
                notify = True
            else:
                notify = False
            email_sent = start_date_change(job, request.GET['start_date'], status, request.GET['notes'],
                              Employees.objects.get(user=request.user), datechange, notify)
            job.save()
            new_date = Jobs.objects.get(job_number=request.GET['job_number']).start_date

            new_date = Jobs.objects.get(job_number=request.GET['job_number']).start_date.strftime("%b-%d-%Y")
            # new_date = str(Jobs.objects.get(job_number=request.GET['job_number']).start_date)
            data_details = {'new_date': new_date, 'is_active': request.GET['is_active'],'email_sent':email_sent}
            return HttpResponse(json.dumps(data_details))


@login_required(login_url='/accounts/login')
def super_home(request, super):
    send_data = {}
    special = False
    if super == 'AUTO':
        employee = Employees.objects.get(user=request.user)
        if employee.job_title.description == "Superintendent":
            super = employee.id
            special = True
        else:
            super = 'ALL'
            special = False
    selected_superid = super  # selected_superid = either 'ALL' or the ID of super
    if request.method == 'GET':
        if 'is_button_collapsed' in request.GET:
            if request.GET['is_button_collapsed'] == "NO":
                send_data['open_button'] = "TRUE"
        if 'search' in request.GET: send_data['search_exists'] = request.GET['search']  # jobname
        if 'search2' in request.GET:
            send_data['search2_exists'] = request.GET['search2']  # super name
            if request.GET['search2'] == 'ALL':
                selected_superid = 'ALL'
            elif request.GET['search2'] == 'UNASSIGNED':
                selected_superid = 'UNASSIGNED'
            else:
                selected_superid = request.GET['search2']
        if 'search3' in request.GET: send_data['search3_exists'] = request.GET['search3']  # open only
        if 'search4' in request.GET: send_data['search4_exists'] = request.GET['search4']  # gc name
        if 'search5' in request.GET: send_data['search5_exists'] = request.GET['search5']  # upcoming only
        if 'search6' in request.GET: send_data['search6_exists'] = request.GET['search6']
        if 'search7' in request.GET: send_data['search7_exists'] = request.GET['search7']  # unassigned
        if 'search8' in request.GET: send_data['search8_exists'] = request.GET['search8']  # unassigned
    if selected_superid == 'ALL' or selected_superid == 'UNASSIGNED':
        send_data['filter_status'] = selected_superid
        send_data['equipment'] = Inventory.objects.filter(is_closed=False).exclude(job_number=None).order_by('job_number')
        send_data['equipment_count'] = Inventory.objects.filter(is_closed=False).exclude(job_number=None).count()
        send_data['rentals'] = Rentals.objects.filter(off_rent_number__isnull=True)
        send_data['rentals_count'] = Rentals.objects.filter(off_rent_number__isnull=True).count()
        send_data['tickets'] = ChangeOrders.objects.filter(is_t_and_m=True, is_ticket_signed=False, is_closed=False)
        send_data['tickets_count'] = ChangeOrders.objects.filter(is_t_and_m=True, is_ticket_signed=False,
                                                                 is_closed=False).count()
        send_data['subcontracts_count'] = Subcontracts.objects.filter(is_closed=False,
                                                                      job_number__is_closed=False).count()
        subcontracts = []
        for x in Subcontracts.objects.filter(job_number__is_closed=False, is_closed=False):
            total_contract = "{:,}".format(int(x.total_contract_amount()))
            percent_complete = format(x.percent_complete(), ".0%")
            subcontracts.append({'id': x.id, 'job_name': x.job_number.job_name, 'po_number': x.po_number,
                                 'subcontractor': x.subcontractor.company,
                                 'total_contract': total_contract, 'percent_complete': percent_complete})
        send_data['subcontracts'] = subcontracts
        search_jobs = JobsFilter2(request.GET, queryset=Jobs.objects.filter(is_closed=False, is_labor_done=False))
    else:
        selected_super = Employees.objects.get(id=selected_superid)
        send_data['subcontracts_count'] = Subcontracts.objects.filter(is_closed=False,
                                                                      job_number__is_closed=False,
                                                                      job_number__superintendent=selected_super).count()
        subcontracts = []
        for x in Subcontracts.objects.filter(job_number__superintendent=selected_super, job_number__is_closed=False,
                                             is_closed=False):
            total_contract = "{:,}".format(int(x.total_contract_amount()))
            percent_complete = format(x.percent_complete(), ".0%")
            subcontracts.append({'id': x.id, 'job_name': x.job_number.job_name, 'po_number': x.po_number,
                                 'subcontractor': x.subcontractor.company,
                                 'total_contract': total_contract, 'percent_complete': percent_complete})
        send_data['subcontracts'] = subcontracts
        send_data['equipment'] = Inventory.objects.filter(job_number__superintendent=selected_super,is_closed=False).order_by(
            'job_number', 'inventory_type')
        send_data['equipment_count'] = Inventory.objects.filter(job_number__superintendent=selected_super,is_closed=False).order_by(
            'job_number', 'inventory_type').count()
        send_data['selected_super'] = selected_super
        send_data['rentals'] = Rentals.objects.filter(job_number__superintendent=selected_super,
                                                      off_rent_number__isnull=True).order_by('job_number')
        send_data['rentals_count'] = Rentals.objects.filter(job_number__superintendent=selected_super,
                                                            off_rent_number__isnull=True).order_by('job_number').count()
        send_data['tickets'] = ChangeOrders.objects.filter(is_t_and_m=True, is_ticket_signed=False, is_closed=False,
                                                           job_number__superintendent=selected_super).order_by(
            'job_number', 'cop_number')
        send_data['tickets_count'] = ChangeOrders.objects.filter(is_t_and_m=True, is_ticket_signed=False,
                                                                 is_closed=False,
                                                                 job_number__superintendent=selected_super).order_by(
            'job_number', 'cop_number').count()
        if special == True:
            search_jobs = JobsFilter2(request.GET,
                                      queryset=Jobs.objects.filter(is_closed=False, superintendent=selected_super,
                                                                   is_labor_done=False))
        else:
            search_jobs = JobsFilter2(request.GET, queryset=Jobs.objects.filter(is_closed=False, is_labor_done=False))

    if any(field in request.GET for field in set(search_jobs.get_fields())) == True:
        send_data['has_filter'] = True
    send_data['search_jobs'] = search_jobs
    send_data['jobs'] = search_jobs.qs.order_by('start_date')
    send_data['jobs_count'] = search_jobs.qs.count()
    send_data['supers'] = Employees.objects.filter(job_title__description="Superintendent", active=True)
    send_data['todays_date'] = date.today() - timedelta(days=45)
    return render(request, "super_home.html", send_data)


@login_required(login_url='/accounts/login')
def filter_super(request):  # I DONT THINK THIS IS USED ANYWHERE
    if request.method == 'POST':
        jobs = Jobs.objects.filter(superintendent=request.POST['selected_super'])[0:2000]
        supers = Employees.objects.all()[0:2000]
        selected_super = Employees.objects.get(id=request.POST['selected_super'])
        equipment = Inventory.objects.filter(job_number__superintendent=selected_super,is_closed=False)
        rentals = Rentals.objects.filter(job_number__superintendent=selected_super, off_rent_number__isnull=True)
        # equipment = []
        # for x in equipmentlist:
        #        equipjobnumber = x.job_number.job_number
        #        if Jobs.objects.filter(job_number = equipjobnumber,superintendent=request.POST['selected_super']).exists():
        #            equipment.append(x)
        return render(request, "super_home.html",
                      {'rentals': rentals, 'selected_super': selected_super, 'jobs': jobs, 'supers': supers,
                       "equipment": equipment})
