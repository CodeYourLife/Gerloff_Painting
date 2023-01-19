
from django.shortcuts import render, redirect
from console.models import *
from datetime import date, timedelta
import datetime

def super_home(request):
    jobs = Jobs.objects.all()[0:2000]
    supers = Employees.objects.all()[0:2000]
    equipment = Inventory.objects.exclude(job_number=None)
    rentals = Rentals.objects.filter(off_rent_date__isnull=True)
    tickets = ChangeOrders.objects.filter(is_t_and_m=True,is_ticket_signed=False,is_closed=False)
    todays_date = date.today() - timedelta(days=45)
    return render(request, "super_home.html", {'tickets':tickets,'rentals':rentals,'jobs': jobs, 'supers': supers, "equipment": equipment,'todays_date':todays_date})

def filter_super(request):
    if request.method == 'POST':
        jobs = Jobs.objects.filter(superintendent= request.POST['selected_super'])[0:2000]
        supers = Employees.objects.all()[0:2000]
        #equipmentlist = Inventory.objects.exclude(job_number = None)
        selected_super = Employees.objects.get(id=request.POST['selected_super'])
        equipment = Inventory.objects.filter(job_number__superintendent= selected_super)
        rentals = Rentals.objects.filter(job_number__superintendent= selected_super,off_rent_date__isnull=True)
        #equipment = []
        #for x in equipmentlist:
        #        equipjobnumber = x.job_number.job_number
        #        if Jobs.objects.filter(job_number = equipjobnumber,superintendent=request.POST['selected_super']).exists():
        #            equipment.append(x)
        return render(request, "super_home.html", {'rentals':rentals,'selected_super':selected_super,'jobs': jobs, 'supers': supers, "equipment": equipment})

