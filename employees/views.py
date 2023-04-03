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
                    for y in request.POST: #count team members
                        if y[0:26+len(team)] =='select_team' + team + 'select_employee':
                                team_members=team_members+1
                                employee_number = y[26+int(len(team)):len(y)]
                                employee = Employees.objects.get(id=request.POST['select_team' + team + 'select_employee'+employee_number]).first_name
                                if 'taskteam_' + team + '_employee_' + employee_number in request.POST:
                                    task = ProductionCategory.objects.get(id=request.POST['taskteam_' + team + '_employee_' + employee_number]).task
                                if 'custom_taskteam_' + team + '_employee_' + employee_number in request.POST:
                                    task = request.POST['custom_taskteam_' + team + '_employee_' + employee_number]
                                team_note = team_note + employee + " " + task + ". "
                    team_note = request.POST['teamnotes_' + team] + ". " + team_note
                    for y in request.POST:
                        if y[0:26 + len(team)] == 'select_team' + team + 'select_employee':
                                employee_number = y[26 + len(team):len(y)]
                                employee = Employees.objects.get(id=request.POST[y])
                                note= request.POST['team_' + team + "_employeenote_" + employee_number]
                                if 'taskteam_' + team + '_employee_' + employee_number in request.POST:
                                    task = ProductionCategory.objects.get(id=request.POST['taskteam_' + team + '_employee_' + employee_number])
                                    description = task.item1 + " - " + task.item2 + " - " + task.item3 + " - " + task.task
                                else:
                                    description = request.POST['custom_category1' + team] + "- " + request.POST['custom_taskteam_' + team + '_employee_' + employee_number]
                                new_entry = ProductionItems.objects.create(team_number=team,note=note, is_team=True,team_note=team_note,daily_report=daily_report,employee=employee,date=date.today(),team_members=team_members,description=description)
                                if 'taskteam_' + team + '_employee_' + employee_number in request.POST:
                                    new_entry.task = ProductionCategory.objects.get(id=request.POST['taskteam_' + team + '_employee_' + employee_number])
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
                                if 'custom_category1' + team in request.POST:
                                    new_entry.value1 = float(request.POST['custom_value' + team])
                                    new_entry.unit = request.POST['custom_unit' + team]
                                new_entry.save()
                if x[0:15] == 'select_employee':
                    employee_number = x[15:len(x)]
                    if 'select_task' + employee_number in request.POST:
                        task=ProductionCategory.objects.get(id=request.POST['select_task'+employee_number])
                        description = task.item1 + " - " + task.item2 + " - " + task.item3 + " - " + task.task
                    else:
                        description = request.POST['custom_description'+employee_number]
                    employee = Employees.objects.get(id=request.POST[x])
                    note = request.POST['note' + employee_number]
                    new_entry = ProductionItems.objects.create(note=note, is_team=False,daily_report=daily_report,employee=employee, date=date.today(),description=description)
                    if 'select_task' + employee_number in request.POST:
                        new_entry.task = ProductionCategory.objects.get(id=request.POST['select_task' + employee_number])
                    else:
                        new_entry.value1= request.POST['custom_value1'+employee_number]
                        new_entry.unit = request.POST['custom_unit'+employee_number]
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
    send_data['exams_json'] = json.dumps(list(Exam.objects.all().values()),cls=DjangoJSONEncoder)
    if request.method == 'POST':
        new_exam=ExamScore.objects.create(score=request.POST['score'],note=request.POST['exam_note'],date=date.today())
        if 'custom_student' in request.POST:
            new_exam.student2 = request.POST['custom_student']
        else:
            new_exam.student = Employees.objects.get(id=request.POST['select_student'])
        if 'custom_teacher' in request.POST:
            new_exam.teacher2 = request.POST['custom_teacher']
        else:
            new_exam.teacher = Employees.objects.get(id=request.POST['select_teacher'])
        if 'custom_exam' in request.POST:
            new_exam.exam2 = request.POST['custom_exam']
            new_exam.custom_score_max = request.POST['custom_score_max']
        else:
            new_exam.exam = Exam.objects.get(id=request.POST['select_exam'])
        new_exam.save()
    return render(request, "new_exam.html", send_data)


def mentorships(request,id):
    send_data = {}
    send_data['mentorships'] = Mentorship.objects.all()
    print(request.POST)
    if request.method == 'POST':
        if 'new_note' in request.POST:
            MentorshipNotes.objects.create(mentorship=Mentorship.objects.get(id=id), date=date.today(), user=request.user,
                                           note=request.POST['note'])
        else:
            if 'closed' in request.POST:
                selected_item = Mentorship.objects.get(id=id)
                selected_item.is_closed=True
                selected_item.end_date=date.today()
                MentorshipNotes.objects.create(mentorship=selected_item, date=date.today(),
                                               user=request.user,
                                               note="Mentorship Ended." + request.POST['note'])
            else:
                selected_item = Mentorship.objects.get(id=id)
                selected_item.is_closed=False
                selected_item.end_date=""
                MentorshipNotes.objects.create(mentorship=selected_item, date=date.today(),
                                               user=request.user,
                                               note="Mentorship Activated Again." + request.POST['note'])
            selected_item.save()
    if id !='ALL':
        send_data['selected_notes'] = MentorshipNotes.objects.filter(mentorship__id = id)
        send_data['selected_item'] = Mentorship.objects.get(id=id)
    return render(request, "mentorships.html", send_data)


