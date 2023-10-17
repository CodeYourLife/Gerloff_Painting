from django.contrib.auth.decorators import login_required
from changeorder.models import ClientJobRoles
from console.models import *
from django.shortcuts import render, redirect
import json
from django.core.serializers.json import DjangoJSONEncoder
from datetime import date
from changeorder.models import ChangeOrders
from equipment.tables import JobsTable
from equipment.filters import JobsFilter
from jobs.models import *
from employees.models import *
from equipment.models import Inventory
from rentals.models import Rentals
from subcontractors.models import *
from wallcovering.models import Wallcovering, Packages, OutgoingItem, OrderItems
from submittals.models import *
from console.misc import Email
import os
import os.path
from django.conf import settings
import csv
from jobs.JobMisc import start_date_change, gerloff_super_change
from jobs.filters import JobNotesFilter
from django.db.models import Q


@login_required(login_url='/accounts/login')
def change_start_date(request, jobnumber, previous, ):
    jobs = Jobs.objects.get(job_number=jobnumber)
    format_date = jobs.start_date.strftime("%Y-%m-%d")
    previous_page = previous
    if request.method == 'POST':
        if 'is_active' in request.POST:
            if jobs.is_active == False:
                status = 1
            else:
                status = 3
        elif jobs.is_active == True:
            status = 2
        else:
            status = 3
        if str(jobs.start_date) != str(request.POST['start_date']):
            start_date_change(jobs, request.POST['start_date'], status, request.POST['date_note'],
                              request.user.first_name + " " + request.user.last_name, True)
        elif status != 3:
            start_date_change(jobs, request.POST['start_date'], status, request.POST['date_note'],
                              request.user.first_name + " " + request.user.last_name, False)
        if previous == 'jobpage':
            return redirect('job_page', jobnumber='ALL')
        else:
            return redirect('super_home')
    return render(request, "change_start_date.html",
                  {'jobs': jobs, 'formatdate': format_date, 'previous_page': previous_page})


def change_gpsuper(request, jobnumber, previous):
    jobs = Jobs.objects.get(job_number=jobnumber)
    previous_page = previous
    employees = Employees.objects.exclude(job_title__description="Painter")
    if request.method == 'POST':
        gerloff_super_change(jobs, Employees.objects.get(id=request.POST['select_gpsuper']),
                             request.user.first_name + " " + request.user.last_name)
        if previous == 'jobpage':
            return redirect('job_page', jobnumber=jobnumber)
        else:
            return redirect('super_home')
    return render(request, "change_gpsuper.html",
                  {'jobs': jobs, 'previous_page': previous_page, 'employees': employees})


