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
import openpyxl
from django_tables2 import RequestConfig


@login_required(login_url='/accounts/login')
def change_start_date(request, jobnumber, previous, super, filter):
    # jobnumber is the job number you are changing
    # previous is either "jobpage"(job_page) or "super"(super_home)
    # super is if super_home was filtered to a certain superintendent
    # filter is if super_home was filtered to UPCOMING or ALL. OR, it is set to JOB for job page

    jobs = Jobs.objects.get(job_number=jobnumber)
    format_date = jobs.start_date.strftime("%Y-%m-%d")
    previous_page = previous
    if request.method == 'POST':
        print(request.POST)
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
                              Employees.objects.get(user=request.user), True)
        elif status != 3:
            start_date_change(jobs, request.POST['start_date'], status, request.POST['date_note'],
                              Employees.objects.get(user=request.user), False)
        else:
            if 'follow_up' in request.POST or request.POST['date_note'] != "":
                jobs.start_date_checked = date.today()
                if request.POST['date_note'] != "":
                    JobNotes.objects.create(job_number=jobs,
                                            note="Start Date is Still: " + str(request.POST['start_date']) + ". " +
                                                 request.POST['date_note'],
                                            type="auto_start_date_note",
                                            user=Employees.objects.get(user=request.user),
                                            date=date.today())
                jobs.save()
        if previous == 'jobpage':
            if filter == 'JOB':
                return redirect('job_page', jobnumber=jobnumber)
            else:
                return redirect('job_page', jobnumber='ALL')
        else:
            return redirect('super_home', super=super)
    return render(request, "change_start_date.html",
                  {'jobs': jobs, 'formatdate': format_date,
                   'notes': JobNotes.objects.filter(job_number=jobnumber, type="auto_start_date_note"),
                   'previous_page': previous_page, 'selected_super': super,
                   'selected_filter': filter})


