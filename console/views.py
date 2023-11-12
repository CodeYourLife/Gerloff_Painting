from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import login_required
import changeorder.models
import employees.models
import equipment.models
import jobs.models
from employees.models import *
from .models import *
from django.contrib.auth.models import User, auth
from django.shortcuts import render, redirect
from django.contrib import messages
import os
import os.path
import csv
from pathlib import Path
from console.misc import createfolder
from jobs.models import *
from accounts.models import *
from changeorder.models import *
from console.models import *
from employees.models import *
from equipment.models import *
from rentals.models import *
from subcontractors.models import *
from submittals.models import *
from superintendent.models import *
from wallcovering.models import *
import random


@login_required(login_url='/accounts/login')
def seperate_test(request):
    fileitem = request.FILES['filename']
    print(fileitem)
    fn = os.path.basename(fileitem.name)
    fn2 = os.path.join("C:/Trinity/", fn)
    open(fn2, 'wb').write(fileitem.file.read())
    return redirect('index')


@login_required(login_url='/accounts/login')
def index(request):
    send_data={}
    next_two_weeks = 0
    for x in Jobs.objects.filter(is_closed=False, is_active=False):
        if x.next_two_weeks() == True:
            next_two_weeks += 1
    send_data['missing'] = Inventory.objects.filter(status = "Missing").count()
    send_data['checked_out'] = Inventory.objects.filter(job_number__is_closed=False).count()
    send_data['closed_job'] = Inventory.objects.filter(job_number__is_closed=True).count()
    send_data['service'] = Inventory.objects.filter(service_vendor__isnull=False).count()
    send_data['pickup_requests'] = PickupRequest.objects.filter(is_closed=False).count()
    send_data['rentals'] = Rentals.objects.filter(off_rent_number = None).count()
    send_data['next_two_weeks'] = next_two_weeks
    send_data['needs_super'] = Jobs.objects.filter(superintendent__isnull = True).count()
    active_super = Employees.objects.get(user=request.user)
    send_data['super_equipment']=Inventory.objects.filter(job_number__superintendent = active_super).count()
    send_data['super_rentals'] = Rentals.objects.filter(job_number__superintendent = active_super).count()
    send_data['tickets'] = 0
    send_data['current_user'] = request.user.first_name
    next_two_weeks = 0
    for x in Jobs.objects.filter(is_closed=False, is_active=False,superintendent=active_super):
        if x.next_two_weeks() == True:
            next_two_weeks += 1
    send_data['super_jobs'] = next_two_weeks
    return render(request, 'index.html',send_data)


@login_required(login_url='/accounts/login')
def warehouse_home(request):
    send_data={}
    if PickupRequest.objects.filter(confirmed=True,is_closed=False).exists():
        send_data['pending_pickups'] = PickupRequest.objects.filter(confirmed=True,is_closed=False)
    return render(request, 'warehouse_home.html',send_data)


@login_required(login_url='/accounts/login')
def admin_home(request):
    send_data = {}
    send_data['employees'] = Employees.objects.filter(user__isnull=True)
    return render(request, 'admin_home.html', send_data)


@login_required(login_url='/accounts/login')
def grant_web_access(request):
    send_data = {}
    send_data['employees'] = Employees.objects.filter(user__isnull=True, pin__isnull=True)
    if request.method == 'POST':
        selected_employee = Employees.objects.get(id=request.POST['select_employee'])
        tester = False
        while tester == False:
            randomPin = random.randint(1000, 9999)
            tester = True
            for x in Employees.objects.filter(user__isnull=True, pin__isnull=False):
                if x.pin == randomPin:
                    tester = False
                    randomPin = random.randint(1000, 9999)
        selected_employee.pin = randomPin
        selected_employee.save()
        send_data['employees'] = Employees.objects.filter(user__isnull=True)
        return render(request, 'admin_home.html', send_data)

    return render(request, 'grant_web_access.html', send_data)