@login_required(login_url='/accounts/login')
def update_job_info(request, jobnumber):
    selectedjob = Jobs.objects.get(job_number=jobnumber)
    allclients = Clients.objects.order_by('company')
    pms = ClientEmployees.objects.values('name', 'id', 'person_pk')
    estimators = Employees.objects.exclude(job_title__description='Painter')
    superintendents = Employees.objects.exclude(job_title__description='Painter')
    notes = JobNotes.objects.filter(job_number=jobnumber)
    # send_employees = Employees.objects.filter(job_title="Superintendent")[0:2000]
    prices_json = json.dumps(list(pms), cls=DjangoJSONEncoder)
    selectedclient = Clients.objects.get(id=selectedjob.client.id)
    pms_filter = ClientEmployees.objects.filter(id=selectedclient.id)
    startdate = selectedjob.start_date.strftime("%Y") + "-" + selectedjob.start_date.strftime(
        "%m") + "-" + selectedjob.start_date.strftime("%d")
    if request.method == 'POST':
        if selectedjob.address != request.POST['address']:
            selectedjob.address = request.POST['address']
        if request.POST['brush_role'] == "":
            if selectedjob.brush_role is not None:
                selectedjob.brush_role = None
        else:
            if selectedjob.brush_role != request.POST['brush_role']:
                selectedjob.brush_role = request.POST['brush_role']
        if selectedjob.city != request.POST['city']:
            selectedjob.city = request.POST['city']
        if request.POST['select_company'] == 'add_new':
            client = Clients.objects.create(company=request.POST['new_client'],
                                            bid_email=request.POST['new_client_bid_email'],
                                            phone=request.POST['new_client_phone'])
            selectedjob.client = client
            selectedjob.save()
        elif selectedjob.client.id != request.POST['select_company']:
            selectedjob.client = Clients.objects.get(id=request.POST['select_company'])
            selectedjob.save()
        if request.POST['select_pm'] == 'use_below':
            client_pm = ClientEmployees.objects.create(id=selectedjob.client, name=request.POST['new_pm'],
                                                       phone=request.POST['new_pm_phone'],
                                                       email=request.POST['new_pm_email'])
            selectedjob.client_Pm = client_pm
        else:
            if selectedjob.client_Pm.person_pk != request.POST['select_pm']:
                selectedjob.client_Pm = ClientEmployees.objects.get(person_pk=request.POST['select_pm'])
        if request.POST['select_super'] == 'use_below':
            client_super = ClientEmployees.objects.create(id=selectedjob.client, name=request.POST['new_super'],
                                                          phone=request.POST['new_super_phone'],
                                                          email=request.POST['new_super_email'])
            selectedjob.client_super = client_super
        elif request.POST['select_super'] == 'not_sure':
            if selectedjob.client_Super is not None:
                selectedjob.client_Super = None
        else:
            if selectedjob.client_Super is not None:
                if selectedjob.client_Super.person_pk != request.POST['select_super']:
                    selectedjob.client_Super = ClientEmployees.objects.get(person_pk=request.POST['select_super'])
            else:
                selectedjob.client_Super = ClientEmployees.objects.get(person_pk=request.POST['select_super'])
        if request.POST['contract_amount'] == "":
            if selectedjob.contract_amount is not None:
                selectedjob.contract_amount = None
        else:
            if selectedjob.contract_amount != request.POST['contract_amount']:
                selectedjob.contract_amount = request.POST['contract_amount']
        if selectedjob.contract_status != request.POST['contract_status']:
            selectedjob.contract_status = request.POST['contract_status']
        if selectedjob.estimator.id != request.POST['select_gpestimator']:
            selectedjob.estimator = Employees.objects.get(id=request.POST['select_gpestimator'])
        if 'has_paint' in request.POST:
            selectedjob.has_paint = True
        else:
            selectedjob.has_paint = False
        if 'has_wallcovering' in request.POST:
            selectedjob.has_wallcovering = True
        else:
            selectedjob.has_wallcovering = False
        if selectedjob.insurance_status != request.POST['insurance_status']:
            selectedjob.insurance_status = request.POST['insurance_status']
        if 'is_bonded' in request.POST:
            selectedjob.is_bonded = True
        else:
            selectedjob.is_bonded = False
        if 'on_base2' in request.POST:
            selectedjob.is_on_base = True
        else:
            selectedjob.is_on_base = False
        if 'is_t_m_job' in request.POST:
            selectedjob.is_t_m_job = True
        else:
            selectedjob.is_t_m_job = False
        if 'is_wage_rate' in request.POST:
            selectedjob.is_wage_scale = True
        else:
            selectedjob.is_wage_scale = False
        if selectedjob.job_name != request.POST['job_name']:
            selectedjob.job_name = request.POST['job_name']
        if selectedjob.notes != request.POST['email_job_note']:
            selectedjob.notes = request.POST['email_job_note']
        if request.POST['painting_budget'] == "":
            if selectedjob.painting_budget is not None:
                selectedjob.painting_budget = None
        else:
            if selectedjob.painting_budget != request.POST['painting_budget']:
                selectedjob.painting_budget = request.POST['painting_budget']
        if request.POST['po_number'] == "":
            if selectedjob.po_number is not None:
                selectedjob.po_number = None
        else:
            if selectedjob.po_number != request.POST['po_number']:
                selectedjob.po_number = request.POST['po_number']
        if 'has_special_paint' in request.POST:
            selectedjob.special_paint_needed = True
        else:
            selectedjob.special_paint_needed = False
        if request.POST['spray_scale'] == "":
            if selectedjob.spray_scale is not None:
                selectedjob.spray_scale = None
        else:
            if selectedjob.spray_scale != request.POST['spray_scale']:
                selectedjob.spray_scale = request.POST['spray_scale']
        if selectedjob.start_date != request.POST['start_date']:
            start_date_change(selectedjob, request.POST['start_date'], 3, request.POST['date_note'],
                              request.user.first_name + " " + request.user.last_name, True)
        if selectedjob.state != request.POST['state']:
            selectedjob.state = request.POST['state']
        if 'has_submittals' in request.POST:
            selectedjob.submittals_needed = True
        else:
            selectedjob.submittals_needed = False
        if request.POST['select_gpsuper'] == 'not_sure':
            if selectedjob.superintendent is not None:
                selectedjob.superintendent = None
        else:
            if selectedjob.superintendent is not None:
                if str(selectedjob.superintendent.id) != str(request.POST['select_gpsuper']):
                    gerloff_super_change(selectedjob, Employees.objects.get(id=request.POST['select_gpsuper']),
                                         request.user.first_name + " " + request.user.last_name)
            else:
                gerloff_super_change(selectedjob, Employees.objects.get(id=request.POST['select_gpsuper']),
                                     request.user.first_name + " " + request.user.last_name)
        if request.POST['t_m_nte_amount'] == "":
            if selectedjob.t_m_nte_amount is not None:
                selectedjob.t_m_nte_amount = None
        else:
            if selectedjob.t_m_nte_amount != request.POST['t_m_nte_amount']:
                selectedjob.t_m_nte_amount = request.POST['t_m_nte_amount']
        if request.POST['wallcovering_budget'] == "":
            if selectedjob.wallcovering_budget is not None:
                selectedjob.wallcovering_budget = None
        else:
            if selectedjob.wallcovering_budget != request.POST['wallcovering_budget']:
                selectedjob.wallcovering_budget = request.POST['wallcovering_budget']
        selectedjob.save()
    return render(request, 'update_job_info.html',
                  {'data': prices_json, 'startdate': startdate, 'notes': notes, 'selectedjob': selectedjob,
                   'allclients': allclients, 'superintendents': superintendents, 'estimators': estimators,
                   'pms_filter': pms_filter})


