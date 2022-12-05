from django.utils import timezone
from django.views import generic
from .models import Jobs, Clients, Employees, Job_Numbers, Checklist, Client_Employees, Job_Notes
from django.contrib.auth.models import User, auth
from django.shortcuts import render, redirect
from json import dumps
import json
from django.core.serializers.json import DjangoJSONEncoder
from datetime import date

def book_new_job(request):
    allclients = Clients.objects.order_by('company')[0:2000]
    pms = Client_Employees.objects.values('name', 'id', 'person_PK')[0:1000]
    send_Employees = Employees.objects.filter(title="Superintendent")[0:2000]

    #pms = Clients.objects.values_list("company", "estimator")[0:1000]
    prices_json = json.dumps(list(pms), cls=DjangoJSONEncoder)
    return render(request, 'book_new_job.html', {'data': prices_json, 'allclients': allclients, 'employees':send_Employees})

def index(request):
    return render(request, 'index.html')


def tester(request):
    return render(request, 'test.html')


def register(request):
    if request.method == 'POST':
        checklist = []
        if request.POST['job_number'] == "":
            if Job_Numbers.objects.latest("id").number == "9990":
                new_letter = chr(ord(Job_Numbers.objects.latest("id").letter) + 1)
                new_job_number = Job_Numbers(letter=new_letter, number="0010")
                new_job_number.save()
                job_number = Job_Numbers.objects.latest("id").letter + Job_Numbers.objects.latest("id").number
                print(job_number)
            else:
                new_number = int(Job_Numbers.objects.latest("id").number) + 10
                new_number_convert = str(new_number)
                if new_number < 100:
                    new_job_number = Job_Numbers(letter=Job_Numbers.objects.latest("id").letter, number="00" + new_number_convert)
                elif new_number < 1000:
                    new_job_number = Job_Numbers(letter=Job_Numbers.objects.latest("id").letter, number="0" + new_number_convert)
                else:
                    new_job_number = Job_Numbers(letter=Job_Numbers.objects.latest("id").letter, number=new_number_convert)
                new_job_number.save()
                job_number = Job_Numbers.objects.latest("id").letter + Job_Numbers.objects.latest("id").number
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
            checklist.append("Waiting for Contract")
        elif request.POST['contract_status'] == 'contract_received':
            contract_status = 1
        else: #contract not required
            contract_status = 3

        if request.POST['insurance_status'] == 'COI_not_received':
            insurance_status = 2
            checklist.append("Get COI")
        elif request.POST['insurance_status'] == 'COI_received':
            insurance_status = 1
        else: #contract not required
            insurance_status = 3

        if request.POST['select_company'] == 'Add_new':
            new_Client = request.POST['new_Client']
            new_Client_phone = request.POST['new_Client_phone']
            new_Client_email = request.POST['new_Client_email']
            client = Clients(company=new_Client, bid_email=new_Client_email,phone=new_Client_phone)
            client.save();
            client_id = Clients.objects.latest('id').id
            print(client)
        else:
            client_id = request.POST['select_company']

        if request.POST['select_PM'] == 'Not_Sure':
            checklist.append("Get PM Info")
            client_PM = 'Not_Sure'
        elif request.POST['select_PM'] == 'Use_Below':
            new_name = request.POST['new_PM']
            new_phone = request.POST['new_PM_Phone']
            new_email = request.POST['new_PM_Email']
            new_ID = client_id
            client_employee = Client_Employees(id=new_ID, name=new_name, phone=new_phone,email=new_email)
            client_employee.save;
            client_PM = Client_Employees.objects.latest('person_PK').person_PK
        else:
            client_PM = request.POST['select_PM']

        if request.POST['select_Super'] == 'Not_Sure':
            checklist.append("Get Superintendent Info")
            client_Super='Not_Sure'
        elif request.POST['select_Super'] == 'Use_Below':
            new_name = request.POST['new_Super']
            new_phone = request.POST['new_Super_Phone']
            new_email = request.POST['new_Super_Email']
            new_ID = client_id
            client_employee = Client_Employees(id=new_ID, name=new_name, phone=new_phone,email=new_email)
            client_employee.save;
            client_Super = Client_Employees.objects.latest('person_PK').person_PK
        else:
            client_Super = request.POST['select_Super']

        superintendent = request.POST['select_GPSuper']
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
                                   insurance_status=insurance_status,id=Clients.objects.get(id=client_id),
                                   has_wallcovering=has_wallcovering, has_paint=has_paint, start_date=start_date,
                                   status="Open", booked_date=date.today())
        if client_Super != 'Not_Sure':
            Jobs.objects.filter(job_number=job_number).update(client_Super=Client_Employees.objects.get(person_PK=client_Super))
        if client_PM != 'Not_Sure':
            Jobs.objects.filter(job_number=job_number).update(client_Pm=Client_Employees.objects.get(person_PK=client_PM))
            Jobs.objects.filter(job_number=job_number).update(client_Submittal_Contact=Client_Employees.objects.get(person_PK=client_PM))
            Jobs.objects.filter(job_number=job_number).update(client_Co_Contact=Client_Employees.objects.get(person_PK=client_PM))
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