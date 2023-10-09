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
from jobs.models import Jobs, JobNotes, JobNumbers, ClientEmployees, Clients
from employees.models import *
from equipment.models import Inventory
from rentals.models import Rentals
from subcontractors.models import *
from wallcovering.models import Wallcovering, Packages, OutgoingItem, OrderItems
from submittals.models import *
from console.misc import Email

@login_required(login_url='/accounts/login')
def change_start_date(request, jobnumber, previous):
    jobs = Jobs.objects.get(job_number=jobnumber)
    format_date = jobs.start_date.strftime("%Y-%m-%d")
    previous_page = previous
    if request.method == 'POST':
        jobs.start_date = request.POST['start_date']
        if 'is_active' in request.POST:
            jobs.is_active = True
        jobs.start_date_checked = date.today()
        new_note = JobNotes.objects.create(job_number=jobs, note=request.POST['date_note'], type="auto_start_date_note",
                                           user=request.user.first_name + request.user.last_name, date=date.today())
        new_note.save()
        jobs.save()
        if previous == 'jobpage':
            return redirect('job_page', jobnumber='ALL')
        else:
            return redirect('super_home')
    return render(request, "change_start_date.html",
                  {'jobs': jobs, 'formatdate': format_date, 'previous_page': previous_page})

@login_required(login_url='/accounts/login')
def update_job_info(request, jobnumber):
    return render(request, "update_job_info.html")

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
    elif request.method == 'GET':
        jobstable = JobsTable(Jobs.objects.filter(job_number=jobnumber))
        jobs = Jobs.objects.filter(job_number=jobnumber)[0:2000]
        tickets = ChangeOrders.objects.filter(job_number=jobnumber, is_t_and_m=True, is_ticket_signed=False)
        open_cos = ChangeOrders.objects.filter(job_number=jobnumber, is_closed=False,
                                               is_approved=False) & ChangeOrders.objects.filter(
            is_t_and_m=False) | ChangeOrders.objects.filter(is_t_and_m=True, is_ticket_signed=True)
        approved_cos = ChangeOrders.objects.filter(job_number=jobnumber, is_closed=False, is_approved=True)
        equipment = Inventory.objects.filter(job_number=jobnumber).order_by('inventory_type')
        rentals = Rentals.objects.filter(job_number=jobnumber)
        wallcovering2 = Wallcovering.objects.filter(job_number=jobnumber)
        wc_not_ordereds = Wallcovering.objects.filter(job_number__job_number=jobnumber, orderitems1__isnull=True)
        # wc_not_ordereds = []
        # for x in wallcovering2:
        #     if x.orderitems1.count() > 0:
        #         print(x)
        #     else:
        #         wc_not_ordereds.append(x)
        wc_ordereds = OrderItems.objects.filter(order__job_number=jobnumber, is_satisfied=False)
        packages = Packages.objects.filter(delivery__order__job_number=jobnumber)
        deliveries = OutgoingItem.objects.filter(outgoing_event__job_number=jobnumber)
        submittals = Submittals.objects.filter(job_number=jobnumber)
        subcontracts = Subcontracts.objects.filter(job_number=jobnumber)
        return render(request, "job_page.html",
                      {'jobstable': jobstable,
                       'subcontracts': subcontracts, 'submittals': submittals, 'packages': packages,
                       'deliveries': deliveries, 'wc_not_ordereds': wc_not_ordereds, 'wc_ordereds': wc_ordereds,
                       'jobs': jobs, 'tickets': tickets, 'open_cos': open_cos, 'approved_cos': approved_cos,
                       'equipments': equipment, 'rentals': rentals})


@login_required(login_url='/accounts/login')
def book_new_job(request):
    allclients = Clients.objects.order_by('company')[0:2000]
    pms = ClientEmployees.objects.values('name', 'id', 'person_pk')[0:1000]
    # send_employees = Employees.objects.filter(job_title="Superintendent")[0:2000]
    prices_json = json.dumps(list(pms), cls=DjangoJSONEncoder)

    return render(request, 'book_new_job.html',
                  {'data': prices_json, 'allclients': allclients, 'employees': {}})


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
        if request.POST['on_base2'] == 'notchecked':
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
            client = Clients.objects.create(company=request.POST['new_client'], bid_email=request.POST['new_client_bid_email'],
                                                   phone=request.POST['new_client_phone'])
        else:
            client = Clients.objects.get(id=request.POST['select_company'])
        # if request.POST['select_pm'] == 'not_sure':
        #     checklist.append("get pm info")
        #     client_pm = 'not_sure'
        if request.POST['select_pm'] == 'use_below':
            client_pm = ClientEmployees.objects.create(id=client, name=request.POST['new_pm'], phone=request.POST['new_pm_phone'], email=request.POST['new_pm_email'])
        else:
            client_pm = ClientEmployees.objects.get(person_pk=request.POST['select_pm'])

        if request.POST['select_super'] == 'not_sure':
            checklist.append("get superintendent info")
            client_super = 'not_sure'
        elif request.POST['select_super'] == 'use_below':
            client_super = ClientEmployees.objects.create(id=client, name=request.POST['new_super'], phone=request.POST['new_super_phone'], email=request.POST['new_super_email'])
        else:
            client_super = ClientEmployees.objects.get(person_pk=request.POST['select_super'])

        superintendent = request.POST['select_gpsuper']


        start_date = request.POST['start_date']

        # add email message request.POST['email_job_note']
        contract_amount = request.POST['contract_amount']
        painting_budget = request.POST['painting_budget']
        wallcovering_budget = request.POST['wallcovering_budget']

        job = Jobs.objects.create(job_number=job_number, job_name=job_name, address=address, city=city, state=state,
                                  is_on_base=is_on_base, is_t_m_job=is_t_m_job, contract_status=contract_status,
                                  insurance_status=insurance_status, client=client,start_date=start_date,
                                  status="Open", booked_date=date.today(),booked_by=request.user.first_name + " " + request.user.last_name)
        if 'is_wage_rate' in request.POST:
            job.is_wage_scale = True
        if 'has_special_paint' in request.POST:
            job.has_special_paint = True
            job.special_paint_needed = True
        if client_super != 'not_sure':
            job.client_Super = client_super
        job.client_Pm = client_pm
        #job.client_submittal_contact = client_pm
        #job.client_co_contact = client_pm
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
        Email.sendEmail("New Job - " + job.job_name, email_body, 'joe@gerloffpainting.com')
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
