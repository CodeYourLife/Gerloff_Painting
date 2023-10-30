from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from rentals.models import Rentals
from datetime import date, timedelta
from employees.models import Employees
from jobs.models import Jobs
from changeorder.models import ChangeOrders
from equipment.models import *
from console.models import *
from subcontractors.models import *
from django.db.models import Q
from equipment.filters import JobsFilter2


@login_required(login_url='/accounts/login')
def super_home(request, super, filter):
    print(request.GET)
    send_data = {}
    selected_superid = super
    if request.method == 'POST':
        if request.POST['selected_super'] == 'all':
            selected_superid = 'ALL'
        else:
            selected_superid = request.POST['selected_super']
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
