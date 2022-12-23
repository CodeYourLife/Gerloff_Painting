from django.views.generic import ListView
from console.models import *
from.tables import JobsTable, EquipmentTable
from django_tables2 import SingleTableView
from django.shortcuts import render, redirect

# class JobsListView(SingleTableView):
#     model = Jobs
#     table_class = JobsTable
#     template_name = 'DELETEjobs.html'


# def jobs_list(request):
#     table = JobsTable(Jobs.objects.all())
#
#     return render(request, "DELETEjobs.html", {
#         "table": table
#     })


# def select_super(request):
#     send_employees = Employees.objects.filter(title="Superintendent")[0:2000]
#     return render(request, "DELETEselect_super.html",{'employees':send_employees})

# def goto_super2(request): #changing view to add buttons, may delete this
#     if request.method == 'POST':
#         jobs = JobsTable(Jobs.objects.filter(superintendent=request.POST['select_GPSuper']))
#         equipmentlist = Inventory.objects.exclude(job_number = "")
#         inventorys = []
#         for x in equipmentlist:
#                 print(x.item)
#                 equipjobnumber = x.job_number.job_number
#                 if Jobs.objects.filter(job_number = equipjobnumber,superintendent=request.POST['select_gpsuper']).exists():
#                     inventorys.append(x)
#                     print("added")
#                 else:
#                     print("no")
#         equipment = EquipmentTable(inventorys)
#         supername = Employees.objects.get(id=request.POST['select_gpsuper'])
#         return render(request, "DELETEsuper_home.html",{'super':request.POST['select_gpsuper'],"jobs": jobs, "equipment":equipment, "supername": supername})

# def goto_super(request):
#     if request.method == 'POST':
#         jobs = JobsTable(Jobs.objects.filter(superintendent=request.POST['select_gpsuper']))
#         equipmentlist = Inventory.objects.exclude(job_number = "")
#         inventorys = []
#         for x in equipmentlist:
#                 print(x.item)
#                 equipjobnumber = x.job_number.job_number
#                 if Jobs.objects.filter(job_number = equipjobnumber,superintendent=request.POST['select_gpsuper']).exists():
#                     inventorys.append(x)
#                     print("added")
#                 else:
#                     print("no")
#         equipment = EquipmentTable(inventorys)
#         supername = Employees.objects.get(id=request.POST['select_gpsuper'])
#         return render(request, "DELETEsuper_home.html",{'super':request.POST['select_gpsuper'],"jobs": jobs, "equipment":equipment, "supername": supername})


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
        #equipment = []
        #for x in equipmentlist:
        #        equipjobnumber = x.job_number.job_number
        #        if Jobs.objects.filter(job_number = equipjobnumber,superintendent=request.POST['selected_super']).exists():
        #            equipment.append(x)
        return render(request, "super_home.html", {'jobs': jobs, 'supers': supers, "equipment": equipment})

