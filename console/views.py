from django.utils import timezone
from django.views import generic
from .models import Jobs, Clients
from django.contrib.auth.models import User, auth
from django.shortcuts import render, redirect
from json import dumps
import json
from django.core.serializers.json import DjangoJSONEncoder

def book_new_job(request):
    allclients = Clients.objects.order_by('company').distinct('company')[0:2000]
    pms = Clients.objects.values("company", "estimator")[0:100]
    #pms = Clients.objects.values_list("company", "estimator")[0:1000]
    prices_json = json.dumps(list(pms), cls=DjangoJSONEncoder)
    return render(request, 'book_new_job.html', {'data': prices_json, 'allclients': allclients})

def index(request):
    return render(request, 'index.html')


def tester(request):
    return render(request, 'test.html')

def register(request):
    if request.method == 'POST':
        job_number1 = request.POST['job_number']
        job_name1 = request.POST['job_name']
        job= Jobs(job_number=job_number1, job_name=job_name1)
        job.save();
        response = redirect('/')
        return response