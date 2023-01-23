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
from equipment.tables import JobsTable
from equipment.filters import JobsFilter
from django_tables2 import SingleTableView


def change_start_date(request,jobnumber,previous):
    jobs = Jobs.objects.get(job_number=jobnumber)
    format_date = jobs.start_date.strftime("%Y-%m-%d")
    previous_page = previous
    if request.method == 'POST':
        jobs.start_date=request.POST['start_date']
        if 'is_active' in request.POST:
            jobs.is_active=True
        jobs.start_date_checked = date.today()
        new_note = JobNotes.objects.create(job_number=jobs, note=request.POST['date_note'],type="auto_start_date_note",user =request.user.first_name+request.user.last_name, date=date.today())
        new_note.save()
        jobs.save()
        if previous == 'jobpage':
            return redirect('job_page',jobnumber='ALL')
        else:
            return redirect('super_home')
    return render(request, "change_start_date.html", {'jobs': jobs,'formatdate': format_date, 'previous_page': previous_page})
def update_job_info(request,jobnumber):
    return render(request, "update_job_info.html")

def jobs_home(request):
    response = redirect('/')
    return response


def job_page(request,jobnumber):
    if jobnumber == 'ALL':
        search_jobs = JobsFilter(request.GET, queryset=Jobs.objects.filter(status="Open"))
        jobstable = JobsTable(search_jobs.qs)
        has_filter = any(field in request.GET for field in set(search_jobs.get_fields()))
        tickets = ChangeOrders.objects.filter(job_number__status="Open", is_t_and_m=True, is_ticket_signed=False)
        open_cos = ChangeOrders.objects.filter(job_number__status="Open", is_closed=False, is_approved=False) & ChangeOrders.objects.filter(is_t_and_m=False) | ChangeOrders.objects.filter(is_t_and_m=True, is_ticket_signed=True)
        approved_cos =  ChangeOrders.objects.filter(job_number__status="Open",is_closed=False,is_approved=True)
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
    elif request.method == 'GET':
        jobstable = JobsTable(Jobs.objects.filter(job_number=jobnumber))
        jobs = Jobs.objects.filter(job_number=jobnumber)[0:2000]
        tickets = ChangeOrders.objects.filter(job_number=jobnumber, is_t_and_m=True, is_ticket_signed=False)
        open_cos = ChangeOrders.objects.filter(job_number=jobnumber, is_closed=False, is_approved=False) & ChangeOrders.objects.filter(is_t_and_m=False) | ChangeOrders.objects.filter(is_t_and_m=True, is_ticket_signed=True)
        approved_cos =  ChangeOrders.objects.filter(job_number=jobnumber,is_closed=False,is_approved=True)
        equipment = Inventory.objects.filter(job_number=jobnumber).order_by('inventory_type')
        rentals = Rentals.objects.filter(job_number=jobnumber)
        wallcovering2 = Wallcovering.objects.filter(job_number = jobnumber)
        wc_not_ordereds = Wallcovering.objects.filter(job_number__job_number=jobnumber, orderitems1__isnull=True)
        # wc_not_ordereds = []
        # for x in wallcovering2:
        #     if x.orderitems1.count() > 0:
        #         print(x)
        #     else:
        #         wc_not_ordereds.append(x)
        wc_ordereds = OrderItems.objects.filter(order__job_number=jobnumber, is_satisfied=False)
        packages = Packages.objects.filter(delivery__order__job_number = jobnumber)
        deliveries = OutgoingItem.objects.filter(outgoing_event__job_number=jobnumber)
        submittals = Submittals.objects.filter(job_number = jobnumber)
        subcontracts = Subcontracts.objects.filter(job_number = jobnumber)
        return render(request, "job_page.html",
                      {'jobstable': jobstable,
                       'subcontracts': subcontracts, 'submittals': submittals, 'packages': packages,
                       'deliveries': deliveries, 'wc_not_ordereds': wc_not_ordereds, 'wc_ordereds': wc_ordereds,
                       'jobs': jobs, 'tickets': tickets, 'open_cos': open_cos, 'approved_cos': approved_cos,
                       'equipments': equipment, 'rentals': rentals})


def book_new_job(request):
        allclients = Clients.objects.order_by('company')[0:2000]
        pms = ClientEmployees.objects.values('name', 'id', 'person_pk')[0:1000]
        send_employees = Employees.objects.filter(title="Superintendent")[0:2000]
        prices_json = json.dumps(list(pms), cls=DjangoJSONEncoder)

        return render(request, 'book_new_job.html',
                      {'data': prices_json, 'allclients': allclients, 'employees': send_employees})


