from django.utils import timezone
from django.views import generic
from django.views.generic import ListView
from console.models import *
from django.contrib.auth.models import User, auth
from django.shortcuts import render, redirect
from json import dumps
import json
from django.core.serializers.json import DjangoJSONEncoder
from datetime import date
from django_tables2 import SingleTableView

# Create your views here.

def employees_home(request):
    send_data = {}
    send_data['employees']=Employees.objects.filter(active = True)
    return render(request, "employees_home.html", send_data)

def employees_page(request,id):
    send_data = {}
    send_data['employee'] = Employees.objects.get(id=id)
    return render(request, "employees_page.html", send_data)


def training(request):
    send_data = {}
    return render(request, "training.html", send_data)

def my_page(request):
    send_data = {}
    send_data['employee'] = Employees.objects.get(user = request.user)
    return render(request, "my_page.html", send_data)

def certifications(request):
    response = redirect('/')
    return response


def add_new_employee(request):
    response = redirect('/')
    return response