@login_required(login_url='/accounts/login')
def upload_new_job(request):
    if request.method == 'POST':
        if 'upload_file' in request.FILES:
            fileitem = request.FILES['upload_file']
            fn = os.path.basename(fileitem.name)
            # fn2 = os.path.join(settings.MEDIA_ROOT, "job_import", str(request.POST['job_number']), fn)
            fn2 = os.path.join(settings.MEDIA_ROOT, "job_import", str(request.POST['job_number']) + ".csv")
            open(fn2, 'wb').write(fileitem.file.read())
            print(1)
            with open(fn2) as f:
                print(2)
                reader = csv.reader(f)
                rows = list(reader)
                print(rows[15][1])
                # line_count1 = 0
                # found = 0
                # for row in reader:
                #     if line_count1 == 0:
                #         for x in range(2):
                #             if row[x] == "id":
                #                 a = x
                #                 found = found + 1
                #             if row[x] == "action":
                #                 b = x
                #                 found = found + 1
                #         line_count1 = line_count1 + 1
                #         if found != 2:
                #             raise ValueError('A very specific bad thing happened.')
                #     else:

                # job_number = ''
                # job_name = ''
                # address = ''
                # city = ''
                # state = ''
                # is_on_base ='' #true or false
                # is_t_m_job = ''
                # contract_status = ''  # 1-received, 2-not received, 3-not required
                # insurance_status = ''  # 1-received 2-not received 3-not required
                # client = ''
                # start_date = ''
                # job = Jobs.objects.create(job_number=job_number, job_name=job_name, address=address, city=city,
                #                           state=state,
                #                           is_on_base=is_on_base, is_t_m_job=is_t_m_job, contract_status=contract_status,
                #                           insurance_status=insurance_status, client=client, start_date=start_date,
                #                           status="Open", booked_date=date.today(),
                #                           booked_by=request.user.first_name + " " + request.user.last_name)
                #
                # spray_scale = ''
                # brush_role = ''
                # t_m_nte_amount = ''
                # client_pm = ''
                # client_super = ''
                # superintendent = ''
                # contract_amount = ''
                # painting_budget =
                # wallcovering_budget =
                # job.is_wage_scale
                # job.special_paint_needed #true or false
                # job.has_paint
                # job.has_wallcovering
                # job.submittals_needed
                # JobNotes.objects.create(job_number=job,
                #                         note="Start Date at Booking: " + start_date + " " + request.POST['date_note'],
                #                         type="auto_start_date_note", date=date.today(),
                #                         user=request.user.first_name + " " + request.user.last_name)
                #
                # JobNotes.objects.create(job_number=job,
                #                         note="New Job Booked By: " + request.user.first_name + " " + request.user.last_name + ": " +
                #                              request.POST['email_job_note'],
                #                         type="auto_booking_note", date=date.today(),
                #                         user=request.user.first_name + " " + request.user.last_name)
                # email_body = "New Job Booked \n" + job.job_number + "\n" + job.job_name + "\n" + job.client.company
                # Email.sendEmail("New Job - " + job.job_name, email_body, 'joe@gerloffpainting.com')
                # job.save()
                #

    return render(request, "upload_new_job.html")


