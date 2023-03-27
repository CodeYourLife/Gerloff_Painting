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

def new_production_report(request,jobnumber):
    send_data = {}
    if jobnumber == 'ALL':
        send_data['jobs'] = Jobs.objects.filter(status = 'Open')
    else:
        send_data['jobs'] = Jobs.objects.get(job_number=jobnumber)
        send_data['selected_job'] = Jobs.objects.get(job_number=jobnumber)

    send_data['category1'] = json.dumps(list(ProductionCategory.objects.all().order_by('item1').values().distinct('item1')), cls=DjangoJSONEncoder)
    send_data['category2'] = json.dumps(list(ProductionCategory.objects.all().order_by('item1','item2','item3','task').values()), cls=DjangoJSONEncoder)
    send_data['employees_json'] = json.dumps(list(Employees.objects.filter(active=True).values()), cls=DjangoJSONEncoder)
    send_data['employees'] = Employees.objects.filter(active=True)
    send_data['current_employee'] = Employees.objects.get(user=request.user)

    if request.method == 'POST':
        if 'job_select' in request.POST:
            jobnumber = request.POST['select_job']
            send_data['jobs'] = Jobs.objects.get(job_number=jobnumber)
            send_data['selected_job'] = Jobs.objects.get(job_number=jobnumber)
            return render(request, "new_production_report.html", send_data)
        send_data['selected_reviewer'] = Employees.objects.get(id=request.POST['select_reviewer'])
        if 'report_complete' in request.POST:
            print(request.POST)
            daily_report = DailyReports.objects.create(foreman=Employees.objects.get(id=request.POST['select_reviewer']),date = date.today(),note=request.POST['report_note'],job=Jobs.objects.get(job_number=request.POST['selected_job']))
            for x in request.POST:
                if x[0:20] == 'select_teamcategory1':
                    team_members=0
                    team = x[20:len(x)]
                    team_note =""
                    for y in request.POST:
                        if y[0:4] =='task':
                            if y[9:9+int(len(team))]== team:
                                team_members=team_members+1
                                employee_number = y[19+int(len(team)):len(y)]
                                for z in request.POST:
                                    if z[0:27+int(len(team))+int(len(employee_number))] == "select_team" + team + "select_employee" + employee_number:
                                        employee = Employees.objects.get(id=request.POST[z]).first_name
                                        task = ProductionCategory.objects.get(id=request.POST[y]).task
                                        team_note = team_note + employee + " " + task + ". "
                    team_note = request.POST['teamnotes_' + team] + ". " + team_note
                    for y in request.POST:
                        if y[0:4] =='task':
                            if y[9:9+int(len(team))]== team:
                                employee_number = y[19+int(len(team)):len(y)]
                                for z in request.POST:
                                    if z[0:27+int(len(team))+int(len(employee_number))] == "select_team" + team + "select_employee" + employee_number:
                                        employee = Employees.objects.get(id=request.POST[z])
                                        task = ProductionCategory.objects.get(id=request.POST[y])
                                note= request.POST['team_' + team + "_employeenote_" + employee_number]
                                description = task.item1 + " - " + task.item2 + " - " + task.item3 + " - " + task.task
                                new_entry = ProductionItems.objects.create(note=note, is_team=True,team_note=team_note,daily_report=daily_report,employee=employee,date=date.today(),team_members=team_members,task=task,description=description)
                                if request.POST['hoursteam_'+ team] != "":
                                    new_entry.hours = float(request.POST['hoursteam_'+ team])
                                if 'unit1team_'+team in request.POST:
                                    if request.POST['unit1team_'+team] != "":
                                        new_entry.value1=float(request.POST['unit1team_'+team])
                                        new_entry.unit = task.unit1
                                if 'unit2team_'+team in request.POST:
                                    if request.POST['unit2team_' + team] != "":
                                        new_entry.value2=float(request.POST['unit2team_'+team])
                                        new_entry.unit2 = task.unit2
                                if 'unit3team_'+team in request.POST:
                                    if request.POST['unit3team_' + team] != "":
                                        new_entry.value3=float(request.POST['unit3team_'+team])
                                        new_entry.unit3 = task.unit3
                                new_entry.save()
                if x[0:15] == 'select_employee':
                    employee_number = x[15:len(x)]
                    print(employee_number)
                    task=ProductionCategory.objects.get(id=request.POST['select_task'+employee_number])
                    description = task.item1 + " - " + task.item2 + " - " + task.item3 + " - " + task.task
                    employee = Employees.objects.get(id=request.POST[x])
                    note = request.POST['note' + employee_number]
                    new_entry = ProductionItems.objects.create(note=note, is_team=False,daily_report=daily_report,employee=employee, date=date.today(),task=task,description=description)
                    if request.POST['hours' + employee_number] != "":
                        new_entry.hours = float(request.POST['hours' + employee_number])
                    if 'value1' + employee_number in request.POST:
                        if request.POST['value1' + employee_number] != "":
                            new_entry.value1 = float(request.POST['value1' + employee_number])
                            new_entry.unit = task.unit1
                    if 'value2' + employee_number in request.POST:
                        if request.POST['value2' + employee_number] != "":
                            new_entry.value2 = float(request.POST['value2' + employee_number])
                            new_entry.unit2 = task.unit2
                    if 'value3' + employee_number in request.POST:
                        if request.POST['value3' + employee_number] != "":
                            new_entry.value3 = float(request.POST['value3' + employee_number])
                            new_entry.unit3 = task.unit3
                    new_entry.save()
            return render(request, "new_production_report.html", send_data)
    return render(request, "new_production_report.html", send_data)