def register(request):
    if request.method == 'POST':
        checklist = []
        if request.POST['job_number'] == "":
            if JobNumbers.objects.latest("id").number == "9990":
                new_letter = chr(ord(JobNumbers.objects.latest("id").letter) + 1)
                new_job_number = JobNumbers(letter=new_letter, number="0010")
                new_job_number.save()
                job_number = JobNumbers.objects.latest("id").letter + JobNumbers.objects.latest("id").number
            else:
                new_number = int(JobNumbers.objects.latest("id").number) + 10
                new_number_convert = str(new_number)
                if new_number < 100:
                    new_job_number = JobNumbers(letter=JobNumbers.objects.latest("id").letter, number="00" + new_number_convert)
                elif new_number < 1000:
                    new_job_number = JobNumbers(letter=JobNumbers.objects.latest("id").letter, number="0" + new_number_convert)
                else:
                    new_job_number = JobNumbers(letter=JobNumbers.objects.latest("id").letter, number=new_number_convert)
                new_job_number.save()
                job_number = JobNumbers.objects.latest("id").letter + JobNumbers.objects.latest("id").number
        else:
            job_number = request.POST['job_number']

        job_name = request.POST['job_name']
        address = request.POST['address']
        city = request.POST['city']
        state = request.POST['state']
        if request.POST['on_base'] == 'notchecked':
            is_on_base = False
        else:
            is_on_base = True
        spray_scale = request.POST['spray_scale']
        brush_role = request.POST['brush_role']
        if request.POST['is_t_m_job'] == 'notchecked':
            is_t_m_job = False
        else:
            is_t_m_job = True

        t_m_nte_amount = request.POST['t_m_nte_amount']

        if request.POST['contract_status'] == 'contract_not_received':
            contract_status = 2
            checklist.append("waiting for contract")
        elif request.POST['contract_status'] == 'contract_received':
            contract_status = 1
        else: #contract not required
            contract_status = 3

        if request.POST['insurance_status'] == 'coi_not_received':
            insurance_status = 2
            checklist.append("get coi")
        elif request.POST['insurance_status'] == 'coi_received':
            insurance_status = 1
        else: #contract not required
            insurance_status = 3

        if request.POST['select_company'] == 'add_new':
            new_client = request.POST['new_client']
            new_client_phone = request.POST['new_client_phone']
            new_client_email = request.POST['new_client_email']
            client = Clients(company=new_client, bid_email=new_client_email,phone=new_client_phone)
            client.save();
            client_id = Clients.objects.latest('id').id
        else:
            client_id = request.POST['select_company']

        if request.POST['select_PM'] == 'not_sure':
            checklist.append("get pm info")
            client_pm = 'not_sure'
        elif request.POST['select_pm'] == 'use_below':
            new_name = request.POST['new_pm']
            new_phone = request.POST['new_pm_phone']
            new_email = request.POST['new_pm_email']
            new_id = client_id
            client_employee = ClientEmployees(id=new_ID, name=new_name, phone=new_phone,email=new_email)
            client_employee.save;
            client_pm = ClientEmployees.objects.latest('person_pk').person_pk
        else:
            client_pm = request.POST['select_pm']

        if request.POST['select_super'] == 'not_sure':
            checklist.append("get superintendent info")
            client_super='not_sure'
        elif request.POST['select_super'] == 'use_below':
            new_name = request.POST['new_super']
            new_phone = request.POST['new_super_phone']
            new_email = request.POST['new_super_email']
            new_ID = client_id
            client_employee = ClientEmployees(id=new_ID, name=new_name, phone=new_phone,email=new_email)
            client_employee.save;
            client_super = ClientEmployees.objects.latest('person_pk').person_pk
        else:
            client_super = request.POST['select_super']

        superintendent = request.POST['select_gpsuper']
        if request.POST['has_paint'] == 'true':
                has_paint = True
        else:
                has_paint = False
        if request.POST['has_wallcovering'] == 'true':
                has_wallcovering = True
        else:
                has_wallcovering = False

        start_date = request.POST['start_date']

        #add email message request.POST['email_job_note']
        contract_amount = request.POST['contract_amount']
        painting_budget = request.POST['painting_budget']
        wallcovering_budget = request.POST['wallcovering_budget']

        jobs = Jobs.objects.create(job_number=job_number, job_name=job_name, address=address, city=city, state=state,
                                   is_on_base=is_on_base, is_t_m_job=is_t_m_job, contract_status=contract_status,
                                   insurance_status=insurance_status, client=Clients.objects.get(id=client_id),
                                   has_wallcovering=has_wallcovering, has_paint=has_paint, start_date=start_date,
                                   status="Open", booked_date=date.today())
        if client_super != 'not_sure':
            Jobs.objects.filter(job_number=job_number).update(client_super=ClientEmployees.objects.get(person_pk=client_super))
        if client_pm != 'not_sure':
            Jobs.objects.filter(job_number=job_number).update(client_pm=ClientEmployees.objects.get(person_pk=client_pm))
            Jobs.objects.filter(job_number=job_number).update(client_submittal_contact=ClientEmployees.objects.get(person_pk=client_pm))
            Jobs.objects.filter(job_number=job_number).update(client_co_contact=ClientEmployees.objects.get(person_pk=client_pm))
        if is_t_m_job == False:
            Jobs.objects.filter(job_number=job_number).update(contract_amount=contract_amount)
        if t_m_nte_amount != "":
            Jobs.objects.filter(job_number=job_number).update( t_m_nte_amount=t_m_nte_amount)
        if spray_scale != "":
            Jobs.objects.filter(job_number=job_number).update(spray_scale=spray_scale)
        if brush_role != "":
            Jobs.objects.filter(job_number=job_number).update(brush_role=brush_role)
        if painting_budget != "":
            Jobs.objects.filter(job_number=job_number).update(painting_budget=painting_budget)
        if wallcovering_budget != "":
            Jobs.objects.filter(job_number=job_number).update(wallcovering_budget=wallcovering_budget)
        if superintendent != 'not_sure':
            Jobs.objects.filter(job_number=job_number).update(superintendent=Employees.objects.get(id=superintendent))
        # job_note = Job_Notes(job_number=job_number, note = "Start Date at Booking: " + start_date + " " + request.POST['date_note'], type="Start_Date", date = date.today(), note_date = date.today())
        # job_note.save;
        # job_note = Job_Notes(job_number=job_number, note = request.POST['email_job_note'], type="PM", date = date.today(), note_date = date.today())
        # job_note.save;
        #
        # for x in checklist:
        #     checklist = Checklist(job_number=job_number, checklist_item=x, category="PM")
        #     checklist.save();

        response = redirect('/')
        return response