@login_required(login_url='/accounts/login')
def upload_new_job(request):
    if request.method == 'POST':
        if 'upload_file' in request.FILES:
            fileitem = request.FILES['upload_file']
            fn = os.path.basename(fileitem.name)
            # fn2 = os.path.join(settings.MEDIA_ROOT, "job_import", str(request.POST['job_number']), fn)
            fn2 = os.path.join(settings.MEDIA_ROOT, "job_import", str(request.POST['job_number']) + ".csv")
            open(fn2, 'wb').write(fileitem.file.read())
            print(1)
            with open(fn2) as f:
                print(2)
                reader = csv.reader(f)
                rows = list(reader)
                print(rows[15][1])
                # line_count1 = 0
                # found = 0
                # for row in reader:
                #     if line_count1 == 0:
                #         for x in range(2):
                #             if row[x] == "id":
                #                 a = x
                #                 found = found + 1
                #             if row[x] == "action":
                #                 b = x
                #                 found = found + 1
                #         line_count1 = line_count1 + 1
                #         if found != 2:
                #             raise ValueError('A very specific bad thing happened.')
                #     else:

                # job_number = ''
                # job_name = ''
                # address = ''
                # city = ''
                # state = ''
                # is_on_base ='' #true or false
                # is_t_m_job = ''
                # contract_status = ''  # 1-received, 2-not received, 3-not required
                # insurance_status = ''  # 1-received 2-not received 3-not required
                # client = ''
                # start_date = ''
                # job = Jobs.objects.create(job_number=job_number, job_name=job_name, address=address, city=city,
                #                           state=state,
                #                           is_on_base=is_on_base, is_t_m_job=is_t_m_job, contract_status=contract_status,
                #                           insurance_status=insurance_status, client=client, start_date=start_date,
                #                           status="Open", booked_date=date.today(),
                #                           booked_by=request.user.first_name + " " + request.user.last_name)
                #
                # spray_scale = ''
                # brush_role = ''
                # t_m_nte_amount = ''
                # client_pm = ''
                # client_super = ''
                # superintendent = ''
                # contract_amount = ''
                # painting_budget =
                # wallcovering_budget =
                # job.is_wage_scale
                # job.special_paint_needed #true or false
                # job.has_paint
                # job.has_wallcovering
                # job.submittals_needed
                # JobNotes.objects.create(job_number=job,
                #                         note="Start Date at Booking: " + start_date + " " + request.POST['date_note'],
                #                         type="auto_start_date_note", date=date.today(),
                #                         user=request.user.first_name + " " + request.user.last_name)
                #
                # JobNotes.objects.create(job_number=job,
                #                         note="New Job Booked By: " + request.user.first_name + " " + request.user.last_name + ": " +
                #                              request.POST['email_job_note'],
                #                         type="auto_booking_note", date=date.today(),
                #                         user=request.user.first_name + " " + request.user.last_name)
                # email_body = "New Job Booked \n" + job.job_number + "\n" + job.job_name + "\n" + job.client.company
                # Email.sendEmail("New Job - " + job.job_name, email_body, 'joe@gerloffpainting.com')
                # job.save()
                #

    return render(request, "upload_new_job.html")