def change_gpsuper(request, jobnumber, previous):
    jobs = Jobs.objects.get(job_number=jobnumber)
    previous_page = previous
    employees = Employees.objects.exclude(job_title__description="Painter")
    if request.method == 'POST':
        gerloff_super_change(jobs, Employees.objects.get(id=request.POST['select_gpsuper']),
                             Employees.objects.get(user=request.user))
        if previous == 'jobpage':
            return redirect('job_page', jobnumber=jobnumber)
        else:
            return redirect('super_home', super='ALL')
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
        if selectedjob.job_name != request.POST['job_name']:
            selectedjob.job_name = request.POST['job_name']
        if selectedjob.address != request.POST['address']:
            selectedjob.address = request.POST['address']
        if selectedjob.city != request.POST['city']:
            selectedjob.city = request.POST['city']
        if selectedjob.state != request.POST['state']:
            selectedjob.state = request.POST['state']
        if 'on_base2' in request.POST:
            selectedjob.is_on_base = True
        else:
            selectedjob.is_on_base = False
        if 'is_wage_rate' in request.POST:
            selectedjob.is_wage_scale = True
        else:
            selectedjob.is_wage_scale = False
        if request.POST['brush_role'] == "":
            if selectedjob.brush_role is not None:
                selectedjob.brush_role = None
        else:
            if selectedjob.brush_role != request.POST['brush_role']:
                selectedjob.brush_role = request.POST['brush_role']
        if request.POST['spray_scale'] == "":
            if selectedjob.spray_scale is not None:
                selectedjob.spray_scale = None
        else:
            if selectedjob.spray_scale != request.POST['spray_scale']:
                selectedjob.spray_scale = request.POST['spray_scale']
        if 'is_closed' in request.POST:
            if selectedjob.is_closed == False:
                if Inventory.objects.filter(job_number=selectedjob).exists():

                    message = "Job: " + selectedjob.job_name + " is closed. The following equipment is assigned to the job and must be returned immediately!\n "
                    recipients = ["admin1@gerloffpainting.com", "admin2@gerloffpainting.com",
                                  "warehouse@gerloffpainting.com", "joe@gerloffpainting.com"]
                    if selectedjob.superintendent.email is None:
                        message = message + "\n No email address for " + selectedjob.superintendent
                    else:
                        recipients.append(selectedjob.superintendent.email)
                    for x in Inventory.objects.filter(job_number=selectedjob):
                        message = message + "\n -" + x.item + " GP Number #" + x.number
                    Email.sendEmail("Closed Job - " + selectedjob.job_name, message,
                                    recipients, False)
            selectedjob.is_closed = True
        else:
            selectedjob.is_closed = False
        if 'is_t_m_job' in request.POST:
            selectedjob.is_t_m_job = True
        else:
            selectedjob.is_t_m_job = False
        if request.POST['t_m_nte_amount'] == "":
            if selectedjob.t_m_nte_amount is not None:
                selectedjob.t_m_nte_amount = None
        else:
            if selectedjob.t_m_nte_amount != request.POST['t_m_nte_amount']:
                selectedjob.t_m_nte_amount = request.POST['t_m_nte_amount']
        if selectedjob.contract_status != request.POST['contract_status']:
            selectedjob.contract_status = request.POST['contract_status']
        if selectedjob.insurance_status != request.POST['insurance_status']:
            selectedjob.insurance_status = request.POST['insurance_status']
        if 'has_submittals' in request.POST:
            selectedjob.submittals_needed = True
        else:
            selectedjob.submittals_needed = False
        if 'is_bonded' in request.POST:
            selectedjob.is_bonded = True
        else:
            selectedjob.is_bonded = False
        if request.POST['select_company'] == 'add_new':
            client = Clients.objects.create(company=request.POST['new_client'],
                                            bid_email=request.POST['new_client_bid_email'],
                                            phone=request.POST['new_client_phone'])
            selectedjob.client = client
            selectedjob.save()
        elif selectedjob.client.id != request.POST['select_company']:
            selectedjob.client = Clients.objects.get(id=request.POST['select_company'])
            selectedjob.save()
        selectedjob.client.company=request.POST['new_client']
        selectedjob.client.bid_email=request.POST['new_client_bid_email']
        selectedjob.client.phone=request.POST['new_client_phone']
        selectedjob.client.save()
        if request.POST['select_pm'] == 'add_new':
            client_pm = ClientEmployees.objects.create(id=selectedjob.client, name=request.POST['new_pm'],
                                                       phone=request.POST['new_pm_phone'],
                                                       email=request.POST['new_pm_email'])
            selectedjob.client_Pm = client_pm
        else:
            if selectedjob.client_Pm.person_pk != request.POST['select_pm']:
                selectedjob.client_Pm = ClientEmployees.objects.get(person_pk=request.POST['select_pm'])
        selectedjob.client_Pm.name=request.POST['new_pm']
        selectedjob.client_Pm.phone=request.POST['new_pm_phone']
        selectedjob.client_Pm.email=request.POST['new_pm_email']
        selectedjob.client_Pm.save()
        if request.POST['select_super'] == 'add_new':
            client_super = ClientEmployees.objects.create(id=selectedjob.client, name=request.POST['new_super'],
                                                          phone=request.POST['new_super_phone'],
                                                          email=request.POST['new_super_email'])
            selectedjob.client_Super = client_super
        elif request.POST['select_super'] == 'not_sure':
            if selectedjob.client_Super is not None:
                selectedjob.client_Super = None
        else:
            if selectedjob.client_Super is not None:
                if selectedjob.client_Super.person_pk != request.POST['select_super']:
                    selectedjob.client_Super = ClientEmployees.objects.get(person_pk=request.POST['select_super'])
            else:
                selectedjob.client_Super = ClientEmployees.objects.get(person_pk=request.POST['select_super'])
            selectedjob.client_Super.name = request.POST['new_super']
            selectedjob.client_Super.phone = request.POST['new_super_phone']
            selectedjob.client_Super.email = request.POST['new_super_email']
            selectedjob.client_Super.save()
        if request.POST['select_gpsuper'] == 'not_sure':
            if selectedjob.superintendent is not None:
                selectedjob.superintendent = None
        else:
            if selectedjob.superintendent is not None:
                if str(selectedjob.superintendent.id) != str(request.POST['select_gpsuper']):
                    gerloff_super_change(selectedjob, Employees.objects.get(id=request.POST['select_gpsuper']),
                                         Employees.objects.get(user=request.user))
            else:
                gerloff_super_change(selectedjob, Employees.objects.get(id=request.POST['select_gpsuper']),
                                     Employees.objects.get(user=request.user))
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
        if 'has_special_paint' in request.POST:
            selectedjob.special_paint_needed = True
        else:
            selectedjob.special_paint_needed = False

        if startdate != request.POST['start_date']:
            start_date_change(selectedjob, request.POST['start_date'], 3, request.POST['date_note'],
                              Employees.objects.get(user=request.user), True)
        if selectedjob.notes != request.POST['email_job_note']:
            selectedjob.notes = request.POST['email_job_note']
        if request.POST['po_number'] == "":
            if selectedjob.po_number is not None:
                selectedjob.po_number = None
        else:
            if selectedjob.po_number != request.POST['po_number']:
                selectedjob.po_number = request.POST['po_number']
        if request.POST['contract_amount'] == "":
            if selectedjob.contract_amount is not None:
                selectedjob.contract_amount = None
        else:
            if selectedjob.contract_amount != request.POST['contract_amount']:
                selectedjob.contract_amount = request.POST['contract_amount']
        if request.POST['painting_budget'] == "":
            if selectedjob.painting_budget is not None:
                selectedjob.painting_budget = None
        else:
            if selectedjob.painting_budget != request.POST['painting_budget']:
                selectedjob.painting_budget = request.POST['painting_budget']

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
            fn2 = os.path.join(settings.MEDIA_ROOT, "job_upload", "Temp.xlsx")
            open(fn2, 'wb').write(fileitem.file.read())
            send_data = {}
            # send_data['employees'] = Employees.objects.filter(user__isnull=True)
            wb_obj = openpyxl.load_workbook(filename=request.FILES['upload_file'].file)
            sheet_obj = wb_obj["Data"]
            client_name = sheet_obj.cell(row=16, column=2).value
            pm_name = sheet_obj.cell(row=19, column=2).value
            send_data['job_name'] = sheet_obj.cell(row=38, column=2).value
            send_data['job_number'] = sheet_obj.cell(row=25, column=2).value
            send_data['new_client'] = client_name
            send_data['new_pm_name'] = sheet_obj.cell(row=19, column=2).value
            send_data['new_pm_phone'] = sheet_obj.cell(row=20, column=2).value
            send_data['new_pm_email'] = sheet_obj.cell(row=21, column=2).value
            send_data['new_super_name'] = sheet_obj.cell(row=22, column=2).value
            send_data['new_super_phone'] = sheet_obj.cell(row=23, column=2).value
            send_data['new_super_email'] = sheet_obj.cell(row=24, column=2).value
            if Clients.objects.filter(company=client_name).exists():
                send_data['client'] = Clients.objects.get(company=client_name)
                send_data['pms_filter'] = ClientEmployees.objects.filter(id=Clients.objects.get(company=client_name))
                if ClientEmployees.objects.filter(name=pm_name, id__company=client_name).exists():
                    send_data['pm'] = ClientEmployees.objects.get(name=pm_name, id__company=client_name)
                super_name = sheet_obj.cell(row=22, column=2).value
                if ClientEmployees.objects.filter(name=super_name, id__company=client_name).exists():
                    send_data['super'] = ClientEmployees.objects.get(name=super_name, id__company=client_name)
            if Employees.objects.filter(first_name=sheet_obj.cell(row=39, column=2).value).exists():
                send_data['estimator'] = Employees.objects.get(first_name=sheet_obj.cell(row=39, column=2).value)
            else:
                send_data['estimator_name'] = sheet_obj.cell(row=39, column=2).value
            send_data['all_clients'] = Clients.objects.all()
            send_data['all_employees'] = Employees.objects.exclude(job_title__description="Painter")
            send_data['data'] = json.dumps(list(ClientEmployees.objects.values('name', 'id', 'person_pk')),
                                           cls=DjangoJSONEncoder)
            return render(request, 'job_upload.html', send_data)
        if 'book_job' in request.POST:
            wb_obj = openpyxl.load_workbook(os.path.join(settings.MEDIA_ROOT, "job_upload", "Temp.xlsx"))
            sheet_obj = wb_obj["Data"]

            if request.POST['select_company'] == 'add_new':
                client = Clients.objects.create(company=request.POST['new_client'],
                                                bid_email=request.POST['new_client_bid_email'],
                                                phone=request.POST['new_client_phone'])

            else:
                client = Clients.objects.get(id=request.POST['select_company'])
                client.company = request.POST['new_client']
                client.bid_email = request.POST['new_client_bid_email']
                client.phone = request.POST['new_client_phone']
                client.save()
            if request.POST['select_pm'] == 'add_new':
                client_pm = ClientEmployees.objects.create(id=client, name=request.POST['new_pm'],
                                                           phone=request.POST['new_pm_phone'],
                                                           email=request.POST['new_pm_email'])

            else:
                client_pm = ClientEmployees.objects.get(person_pk=request.POST['select_pm'])
                client_pm.name=request.POST['new_pm']
                client_pm.phone=request.POST['new_pm_phone']
                client_pm.email=request.POST['new_pm_email']
                client_pm.save()

            gp_estimator = Employees.objects.get(id=request.POST['select_gpestimator'])
            job_number = sheet_obj.cell(row=25, column=2).value
            job_name = sheet_obj.cell(row=38, column=2).value
            address = sheet_obj.cell(row=40, column=2).value
            city = sheet_obj.cell(row=41, column=2).value
            state = sheet_obj.cell(row=256, column=2).value
            if sheet_obj.cell(row=42, column=2).value == "Yes":
                is_on_base = True
            else:
                is_on_base = False
            if sheet_obj.cell(row=47, column=2).value == "Yes":
                is_t_m_job = True
            else:
                is_t_m_job = False
            if sheet_obj.cell(row=3, column=2).value == "Yes":
                contract_status = 1  # received
            elif sheet_obj.cell(row=1, column=2).value == "Yes":
                contract_status = 2  # not received
            else:
                contract_status = 3  # not needed
            if sheet_obj.cell(row=6, column=2).value == "Yes":
                insurance_status = 1
            elif sheet_obj.cell(row=4, column=2).value == "Yes":
                insurance_status = 2
            else:
                insurance_status = 3

            start_date = sheet_obj.cell(row=33, column=2).value
            job = Jobs.objects.create(job_number=job_number, job_name=job_name, address=address, city=city,
                                      state=state,
                                      is_on_base=is_on_base, is_t_m_job=is_t_m_job, contract_status=contract_status,
                                      insurance_status=insurance_status, client=client, start_date=start_date,
                                      status="Open", booked_date=date.today(), client_Pm=client_pm,
                                      booked_by=request.user.first_name + " " + request.user.last_name,
                                      estimator=gp_estimator)

            if request.POST['select_super'] != "not_sure":
                if 'duplicate' in request.POST:
                    job.client_Super = client_pm
                elif request.POST['select_super'] == 'add_new':
                        job.client_Super = ClientEmployees.objects.create(id=client, name=request.POST['new_super'],
                                                                          phone=request.POST['new_super_phone'],
                                                                          email=request.POST['new_super_email'])
                elif request.POST['select_super'] == 'duplicate':
                    job.client_Super = client_pm
                else:
                    job.client_Super = ClientEmployees.objects.get(person_pk=request.POST['select_super'])

            if sheet_obj.cell(row=44, column=2).value: job.brush_role = sheet_obj.cell(row=44, column=2).value
            if sheet_obj.cell(row=45, column=2).value: job.spray_scale = sheet_obj.cell(row=45, column=2).value
            if sheet_obj.cell(row=48, column=2).value: job.t_m_nte_amount = sheet_obj.cell(row=48, column=2).value
            if sheet_obj.cell(row=74, column=2).value: job.contract_amount = sheet_obj.cell(row=74, column=2).value
            if sheet_obj.cell(row=76, column=2).value: job.painting_budget = sheet_obj.cell(row=76, column=2).value
            if sheet_obj.cell(row=77, column=2).value: job.wallcovering_budget = sheet_obj.cell(row=77, column=2).value
            if sheet_obj.cell(row=43, column=2).value: job.is_wage_scale = True
            if sheet_obj.cell(row=57, column=2).value: job.special_paint_needed = True
            if sheet_obj.cell(row=29, column=2).value: job.has_paint = True
            if sheet_obj.cell(row=30, column=2).value: job.has_wallcovering = True
            if sheet_obj.cell(row=52, column=2).value:
                job.submittals_needed = False
            else:
                job.submittals_needed = True
            if sheet_obj.cell(row=18, column=2).value: job.po_number = sheet_obj.cell(row=18, column=2).value
            if sheet_obj.cell(row=36, column=2).value: job.is_off_hours = True
            job.start_date_checked = date.today()
            job.save()
            temp_note = "New Job Booked By: " + request.user.first_name + " " + request.user.last_name
            if sheet_obj.cell(row=37, column=2).value: temp_note = temp_note + ": " + sheet_obj.cell(row=37,
                                                                                                     column=2).value
            if sheet_obj.cell(row=60, column=2).value: temp_note = temp_note + ": " + sheet_obj.cell(row=60,
                                                                                                     column=2).value

            JobNotes.objects.create(job_number=job,
                                    note="Start Date at Booking: " + start_date.strftime(
                                        "%m/%d/%Y") + " " + sheet_obj.cell(row=258,
                                                                           column=2).value,
                                    type="auto_start_date_note", date=date.today(),
                                    user=Employees.objects.get(user=request.user))
            JobNotes.objects.create(job_number=job,
                                    note=temp_note,
                                    type="auto_booking_note", date=date.today(),
                                    user=Employees.objects.get(user=request.user))
            email_body = "New Job Booked \n" + job.job_number + "\n" + job.job_name + "\n" + job.client.company
            Email.sendEmail("New Job - " + job.job_name, email_body,
                            ['admin1@gerloffpainting.com', 'admin2@gerloffpainting.com', 'joe@gerloffpainting.com'],
                            False)

            return render(request, "upload_new_job.html")
    return render(request, "upload_new_job.html")