# Create your views here.
def register_user(request):
    send_data = {}
    send_data['employees'] = EmployeeLevels.objects.filter(user=None)
    if request.method == 'POST':
        # first_name = request.POST['first_name']
        # last_name = request.POST['last_name']
        username = request.POST['username']
        password1 = request.POST['password1']
        password2 = request.POST['password2']
        email = request.POST['email']
        if password1 == password2:
            if User.objects.filter(username=username).exists():
                messages.info(request, 'Username Taken')
                return redirect('register_user')
            else:
                user = User.objects.create_user(username=username, password=password1, email=email,
                                                first_name=Employees.objects.get(
                                                    id=request.POST['select_employee']).first_name,
                                                last_name=Employees.objects.get(
                                                    id=request.POST['select_employee']).last_name, is_active=False)
                user.save();
                employee = Employees.objects.get(id=request.POST['select_employee'])
                employee.user = user
                employee.save()
                return redirect('login')
        else:
            messages.info(request, 'password not matching...')
            return redirect('register_user')

    else:
        return render(request, 'register.html', send_data)


def import_csv2(request):
    equipment.models.InventoryItems4.objects.all().delete()
    equipment.models.InventoryItems3.objects.all().delete()
    equipment.models.InventoryItems2.objects.all().delete()
    equipment.models.InventoryItems.objects.all().delete()
    equipment.models.InventoryType.objects.all().delete()
    employees.models.MetricLevels.objects.all().delete()
    employees.models.MetricCategories.objects.all().delete()
    employees.models.TrainingTopic.objects.all().delete()
    employees.models.Metrics.objects.all().delete()

    with open("c:/sql_backup/certificationactionrequired.csv") as f:
        current_table = employees.models.CertificationActionRequired
        current_table.objects.all().delete()
        reader = csv.reader(f)
        line_count1 = 0
        found = 0
        for row in reader:
            if line_count1 == 0:
                for x in range(2):
                    if row[x] == "id":
                        a = x
                        found = found + 1
                    if row[x] == "action":
                        b = x
                        found = found + 1
                line_count1 = line_count1 + 1
                if found != 2:
                    raise ValueError('A very specific bad thing happened.')
            else:
                current_table.objects.create(id=row[a], action=row[b])

    with open("c:/sql_backup/certificationcategories.csv") as f:
        current_table = employees.models.CertificationCategories
        current_table.objects.all().delete()
        reader = csv.reader(f)
        line_count1 = 0
        found = 0
        for row in reader:
            if line_count1 == 0:
                for x in range(2):
                    if row[x] == "id":
                        a = x
                        found = found + 1
                    if row[x] == "description":
                        b = x
                        found = found + 1
                line_count1 = line_count1 + 1
                if found != 2:
                    raise ValueError('A very specific bad thing happened.')
            else:
                current_table.objects.create(id=row[a], description=row[b])

    with open("c:/sql_backup/employeelevels.csv") as f:
        current_table = employees.models.EmployeeLevels
        current_table.objects.all().delete()
        reader = csv.reader(f)
        line_count1 = 0
        found = 0
        for row in reader:
            if line_count1 == 0:
                for x in range(3):
                    if row[x] == "id":
                        a = x
                        found = found + 1
                    if row[x] == "description":
                        b = x
                        found = found + 1
                    if row[x] == "pay_rate":
                        c = x
                        found = found + 1
                line_count1 = line_count1 + 1
                if found != 3:
                    raise ValueError('A very specific bad thing happened.')
            else:
                current_table.objects.create(id=row[a], description=row[b], pay_rate=row[c])

    with open("c:/sql_backup/employeetitles.csv") as f:
        current_table = employees.models.EmployeeTitles
        current_table.objects.all().delete()
        reader = csv.reader(f)
        line_count1 = 0
        found = 0
        for row in reader:
            if line_count1 == 0:
                for x in range(2):
                    if row[x] == "id":
                        a = x
                        found = found + 1
                    if row[x] == "description":
                        b = x
                        found = found + 1
                line_count1 = line_count1 + 1
                if found != 2:
                    raise ValueError('A very specific bad thing happened.')
            else:
                current_table.objects.create(id=row[a], description=row[b])

    with open("c:/sql_backup/exam.csv") as f:
        current_table = employees.models.Exam
        current_table.objects.all().delete()
        reader = csv.reader(f)
        line_count1 = 0
        found = 0
        for row in reader:
            if line_count1 == 0:
                for x in range(4):
                    if row[x] == "id":
                        a = x
                        found = found + 1
                    if row[x] == "description":
                        b = x
                        found = found + 1
                    if row[x] == "details":
                        c = x
                        found = found + 1
                    if row[x] == "max_score":
                        d = x
                        found = found + 1
                line_count1 = line_count1 + 1
                if found != 4:
                    raise ValueError('A very specific bad thing happened.')
            else:
                current_table.objects.create(id=row[a], description=row[b], details=row[c], max_score=row[d])

    with open("c:/sql_backup/inventorytype.csv") as f:
        current_table = equipment.models.InventoryType
        # current_table.objects.all().delete()
        reader = csv.reader(f)
        line_count1 = 0
        found = 0
        for row in reader:
            if line_count1 == 0:
                for x in range(3):
                    if row[x] == "id":
                        a = x
                        found = found + 1
                    if row[x] == "type":
                        b = x
                        found = found + 1
                    if row[x] == "is_active":
                        c = x
                        found = found + 1
                line_count1 = line_count1 + 1
                if found != 3:
                    raise ValueError('A very specific bad thing happened.')
            else:
                current_table.objects.create(id=row[a], type=row[b], is_active=row[c])

    with open("c:/sql_backup/inventoryitems.csv") as f:
        current_table = equipment.models.InventoryItems
        # current_table.objects.all().delete()
        reader = csv.reader(f)
        line_count1 = 0
        found = 0
        for row in reader:
            if line_count1 == 0:
                for x in range(3):
                    if row[x] == "id":
                        a = x
                        found = found + 1
                    if row[x] == "name":
                        b = x
                        found = found + 1
                    if row[x] == "type_id":
                        c = x
                        found = found + 1
                line_count1 = line_count1 + 1
                if found != 3:
                    raise ValueError('A very specific bad thing happened.')
            else:
                current_table.objects.create(id=row[a], name=row[b],
                                             type=equipment.models.InventoryType.objects.get(id=row[c]))

    with open("c:/sql_backup/inventoryitems2.csv") as f:
        current_table = equipment.models.InventoryItems2
        # current_table.objects.all().delete()
        reader = csv.reader(f)
        line_count1 = 0
        found = 0
        for row in reader:
            if line_count1 == 0:
                for x in range(3):
                    if row[x] == "id":
                        a = x
                        found = found + 1
                    if row[x] == "name":
                        b = x
                        found = found + 1
                    if row[x] == "type_id":
                        c = x
                        found = found + 1
                line_count1 = line_count1 + 1
                if found != 3:
                    raise ValueError('A very specific bad thing happened.')
            else:
                current_table.objects.create(id=row[a], name=row[b],
                                             type=equipment.models.InventoryItems.objects.get(id=row[c]))

    with open("c:/sql_backup/inventoryitems3.csv") as f:
        current_table = equipment.models.InventoryItems3
        # current_table.objects.all().delete()
        reader = csv.reader(f)
        line_count1 = 0
        found = 0
        for row in reader:
            if line_count1 == 0:
                for x in range(3):
                    if row[x] == "id":
                        a = x
                        found = found + 1
                    if row[x] == "name":
                        b = x
                        found = found + 1
                    if row[x] == "type_id":
                        c = x
                        found = found + 1
                line_count1 = line_count1 + 1
                if found != 3:
                    raise ValueError('A very specific bad thing happened.')
            else:
                current_table.objects.create(id=row[a], name=row[b],
                                             type=equipment.models.InventoryItems2.objects.get(id=row[c]))

    with open("c:/sql_backup/inventoryitems4.csv") as f:
        current_table = equipment.models.InventoryItems4
        # current_table.objects.all().delete()
        reader = csv.reader(f)
        line_count1 = 0
        found = 0
        for row in reader:
            if line_count1 == 0:
                for x in range(3):
                    if row[x] == "id":
                        a = x
                        found = found + 1
                    if row[x] == "name":
                        b = x
                        found = found + 1
                    if row[x] == "type_id":
                        c = x
                        found = found + 1
                line_count1 = line_count1 + 1
                if found != 3:
                    raise ValueError('A very specific bad thing happened.')
            else:
                current_table.objects.create(id=row[a], name=row[b],
                                             type=equipment.models.InventoryItems3.objects.get(id=row[c]))

    with open("c:/sql_backup/jobnumbers.csv") as f:
        current_table = jobs.models.JobNumbers
        current_table.objects.all().delete()
        reader = csv.reader(f)
        line_count1 = 0
        found = 0
        for row in reader:
            if line_count1 == 0:
                for x in range(3):
                    if row[x] == "id":
                        a = x
                        found = found + 1
                    if row[x] == "letter":
                        b = x
                        found = found + 1
                    if row[x] == "number":
                        c = x
                        found = found + 1
                line_count1 = line_count1 + 1
                if found != 3:
                    raise ValueError('A very specific bad thing happened.')
            else:
                current_table.objects.create(letter=row[b], number=row[c])

    with open("c:/sql_backup/metrics.csv") as f:
        current_table = employees.models.Metrics
        # current_table.objects.all().delete()
        reader = csv.reader(f)
        line_count1 = 0
        found = 0
        for row in reader:
            if line_count1 == 0:
                for x in range(2):
                    if row[x] == "id":
                        a = x
                        found = found + 1
                    if row[x] == "description":
                        b = x
                        found = found + 1
                line_count1 = line_count1 + 1
                if found != 2:
                    raise ValueError('A very specific bad thing happened.')
            else:
                current_table.objects.create(id=row[a], description=row[b])

    with open("c:/sql_backup/metriclevels.csv") as f:
        current_table = employees.models.MetricLevels
        # current_table.objects.all().delete()
        reader = csv.reader(f)
        line_count1 = 0
        found = 0
        for row in reader:
            if line_count1 == 0:
                for x in range(3):
                    if row[x] == "id":
                        a = x
                        found = found + 1
                    if row[x] == "level_id":
                        b = x
                        found = found + 1
                    if row[x] == "metric_id":
                        c = x
                        found = found + 1
                line_count1 = line_count1 + 1
                if found != 3:
                    raise ValueError('A very specific bad thing happened.')
            else:
                current_table.objects.create(id=row[a], level=employees.models.EmployeeLevels.objects.get(id=row[b]),
                                             metric=employees.models.Metrics.objects.get(id=row[c]))

    with open("c:/sql_backup/metriccategories.csv") as f:
        current_table = employees.models.MetricCategories
        # current_table.objects.all().delete()
        reader = csv.reader(f)
        line_count1 = 0
        found = 0
        for row in reader:
            if line_count1 == 0:
                for x in range(4):
                    if row[x] == "id":
                        a = x
                        found = found + 1
                    if row[x] == "number":
                        b = x
                        found = found + 1
                    if row[x] == "description":
                        c = x
                        found = found + 1
                    if row[x] == "metric_id":
                        d = x
                        found = found + 1
                line_count1 = line_count1 + 1
                if found != 4:
                    raise ValueError('A very specific bad thing happened.')
            else:
                current_table.objects.create(id=row[a], number=row[b], description=row[c],
                                             metric=employees.models.Metrics.objects.get(id=row[d]))

    with open("c:/sql_backup/productioncategory.csv") as f:
        current_table = employees.models.ProductionCategory
        current_table.objects.all().delete()
        reader = csv.reader(f)
        line_count1 = 0
        found = 0
        for row in reader:
            if line_count1 == 0:
                for x in range(8):
                    if row[x] == "id":
                        a = x
                        found = found + 1
                    if row[x] == "item1":
                        b = x
                        found = found + 1
                    if row[x] == "item2":
                        c = x
                        found = found + 1
                    if row[x] == "item3":
                        d = x
                        found = found + 1
                    if row[x] == "task":
                        e = x
                        found = found + 1
                    if row[x] == "unit1":
                        f = x
                        found = found + 1
                    if row[x] == "unit2":
                        g = x
                        found = found + 1
                    if row[x] == "unit3":
                        h = x
                        found = found + 1
                line_count1 = line_count1 + 1
                if found != 8:
                    raise ValueError('A very specific bad thing happened.')
            else:
                current_table.objects.create(id=row[a], item1=row[b], item2=row[c], item3=row[d], task=row[e],
                                             unit1=row[f], unit2=row[g], unit3=row[h])

    with open("c:/sql_backup/tmpricesmaster.csv") as f:
        current_table = changeorder.models.TMPricesMaster
        current_table.objects.all().delete()
        reader = csv.reader(f)
        line_count1 = 0
        found = 0
        for row in reader:
            if line_count1 == 0:
                for x in range(5):
                    if row[x] == "id":
                        a = x
                        found = found + 1
                    if row[x] == "category":
                        b = x
                        found = found + 1
                    if row[x] == "item":
                        c = x
                        found = found + 1
                    if row[x] == "unit":
                        d = x
                        found = found + 1
                    if row[x] == "rate":
                        e = x
                        found = found + 1
                line_count1 = line_count1 + 1
                if found != 5:
                    raise ValueError('A very specific bad thing happened.')
            else:
                current_table.objects.create(id=row[a], category=row[b], item=row[c], unit=row[d], rate=row[e])

    with open("c:/sql_backup/trainingtopic.csv") as f:
        current_table = employees.models.TrainingTopic
        # current_table.objects.all().delete()
        reader = csv.reader(f)
        line_count1 = 0
        found = 0
        for row in reader:
            if line_count1 == 0:
                for x in range(5):
                    if row[x] == "id":
                        a = x
                        found = found + 1
                    if row[x] == "description":
                        b = x
                        found = found + 1
                    if row[x] == "details":
                        c = x
                        found = found + 1
                    if row[x] == "assessment_category_id":
                        d = x
                        found = found + 1
                    if row[x] == "assessment_category1_id":
                        e = x
                        found = found + 1

                line_count1 = line_count1 + 1
                if found != 5:
                    raise ValueError('A very specific bad thing happened.')
            else:
                new_item = current_table.objects.create(id=row[a], description=row[b], details=row[c])
                if row[d] != '':
                    new_item.assessment_category = employees.models.Metrics.objects.get(id=row[d])
                if row[e] != '':
                    new_item.assessment_category1 = employees.models.Metrics.objects.get(id=row[e])
    with open("c:/sql_backup/vendorcategory.csv") as f:
        current_table = equipment.models.VendorCategory
        current_table.objects.all().delete()
        reader = csv.reader(f)
        line_count1 = 0
        found = 0
        for row in reader:
            if line_count1 == 0:
                for x in range(2):
                    if row[x] == "id":
                        a = x
                        found = found + 1
                    if row[x] == "category":
                        b = x
                        found = found + 1
                line_count1 = line_count1 + 1
                if found != 2:
                    raise ValueError('A very specific bad thing happened.')
            else:
                current_table.objects.create(id=row[a], category=row[b])

    with open("c:/sql_backup/writeupdefaults.csv") as f:
        current_table = employees.models.WriteUpDefaults
        current_table.objects.all().delete()
        reader = csv.reader(f)
        line_count1 = 0
        found = 0
        for row in reader:
            if line_count1 == 0:
                for x in range(2):
                    if row[x] == "id":
                        a = x
                        found = found + 1
                    if row[x] == "description":
                        b = x
                        found = found + 1
                line_count1 = line_count1 + 1
                if found != 2:
                    raise ValueError('A very specific bad thing happened.')
            else:
                current_table.objects.create(id=row[a], description=row[b])

    print("SUCCESS MOTHER")
    return render(request, 'index.html')