def new_assessment(request,id):
    send_data = {}
    if request.method == 'POST':
        if 'new_assessment' in request.POST:
            assessment= MetricAssessment.objects.create(reviewer=Employees.objects.get(id=request.POST['reviewer']),note=request.POST['note_main'],date=date.today())
            review = EmployeeReview.objects.create(assessment=assessment,employee=Employees.objects.get(id=request.POST['employee']))
            for x in request.POST:
                if request.POST[x] =='on':
                    print(x)
                #if x[0:4] != 'note':
                    category = MetricCategories.objects.get(id=x)
                    MetricAssessmentItem.objects.create(assessment=review,note = request.POST['note'+str(category.metric.id)],category=category, employee=Employees.objects.get(id=request.POST['employee']))
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
def classes(request,id):
    send_data = {}
    send_data['classoccurrences']=ClassOccurrence.objects.all()
    if id != 'ALL':
        send_data['selected_item']= ClassOccurrence.objects.get(id=id)
        send_data['attendees'] = ClassAttendees.objects.filter(class_event__id=id)
    return render(request, "classes.html", send_data)

def new_class(request):
    send_data = {}
    send_data['employees']=Employees.objects.filter(active = True)
    send_data['topics']=TrainingTopic.objects.all()
    send_data['jobs'] = Jobs.objects.filter(status = 'Open')
    send_data['topics_json'] = json.dumps(list(TrainingTopic.objects.values()), cls=DjangoJSONEncoder)
    send_data['employees_json'] = json.dumps(list(Employees.objects.filter(active = True).values()), cls=DjangoJSONEncoder)
    if request.method == 'POST':
        new_class = ClassOccurrence.objects.create(date=date.today(),note = request.POST['class_note'],location=request.POST['location'])
        if request.POST['select_job'] != 'please_select':
            new_class.job= Jobs.objects.get(job_number =request.POST['select_job'])
        if request.POST['select_topic'] != 'custom_topic':
            topic = TrainingTopic.objects.get(id=request.POST['select_topic'])
            description = topic.description
            new_class.topic=topic
            new_class.description=description
        else:
            description = request.POST['custom_topic']
            new_class.description=description
        if request.POST['select_teacher'] != 'custom_teacher':
            teacher = Employees.objects.get(id=request.POST['select_teacher'])
            new_class.teacher=teacher
        else:
            teacher2 = request.POST['custom_teacher']
            new_class.teacher2=teacher2
        new_class .save()
        for x in request.POST:
            if x[0:15] == 'select_employee':
                employee_number= x[15:int(len(x))]
                if request.POST[x] == 'custom_student':
                    ClassAttendees.objects.create(class_event=new_class,student2=request.POST['custom_student'+employee_number],note=request.POST['note_'+employee_number])
                else:
                    ClassAttendees.objects.create(class_event=new_class,student = Employees.objects.get(id=request.POST[x]),note=request.POST['note_'+employee_number])
        return redirect('classes',id='ALL')
    return render(request, "new_class.html", send_data)

def exams(request,id):
    send_data = {}
    send_data['employees']=Employees.objects.filter(active = True)
    send_data['exam_scores']=ExamScore.objects.all()
    if id != 'ALL':
        send_data['selected_item']= ExamScore.objects.get(id=id)
        send_data['attendees'] = ClassAttendees.objects.filter(class_event__id=id)
    return render(request, "exams.html", send_data)

def new_exam(request):
    send_data = {}
    send_data['employees']=Employees.objects.filter(active = True)
    send_data['exams']=Exam.objects.all()
    send_data['exams_json'] = json.dumps(list(Exam.objects.all().values()),
                                             cls=DjangoJSONEncoder)
    if request.method == 'POST':
        print(request.POST)
    return render(request, "new_exam.html", send_data)

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


def production_reports(request,id):
    send_data = {}
    if id != 'ALL':
        send_data['production_reports'] = ProductionItems.objects.filter(id=id).order_by('employee', 'date')
        send_data['selected_item'] = ProductionItems.objects.get(id=id)
    else:
        send_data['production_reports']=ProductionItems.objects.all().order_by('employee','date')
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