@login_required(login_url='/accounts/login')
def jobs_home(request):
    response = redirect('/')
    return response


@login_required(login_url='/accounts/login')
def job_page(request, jobnumber):
    if jobnumber == 'ALL':
        print(request.GET)
        send_data = {}
        if request.method == 'GET':
            if 'search' in request.GET: send_data['search_exists'] = request.GET['search']  # jobname
            if 'search2' in request.GET:
                send_data['search2_exists'] = request.GET['search2']  # super name
                if request.GET['search2'] != 'ALL' and request.GET['search2'] != 'UNASSIGNED':
                    send_data['selected_supername'] = Employees.objects.get(
                        id=request.GET['search2']).first_name + " " + Employees.objects.get(
                        id=request.GET['search2']).last_name
            if 'search3' in request.GET: send_data['search3_exists'] = request.GET['search3']  # open only
            if 'search4' in request.GET: send_data['search4_exists'] = request.GET['search4']  # gc name
            if 'search5' in request.GET: send_data['search5_exists'] = request.GET['search5']  # upcoming only
            if 'search6' in request.GET: send_data['search6_exists'] = request.GET['search6']  # unassigned
            if 'search7' in request.GET: send_data['search7_exists'] = request.GET['search7']  # labor done
        search_jobs = JobsFilter(request.GET, queryset=Jobs.objects.filter())
        send_data['search_jobs'] = JobsFilter(request.GET, queryset=Jobs.objects.filter())
        send_data['jobstable'] = search_jobs.qs.order_by('start_date')
        # RequestConfig(request).configure(jobstable)
        # RequestConfig(request, paginate=False).configure(jobstable)
        send_data['has_filter'] = any(field in request.GET for field in set(search_jobs.get_fields()))
        send_data['supers'] = Employees.objects.exclude(Q(job_title__description="Painter") | Q(active=False))
        send_data['tickets'] = ChangeOrders.objects.filter(job_number__is_closed=False, is_t_and_m=True,
                                                           is_ticket_signed=False)
        send_data['open_cos'] = ChangeOrders.objects.filter(job_number__is_closed=False, is_closed=False,
                                                            is_approved=False) & ChangeOrders.objects.filter(
            is_t_and_m=False) | ChangeOrders.objects.filter(is_t_and_m=True, is_ticket_signed=True)
        send_data['approved_cos'] = ChangeOrders.objects.filter(job_number__is_closed=False, is_closed=False,
                                                                is_approved=True)
        send_data['equipment'] = Inventory.objects.filter(job_number__is_closed=False).order_by('inventory_type')
        send_data['rentals'] = Rentals.objects.filter(job_number__is_closed=False, off_rent_number__isnull=True)
        wallcovering2 = Wallcovering.objects.filter(job_number__is_closed=False)
        wc_not_ordereds = []
        for x in wallcovering2:
            if x.orderitems1.count() > 0:
                print(x)
            else:
                wc_not_ordereds.append(x)
        send_data['wc_not_ordereds'] = wc_not_ordereds
        send_data['wc_ordereds'] = OrderItems.objects.filter(wallcovering__job_number__is_closed=False,
                                                             is_satisfied=False)
        send_data['packages'] = Packages.objects.filter(delivery__order__job_number__is_closed=False)
        send_data['deliveries'] = OutgoingItem.objects.filter(outgoing_event__job_number__is_closed=False)
        send_data['submittals'] = Submittals.objects.filter(job_number__is_closed=False)
        send_data['subcontracts'] = Subcontracts.objects.filter(job_number__is_closed=False)
        send_data['jobs'] = 'ALL'
        return render(request, "job_page.html", send_data)
    else:
        selectedjob = Jobs.objects.get(job_number=jobnumber)
        if request.method == 'POST':
            if 'select_status' in request.POST:
                if request.POST['select_status'] == 'nothing_done':
                    message = "Labor is not done."
                    if selectedjob.is_labor_done == True:
                        Email.sendEmail("Labor not done - " + selectedjob.job_name,
                                        "Per " + request.user.first_name + " " + request.user.last_name + "- Labor is not done. " +
                                        request.POST['closed_note'],
                                        ['joe@gerloffpainting.com', 'bridgette@gerloffpainting.com',
                                         'victor@gerloffpainting.com'])
                    selectedjob.labor_done_Date = None
                    selectedjob.is_waiting_for_punchlist = False
                    selectedjob.is_labor_done = False
                if request.POST['select_status'] == 'waiting_for_punchlist':
                    message = "Waiting for punchlist."
                    selectedjob.labor_done_Date = None
                    selectedjob.is_waiting_for_punchlist = True
                    selectedjob.is_labor_done = False
                if request.POST['select_status'] == 'done_done':
                    message = "Labor is 100% done."
                    Email.sendEmail("Labor Done - " + selectedjob.job_name,
                                    "Per " + request.user.first_name + " " + request.user.last_name + "- Labor is 100% Done. " +
                                    request.POST['closed_note'],
                                    ['joe@gerloffpainting.com', 'bridgette@gerloffpainting.com',
                                     'victor@gerloffpainting.com'])
                    selectedjob.labor_done_Date = date.today()
                    selectedjob.is_waiting_for_punchlist = True
                    selectedjob.is_labor_done = True
                selectedjob.save()
                JobNotes.objects.create(job_number=selectedjob,
                                        note=message + " " + request.POST['closed_note'], type="employee_note",
                                        user=Employees.objects.get(user=request.user), date=date.today())

            if 'add_note' in request.POST:
                JobNotes.objects.create(job_number=selectedjob,
                                        note=request.POST['add_note'], type="employee_note",
                                        user=Employees.objects.get(user=request.user), date=date.today())
            if 'submit_pm' in request.POST:
                if request.POST['select_pm'] == 'add_new':
                    selectedjob.client_Pm = ClientEmployees.objects.create(id=selectedjob.client,
                                                                           name=request.POST['new_pm'],
                                                                           phone=request.POST['new_pm_phone'],
                                                                           email=request.POST['new_pm_email'])
                    selectedjob.save()
                else:
                    selectedjob.client_Pm = ClientEmployees.objects.get(person_pk=request.POST['select_pm'])
                    selectedjob.save()
                    selectedjob.client_Pm.email = request.POST['pm_email']
                    selectedjob.client_Pm.phone = request.POST['pm_phone']
                    selectedjob.client_Pm.save()
            if 'submit_super' in request.POST:
                if request.POST['select_super'] == 'add_new':
                    selectedjob.client_Super = ClientEmployees.objects.create(id=selectedjob.client,
                                                                              name=request.POST['new_super'],
                                                                              phone=request.POST['new_super_phone'],
                                                                              email=request.POST['new_super_email'])
                    selectedjob.save()
                elif request.POST['select_super'] != 'not_sure':
                    selectedjob.client_Super = ClientEmployees.objects.get(person_pk=request.POST['select_super'])
                    selectedjob.save()
                    selectedjob.client_Super.email = request.POST['super_email']
                    selectedjob.client_Super.phone = request.POST['super_phone']
                    selectedjob.client_Super.save()
                elif selectedjob.client_Super:
                    selectedjob.client_Super = None
                    selectedjob.save()
            if 'submit_client' in request.POST:
                selectedjob.client.bid_email = request.POST['client_bid_email']
                selectedjob.client.phone = request.POST['client_phone']
                selectedjob.save()
        send_data = {}
        send_data['client_employees'] = ClientEmployees.objects.filter(id=selectedjob.client)
        # send_data['jobstable'] = JobsTable(selectedjob)
        send_data['job'] = selectedjob
        send_data['tickets'] = ChangeOrders.objects.filter(job_number=selectedjob, is_t_and_m=True,
                                                           is_ticket_signed=False)
        send_data['open_cos'] = ChangeOrders.objects.filter(job_number=selectedjob, is_closed=False,
                                                            is_approved=False) & ChangeOrders.objects.filter(
            job_number=selectedjob,
            is_t_and_m=False) | ChangeOrders.objects.filter(job_number=selectedjob, is_t_and_m=True,
                                                            is_ticket_signed=True)
        send_data['approved_cos'] = ChangeOrders.objects.filter(job_number=selectedjob, is_closed=False,
                                                                is_approved=True)
        send_data['equipments'] = Inventory.objects.filter(job_number=selectedjob).order_by('inventory_type')
        send_data['rentals'] = Rentals.objects.filter(job_number=selectedjob, off_rent_number__isnull=True)
        send_data['wallcovering2'] = Wallcovering.objects.filter(job_number=selectedjob)
        send_data['wc_not_ordereds'] = Wallcovering.objects.filter(job_number=selectedjob,
                                                                   orderitems1__isnull=True)
        send_data['wc_ordereds'] = OrderItems.objects.filter(order__job_number=selectedjob, is_satisfied=False)
        send_data['packages'] = Packages.objects.filter(delivery__order__job_number=selectedjob)
        send_data['deliveries'] = OutgoingItem.objects.filter(outgoing_event__job_number=selectedjob)
        send_data['submittals'] = Submittals.objects.filter(job_number=selectedjob)
        send_data['subcontracts'] = Subcontracts.objects.filter(job_number=selectedjob)
        all_notes = JobNotesFilter(request.GET, queryset=JobNotes.objects.filter(job_number=selectedjob))
        send_data['all_notes'] = all_notes
        send_data['filtered_notes'] = all_notes.qs
        send_data['has_filter'] = any(field in request.GET for field in set(all_notes.get_fields()))
        if request.method == 'GET':
            made_already = False
            if 'admin' in request.GET:
                notes = JobNotes.objects.filter(job_number=selectedjob,
                                                type="auto_booking_note") | JobNotes.objects.filter(
                    job_number=selectedjob, type="auto_misc_note")
                made_already = True
                send_data['admin'] = 'admin'
            if 'start' in request.GET:
                send_data['start'] = 'start'
                if made_already == False:
                    notes = JobNotes.objects.filter(job_number=selectedjob, type="auto_start_date_note")
                    made_already = True
                else:
                    notes = notes | JobNotes.objects.filter(job_number=selectedjob, type="auto_start_date_note")
                    made_already = True
            if 'field' in request.GET:
                send_data['field'] = 'field'
                if made_already == False:
                    notes = JobNotes.objects.filter(job_number=selectedjob,
                                                    type="employee_note") | JobNotes.objects.filter(
                        job_number=selectedjob, type="daily_report")
                    made_already = True
                else:
                    notes = notes | JobNotes.objects.filter(job_number=selectedjob,
                                                            type="employee_note") | JobNotes.objects.filter(
                        job_number=selectedjob, type="daily_report")
                    made_already = True
            if 'change_order' in request.GET:
                send_data['change_order'] = 'change_order'
                if made_already == False:
                    notes = JobNotes.objects.filter(job_number=selectedjob, type="auto_co_note")
                    made_already = True
                else:
                    notes = notes | JobNotes.objects.filter(job_number=selectedjob, type="auto_co_note")
                    made_already = True
            if 'submittal' in request.GET:
                send_data['submittal'] = 'submittal'
                if made_already == False:
                    notes = JobNotes.objects.filter(job_number=selectedjob, type="auto_submittal_note")
                    made_already = True
                else:
                    notes = notes | JobNotes.objects.filter(job_number=selectedjob, type="auto_submittal_note")
                    made_already = True
            if made_already == False:
                notes = JobNotes.objects.filter(job_number=selectedjob)
        else:
            notes = JobNotes.objects.filter(job_number=selectedjob)
        send_data['notes'] = notes
        send_data['supers'] = Employees.objects.exclude(Q(job_title__description="Painter") | Q(active=False))
        return render(request, 'job_page.html', send_data)


