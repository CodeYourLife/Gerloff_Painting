from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from rentals.models import Rentals
from datetime import date, timedelta
from employees.models import Employees
from jobs.models import Jobs, JobNotes
from changeorder.models import ChangeOrders
from equipment.models import *
from console.models import *
from subcontractors.models import *
from django.db.models import Q
from equipment.filters import JobsFilter2
from django.http import HttpResponse
from jobs.JobMisc import start_date_change, gerloff_super_change
import json
from django.core.serializers.json import DjangoJSONEncoder

def super_ajax(request):
    if request.is_ajax():
        job = Jobs.objects.get(job_number=request.GET['job_number'])
        if 'build_notes' in request.GET:
            print("PUMPKIN")
            job_notes = JobNotes.objects.filter(Q(type="auto_start_date_note")| Q(type = "employee_note"),job_number=job)
            notes=[]
            for note in job_notes:
                notes.append({'note': note.note, 'user': note.user,
                              'date': str(note.date)})
            data_details = {'notes': notes}
            return HttpResponse(json.dumps(data_details))
        else:
            if job.is_active == True:
                if request.GET['is_active'] == "true":
                    status=3
                else:
                    status=2
            else:
                if request.GET['is_active'] == "true":
                    status=1
                else:
                    status=3
            if str(job.start_date) != str(request.GET['start_date']):
                datechange=True
            else: datechange=False
            start_date_change(job, request.GET['start_date'], status, request.GET['notes'],
                              request.user.first_name + " " + request.user.last_name, datechange)
            job.save()
            new_date = Jobs.objects.get(job_number=request.GET['job_number']).start_date
            print(new_date.strftime("%b"))
            print(new_date.strftime("%d"))
            print(new_date.strftime("%Y"))
            new_date= Jobs.objects.get(job_number=request.GET['job_number']).start_date.strftime("%b %d,%Y")
            # new_date = str(Jobs.objects.get(job_number=request.GET['job_number']).start_date)
            data_details = {'new_date':new_date,'is_active':request.GET['is_active']}
            return HttpResponse(json.dumps(data_details))

@login_required(login_url='/accounts/login')
def super_home(request, super, filter):
    print(request.GET)
    send_data = {}
    if super == 'AUTO':
        employee= Employees.objects.get(user=request.user)
        if employee.job_title.description == 'Superintendent':
            super=employee.id
        else: super = 'ALL'
    selected_superid = super
    if request.is_ajax():
        print("HOW BOUT THIS")
        return HttpResponse("PUMPKIN")
    if request.method == 'POST':
        if 'selected_super' in request.POST:
            if request.POST['selected_super'] == 'all':
                selected_superid = 'ALL'
            else:
                selected_superid = request.POST['selected_super']
        else:
            print(request.POST['date_note'])
    if selected_superid == 'ALL':
        send_data['equipment'] = Inventory.objects.exclude(job_number=None)
        send_data['equipment_count'] = Inventory.objects.exclude(job_number=None).count()
        send_data['rentals'] = Rentals.objects.filter(off_rent_number__isnull=True)
        send_data['rentals_count'] = Rentals.objects.filter(off_rent_number__isnull=True).count()
        send_data['tickets'] = ChangeOrders.objects.filter(is_t_and_m=True, is_ticket_signed=False, is_closed=False)
        send_data['tickets_count'] = ChangeOrders.objects.filter(is_t_and_m=True, is_ticket_signed=False,
                                                                 is_closed=False).count()
        send_data['subcontractor_count'] = Subcontracts.objects.exclude(job_number=None)

        if filter == 'UPCOMING':
            send_data['filtered'] = 'filtered'
            search_jobs = JobsFilter2(request.GET, queryset=Jobs.objects.filter(is_closed=False, is_active=False).order_by(
                'start_date'))
        else:
            search_jobs = JobsFilter2(request.GET, queryset=Jobs.objects.filter(is_closed=False).order_by('start_date'))
    else:
        selected_super = Employees.objects.get(id=selected_superid)
        send_data['equipment'] = Inventory.objects.filter(job_number__superintendent=selected_super).order_by(
            'job_number', 'inventory_type')
        send_data['equipment_count'] = Inventory.objects.filter(job_number__superintendent=selected_super).order_by(
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

        if filter == 'UPCOMING':
            send_data['filtered'] = 'filtered'
            search_jobs = JobsFilter2(request.GET, queryset=Jobs.objects.filter(is_closed=False, is_active=False,
                                       superintendent=Employees.objects.get(id=selected_superid)).order_by(
                'start_date'))
            # jobs = Jobs.objects.filter(is_closed=False, is_active=False,
            #                            superintendent=Employees.objects.get(id=selected_superid)).order_by(
            #     'start_date')
        else:
            search_jobs = JobsFilter2(request.GET, queryset=Jobs.objects.filter(is_closed=False,
                                       superintendent=Employees.objects.get(id=selected_superid)).order_by(
                'start_date'))
            # jobs = Jobs.objects.filter(is_closed=False,
            #                            superintendent=Employees.objects.get(id=selected_superid)).order_by(
            #     'start_date')
    if any(field in request.GET for field in set(search_jobs.get_fields())) == True:
        send_data['has_filter'] = True
    send_data['search_jobs'] = search_jobs
    send_data['jobs'] = search_jobs.qs
    # send_data['jobs'] = jobs
    send_data['supers'] = Employees.objects.exclude(Q(job_title__description="Painter") | Q(active=False))
    send_data['todays_date'] = date.today() - timedelta(days=45)
    return render(request, "super_home.html", send_data)


@login_required(login_url='/accounts/login')
def filter_super(request):  # I DONT THINK THIS IS USED ANYWHERE
    if request.method == 'POST':
        jobs = Jobs.objects.filter(superintendent=request.POST['selected_super'])[0:2000]
        supers = Employees.objects.all()[0:2000]
        selected_super = Employees.objects.get(id=request.POST['selected_super'])
        equipment = Inventory.objects.filter(job_number__superintendent=selected_super)
        rentals = Rentals.objects.filter(job_number__superintendent=selected_super, off_rent_number__isnull=True)
        # equipment = []
        # for x in equipmentlist:
        #        equipjobnumber = x.job_number.job_number
        #        if Jobs.objects.filter(job_number = equipjobnumber,superintendent=request.POST['selected_super']).exists():
        #            equipment.append(x)
        return render(request, "super_home.html",
                      {'rentals': rentals, 'selected_super': selected_super, 'jobs': jobs, 'supers': supers,
                       "equipment": equipment})