@login_required(login_url='/accounts/login')
def jobs_home(request):
    response = redirect('/')
    return response


@login_required(login_url='/accounts/login')
def job_page(request, jobnumber):
    if jobnumber == 'ALL':
        search_jobs = JobsFilter(request.GET, queryset=Jobs.objects.filter(status="Open"))
        jobstable = JobsTable(search_jobs.qs)
        has_filter = any(field in request.GET for field in set(search_jobs.get_fields()))
        tickets = ChangeOrders.objects.filter(job_number__status="Open", is_t_and_m=True, is_ticket_signed=False)
        open_cos = ChangeOrders.objects.filter(job_number__status="Open", is_closed=False,
                                               is_approved=False) & ChangeOrders.objects.filter(
            is_t_and_m=False) | ChangeOrders.objects.filter(is_t_and_m=True, is_ticket_signed=True)
        approved_cos = ChangeOrders.objects.filter(job_number__status="Open", is_closed=False, is_approved=True)
        equipment = Inventory.objects.filter(job_number__status="Open").order_by('inventory_type')
        rentals = Rentals.objects.filter(job_number__status="Open")
        wallcovering2 = Wallcovering.objects.filter(job_number__status="Open")
        wc_not_ordereds = []
        for x in wallcovering2:
            if x.orderitems1.count() > 0:
                print(x)
            else:
                wc_not_ordereds.append(x)
        wc_ordereds = OrderItems.objects.filter(wallcovering__job_number__status="Open", is_satisfied=False)
        packages = Packages.objects.filter(delivery__order__job_number__status="Open")
        deliveries = OutgoingItem.objects.filter(outgoing_event__job_number__status="Open")
        submittals = Submittals.objects.filter(job_number__status="Open")
        subcontracts = Subcontracts.objects.filter(job_number__status="Open")
        jobs = 'ALL'
        return render(request, "job_page.html",
                      {'search_jobs': search_jobs, 'has_filter': has_filter, 'jobstable': jobstable,
                       'subcontracts': subcontracts, 'submittals': submittals, 'packages': packages,
                       'deliveries': deliveries, 'wc_not_ordereds': wc_not_ordereds, 'wc_ordereds': wc_ordereds,
                       'jobs': jobs, 'tickets': tickets, 'open_cos': open_cos, 'approved_cos': approved_cos,
                       'equipments': equipment, 'rentals': rentals})
    else:
        if request.method == 'POST':
            if 'add_note' in request.POST:
                JobNotes.objects.create(job_number=Jobs.objects.get(job_number=jobnumber), note=request.POST['add_note'], type="employee_note",
                                        user=request.user.first_name + " " + request.user.last_name, date=date.today())
        send_data = {}
        send_data['jobstable'] = JobsTable(Jobs.objects.filter(job_number=jobnumber))
        send_data['jobs'] = Jobs.objects.filter(job_number=jobnumber)
        send_data['tickets'] = ChangeOrders.objects.filter(job_number=jobnumber, is_t_and_m=True,
                                                           is_ticket_signed=False)
        send_data['open_cos'] = ChangeOrders.objects.filter(job_number=jobnumber, is_closed=False,
                                                            is_approved=False) & ChangeOrders.objects.filter(job_number=jobnumber,
            is_t_and_m=False) | ChangeOrders.objects.filter(job_number=jobnumber, is_t_and_m=True, is_ticket_signed=True)
        send_data['approved_cos'] = ChangeOrders.objects.filter(job_number=jobnumber, is_closed=False, is_approved=True)
        send_data['equipments'] = Inventory.objects.filter(job_number=jobnumber).order_by('inventory_type')
        send_data['rentals'] = Rentals.objects.filter(job_number=jobnumber)
        send_data['wallcovering2'] = Wallcovering.objects.filter(job_number=jobnumber)
        send_data['wc_not_ordereds'] = Wallcovering.objects.filter(job_number__job_number=jobnumber,
                                                                   orderitems1__isnull=True)
        send_data['wc_ordereds'] = OrderItems.objects.filter(order__job_number=jobnumber, is_satisfied=False)
        send_data['packages'] = Packages.objects.filter(delivery__order__job_number=jobnumber)
        send_data['deliveries'] = OutgoingItem.objects.filter(outgoing_event__job_number=jobnumber)
        send_data['submittals'] = Submittals.objects.filter(job_number=jobnumber)
        send_data['subcontracts'] = Subcontracts.objects.filter(job_number=jobnumber)
        all_notes = JobNotesFilter(request.GET, queryset=JobNotes.objects.filter(job_number=jobnumber))
        send_data['all_notes'] = all_notes
        send_data['filtered_notes'] = all_notes.qs
        send_data['has_filter'] = any(field in request.GET for field in set(all_notes.get_fields()))
        if request.method == 'GET':
            made_already = False
            if 'admin' in request.GET:
                notes = JobNotes.objects.filter(job_number=jobnumber,
                                                type="auto_booking_note") | JobNotes.objects.filter(
                    job_number=jobnumber, type="auto_misc_note")
                made_already = True
                send_data['admin'] = 'admin'
            if 'start' in request.GET:
                send_data['start'] = 'start'
                if made_already == False:
                    notes = JobNotes.objects.filter(job_number=jobnumber, type="auto_start_date_note")
                    made_already = True
                else:
                    notes = notes | JobNotes.objects.filter(job_number=jobnumber, type="auto_start_date_note")
                    made_already = True
            if 'field' in request.GET:
                send_data['field'] = 'field'
                if made_already == False:
                    notes = JobNotes.objects.filter(job_number=jobnumber,
                                                    type="employee_note") | JobNotes.objects.filter(
                        job_number=jobnumber, type="daily_report")
                    made_already = True
                else:
                    notes = notes | JobNotes.objects.filter(job_number=jobnumber,
                                                            type="employee_note") | JobNotes.objects.filter(
                        job_number=jobnumber, type="daily_report")
                    made_already = True
            if 'change_order' in request.GET:
                send_data['change_order'] = 'change_order'
                if made_already == False:
                    notes = JobNotes.objects.filter(job_number=jobnumber, type="auto_co_note")
                    made_already = True
                else:
                    notes = notes | JobNotes.objects.filter(job_number=jobnumber, type="auto_co_note")
                    made_already = True
            if 'submittal' in request.GET:
                send_data['submittal'] = 'submittal'
                if made_already == False:
                    notes = JobNotes.objects.filter(job_number=jobnumber, type="auto_submittal_note")
                    made_already = True
                else:
                    notes = notes | JobNotes.objects.filter(job_number=jobnumber, type="auto_submittal_note")
                    made_already = True
            if made_already == False:
                notes = JobNotes.objects.filter(job_number=jobnumber)
        else:
            notes = JobNotes.objects.filter(job_number=jobnumber)
        send_data['notes'] = notes
        print(send_data)
        return render(request, 'job_page.html', send_data)