def reset_databases(request):
    # git hub2
    if request.user.first_name == "Joe" and request.user.last_name == "Gerloff":
        TMList.objects.all().delete()
        TMProposal.objects.all().delete()
        EWTicket.objects.all().delete()
        EWT.objects.all().delete()
        TempRecipients.objects.all().delete()
        ChangeOrderNotes.objects.all().delete()
        ChangeOrders.objects.all().delete()
        Signature.objects.all().delete()
        InventoryNotes.objects.all().delete()
        Inventory.objects.all().delete()
        OutgoingItem.objects.all().delete()
        OutgoingWallcovering.objects.all().delete()
        Packages.objects.all().delete()
        ReceivedItems.objects.all().delete()
        WallcoveringDelivery.objects.all().delete()
        OrderItems.objects.all().delete()
        WallcoveringPricing.objects.all().delete()
        Wallcovering.objects.all().delete()
        Orders.objects.all().delete()
        RentalNotes.objects.all().delete()
        Rentals.objects.all().delete()
        SubmittalNotes.objects.all().delete()
        SubmittalItems.objects.all().delete()
        Submittals.objects.all().delete()
        ClientEmployees.objects.all().delete() #dangerous
        Clients.objects.all().delete() #dangerous
        JobNotes.objects.all().delete()
        Jobs.objects.all().delete()
    return redirect("/")


