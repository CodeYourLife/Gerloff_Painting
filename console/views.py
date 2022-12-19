from django.utils import timezone
from django.views import generic
#from .models import Jobs, Clients, Employees, JobNumbers, Checklist, ClientEmployees, JobNotes
from .models import *
from django.contrib.auth.models import User, auth
from django.shortcuts import render, redirect
from json import dumps
import json
from django.core.serializers.json import DjangoJSONEncoder
from datetime import date
from django.contrib import messages
def book_new_job(request):
    allclients = Clients.objects.order_by('company')[0:2000]
    pms = ClientEmployees.objects.values('name', 'id', 'person_pk')[0:1000]
    send_employees = Employees.objects.filter(title="Superintendent")[0:2000]
    prices_json = json.dumps(list(pms), cls=DjangoJSONEncoder)
    return render(request, 'book_new_job.html', {'data': prices_json, 'allclients': allclients, 'employees':send_employees})

def index(request):
    return render(request, 'index.html')



def register(request):
    if request.method == 'POST':
        checklist = []
        if request.POST['job_number'] == "":
            if JobNumbers.objects.latest("id").number == "9990":
                new_letter = chr(ord(JobNumbers.objects.latest("id").letter) + 1)
                new_job_number = JobNumbers(letter=new_letter, number="0010")
                new_job_number.save()
                job_number = JobNumbers.objects.latest("id").letter + JobNumbers.objects.latest("id").number
                print(job_number)
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
        print(list(request.POST.items()))
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
            print(client)
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


# Create your views here.
def register_user(request):

    if request.method == 'POST':
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        username = request.POST['username']
        password1 = request.POST['password1']
        password2 = request.POST['password2']
        email = request.POST['email']

        if password1==password2:
            if User.objects.filter(username=username).exists():
                messages.info(request, 'Username Taken')
                return redirect('register')
            else:
                user = User.objects.create_user(username=username, password=password1, email=email, first_name=first_name,last_name=last_name)
                user.save();
                return redirect('login')
        else:
            messages.info(request, 'password not matching...')
            return redirect('register')

    else:
        return render(request,'register.html')

def login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = auth.authenticate(username=username, password=password)
        if user is not None:
            auth.login(request, user)
            return redirect("/")
        else:
            messages.info(request,'invalid credentials')
            return redirect('login')
    else:
        return render(request, 'login.html')

def logout(request):
    auth.logout(request)
    return redirect("/")