@login_required(login_url='/accounts/login')
def book_new_job(request):
    allclients = Clients.objects.order_by('company')
    estimators = Employees.objects.exclude(job_title__description='Painter')
    superintendents = Employees.objects.exclude(job_title__description='Painter')
    pms = ClientEmployees.objects.values('name', 'id', 'person_pk')
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
        if request.POST['select_company'] == 'add_new':
            client = Clients.objects.create(company=request.POST['new_client'],
                                            bid_email=request.POST['new_client_bid_email'],
                                            phone=request.POST['new_client_phone'])

        else:
            client = Clients.objects.get(id=request.POST['select_company'])

        if request.POST['select_pm'] == 'use_below':
            client_pm = ClientEmployees.objects.create(id=client, name=request.POST['new_pm'],
                                                       phone=request.POST['new_pm_phone'],
                                                       email=request.POST['new_pm_email'])

        else:
            client_pm = ClientEmployees.objects.get(person_pk=request.POST['select_pm'])

        job = Jobs.objects.create(job_number=job_number, job_name=request.POST['job_name'],
                                  address=request.POST['address'], city=request.POST['city'],
                                  state=request.POST['state'],
                                  contract_status=request.POST['contract_status'],
                                  insurance_status=request.POST['insurance_status'], client=client, client_Pm=client_pm,
                                  start_date=request.POST['start_date'],
                                  status="Open", booked_date=date.today(),
                                  booked_by=request.user.first_name + " " + request.user.last_name,
                                  estimator=Employees.objects.get(id=request.POST['select_gpestimator']),
                                  notes=request.POST['email_job_note'], po_number=request.POST['po_number'])

        if request.POST['select_super'] == 'not_sure':
            checklist.append("get superintendent info")
        elif request.POST['select_super'] == 'use_below':
            job.client_Super = ClientEmployees.objects.create(id=client, name=request.POST['new_super'],
                                                              phone=request.POST['new_super_phone'],
                                                              email=request.POST['new_super_email'])

        else:
            job.client_Super = ClientEmployees.objects.get(person_pk=request.POST['select_super'])
        if request.POST['spray_scale'] != "": job.spray_scale = request.POST['spray_scale']
        if request.POST['brush_role'] != "": job.brush_role = request.POST['brush_role']
        if request.POST['t_m_nte_amount'] != "": job.t_m_nte_amount = request.POST['t_m_nte_amount']
        if request.POST['select_gpsuper'] != "not_sure": job.superintendent = Employees.objects.get(
            id=request.POST['select_gpsuper'])
        # add email message request.POST['email_job_note']
        if request.POST['contract_amount'] != "": contract_amount = request.POST['contract_amount']
        if request.POST['painting_budget'] != "": painting_budget = request.POST['painting_budget']
        if request.POST['wallcovering_budget'] != "": wallcovering_budget = request.POST['wallcovering_budget']
        if 'is_t_m_job' in request.POST: job.is_t_m_job = True
        if 'on_base2' in request.POST: job.is_on_base = True
        if 'is_wage_rate' in request.POST: job.is_wage_scale = True
        if 'is_bonded' in request.POST: job.is_bonded = True
        if 'has_special_paint' in request.POST: job.special_paint_needed = True
        if 'has_paint' in request.POST: job.has_paint = True
        if 'has_wallcovering' in request.POST: job.has_wallcovering = True
        if 'has_submittals' in request.POST:  job.submittals_needed = True
        job.start_date_checked = date.today()
        job.save()
        JobNotes.objects.create(job_number=job,
                                note="Start Date at Booking: " + job.start_date + " " + request.POST['date_note'],
                                type="auto_start_date_note", date=date.today(),
                                user=Employees.objects.get(user=request.user))
        JobNotes.objects.create(job_number=job,
                                note="New Job Booked By: " + request.user.first_name + " " + request.user.last_name + ": " +
                                     request.POST['email_job_note'],
                                type="auto_booking_note", date=date.today(),
                                user=Employees.objects.get(user=request.user))
        email_body = "New Job Booked \n" + job.job_number + "\n" + job.job_name + "\n" + job.client.company
        Email.sendEmail("New Job - " + job.job_name, email_body, ['joe@gerloffpainting.com'], False)
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
