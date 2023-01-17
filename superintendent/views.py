
from django.shortcuts import render, redirect
from console.models import *


def super_home(request):
    jobs = Jobs.objects.all()[0:2000]
    supers = Employees.objects.all()[0:2000]
    equipment = Inventory.objects.exclude(job_number= None)
    return render(request, "super_home.html", {'jobs': jobs, 'supers': supers, "equipment": equipment})

def filter_super(request):
    if request.method == 'POST':
        jobs = Jobs.objects.filter(superintendent= request.POST['selected_super'])[0:2000]
        supers = Employees.objects.all()[0:2000]
        #equipmentlist = Inventory.objects.exclude(job_number = None)
        equipment = Inventory.objects.filter(job_number__superintendent= request.POST['selected_super'])
        selected_super= Employees.objects.get(id=request.POST['selected_super'])
        #equipment = []
        #for x in equipmentlist:
        #        equipjobnumber = x.job_number.job_number
        #        if Jobs.objects.filter(job_number = equipjobnumber,superintendent=request.POST['selected_super']).exists():
        #            equipment.append(x)
        return render(request, "super_home.html", {'selected_super':selected_super,'jobs': jobs, 'supers': supers, "equipment": equipment})