@login_required(login_url='/accounts/login')
def book_new_job(request):
    allclients = Clients.objects.order_by('company')
    pms = ClientEmployees.objects.values('name', 'id', 'person_pk')
    estimators = Employees.objects.exclude(job_title__description='Painter')
    superintendents = Employees.objects.exclude(job_title__description='Painter')
    # send_employees = Employees.objects.filter(job_title="Superintendent")[0:2000]
    prices_json = json.dumps(list(pms), cls=DjangoJSONEncoder)

    return render(request, 'book_new_job.html',
                  {'data': prices_json, 'allclients': allclients, 'superintendents': superintendents,
                   'estimators': estimators})


@login_required(login_url='/accounts/login')
def register(request):
    if request.method == 'POST':
        checklist = []
        if request.POST['job_number'] == "":
            if JobNumbers.objects.latest("id").number == "9990":
                new_letter = chr(ord(JobNumbers.objects.latest("id").letter) + 1)
                new_job_number = JobNumbers.objects.create(letter=new_letter, number="0010")
                job_number = new_job_number.letter + new_job_number.number
            else:
                new_number = int(JobNumbers.objects.latest("id").number) + 10
                new_number_convert = str(new_number)
                if new_number < 100:
                    new_job_number = JobNumbers.objects.create(letter=JobNumbers.objects.latest("id").letter,
                                                               number="00" + new_number_convert)
                elif new_number < 1000:
                    new_job_number = JobNumbers.objects.create(letter=JobNumbers.objects.latest("id").letter,
                                                               number="0" + new_number_convert)
                else:
                    new_job_number = JobNumbers.objects.create(letter=JobNumbers.objects.latest("id").letter,
                                                               number=new_number_convert)
                new_job_number.save()
                job_number = new_job_number.letter + new_job_number.number
        else:
            job_number = request.POST['job_number']
        job_name = request.POST['job_name']
        address = request.POST['address']
        city = request.POST['city']
        state = request.POST['state']

        spray_scale = request.POST['spray_scale']
        brush_role = request.POST['brush_role']

        t_m_nte_amount = request.POST['t_m_nte_amount']

        if request.POST['contract_status'] == 'contract_not_received':
            contract_status = 2
            checklist.append("waiting for contract")
        elif request.POST['contract_status'] == 'contract_received':
            contract_status = 1
        else:  # contract not required
            contract_status = 3

        if request.POST['insurance_status'] == 'coi_not_received':
            insurance_status = 2
            checklist.append("get coi")
        elif request.POST['insurance_status'] == 'coi_received':
            insurance_status = 1
        else:  # contract not required
            insurance_status = 3

        if request.POST['select_company'] == 'add_new':
            client = Clients.objects.create(company=request.POST['new_client'],
                                            bid_email=request.POST['new_client_bid_email'],
                                            phone=request.POST['new_client_phone'])

        else:
            client = Clients.objects.get(id=request.POST['select_company'])
        # if request.POST['select_pm'] == 'not_sure':
        #     checklist.append("get pm info")
        #     client_pm = 'not_sure'
        if request.POST['select_pm'] == 'use_below':

            client_pm = ClientEmployees.objects.create(id=client, name=request.POST['new_pm'],
                                                       phone=request.POST['new_pm_phone'],
                                                       email=request.POST['new_pm_email'])

        else:
            client_pm = ClientEmployees.objects.get(person_pk=request.POST['select_pm'])

        if request.POST['select_super'] == 'not_sure':
            checklist.append("get superintendent info")
            client_super = 'not_sure'
        elif request.POST['select_super'] == 'use_below':
            client_super = ClientEmployees.objects.create(id=client, name=request.POST['new_super'],
                                                          phone=request.POST['new_super_phone'],
                                                          email=request.POST['new_super_email'])

        else:
            client_super = ClientEmployees.objects.get(person_pk=request.POST['select_super'])

        superintendent = request.POST['select_gpsuper']

        start_date = request.POST['start_date']

        # add email message request.POST['email_job_note']
        contract_amount = request.POST['contract_amount']
        painting_budget = request.POST['painting_budget']
        wallcovering_budget = request.POST['wallcovering_budget']

        job = Jobs.objects.create(job_number=job_number, job_name=job_name, address=address, city=city, state=state,contract_status=contract_status,
                                  insurance_status=insurance_status, client=client, start_date=start_date,
                                  status="Open", booked_date=date.today(),
                                  booked_by=request.user.first_name + " " + request.user.last_name,
                                  estimator=Employees.objects.get(id=request.POST['select_gpestimator']),
                                  notes=request.POST['email_job_note'], po_number=request.POST['po_number'])
        if 'is_t_m_job' in request.POST:
            job.is_t_m_job = True
        else:
            is_t_m_job = False
        if 'on_base2' in request.POST:
            job.is_on_base = True
        if 'is_wage_rate' in request.POST:
            job.is_wage_scale = True
        if 'is_bonded' in request.POST:
            job.is_bonded = True

        if 'has_special_paint' in request.POST:
            job.has_special_paint = True
            job.special_paint_needed = True
        if client_super != 'not_sure':
            job.client_Super = client_super
        job.client_Pm = client_pm

        # job.client_submittal_contact = client_pm
        # job.client_co_contact = client_pm

        if is_t_m_job == False:
            job.contract_amount = contract_amount
        if t_m_nte_amount != "":
            job.t_m_nte_amount = t_m_nte_amount
        if spray_scale != "":
            job.spray_scale = spray_scale
        if brush_role != "":
            job.brush_role = brush_role
        if painting_budget != "":
            job.painting_budget = painting_budget
        if wallcovering_budget != "":
            job.wallcovering_budget = wallcovering_budget
        if superintendent != 'not_sure':
            job.superintendent = Employees.objects.get(id=superintendent)
        if 'has_paint' in request.POST:
            job.has_paint = True
        if 'has_wallcovering' in request.POST:
            job.has_wallcovering = True
        if 'has_submittals' in request.POST:
            job.submittals_needed = True
        else:
            job.submittals_required = False

        JobNotes.objects.create(job_number=job,
                                note="Start Date at Booking: " + start_date + " " + request.POST['date_note'],
                                type="auto_start_date_note", date=date.today(),
                                user=request.user.first_name + " " + request.user.last_name)

        JobNotes.objects.create(job_number=job,
                                note="New Job Booked By: " + request.user.first_name + " " + request.user.last_name + ": " +
                                     request.POST['email_job_note'],
                                type="auto_booking_note", date=date.today(),
                                user=request.user.first_name + " " + request.user.last_name)
        email_body = "New Job Booked \n" + job.job_number + "\n" + job.job_name + "\n" + job.client.company
        Email.sendEmail("New Job - " + job.job_name, email_body, 'joe@gerloffpainting.com', False)
        job.save()
        # for x in checklist:
        #     checklist = Checklist(job_number=job_number, checklist_item=x, category="PM")
        #     checklist.save();
        response = redirect('/')
        return response


@login_required(login_url='/accounts/login')
class Checklist(models.Model):
    id = models.BigAutoField(primary_key=True)
    category = models.CharField(null=True, max_length=1000)
    checklist_item = models.CharField(null=True, max_length=2000)
    is_closed = models.BooleanField(default=False)
    job_number = models.ForeignKey(Jobs, on_delete=models.PROTECT)
    notes = models.CharField(null=True, max_length=2500)
    job_start_date_from_schedule = models.DateField(null=True, blank=True)
    cop = models.BooleanField(default=False)
    cop_amount = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, null=True)
    cop_sent_date = models.DateField(null=True, blank=True)
    cop_number = models.IntegerField(default=0)
    is_ewt = models.BooleanField(default=False)
    ewt_date = models.DateField(null=True, blank=True)
    is_submittal = models.BooleanField(default=False)
    submittal_number = models.IntegerField(default=0)
    submittal_description = models.CharField(null=True, max_length=2000)
    submittal_date_sent = models.DateField(null=True, blank=True)
    wallcovering_order_date = models.DateField(null=True, blank=True)
    assigned = models.CharField(null=True, max_length=2000)

    def __str__(self):
        return f"{self.job_number} {self.checklist_item}"
