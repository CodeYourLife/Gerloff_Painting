from django.utils import timezone
from django.views import generic
from .models import Jobs, Clients, Employees, Job_Numbers
from django.contrib.auth.models import User, auth
from django.shortcuts import render, redirect
from json import dumps
import json
from django.core.serializers.json import DjangoJSONEncoder


def book_new_job(request):
    allclients = Clients.objects.order_by('company').distinct('company')[0:2000]
    pms = Clients.objects.values("company", "estimator")[0:100]
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
                print(job_number)
            #job_number = request.POST['job_number']
        #job_name = request.POST['job_name']
        #job= Jobs(job_number=job_number1, job_name=job_name1)
        #job.save();

        response = redirect('/')
        return response