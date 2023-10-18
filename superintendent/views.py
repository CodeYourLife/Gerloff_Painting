from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from rentals.models import Rentals
from datetime import date, timedelta
from employees.models import Employees
from jobs.models import Jobs
from changeorder.models import ChangeOrders
from equipment.models import *
from console.models import *


@login_required(login_url='/accounts/login')
def super_home(request, super, filter):
    send_data = {}
    selected_superid = super
    if request.method == 'POST':
        if request.POST['selected_super'] == 'all':
            selected_superid = 'ALL'
        else:
            selected_superid = request.POST['selected_super']
    if selected_superid == 'ALL':
        if filter == 'UPCOMING':
            send_data['filtered'] = 'filtered'
            jobs = Jobs.objects.filter(is_active=False).order_by('start_date')
        else:
            jobs = Jobs.objects.all().order_by('start_date')
    else:
        send_data['selected_super'] = Employees.objects.get(id=selected_superid)
        if filter == 'UPCOMING':
            send_data['filtered'] = 'filtered'
            jobs = Jobs.objects.filter(is_active=False,
                                                    superintendent=Employees.objects.get(id=selected_superid)).order_by(
                'start_date')
        else:
            jobs = Jobs.objects.filter(superintendent=Employees.objects.get(id=selected_superid)).order_by(
                'start_date')
    send_data['jobs'] = jobs
    send_data['supers'] = Employees.objects.exclude(job_title__description="Painter")
    send_data['equipment'] = Inventory.objects.exclude(job_number=None)
    send_data['rentals'] = Rentals.objects.filter(off_rent_date__isnull=True)
    send_data['tickets'] = ChangeOrders.objects.filter(is_t_and_m=True, is_ticket_signed=False, is_closed=False)
    send_data['todays_date'] = date.today() - timedelta(days=45)
    return render(request, "super_home.html", send_data)


@login_required(login_url='/accounts/login')
def filter_super(request):
    if request.method == 'POST':
        jobs = Jobs.objects.filter(superintendent=request.POST['selected_super'])[0:2000]
        supers = Employees.objects.all()[0:2000]
        # equipmentlist = Inventory.objects.exclude(job_number = None)
        selected_super = Employees.objects.get(id=request.POST['selected_super'])
        equipment = Inventory.objects.filter(job_number__superintendent=selected_super)
        rentals = Rentals.objects.filter(job_number__superintendent=selected_super, off_rent_date__isnull=True)
        # equipment = []
        # for x in equipmentlist:
        #        equipjobnumber = x.job_number.job_number
        #        if Jobs.objects.filter(job_number = equipjobnumber,superintendent=request.POST['selected_super']).exists():
        #            equipment.append(x)
        return render(request, "super_home.html",
                      {'rentals': rentals, 'selected_super': selected_super, 'jobs': jobs, 'supers': supers,
                       "equipment": equipment})