def create_folders(request):
    for x in Inventory.objects.all():
        createfolder("equipment/" + str(x.id))
    print("HI")
    return render(request, 'index.html')

def customize(request):

    for x in ChangeOrderNotes.objects.all():
        if x.user == "Bridgette Clause":
            x.user = 12
        elif x.user == "Charity Archibald":
            x.user = 14
        elif x.user == "Steve Beaudoin":
            x.user = 21
        elif x.user == "Edward Diggs":
            x.user = 26
        elif x.user == "Joe Gerloff":
            x.user = 3
        elif x.user == "Anthony Taroli":
            x.user = 5
        elif x.user == "D'Angelo Smith":
            x.user = 40
        else:
            print("Change Order Notes")
            print(x.user)
        x.save()

    for x in RentalNotes.objects.all():
        if x.user == "Bridgette Clause":
            x.user = 12
        elif x.user == "Charity Archibald":
            x.user = 14
        elif x.user == "Steve Beaudoin":
            x.user = 21
        elif x.user == "Edward Diggs":
            x.user = 26
        elif x.user == "Joe Gerloff":
            x.user = 3
        elif x.user == "Anthony Taroli":
            x.user = 5
        elif x.user == "D'Angelo Smith":
            x.user = 40
        else:
            print("Change Order Notes")
            print(x.user)
        x.save()


    return redirect('/')

def import_csv(request):
    with open("c:/sql_backup/workorderimport.csv",encoding='utf-8-sig') as f:
        current_table = employees.models.CertificationActionRequired
        current_table.objects.all().delete()
        reader = csv.reader(f)
        for row in reader:
            try:
                job = Jobs.objects.get(job_number=row[0])
                if row[1]:
                    job.is_work_order_done = True
                else:
                    print(job)
                job.save()
            except:
                print(row[0])
        return render(request, 'index.html')