def new_mentorship(request):
    send_data = {}
    send_data['employees']=Employees.objects.filter(active = True)
    if request.method == 'POST':
        new_item= Mentorship.objects.create(apprentice = Employees.objects.get(id=request.POST['select_apprentice']),mentor = Employees.objects.get(id=request.POST['select_mentor']),start_date=date.today(),note=request.POST['note'])
        MentorshipNotes.objects.create(mentorship=new_item,date=date.today(),user=request.user,note="New mentorship added")
        return redirect('mentorships', id=new_item.id)
    return render(request, "new_mentorship.html", send_data)

def assessments(request,id):
    send_data = {}
    send_data['employeereviews']=EmployeeReview.objects.filter(employee__active = True)
    if id != 'ALL':
        send_data['selected_item']= EmployeeReview.objects.get(id=id)
        selected_assessment = []
        for x in MetricAssessmentItem.objects.filter(assessment__id=id):
            if MetricCategories.objects.filter(metric=x.category.metric, number=x.category.number + 1).exists():
                selected_assessment.append({'category':x.category,'total':x.category.metric.total_numbers,'note':x.note,'description':x.category.description,'next':MetricCategories.objects.get(metric=x.category.metric, number=x.category.number + 1).description})
            else:
                selected_assessment.append(
                    {'category': x.category, 'total': x.category.metric.total_numbers, 'note': x.note,
                     'description': x.category.description, 'next': "None"})
        send_data['selected_assessment'] = selected_assessment
    return render(request, "assessments.html", send_data)


def production_reports(request,id):
    send_data = {}
    if id != 'ALL':
        send_data['production_reports'] = ProductionItems.objects.filter(id=id).order_by('employee', 'date')
        send_data['selected_item'] = ProductionItems.objects.get(id=id)
    else:
        send_data['production_reports'] = ProductionItems.objects.all().order_by('employee','date')
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
    employee= Employees.objects.get(user = request.user)
    send_data['employee'] = employee
    send_data['inventory']= Inventory.objects.filter(assigned_to=employee)
    send_data['assessments_performed'] = EmployeeReview.objects.filter(assessment__reviewer=employee)
    send_data['assessments_received'] = EmployeeReview.objects.filter(employee=employee)
    send_data['writeups_written'] = WriteUp.objects.filter(supervisor=employee)
    send_data['writeups_received'] = WriteUp.objects.filter(employee=employee)
    send_data['vacation_requests'] = Vacation.objects.filter(employee=employee)
    send_data['production_reports_written'] = DailyReports.objects.filter(foreman=employee)
    send_data['production_reports_received'] = ProductionItems.objects.filter(employee=employee)
    send_data['classes_taught'] = ClassOccurrence.objects.filter(teacher=employee)
    send_data['classes_attended'] = ClassAttendees.objects.filter(student=employee)
    send_data['exams'] = ExamScore.objects.filter(student=employee)
    send_data['mentorship_mentor'] = Mentorship.objects.filter(mentor=employee)
    send_data['mentorship_apprentice'] = Mentorship.objects.filter(apprentice=employee)
    send_data['certifications'] = Certifications.objects.filter(employee=employee)
    send_data['actions'] = Certifications.objects.filter(employee=employee,action_required=True)


    if request.method == 'POST':
        employee.nickname=request.POST['nickname']
        employee.phone = request.POST['phone']
        employee.email = request.POST['email']
        employee.save()
    return render(request, "my_page.html", send_data)

