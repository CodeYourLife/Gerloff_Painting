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

def new_assessment(request,id):
    send_data = {}
    if request.method == 'POST':
        if 'select_employees' in request.POST:
            send_data['reviewer'] = Employees.objects.get(id=request.POST['select_reviewer'])
            employee = Employees.objects.get(id=request.POST['select_employee'])
            send_data['employee'] = employee
            categories = MetricCategories.objects.order_by('metric','number').values('id','metric__id','metric__description','number','description')
            allcategories_json = json.dumps(list(categories), cls=DjangoJSONEncoder)
            send_data['allcategories'] = allcategories_json
            categories = []
            for x in MetricLevels.objects.filter(level = employee.level):
                for y in MetricCategories.objects.order_by('metric','number'):
                    if x.metric == y.metric:
                        categories.append({'id':y.id, 'metric__id':y.metric.id,'metric__description':y.metric.description,'number':y.number,'description':y.description})

            categories_json = json.dumps(list(categories), cls=DjangoJSONEncoder)
            send_data['categories'] = categories_json
            send_data['metrics'] = json.dumps(list(Metrics.objects.values('id','description')), cls=DjangoJSONEncoder)
    else:
        send_data['current_user']=Employees.objects.get(user=request.user)
        send_data['employees'] = Employees.objects.filter(active=True)
        # send_data['current_user']=json.dumps(list(Employees.objects.filter(user=request.user).values('id','last_name','first_name')), cls=DjangoJSONEncoder)
        # send_data['employees'] = json.dumps(list(Employees.objects.filter(active=True).values('id','last_name','first_name')), cls=DjangoJSONEncoder)
    return render(request, "new_assessment.html", send_data)
def classes(request):
    send_data = {}
    send_data['employees']=Employees.objects.filter(active = True)
    return render(request, "classes.html", send_data)

def exams(request):
    send_data = {}
    send_data['employees']=Employees.objects.filter(active = True)
    return render(request, "exams.html", send_data)

def mentorships(request):
    send_data = {}
    send_data['employees']=Employees.objects.filter(active = True)
    return render(request, "mentorships.html", send_data)

def assessments(request,id):
    send_data = {}
    send_data['employeereviews']=EmployeeReview.objects.filter(employee__active = True)
    if id != 'ALL':
        send_data['selected_item']= EmployeeReview.objects.get(id=id)
        send_data['selected_assessment'] = MetricAssessmentItem.objects.filter(assessment__id=id)

    return render(request, "assessments.html", send_data)


def production_reports(request):
    send_data = {}
    send_data['employees']=Employees.objects.filter(active = True)
    return render(request, "production_reports.html", send_data)


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