def certifications(request,id):
    send_data = {}
    send_data['certifications'] = Certifications.objects.all()
    send_data['actions'] = CertificationActionRequired.objects.all()
    if id != 'ALL':
        send_data['selected_item'] = Certifications.objects.get(id=id)
        send_data['notes2'] = CertificationNotes.objects.filter(certification__id=id)
    if request.method == 'POST':
        cert = Certifications.objects.get(id=id)
        if 'new_note' in request.POST:
            CertificationNotes.objects.create(certification=cert,date=date.today(),user=request.user,note=request.POST['note'])
        if 'closed_item' in request.POST:
            cert.is_closed == False
            CertificationNotes.objects.create(certification=cert, date=date.today(),
                                                  user=request.user, note="Cert closed." + request.POST['closed_note'])
        if 'closed_action' in request.POST:
            cert.action_required = False
            CertificationNotes.objects.create(certification=cert, date=date.today(),
                                                  user=request.user, note="Action: <" + cert.action + "> Completed! " + request.POST['closed_action_note'])
            cert.action = ""
        if 'select_action_now' in request.POST:
            cert.action_required = True
            cert.action = CertificationActionRequired.objects.get(id=request.POST['closed_action_note']).action
            CertificationNotes.objects.create(certification=cert, date=date.today(),
                                                  user=request.user, note="Action: <" + cert.action + "> Required! ")
        if 'custom_action_now' in request.POST:
            cert.action_required = True
            cert.action = request.POST['custom_action']
            CertificationNotes.objects.create(certification=cert, date=date.today(),
                                                  user=request.user, note="Action: <" + cert.action + "> Required! ")
        if 'change_start_date' in request.POST:
            cert.date_received = request.POST['start_date']
            CertificationNotes.objects.create(certification=cert, date=date.today(),user=request.user, note="Start Date Changed to: " + cert.date_received + "- "+ request.POST['start_date_note'])
        if 'change_end_date' in request.POST:
            cert.date_expires = request.POST['end_date']
            CertificationNotes.objects.create(certification=cert, date=date.today(),user=request.user, note="Expiration Date Changed to: " + cert.date_expires + "- "+ request.POST['end_date_note'])
        cert.save()
    return render(request, "certifications.html", send_data)

def new_certification(request):
    send_data = {}
    send_data['employees']=Employees.objects.filter(active=True)
    send_data['jobs'] = Jobs.objects.filter(status = 'Open')
    send_data['categories'] = CertificationCategories.objects.all()
    send_data['actions']=CertificationActionRequired.objects.all()
    if request.method == 'POST':
        print(request.POST)
        new_cert = Certifications.objects.create(category = CertificationCategories.objects.get(id=request.POST['select_category']),employee = Employees.objects.get(id=request.POST['select_employee']),note=request.POST['note'])
        if 'dont_know_end' in request.POST:
            print("HI")
        else:
            new_cert.date_expires=request.POST['end_date']
        if 'dont_know_start' in request.POST:
            print("HI")
        else:
            new_cert.date_received = request.POST['start_date']
        if request.POST['select_job'] != 'please_select':
            new_cert.job=Jobs.objects.get(job_number=request.POST['select_job'])
        if 'is_action_required' in request.POST:
            new_cert.action_required = True
            if request.POST['custom_action'] != "":
                new_cert.action = request.POST['custom_action']
            else:
                new_cert.action = CertificationActionRequired.objects.get(id=request.POST['select_action']).action
        new_cert.save()
        return redirect('certifications', id=new_cert.id)
    return render(request, "new_certification.html", send_data)
def add_new_employee(request):
    response = redirect('/')
    return response

def write_ups(request,id):
    send_data = {}
    send_data['employees']=Employees.objects.filter(active=True)
    send_data['me'] = Employees.objects.get(user=request.user)
    send_data['jobs'] = Jobs.objects.filter(status = 'Open')
    send_data['write_ups'] = WriteUp.objects.filter(employee__active = True)
    if id != 'ALL':
        send_data['selected_item'] = WriteUp.objects.get(id=id)
    return render(request, "write_ups.html", send_data)

def write_ups_new(request):
    send_data = {}
    send_data['employees']=Employees.objects.filter(active=True)
    send_data['me'] = Employees.objects.get(user=request.user)
    send_data['jobs'] = Jobs.objects.filter(status = 'Open')
    send_data['write_ups'] = WriteUp.objects.filter(employee__active = True)
    send_data['defaults'] = WriteUpDefaults.objects.all()
    if request.method == 'POST':
        if 'custom_topic' in request.POST:
            new_writeup=WriteUp.objects.create(supervisor=Employees.objects.get(id=request.POST['select_supervisor']),employee=Employees.objects.get(id=request.POST['select_employee']),date=date.today(),description=request.POST['custom_topic'],note=request.POST['note'])
        else:
            new_writeup = WriteUp.objects.create(supervisor=Employees.objects.get(id=request.POST['select_supervisor']),employee=Employees.objects.get(id=request.POST['select_employee']), date=date.today(),
                                                 description=request.POST['select_topic'], note=request.POST['note'])
        if request.POST['select_job'] != "please_select":
            new_writeup.job=Jobs.objects.get(job_number=request.POST['select_job'])
            new_writeup.save()
        return redirect('write_ups', id=new_writeup.id)
    return render(request, "write_ups_new.html", send_data)

def daily_reports(request,id):
    send_data = {}
    send_data['dailyreports']=DailyReports.objects.all()
    if id != 'ALL':
        teamnumbers = []
        a=0
        for x in ProductionItems.objects.filter(daily_report__id=id):
            if x.team_number != None:
                a=1
                if x.team_number not in teamnumbers:
                    teamnumbers.append(x.team_number)
        if a=1:
            send_data['teamnumbers']=teamnumbers
        send_data['selected_item']=DailyReports.objects.get(id=id)
        send_data['items']= ProductionItems.objects.filter(daily_report__id=id)
    return render(request, "daily_reports.html", send_data)