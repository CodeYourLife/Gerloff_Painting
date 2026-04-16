from .forms import EmployeeUploadForm
from console.misc import createfolder
from console.misc import Email
from datetime import date, timedelta, datetime
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Q, Max
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import get_template
from django.utils.timezone import now
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from employees.models import *
from employees.models import Employees, ToolboxTalks, ScheduledToolboxTalks,ScheduledToolboxTalkEmployees
from equipment.models import Inventory
from jobs.models import Jobs, JobNotes, Email_Errors, JobsiteSafetyInspection, ClockSharkTimeEntry
from media.utilities import MediaUtilities
import json
import openpyxl
import os
import shutil
from subcontractors.models import (
    Subcontractors,
    Subcontractor_Employees,
    Subcontractor_Job_Assignments,
    Subcontracts,
    ScheduledToolboxTalkSubEmployees,
    ScheduledToolboxTalkSubJobs,
    CompletedSubToolboxTalks,
    ViewedSubToolboxTalks,
)
from xhtml2pdf import pisa

@login_required(login_url='/accounts/login')
def employee_notes(request, employee):
    send_data = {}
    special = False
    if employee == 'AUTO':
        selected_superid = Employees.objects.get(user=request.user).id
    else:
        selected_superid = employee  # selected_superid = either 'ALL' or the ID of super
    if request.method == 'GET':
        if 'search2' in request.GET:
            send_data['search2_exists'] = request.GET['search2']  # super name
            if request.GET['search2'] == 'ALL':
                selected_superid = 'ALL'
            else:
                selected_superid = request.GET['search2']
    if selected_superid == 'ALL':
        send_data['filter_status'] = 'ALL'
        send_data['notes'] = JobNotes.objects.all()
    else:
        selected_employee = Employees.objects.get(id=selected_superid)
        send_data['selected_super'] = selected_employee
        send_data['notes'] = JobNotes.objects.filter(user=selected_employee)
    send_data['supers'] = Employees.objects.filter(active=True)
    # notes = []
    # for x in notes_list:
    #     notes.append({'job_name': jobs.objects.get(job_number=x.job_number)})
    # invoice_items.append({'description': "Release Retainage", 'billed': selected_invoice.release_retainage,
    #                       'notes': selected_invoice.retainage_note, 'sov_item': 0, 'quantity': 0})
    return render(request, "employee_notes.html", send_data)
@login_required(login_url='/accounts/login')
def new_production_report(request, jobnumber):
    send_data = {}
    if jobnumber == 'ALL':
        send_data['jobs'] = Jobs.objects.filter(is_closed=False)
    else:
        send_data['jobs'] = Jobs.objects.get(job_number=jobnumber)
        send_data['selected_job'] = Jobs.objects.get(job_number=jobnumber)

    send_data['category1'] = json.dumps(
        list(ProductionCategory.objects.all().order_by('item1').values().distinct('item1')), cls=DjangoJSONEncoder)
    send_data['category2'] = json.dumps(
        list(ProductionCategory.objects.all().order_by('item1', 'item2', 'item3', 'task').values()),
        cls=DjangoJSONEncoder)
    send_data['employees_json'] = json.dumps(list(Employees.objects.filter(active=True).values()),
                                             cls=DjangoJSONEncoder)
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
            daily_report = DailyReports.objects.create(
                foreman=Employees.objects.get(id=request.POST['select_reviewer']), date=date.today(),
                note=request.POST['report_note'], job=Jobs.objects.get(job_number=request.POST['selected_job']))
            for x in request.POST:
                if x[0:20] == 'select_teamcategory1':
                    team_members = 0
                    team = x[20:len(x)]
                    team_note = ""
                    for y in request.POST:  # count team members
                        if y[0:26 + len(team)] == 'select_team' + team + 'select_employee':
                            team_members = team_members + 1
                            employee_number = y[26 + int(len(team)):len(y)]
                            employee = Employees.objects.get(
                                id=request.POST['select_team' + team + 'select_employee' + employee_number]).first_name
                            if 'taskteam_' + team + '_employee_' + employee_number in request.POST:
                                task = ProductionCategory.objects.get(
                                    id=request.POST['taskteam_' + team + '_employee_' + employee_number]).task
                            if 'custom_taskteam_' + team + '_employee_' + employee_number in request.POST:
                                task = request.POST['custom_taskteam_' + team + '_employee_' + employee_number]
                            team_note = team_note + employee + " " + task + ". "
                    team_note = request.POST['teamnotes_' + team] + ". " + team_note
                    for y in request.POST:
                        if y[0:26 + len(team)] == 'select_team' + team + 'select_employee':
                            employee_number = y[26 + len(team):len(y)]
                            employee = Employees.objects.get(id=request.POST[y])
                            note = request.POST['team_' + team + "_employeenote_" + employee_number]
                            if 'taskteam_' + team + '_employee_' + employee_number in request.POST:
                                task = ProductionCategory.objects.get(
                                    id=request.POST['taskteam_' + team + '_employee_' + employee_number])
                                description = task.item1 + " - " + task.item2 + " - " + task.item3 + " - " + task.task
                            else:
                                description = request.POST['custom_category1' + team] + "- " + request.POST[
                                    'custom_taskteam_' + team + '_employee_' + employee_number]
                            new_entry = ProductionItems.objects.create(team_number=team, note=note, is_team=True,
                                                                       team_note=team_note, daily_report=daily_report,
                                                                       employee=employee, date=date.today(),
                                                                       team_members=team_members,
                                                                       description=description)
                            if 'taskteam_' + team + '_employee_' + employee_number in request.POST:
                                new_entry.task = ProductionCategory.objects.get(
                                    id=request.POST['taskteam_' + team + '_employee_' + employee_number])
                            if request.POST['hoursteam_' + team] != "":
                                new_entry.hours = float(request.POST['hoursteam_' + team])
                            if 'unit1team_' + team in request.POST:
                                if request.POST['unit1team_' + team] != "":
                                    new_entry.value1 = float(request.POST['unit1team_' + team])
                                    new_entry.unit = task.unit1
                            if 'unit2team_' + team in request.POST:
                                if request.POST['unit2team_' + team] != "":
                                    new_entry.value2 = float(request.POST['unit2team_' + team])
                                    new_entry.unit2 = task.unit2
                            if 'unit3team_' + team in request.POST:
                                if request.POST['unit3team_' + team] != "":
                                    new_entry.value3 = float(request.POST['unit3team_' + team])
                                    new_entry.unit3 = task.unit3
                            if 'custom_category1' + team in request.POST:
                                new_entry.value1 = float(request.POST['custom_value' + team])
                                new_entry.unit = request.POST['custom_unit' + team]
                            new_entry.save()
                if x[0:15] == 'select_employee':
                    employee_number = x[15:len(x)]
                    if 'select_task' + employee_number in request.POST:
                        task = ProductionCategory.objects.get(id=request.POST['select_task' + employee_number])
                        description = task.item1 + " - " + task.item2 + " - " + task.item3 + " - " + task.task
                    else:
                        description = request.POST['custom_description' + employee_number]
                    employee = Employees.objects.get(id=request.POST[x])
                    note = request.POST['note' + employee_number]
                    new_entry = ProductionItems.objects.create(note=note, is_team=False, daily_report=daily_report,
                                                               employee=employee, date=date.today(),
                                                               description=description)
                    if 'select_task' + employee_number in request.POST:
                        new_entry.task = ProductionCategory.objects.get(
                            id=request.POST['select_task' + employee_number])
                    else:
                        new_entry.value1 = request.POST['custom_value1' + employee_number]
                        new_entry.unit = request.POST['custom_unit' + employee_number]
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


@login_required(login_url='/accounts/login')
def new_assessment(request, id):
    send_data = {}
    if request.method == 'POST':
        if 'new_assessment' in request.POST:
            assessment = MetricAssessment.objects.create(reviewer=Employees.objects.get(id=request.POST['reviewer']),
                                                         note=request.POST['note_main'], date=date.today())
            review = EmployeeReview.objects.create(assessment=assessment,
                                                   employee=Employees.objects.get(id=request.POST['employee']))
            for x in request.POST:
                if request.POST[x] == 'on':
                    # if x[0:4] != 'note':
                    category = MetricCategories.objects.get(id=x)
                    MetricAssessmentItem.objects.create(assessment=review,
                                                        note=request.POST['note' + str(category.metric.id)],
                                                        category=category,
                                                        employee=Employees.objects.get(id=request.POST['employee']))
        if 'select_employees' in request.POST:
            send_data['reviewer'] = Employees.objects.get(id=request.POST['select_reviewer'])
            employee = Employees.objects.get(id=request.POST['select_employee'])
            send_data['employee'] = employee
            categories = MetricCategories.objects.order_by('metric', 'number').values('id', 'metric__id',
                                                                                      'metric__description', 'number',
                                                                                      'description')
            allcategories_json = json.dumps(list(categories), cls=DjangoJSONEncoder)
            send_data['allcategories'] = allcategories_json
            categories = []
            for x in MetricLevels.objects.filter(level=employee.level):
                for y in MetricCategories.objects.order_by('metric', 'number'):
                    if x.metric == y.metric:
                        categories.append(
                            {'id': y.id, 'metric__id': y.metric.id, 'metric__description': y.metric.description,
                             'number': y.number, 'description': y.description})

            categories_json = json.dumps(list(categories), cls=DjangoJSONEncoder)
            send_data['categories'] = categories_json
            send_data['metrics'] = json.dumps(list(Metrics.objects.values('id', 'description')), cls=DjangoJSONEncoder)
    else:
        send_data['current_user'] = Employees.objects.get(user=request.user)
        send_data['employees'] = Employees.objects.filter(active=True)
        # send_data['current_user']=json.dumps(list(Employees.objects.filter(user=request.user).values('id','last_name','first_name')), cls=DjangoJSONEncoder)
        # send_data['employees'] = json.dumps(list(Employees.objects.filter(active=True).values('id','last_name','first_name')), cls=DjangoJSONEncoder)
    return render(request, "new_assessment.html", send_data)


@login_required(login_url='/accounts/login')
def classes(request, id):
    send_data = {}
    send_data['classoccurrences'] = ClassOccurrence.objects.all()
    if id != 'ALL':
        send_data['selected_item'] = ClassOccurrence.objects.get(id=id)
        send_data['attendees'] = ClassAttendees.objects.filter(class_event__id=id)
    return render(request, "classes.html", send_data)


@login_required(login_url='/accounts/login')
def new_class(request):
    send_data = {}
    send_data['employees'] = Employees.objects.filter(active=True)
    send_data['topics'] = TrainingTopic.objects.all()
    send_data['jobs'] = Jobs.objects.filter(is_closed=False)
    send_data['topics_json'] = json.dumps(list(TrainingTopic.objects.values()), cls=DjangoJSONEncoder)
    send_data['employees_json'] = json.dumps(list(Employees.objects.filter(active=True).values()),
                                             cls=DjangoJSONEncoder)
    if request.method == 'POST':
        new_class = ClassOccurrence.objects.create(date=date.today(), note=request.POST['class_note'],
                                                   location=request.POST['location'])
        if request.POST['select_job'] != 'please_select':
            new_class.job = Jobs.objects.get(job_number=request.POST['select_job'])
        if request.POST['select_topic'] != 'custom_topic':
            topic = TrainingTopic.objects.get(id=request.POST['select_topic'])
            description = topic.description
            new_class.topic = topic
            new_class.description = description
        else:
            description = request.POST['custom_topic']
            new_class.description = description
        if request.POST['select_teacher'] != 'custom_teacher':
            teacher = Employees.objects.get(id=request.POST['select_teacher'])
            new_class.teacher = teacher
        else:
            teacher2 = request.POST['custom_teacher']
            new_class.teacher2 = teacher2
        new_class.save()
        for x in request.POST:
            if x[0:15] == 'select_employee':
                employee_number = x[15:int(len(x))]
                if request.POST[x] == 'custom_student':
                    ClassAttendees.objects.create(class_event=new_class,
                                                  student2=request.POST['custom_student' + employee_number],
                                                  note=request.POST['note_' + employee_number])
                else:
                    ClassAttendees.objects.create(class_event=new_class,
                                                  student=Employees.objects.get(id=request.POST[x]),
                                                  note=request.POST['note_' + employee_number])
        return redirect('classes', id='ALL')
    return render(request, "new_class.html", send_data)


@login_required(login_url='/accounts/login')
def exams(request, id):
    send_data = {}
    send_data['employees'] = Employees.objects.filter(active=True)
    send_data['exam_scores'] = ExamScore.objects.all()
    if id != 'ALL':
        send_data['selected_item'] = ExamScore.objects.get(id=id)
        send_data['attendees'] = ClassAttendees.objects.filter(class_event__id=id)
    return render(request, "exams.html", send_data)


@login_required(login_url='/accounts/login')
def new_exam(request):
    send_data = {}
    send_data['employees'] = Employees.objects.filter(active=True)
    send_data['exams'] = Exam.objects.all()
    send_data['exams_json'] = json.dumps(list(Exam.objects.all().values()), cls=DjangoJSONEncoder)
    if request.method == 'POST':
        new_exam = ExamScore.objects.create(score=request.POST['score'], note=request.POST['exam_note'],
                                            date=date.today())
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


@login_required(login_url='/accounts/login')
def mentorships(request, id):
    send_data = {}
    send_data['mentorships'] = Mentorship.objects.all()
    if request.method == 'POST':
        if 'new_note' in request.POST:
            MentorshipNotes.objects.create(mentorship=Mentorship.objects.get(id=id), date=date.today(),
                                           user=Employees.objects.get(user=request.user),
                                           note=request.POST['note'])
        else:
            if 'closed' in request.POST:
                selected_item = Mentorship.objects.get(id=id)
                selected_item.is_closed = True
                selected_item.end_date = date.today()
                MentorshipNotes.objects.create(mentorship=selected_item, date=date.today(),
                                               user=Employees.objects.get(user=request.user),
                                               note="Mentorship Ended." + request.POST['note'])
            else:
                selected_item = Mentorship.objects.get(id=id)
                selected_item.is_closed = False
                selected_item.end_date = ""
                MentorshipNotes.objects.create(mentorship=selected_item, date=date.today(),
                                               user=Employees.objects.get(user=request.user),
                                               note="Mentorship Activated Again." + request.POST['note'])
            selected_item.save()
    if id != 'ALL':
        send_data['selected_notes'] = MentorshipNotes.objects.filter(mentorship__id=id)
        send_data['selected_item'] = Mentorship.objects.get(id=id)
    return render(request, "mentorships.html", send_data)


@login_required(login_url='/accounts/login')
def new_mentorship(request):
    send_data = {}
    send_data['employees'] = Employees.objects.filter(active=True)
    if request.method == 'POST':
        new_item = Mentorship.objects.create(apprentice=Employees.objects.get(id=request.POST['select_apprentice']),
                                             mentor=Employees.objects.get(id=request.POST['select_mentor']),
                                             start_date=date.today(), note=request.POST['note'])
        MentorshipNotes.objects.create(mentorship=new_item, date=date.today(),
                                       user=Employees.objects.get(user=request.user),
                                       note="New mentorship added")
        return redirect('mentorships', id=new_item.id)
    return render(request, "new_mentorship.html", send_data)


@login_required(login_url='/accounts/login')
def assessments(request, id):
    send_data = {}
    send_data['employeereviews'] = EmployeeReview.objects.filter(employee__active=True)
    if id != 'ALL':
        send_data['selected_item'] = EmployeeReview.objects.get(id=id)
        selected_assessment = []
        for x in MetricAssessmentItem.objects.filter(assessment__id=id):
            if MetricCategories.objects.filter(metric=x.category.metric, number=x.category.number + 1).exists():
                selected_assessment.append(
                    {'category': x.category, 'total': x.category.metric.total_numbers, 'note': x.note,
                     'description': x.category.description,
                     'next': MetricCategories.objects.get(metric=x.category.metric,
                                                          number=x.category.number + 1).description})
            else:
                selected_assessment.append(
                    {'category': x.category, 'total': x.category.metric.total_numbers, 'note': x.note,
                     'description': x.category.description, 'next': "None"})
        send_data['selected_assessment'] = selected_assessment
    return render(request, "assessments.html", send_data)


@login_required(login_url='/accounts/login')
def production_reports(request, id):
    send_data = {}
    if id != 'ALL':
        send_data['production_reports'] = ProductionItems.objects.filter(id=id).order_by('employee', 'date')
        send_data['selected_item'] = ProductionItems.objects.get(id=id)
    else:
        send_data['production_reports'] = ProductionItems.objects.all().order_by('employee', 'date')
    return render(request, "production_reports.html", send_data)


@login_required(login_url='/accounts/login')
def employees_home(request):
    send_data = {}
    send_data['employees'] = Employees.objects.filter(active=True)
    if request.is_ajax():
        employeeId = request.GET['id']
        certifications = Certifications.objects.filter(employee=employeeId)
        equipment = Inventory.objects.filter(assigned_to=employeeId, date_returned__isnull=True,is_closed=False)
        writeUps = WriteUp.objects.filter(employee=employeeId)
        certs = []
        for cert in certifications:
            certs.append({'category': cert.category.description, 'description': cert.description,
                          'dateExpires': str(cert.date_expires)})
        equips = []
        for equip in equipment:
            equips.append({'id': str(equip.id), 'item': equip.item, 'storageLocation': equip.storage_location,
                           'dateOut': str(equip.date_out)})
        wrtUps = []
        for writeUp in writeUps:
            wrtUps.append({'supervisor': writeUp.supervisor.first_name + " " + writeUp.supervisor.last_name,
                           'date': str(writeUp.date), 'description': writeUp.description,
                           'job': writeUp.job.job_name})
        data_details = {'certifications': certs, 'equipment': equips, 'writeUps': wrtUps}
        return HttpResponse(json.dumps(data_details))

    return render(request, "employees_home.html", send_data)


@login_required(login_url='/accounts/login')
def employees_page(request, id):
    send_data = {}
    send_data['employee'] = Employees.objects.get(id=id)
    return render(request, "employees_page.html", send_data)


@login_required(login_url='/accounts/login')
def training(request):
    send_data = {}
    return render(request, "training.html", send_data)

def toolbox_file(request, scheduled_id, language):
    employee = Employees.objects.get(user=request.user)
    scheduled = ScheduledToolboxTalks.objects.get(id=scheduled_id)

    # Prevent duplicate entries for same talk + language
    ViewedToolboxTalks.objects.get_or_create(
        employee=employee,
        master=scheduled,
        language=language,
        defaults={"date": now().date()}
    )

    if scheduled.master:
        folder_path = os.path.join(
            settings.MEDIA_ROOT,
            "toolbox_talks",
            str(scheduled.master.id),
            language
        )

        relative_id = f"{scheduled.master.id}/{language}"
        app_name = "toolbox_talks"

    else:
        folder_path = os.path.join(
            settings.MEDIA_ROOT,
            "custom_toolbox_talks",
            str(scheduled.id),
            language
        )

        relative_id = f"{scheduled.id}/{language}"
        app_name = "custom_toolbox_talks"

    if not os.path.exists(folder_path):
        return HttpResponse("File not found", status=404)

    files = [
        f for f in os.listdir(folder_path)
        if os.path.isfile(os.path.join(folder_path, f))
    ]

    if not files:
        return HttpResponse("File not found", status=404)

    file_name = files[0]

    return MediaUtilities().getDirectoryContents(
        relative_id,
        file_name,
        app_name
    )

@login_required(login_url='/accounts/login')
def my_page(request):

    employee = Employees.objects.get(user=request.user)
    send_data = {}

    if request.method == 'POST':

        if 'nickname' in request.POST:
            employee.nickname = request.POST['nickname']
            employee.phone = request.POST['phone']
            employee.email = request.POST['email']
            employee.save()

        if request.POST.get('selected_file') == "pumpkin":

            selected_talk = ScheduledToolboxTalks.objects.get(
                id=request.POST['scheduledtalk_id']
            )

            if selected_talk.link_has_been_viewed(employee):
                CompletedToolboxTalks.objects.create(
                    employee=employee,
                    date=date.today(),
                    master=selected_talk
                )
            return redirect('my_page')
    # Everything else is just data preparation

    if not RespiratorClearance.objects.filter(employee=employee, date_completed__isnull=False).exists():
        send_data['respirator_clearance_required'] = "Yes"
    else:
        send_data['respirator_clearance_id'] = RespiratorClearance.objects.get(employee=employee).id
        if not RespiratorClearance.objects.get(employee=employee).approved_for_use:
            send_data['respirator_not_approved'] = "Yes"
    send_data['employeeJobs'] = EmployeeJob.objects.filter(employee=employee.id)
    send_data['employee'] = employee
    send_data['inventory'] = Inventory.objects.filter(assigned_to=employee,is_closed=False)
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
    send_data['actions'] = Certifications.objects.filter(employee=employee, action_required=True)
    from django.utils.timezone import now

    if employee.job_title.description == "Painter":

        toolbox_talks_required = []

        scheduled_qs = ScheduledToolboxTalks.objects.filter(
            date__lte=date.today(),
            date__gte=employee.date_added
        ).filter(
            Q(is_all_employees=True) |
            Q(scheduledtoolboxtalkemployees__employee=employee)
        ).distinct().order_by('date')

        for x in scheduled_qs:

            if CompletedToolboxTalks.objects.filter(employee=employee, master=x).exists():
                continue

            if x.master:
                talk_description = x.master.description
                talk_display_id = x.master.id
            else:
                talk_description = x.description or "Custom Toolbox Talk"
                talk_display_id = x.id

            english_file = get_uploaded_toolbox_file(x, "English")
            spanish_file = get_uploaded_toolbox_file(x, "Spanish")

            english = english_file['filename'] if english_file else None
            spanish = spanish_file['filename'] if spanish_file else None

            spanish_view = ViewedToolboxTalks.objects.filter(
                employee=employee,
                master=x,
                language="Spanish"
            ).order_by('-date').first()

            english_view = ViewedToolboxTalks.objects.filter(
                employee=employee,
                master=x,
                language="English"
            ).order_by('-date').first()

            toolbox_talks_required.append({
                'id': talk_display_id,
                'item': x.id,
                'description': talk_description,
                'date': x.date,
                'english': english,
                'spanish': spanish,
                'spanish_viewed': bool(spanish_view),
                'spanish_date': spanish_view.date if spanish_view else None,
                'english_viewed': bool(english_view),
                'english_date': english_view.date if english_view else None,
                'can_complete': bool(spanish_view or english_view),
                'notes': x.notes or "",
                'is_all_employees': x.is_all_employees,
            })

        send_data['toolbox_talks_required'] = toolbox_talks_required
        send_data['toolbox_talks_required_count'] = len(toolbox_talks_required)
    return render(request, "my_page.html", send_data)


@login_required(login_url='/accounts/login')
def certifications(request, id):
    send_data = {}
    if id != 'ALL':
        selected_cert = Certifications.objects.get(id=id)
        if selected_cert.category.description=="Respirator Clearance" and RespiratorClearance.objects.filter(certification=selected_cert).exists():
            return redirect('view_respirator_certification',id=id)
        else:
            send_data['selected_item'] = Certifications.objects.get(id=id)
            send_data['notes2'] = CertificationNotes.objects.filter(certification__id=id)
    if request.method == 'POST':
        cert = Certifications.objects.get(id=id)
        if 'new_note' in request.POST:
            CertificationNotes.objects.create(certification=cert, date=date.today(),
                                              user=Employees.objects.get(user=request.user),
                                              note=request.POST['note'])
        if 'closed_item' in request.POST:
            cert.is_closed == False
            CertificationNotes.objects.create(certification=cert, date=date.today(),
                                              user=Employees.objects.get(user=request.user),
                                              note="Cert closed." + request.POST['closed_note'])
        if 'closed_action' in request.POST:
            cert.action_required = False
            CertificationNotes.objects.create(certification=cert, date=date.today(),
                                              user=Employees.objects.get(user=request.user),
                                              note="Action: <" + cert.action + "> Completed! " + request.POST[
                                                  'closed_action_note'])
            cert.action = ""
        if 'select_action_now' in request.POST:
            cert.action_required = True
            cert.action = CertificationActionRequired.objects.get(id=request.POST['closed_action_note']).action
            CertificationNotes.objects.create(certification=cert, date=date.today(),
                                              user=Employees.objects.get(user=request.user),
                                              note="Action: <" + cert.action + "> Required! ")
        if 'custom_action_now' in request.POST:
            cert.action_required = True
            cert.action = request.POST['custom_action']
            CertificationNotes.objects.create(certification=cert, date=date.today(),
                                              user=Employees.objects.get(user=request.user),
                                              note="Action: <" + cert.action + "> Required! ")
        if 'change_start_date' in request.POST:
            cert.date_received = request.POST['start_date']
            CertificationNotes.objects.create(certification=cert, date=date.today(),
                                              user=Employees.objects.get(user=request.user),
                                              note="Start Date Changed to: " + cert.date_received + "- " + request.POST[
                                                  'start_date_note'])
        if 'change_end_date' in request.POST:
            cert.date_expires = request.POST['end_date']
            CertificationNotes.objects.create(certification=cert, date=date.today(),
                                              user=Employees.objects.get(user=request.user),
                                              note="Expiration Date Changed to: " + cert.date_expires + "- " +
                                                   request.POST['end_date_note'])
        cert.save()
    send_data['certifications'] = Certifications.objects.filter(is_closed=False)
    send_data['actions'] = CertificationActionRequired.objects.all()
    return render(request, "certifications.html", send_data)


@login_required(login_url='/accounts/login')
def new_certification(request):
    send_data = {}
    send_data['employees'] = Employees.objects.filter(active=True,job_title__description="Painter")
    send_data['jobs'] = Jobs.objects.filter(is_closed=False)
    send_data['categories'] = CertificationCategories.objects.all()
    send_data['actions'] = CertificationActionRequired.objects.all()
    if request.method == 'POST':
        if 'new_certification_type' in request.POST:
            if not CertificationCategories.objects.filter(description=request.POST['new_certification_type']).exists():
                CertificationCategories.objects.create(description = request.POST['new_certification_type'])
            return redirect('new_certification')
        else:
            new_cert = Certifications.objects.create(
                category=CertificationCategories.objects.get(id=request.POST['select_category']),
                employee=Employees.objects.get(id=request.POST['select_employee']), note=request.POST['note'])
            if 'dont_know_end' in request.POST:
                print("HI")
            else:
                new_cert.date_expires = request.POST['end_date']
            if 'dont_know_start' in request.POST:
                print("HI")
            else:
                new_cert.date_received = request.POST['start_date']
            if request.POST['select_job'] != 'please_select':
                new_cert.job = Jobs.objects.get(job_number=request.POST['select_job'])
            if 'is_action_required' in request.POST:
                new_cert.action_required = True
                if request.POST['custom_action'] != "":
                    new_cert.action = request.POST['custom_action']
                else:
                    new_cert.action = CertificationActionRequired.objects.get(id=request.POST['select_action']).action
            new_cert.save()
            return redirect('certifications', id=new_cert.id)
    return render(request, "new_certification.html", send_data)


@login_required(login_url='/accounts/login')
def add_new_employee(request):
    send_data = {}
    send_data['jobtitles'] = EmployeeTitles.objects.all
    send_data['employers'] = Employers.objects.all
    if request.method == 'POST':
        employee = Employees.objects.create(first_name=request.POST['first_name'],
                                            middle_name=request.POST['middle_name'],
                                            last_name=request.POST['last_name'],
                                            job_title=EmployeeTitles.objects.get(id=request.POST['jobTitle']),
                                            employer=Employers.objects.get(id=request.POST['employer']), date_added=date.today())
        try:
            # check if employees directory exists
            employeesFolderPath = os.path.join(settings.MEDIA_ROOT, "employees")
            if not os.path.isdir(employeesFolderPath):
                # create employees directory
                os.mkdir(employeesFolderPath)
            # create employee folder
            employeeFolderPath = os.path.join(settings.MEDIA_ROOT, "employees", str(employee.id))
            os.mkdir(employeeFolderPath)
        except Exception as e:
            print('unable to create employee folder', e)

        return redirect('employees_home')
    return render(request, "add_new_employee.html", send_data)


@login_required(login_url='/accounts/login')
def write_ups(request, id):
    send_data = {}
    send_data['employees'] = Employees.objects.filter(active=True)
    send_data['me'] = Employees.objects.get(user=request.user)
    send_data['jobs'] = Jobs.objects.filter(is_closed=False)
    send_data['write_ups'] = WriteUp.objects.filter(employee__active=True)
    if id != 'ALL':
        send_data['selected_item'] = WriteUp.objects.get(id=id)
    return render(request, "write_ups.html", send_data)


@login_required(login_url='/accounts/login')
def write_ups_new(request):
    send_data = {}
    send_data['employees'] = Employees.objects.filter(active=True)
    send_data['me'] = Employees.objects.get(user=request.user)
    send_data['jobs'] = Jobs.objects.filter(is_closed=False)
    send_data['write_ups'] = WriteUp.objects.filter(employee__active=True)
    send_data['defaults'] = WriteUpDefaults.objects.all()
    if request.method == 'POST':
        if 'custom_topic' in request.POST:
            new_writeup = WriteUp.objects.create(supervisor=Employees.objects.get(id=request.POST['select_supervisor']),
                                                 employee=Employees.objects.get(id=request.POST['select_employee']),
                                                 date=date.today(), description=request.POST['custom_topic'],
                                                 note=request.POST['note'])
        else:
            new_writeup = WriteUp.objects.create(supervisor=Employees.objects.get(id=request.POST['select_supervisor']),
                                                 employee=Employees.objects.get(id=request.POST['select_employee']),
                                                 date=date.today(),
                                                 description=request.POST['select_topic'], note=request.POST['note'])
        if request.POST['select_job'] != "please_select":
            new_writeup.job = Jobs.objects.get(job_number=request.POST['select_job'])
            new_writeup.save()
        return redirect('write_ups', id=new_writeup.id)
    return render(request, "write_ups_new.html", send_data)


@login_required(login_url='/accounts/login')
def daily_reports(request, id):
    send_data = {}
    send_data['dailyreports'] = DailyReports.objects.all()
    if id != 'ALL':
        teamnumbers = []
        numbercheck = []
        a = 0
        for x in ProductionItems.objects.filter(daily_report__id=id):
            if x.team_number != None:
                a = 1
                if x.team_number not in numbercheck:
                    numbercheck.append(x.team_number)
                    if x.task != None:
                        teamnumbers.append(
                            {'number': x.team_number, 'value1': x.value1, 'value2': x.value2, 'value3': x.value3,
                             'unit1': x.unit, 'unit2': x.unit2, 'unit3': x.unit3, 'hours': x.hours,
                             'description': x.task.item1 + ' ' + x.task.item2 + ' ' + x.task.item3})
                    else:
                        teamnumbers.append(
                            {'number': x.team_number, 'value1': x.value1, 'value2': x.value2, 'value3': x.value3,
                             'unit1': x.unit, 'unit2': x.unit2, 'unit3': x.unit3, 'hours': x.hours,
                             'description': x.description})
        if a == 1:
            send_data['teamnumbers'] = teamnumbers
        send_data['selected_item'] = DailyReports.objects.get(id=id)
        send_data['items'] = ProductionItems.objects.filter(daily_report__id=id)
    return render(request, "daily_reports.html", send_data)

def safety_home(request):
    send_data = {}
    painters_needing_respirator = []
    for x in Employees.objects.filter(active=True, job_title__description="Painter"):
        if not RespiratorClearance.objects.filter(employee=x).exists():
            if not Certifications.objects.filter(employee=x, category__description="Respirator Clearance").exists():
                painters_needing_respirator.append({'employee': x.first_name + " " + x.last_name})
    send_data['pending_respirators'] = painters_needing_respirator
    respirators_in_review = []
    for x in RespiratorClearance.objects.filter(date_approved__isnull=True):
        respirators_in_review.append({'employee': x.employee.first_name + " " + x.employee.last_name,'date': x.date_created, 'status': x.certification.action})
    send_data['respirators_in_review'] = respirators_in_review
    send_data['safety_inspections'] = (
        JobsiteSafetyInspection.objects
        .select_related('job', 'inspector')
        .order_by('-inspection_date')[:50]
    )
    return render(request, 'safety_home.html', send_data)

def toolbox_talks_master(request):
    send_data = {}
    toolboxtalks = []
    folder_name = settings.MEDIA_ROOT
    for x in ToolboxTalks.objects.all():
        path = folder_name + "/toolbox_talks/" + str(x.id) + "/Spanish"
        spanish = "Need to upload"
        english = "Need to upload"
        for entry in os.listdir(path):
            full_path = os.path.join(path, entry)
            if os.path.isfile(full_path):
                spanish = entry
        path = folder_name + "/toolbox_talks/" + str(x.id) + "/English"
        for entry in os.listdir(path):
            full_path = os.path.join(path, entry)
            if os.path.isfile(full_path):
                english = entry
        toolboxtalks.append({'id':x.id, 'description': x.description,'english': english, 'spanish': spanish})
    send_data['toolboxtalks']= toolboxtalks
    if request.method == 'POST':
        if 'description' in request.POST:
            newitem = ToolboxTalks.objects.create(description = request.POST['description'])
            createfolder("toolbox_talks/" + str(newitem.id))
            createfolder("toolbox_talks/" + str(newitem.id) + "/English")
            createfolder("toolbox_talks/" + str(newitem.id) + "/Spanish")
            return redirect('toolbox_talks_master')
        if 'selected_id' in request.POST:
            id = str(request.POST['selected_id'] + "/" + request.POST['selected_language'])
            return MediaUtilities().getDirectoryContents(id, request.POST['selected_file'], 'toolbox_talks')
    return render(request, 'toolbox_talks_master.html', send_data)

def scheduled_toolbox_talks(request):
    today = date.today()
    days_until_monday = (0 - today.weekday() + 7) % 7
    if days_until_monday == 0:
        days_until_monday = 7

    next_monday_date = today + timedelta(days=days_until_monday)
    next_date = next_monday_date - timedelta(days=7)

    if request.method == 'POST':
        if ScheduledToolboxTalks.objects.exists():
            latest_object = ScheduledToolboxTalks.objects.order_by('-date').first()
            next_date = latest_object.date + timedelta(days=7)

        for x in ToolboxTalks.objects.all():
            ScheduledToolboxTalks.objects.create(
                master=x,
                date=next_date,
                is_all_employees=True,
                notes="All Employees"
            )
            next_date = next_date + timedelta(days=7)

        return redirect('scheduled_toolbox_talks')

    send_data = {}
    toolboxtalks = []

    scheduled_rows = ScheduledToolboxTalks.objects.all().order_by('date')

    for x in scheduled_rows:
        if x.master:
            description = f"{x.master.description}"
        else:
            description = x.description or "Custom Toolbox Talk"

        english_file = get_uploaded_toolbox_file(x, "English")
        spanish_file = get_uploaded_toolbox_file(x, "Spanish")
        files_uploaded = bool(english_file) and bool(spanish_file)
        if not files_uploaded:
            ratio = "FILES NOT UPLOADED"
        else:

            ratio = "Not Issued Yet"

            employee_assignments = ScheduledToolboxTalkEmployees.objects.filter(
                scheduled=x
            ).select_related('employee')

            sub_assignments = ScheduledToolboxTalkSubEmployees.objects.filter(
                scheduled=x
            ).select_related('employee', 'job', 'employee__subcontractor')

            if x.date < next_monday_date:
                if employee_assignments.exists():
                    total_count = employee_assignments.count()
                    completed_count = 0

                    for row in employee_assignments:
                        if CompletedToolboxTalks.objects.filter(master=x, employee=row.employee).exists():
                            completed_count += 1

                    ratio = f"{completed_count} of {total_count}"

                elif sub_assignments.exists():
                    total_count = sub_assignments.count()
                    completed_count = 0

                    for row in sub_assignments:
                        if CompletedSubToolboxTalks.objects.filter(master=x, employee=row.employee).exists():
                            completed_count += 1

                    ratio = f"{completed_count} of {total_count}"

                elif x.is_all_employees:
                    target_employees = Employees.objects.filter(
                        active=True,
                        date_added__lte=x.date,
                        job_title__description="Painter"
                    )

                    total_count = target_employees.count()
                    completed_count = 0

                    for y in target_employees:
                        if CompletedToolboxTalks.objects.filter(master=x, employee=y).exists():
                            completed_count += 1

                    ratio = f"{completed_count} of {total_count}"

                else:
                    ratio = "0 of 0"

        toolboxtalks.append({
            'Item': x.id,
            'description': description,
            'date': x.date,
            'ratio': ratio,
            'notes': x.notes or "",
        })

    send_data['toolboxtalks'] = toolboxtalks
    return render(request, 'scheduled_toolbox_talks.html', send_data)

def respirator_clearance_base(request):
    send_data = {}
    employee = Employees.objects.get(user=request.user)
    send_data['employee'] = employee
    if RespiratorClearance.objects.filter(employee=employee).exists():
        send_data['started_at_base'] = True
        send_data['respirator_clearance0'] = True
        main = RespiratorClearance.objects.get(employee=employee)
        if RespiratorClearance1.objects.filter(main=main).exists():
            send_data['respirator_clearance1'] = True
        if RespiratorClearance2.objects.filter(main=main).exists():
            send_data['respirator_clearance2'] = True
        if RespiratorClearance3.objects.filter(main=main).exists():
            send_data['respirator_clearance3'] = True
        if RespiratorClearance4.objects.filter(main=main).exists():
            send_data['respirator_clearance4'] = True
        if RespiratorClearance5.objects.filter(main=main).exists():
            send_data['respirator_clearance5'] = True
        if RespiratorClearance6.objects.filter(main=main).exists():
            send_data['respirator_clearance6'] = True
    return render(request, 'respirator_clearance_base.html', send_data)

def respirator_clearance_section0(request):
    #basic employee info
    send_data = {}
    employee = Employees.objects.get(user=request.user)
    send_data['employee'] = employee
    if request.method == 'POST':
        if not RespiratorClearance.objects.filter(employee=employee).exists():
            rc = RespiratorClearance(employee = employee,date_created=date.today())
            rc.save()
            RespiratorNotes.objects.create(employee=employee, date=date.today(), main=rc,
                                           note="Respirator Clearance Form Started")
            new_cert = Certifications.objects.create(employee=employee, category=CertificationCategories.objects.get(
                description="Respirator Clearance"),description="Respirator Clearance", action_required=True, action="Need to Complete Application")
            CertificationNotes.objects.create(certification=new_cert, date=date.today(), user=employee,
                                              note="Respirator Clearance Form Started")
            rc.certification = new_cert
            rc.save()
        employee.gender = request.POST.get('gender')
        employee.height = request.POST.get('height')
        employee.weight = request.POST.get('weight')
        employee.phone = request.POST.get('phone')
        employee.birth_date = request.POST.get('birth_date')
        employee.save()
        if request.POST['next_page'] == 'back_to_base':
            return redirect('respirator_clearance_base')
        if request.POST['next_page'] == 'next_page':
            return redirect('respirator_clearance_section1')
    return render(request, 'respirator_clearance_section0.html', send_data)



@csrf_exempt
def respirator_clearance_section1(request):
    send_data = {}
    employee = Employees.objects.get(user=request.user)
    send_data['employee'] = employee
    main = RespiratorClearance.objects.get(employee=employee)
    if not RespiratorClearance1.objects.filter(main=main).exists():
        RespiratorClearance1.objects.create(main=main)
    part1 = RespiratorClearance1.objects.get(main=main)
    send_data['part1'] = part1
    if request.method == 'POST':
        for field in part1._meta.fields:
            name = field.name
            if name == 'id' or name == 'main':
                continue
            if name in request.POST:
                value = request.POST[name]
                setattr(part1, name, value)
                part1.save()

        return redirect('respirator_clearance_section2')
    return render(request, 'respirator_clearance_section1.html', send_data)

@csrf_exempt
def respirator_clearance_section2(request):
    send_data = {}
    employee = Employees.objects.get(user=request.user)
    send_data['employee'] = employee
    main = RespiratorClearance.objects.get(employee=employee)
    if not RespiratorClearance2.objects.filter(main=main).exists():
        RespiratorClearance2.objects.create(main=main)
    part1 = RespiratorClearance2.objects.get(main=main)
    send_data['part1'] = part1
    if request.method == 'POST':
        for field in part1._meta.fields:
            name = field.name
            if name == 'id' or name == 'main':
                continue
            if name in request.POST:
                value = request.POST[name]
                setattr(part1, name, value)
                part1.save()
        return redirect('respirator_clearance_section3')
    return render(request, 'respirator_clearance_section2.html', send_data)

def respirator_clearance_section3(request):
    send_data = {}
    employee = Employees.objects.get(user=request.user)
    send_data['employee'] = employee
    main = RespiratorClearance.objects.get(employee=employee)
    if not RespiratorClearance3.objects.filter(main=main).exists():
        RespiratorClearance3.objects.create(main=main)
    part1 = RespiratorClearance3.objects.get(main=main)
    send_data['part1'] = part1
    if request.method == 'POST':
        for field in part1._meta.fields:
            name = field.name
            if name == 'id' or name == 'main':
                continue
            if name in request.POST:
                value = request.POST[name]
                setattr(part1, name, value)
                part1.save()
        return redirect('respirator_clearance_section4')
    return render(request, 'respirator_clearance_section3.html', send_data)


def respirator_clearance_section4(request):
    send_data = {}
    employee = Employees.objects.get(user=request.user)
    send_data['employee'] = employee
    main = RespiratorClearance.objects.get(employee=employee)
    if not RespiratorClearance4.objects.filter(main=main).exists():
        RespiratorClearance4.objects.create(main=main)
    part1 = RespiratorClearance4.objects.get(main=main)
    send_data['part1'] = part1
    if request.method == 'POST':
        for field in part1._meta.fields:
            name = field.name
            if name == 'id' or name == 'main':
                continue
            if name in request.POST:
                value = request.POST[name]
                setattr(part1, name, value)
                part1.save()
        return redirect('respirator_clearance_section5')
    return render(request, 'respirator_clearance_section4.html', send_data)

def respirator_clearance_section5(request):
    send_data = {}
    employee = Employees.objects.get(user=request.user)
    send_data['employee'] = employee
    main = RespiratorClearance.objects.get(employee=employee)
    if not RespiratorClearance5.objects.filter(main=main).exists():
        RespiratorClearance5.objects.create(main=main)
    part1 = RespiratorClearance5.objects.get(main=main)
    send_data['part1'] = part1
    if request.method == 'POST':
        for field in part1._meta.fields:
            name = field.name
            if name == 'id' or name == 'main':
                continue
            if name in request.POST:
                value = request.POST[name]
                setattr(part1, name, value)
                part1.save()
        return redirect('respirator_clearance_section6')
    return render(request, 'respirator_clearance_section5.html', send_data)

def respirator_clearance_section6(request):
    send_data = {}
    employee = Employees.objects.get(user=request.user)
    send_data['employee'] = employee
    main = RespiratorClearance.objects.get(employee=employee)
    if not RespiratorClearance6.objects.filter(main=main).exists():
        RespiratorClearance6.objects.create(main=main)
    part1 = RespiratorClearance6.objects.get(main=main)
    send_data['part1'] = part1
    if request.method == 'POST':
        for field in part1._meta.fields:
            name = field.name
            if name == 'id' or name == 'main':
                continue
            if name in request.POST:
                value = request.POST[name]
                setattr(part1, name, value)
                part1.save()
        main.date_completed = date.today()
        main.save()
        message = "Respirator Clearance Completed. \n Employee: " + employee.first_name + employee.last_name
        recipients = ["skip@gerloffpainting.com","bridgette@gerloffpainting.com"]
        Email_Errors.objects.filter(user=request.user.first_name + " " + request.user.last_name).delete()
        check_sender = Employees.objects.filter(user=request.user).first() if request.user.is_authenticated else None
        sender = check_sender.email if check_sender else "operations@gerloffpainting.com"
        try:
            Email.sendEmail("Respirator Clearance Completed", message,
                            recipients, False,sender)
            message = "Your email about the respirator clearance was sent successfully"
        except:
            message = "Error! Your email about the respirator clearance failed to send. Please call them and let them know it was completed."
        Email_Errors.objects.create(user=request.user.first_name + " " + request.user.last_name, error=message,
                                    date=date.today())
        RespiratorNotes.objects.create(employee=employee,date=date.today(),main=main, note="Respirator Clearance Form Completed")
        new_cert = main.certification
        CertificationNotes.objects.create(certification=new_cert,date=date.today(),user=employee,note="Respirator Clearance Form Completed")
        new_cert.action = "Need Safety Director Approval"
        new_cert.save()
        if request.POST['physician'] == 'Yes':
            main.is_physician_required = True
            main.is_physician_actually_required = True
            main.save()
            CertificationNotes.objects.create(certification=new_cert, date=date.today(), user=employee,
                                              note="Employee Requested Physician Review")
        CertificationActionRequired.objects.create(main=new_cert,action="Waiting for Safety Director")
        return redirect('my_page')
    return render(request, 'respirator_clearance_section6.html', send_data)

def respirator_clearance_completed(request,respirator_id):
    send_data = {}
    main = RespiratorClearance.objects.get(id=respirator_id)
    employee = main.employee
    send_data['employee'] = employee
    send_data['main'] = main
    send_data['part1'] = RespiratorClearance1.objects.get(main=main)
    send_data['part2'] = RespiratorClearance2.objects.get(main=main)
    send_data['part3'] = RespiratorClearance3.objects.get(main=main)
    send_data['part4'] = RespiratorClearance4.objects.get(main=main)
    send_data['part5'] = RespiratorClearance5.objects.get(main=main)
    send_data['part6'] = RespiratorClearance6.objects.get(main=main)
    return render(request, 'respirator_clearance_completed.html', send_data)


def _get_talk_title(talk):
    if talk.master and talk.master.description:
        return talk.master.description
    if talk.description:
        return talk.description
    return f"Scheduled Toolbox Talk #{talk.id}"


def _get_assigned_talk_ids_for_employee(employee):
    """
    Assigned talks for regular employees:
    1. Explicitly assigned via ScheduledToolboxTalkEmployees
    2. OR talk.is_all_employees=True AND:
       - talk.date is not null
       - talk.date <= today
       - employee.date_added <= talk.date
    """
    assigned_ids = set()

    explicit_ids = set(
        ScheduledToolboxTalkEmployees.objects
        .filter(employee=employee)
        .values_list('scheduled_id', flat=True)
        .distinct()
    )
    assigned_ids.update(explicit_ids)

    if employee.date_added:
        today = timezone.localdate()
        global_ids = set(
            ScheduledToolboxTalks.objects
            .filter(
                is_all_employees=True,
                date__isnull=False,
                date__lte=today,
                date__gte=employee.date_added,
            )
            .values_list('id', flat=True)
            .distinct()
        )
        assigned_ids.update(global_ids)

    return assigned_ids


def _get_assigned_talk_ids_for_sub_employee(sub_employee):
    """
    Assigned talks for subcontractor employees:
    1. If has_access_to_toolbox=False -> none
    2. Explicitly assigned via ScheduledToolboxTalkSubEmployees
    3. OR talk.is_all_employees=True AND:
       - talk.date is not null
       - talk.date <= today
       - sub_employee.date_enrolled <= talk.date
       - sub_employee.has_access_to_toolbox=True
    """
    if not sub_employee.has_access_to_toolbox:
        return set()

    assigned_ids = set()

    explicit_ids = set(
        ScheduledToolboxTalkSubEmployees.objects
        .filter(employee=sub_employee)
        .values_list('scheduled_id', flat=True)
        .distinct()
    )
    assigned_ids.update(explicit_ids)

    if sub_employee.date_enrolled:
        today = timezone.localdate()
        global_ids = set(
            ScheduledToolboxTalks.objects
            .filter(
                is_all_employees=True,
                date__isnull=False,
                date__lte=today,
                date__gte=sub_employee.date_enrolled,
            )
            .values_list('id', flat=True)
            .distinct()
        )
        assigned_ids.update(global_ids)

    return assigned_ids


def toolbox_talks_by_employee(request):
    rows = []

    employees = (
        Employees.objects
        .filter(active=True)
        .select_related('employment_company')
        .order_by('first_name', 'last_name')
    )

    for emp in employees:
        assigned_ids = _get_assigned_talk_ids_for_employee(emp)

        completed_ids = set(
            CompletedToolboxTalks.objects
            .filter(employee=emp, master_id__in=assigned_ids)
            .values_list('master_id', flat=True)
            .distinct()
        )

        total_assigned = len(assigned_ids)
        total_completed = len(completed_ids)

        full_name = f"{emp.first_name or ''} {emp.last_name or ''}".strip()
        if not full_name:
            full_name = f"Employee #{emp.id}"

        employer_name = str(emp.employment_company) if emp.employment_company else ""

        rows.append({
            'person_type': 'employee',
            'person_id': emp.id,
            'name': full_name,
            'employer': employer_name,
            'ratio_sort_completed': total_completed,
            'ratio_sort_total': total_assigned,
            'ratio_display': f"{total_completed} out of {total_assigned}",
        })

    sub_employees = (
        Subcontractor_Employees.objects
        .filter(is_active=True)
        .select_related('subcontractor')
        .order_by('name')
    )

    for sub_emp in sub_employees:
        employer_name = sub_emp.subcontractor.company if sub_emp.subcontractor else ""

        if not sub_emp.has_access_to_toolbox:
            rows.append({
                'person_type': 'sub',
                'person_id': sub_emp.id,
                'name': sub_emp.name or f"Sub Employee #{sub_emp.id}",
                'employer': employer_name,
                'ratio_sort_completed': -1,
                'ratio_sort_total': -1,
                'ratio_display': "Not Signed Up",
            })
            continue

        assigned_ids = _get_assigned_talk_ids_for_sub_employee(sub_emp)

        completed_ids = set(
            CompletedSubToolboxTalks.objects
            .filter(employee=sub_emp, master_id__in=assigned_ids)
            .values_list('master_id', flat=True)
            .distinct()
        )

        total_assigned = len(assigned_ids)
        total_completed = len(completed_ids)

        rows.append({
            'person_type': 'sub',
            'person_id': sub_emp.id,
            'name': sub_emp.name or f"Sub Employee #{sub_emp.id}",
            'employer': employer_name,
            'ratio_sort_completed': total_completed,
            'ratio_sort_total': total_assigned,
            'ratio_display': f"{total_completed} out of {total_assigned}",
        })

    rows = sorted(
        rows,
        key=lambda x: (
            (x['employer'] or '').lower(),
            (x['name'] or '').lower()
        )
    )

    return render(request, 'toolbox_talks_by_employee.html', {
        'rows': rows
    })


def toolbox_talks_by_employee_modal(request, person_type, person_id):
    if person_type == 'employee':
        person = get_object_or_404(
            Employees.objects.select_related('employment_company'),
            id=person_id,
            active=True
        )

        person_name = f"{person.first_name or ''} {person.last_name or ''}".strip()
        if not person_name:
            person_name = f"Employee #{person.id}"

        employer_name = str(person.employment_company) if person.employment_company else ""
        has_access_to_toolbox = True

        assigned_ids = _get_assigned_talk_ids_for_employee(person)

        completed_ids = set(
            CompletedToolboxTalks.objects
            .filter(employee=person, master_id__in=assigned_ids)
            .values_list('master_id', flat=True)
            .distinct()
        )

    elif person_type == 'sub':
        person = get_object_or_404(
            Subcontractor_Employees.objects.select_related('subcontractor'),
            id=person_id,
            is_active=True
        )

        person_name = person.name or f"Sub Employee #{person.id}"
        employer_name = person.subcontractor.company if person.subcontractor else ""
        has_access_to_toolbox = person.has_access_to_toolbox

        if not has_access_to_toolbox:
            return JsonResponse({
                'success': True,
                'person_name': person_name,
                'employer_name': employer_name,
                'has_access_to_toolbox': False,
                'completed_talks': [],
                'incomplete_talks': [],
            })

        assigned_ids = _get_assigned_talk_ids_for_sub_employee(person)

        completed_ids = set(
            CompletedSubToolboxTalks.objects
            .filter(employee=person, master_id__in=assigned_ids)
            .values_list('master_id', flat=True)
            .distinct()
        )

    else:
        return JsonResponse({
            'success': False,
            'error': 'Invalid person type.'
        }, status=400)

    assigned_talks = list(
        ScheduledToolboxTalks.objects
        .filter(id__in=assigned_ids)
        .select_related('master')
        .order_by('-date', '-id')
    )

    completed_talks = []
    incomplete_talks = []

    for talk in assigned_talks:
        talk_dict = {
            'id': talk.id,
            'title': _get_talk_title(talk),
            'date': talk.date.strftime('%m/%d/%Y') if talk.date else '',
            'notes': talk.notes or '',
        }

        if talk.id in completed_ids:
            completed_talks.append(talk_dict)
        else:
            incomplete_talks.append(talk_dict)

    return JsonResponse({
        'success': True,
        'person_name': person_name,
        'employer_name': employer_name,
        'has_access_to_toolbox': has_access_to_toolbox,
        'completed_talks': completed_talks,
        'incomplete_talks': incomplete_talks,
    })

def view_respirator_certification(request,id):
    send_data = {}
    selected_cert = Certifications.objects.get(id=id)
    selected_respirator_cert = RespiratorClearance.objects.get(certification=selected_cert)
    if request.method == 'POST':
        if 'note' in request.POST:
            CertificationNotes.objects.create(certification=selected_cert,date=date.today(), user=Employees.objects.get(user=request.user), note=request.POST['note'])
        else:
            if request.POST['submit_status'] == 'Approved':
                selected_cert.date_received = date.today()
                selected_cert.action_required=False
                selected_cert.action=""
                selected_cert.save()
                CertificationActionRequired.objects.filter(main=selected_cert,action="Waiting for Safety Director").delete()
                selected_respirator_cert.approved_for_use = True
                selected_respirator_cert.date_approved = date.today()
                if request.POST['is_physician_required'] == 'Yes':
                    selected_respirator_cert.is_physician_actually_required = True
                    selected_respirator_cert.physician_approved = True
                else:
                    selected_respirator_cert.is_physician_actually_required = False
                    selected_respirator_cert.physician_approved = False
                CertificationNotes.objects.create(certification=selected_cert, date=date.today(),
                                                  user=Employees.objects.get(user=request.user),
                                                  note="Approved for Respirator Use")
            else:
                if request.POST['is_physician_required'] == 'No':
                    selected_respirator_cert.is_physician_actually_required = False
                if request.POST['is_physician_required'] == 'Yes':
                    selected_respirator_cert.is_physician_actually_required = True
                CertificationNotes.objects.create(certification=selected_cert, date=date.today(),
                                                  user=Employees.objects.get(user=request.user),
                                                  note="Not Approved Yet. Physician Required? - " + request.POST['is_physician_required'] + ". Physician Approved? - " + request.POST['physician_approved'])
            selected_respirator_cert.save()
            return redirect('certifications', id='ALL')
    if selected_respirator_cert.approved_for_use:
        send_data['approved_for_use'] = 'True'
    send_data['certification'] = selected_respirator_cert
    send_data['certification_id'] = selected_cert.id
    send_data['notes'] = CertificationNotes.objects.filter(certification=selected_cert)
    if not selected_respirator_cert.date_completed:
        send_data['not_completed_yet']=True
        #return redirect('certifications', id='ALL')
    return render(request, 'view_respirator_certification.html', send_data)

def delete_employee(request,id):
    deleted_employee = Employees.objects.get(id=id)
    deleted_employee.active=False
    deleted_employee.save()
    return redirect('employees_home')

def upload_employees(request):
    if request.method == "POST":
        form = EmployeeUploadForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES["excel_file"]

            wb = openpyxl.load_workbook(excel_file)
            sheet = wb.active

            created = 0
            skipped = 0

            with transaction.atomic():
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    (
                        employee_number,
                        active,
                        first_name,
                        middle_name,
                        last_name,
                        phone,
                        email,
                        level_name,
                        nickname,
                        job_title,
                        employer,
                        pin,
                        date_added,
                        birth_date,
                        gender,
                        height,
                        weight,
                    ) = row

                    # REQUIRED FIELDS CHECK
                    if not first_name or not last_name or not employer:
                        skipped += 1
                        continue

                    # Resolve Foreign Keys safely
                    level = None
                    if level_name:
                        level = EmployeeLevels.objects.filter(name=level_name).first()

                    # job_title = None
                    # if job_title_name:
                    #     job_title = EmployeeTitles.objects.filter(description=job_title_name).first()

                    Employees.objects.create(
                        employee_number=employee_number or 0,
                        active=bool(active) if active is not None else True,
                        first_name=first_name,
                        middle_name=middle_name,
                        last_name=last_name,
                        phone=phone,
                        email=email,
                        level=level,
                        nickname=nickname,
                        job_title=EmployeeTitles.objects.get(id=job_title),
                        employment_company=Employers.objects.get(id=employer),
                        pin=pin,
                        date_added=date_added if isinstance(date_added, datetime) else datetime.today(),
                        birth_date=birth_date if isinstance(birth_date, datetime) else None,
                        gender=gender if gender in ["Male", "Female", "Unassigned"] else "Select",
                        height=height,
                        weight=weight,
                    )

                    created += 1

            messages.success(
                request,
                f"Employees imported: {created}. Rows skipped: {skipped}."
            )
            return redirect("employees_home")

    else:
        form = EmployeeUploadForm()

    return render(request, "upload_employees.html", {"form": form})



@login_required
@transaction.atomic
def toolbox_talk_assign(request):
    toolbox_talks = ToolboxTalks.objects.all().order_by('description')

    painters = Employees.objects.filter(
        active=True,
        job_title__description="Painter"
    ).order_by('last_name', 'first_name')

    subcontractors = Subcontractors.objects.filter(
        is_inactive=False
    ).order_by('company')

    jobs = Jobs.objects.filter(
        is_closed=False
    ).order_by('job_number')

    context = {
        'toolbox_talks': toolbox_talks,
        'painters': painters,
        'subcontractors': subcontractors,
        'jobs': jobs,
    }

    def create_custom_toolbox_folders(scheduled_obj):
        base_path = f"custom_toolbox_talks/{scheduled_obj.id}"
        createfolder(base_path)
        createfolder(f"{base_path}/English")
        createfolder(f"{base_path}/Spanish")

    if request.method == 'POST':
        talk_source = request.POST.get('talk_source')
        schedule_mode = request.POST.get('schedule_mode')
        assignment_type = request.POST.get('assignment_type')

        existing_talk_id = request.POST.get('existing_talk_id')
        custom_description = request.POST.get('custom_description', '').strip()
        custom_date_raw = request.POST.get('custom_date')

        employee_ids = request.POST.getlist('employee_ids')
        sub_employee_ids = request.POST.getlist('sub_employee_ids')
        sub_job_id = request.POST.get('sub_job_ids')

        job_number = request.POST.get('job_number')
        subcontractor_employee_id = request.POST.get('subcontractor_employee_id')
        subcontractor_job_id = request.POST.get('subcontractor_job_id')

        selected_master = None
        selected_description = None

        # -----------------------------
        # Validate talk selection
        # -----------------------------
        if talk_source == 'existing':
            if not existing_talk_id:
                messages.error(request, 'Please select an existing Toolbox Talk.')
                return render(request, 'toolbox_talk_assign.html', context)

            try:
                selected_master = ToolboxTalks.objects.get(id=existing_talk_id)
            except ToolboxTalks.DoesNotExist:
                messages.error(request, 'Selected Toolbox Talk could not be found.')
                return render(request, 'toolbox_talk_assign.html', context)

        elif talk_source == 'custom':
            if not custom_description:
                messages.error(request, 'Please enter a custom Toolbox Talk description.')
                return render(request, 'toolbox_talk_assign.html', context)
            selected_description = custom_description

        else:
            messages.error(request, 'Please choose an existing Toolbox Talk or enter a custom one.')
            return render(request, 'toolbox_talk_assign.html', context)

        # -----------------------------
        # Scheduling method: Replace next scheduled talk for all employees
        # -----------------------------
        if schedule_mode == 'replace_next':
            next_scheduled = ScheduledToolboxTalks.objects.filter(
                date__gte=date.today()
            ).order_by('date', 'id').first()

            if next_scheduled:
                next_date = next_scheduled.date

                future_talks = ScheduledToolboxTalks.objects.filter(
                    date__gte=next_date
                ).order_by('-date', '-id')

                for talk in future_talks:
                    talk.date = talk.date + timedelta(days=7)
                    talk.save()

                new_scheduled = ScheduledToolboxTalks.objects.create(
                    master=selected_master,
                    description=selected_description if selected_master is None else None,
                    date=next_date,
                    is_all_employees=True,
                    notes="All Employees"
                )
            else:
                fallback_date = date.today()
                new_scheduled = ScheduledToolboxTalks.objects.create(
                    master=selected_master,
                    description=selected_description if selected_master is None else None,
                    date=fallback_date,
                    is_all_employees=True,
                    notes="All Employees"
                )

            if selected_master is None:
                create_custom_toolbox_folders(new_scheduled)

            messages.success(request, 'Toolbox Talk created successfully.')
            return redirect('toolbox_talk_assign')

        # -----------------------------
        # Scheduling method: Add to end of schedule for all employees
        # -----------------------------
        if schedule_mode == 'add_to_end_all':
            latest_scheduled = ScheduledToolboxTalks.objects.order_by('-date', '-id').first()

            if latest_scheduled and latest_scheduled.date:
                scheduled_date = latest_scheduled.date + timedelta(days=7)
            else:
                scheduled_date = date.today()

            new_scheduled = ScheduledToolboxTalks.objects.create(
                master=selected_master,
                description=selected_description if selected_master is None else None,
                date=scheduled_date,
                is_all_employees=True,
                notes="All Employees"
            )

            if selected_master is None:
                create_custom_toolbox_folders(new_scheduled)

            messages.success(request, 'Toolbox Talk added to the end of the schedule for all employees.')
            return redirect('toolbox_talk_assign')

        # -----------------------------
        # All other options require custom date
        # -----------------------------
        if schedule_mode != 'custom_date':
            messages.error(request, 'Please choose a scheduling option.')
            return render(request, 'toolbox_talk_assign.html', context)

        if not custom_date_raw:
            messages.error(request, 'Please choose a date.')
            return render(request, 'toolbox_talk_assign.html', context)

        try:
            scheduled_date = date.fromisoformat(custom_date_raw)
        except ValueError:
            messages.error(request, 'Invalid date.')
            return render(request, 'toolbox_talk_assign.html', context)

        is_all_employees = assignment_type == 'all_employees'

        scheduled = ScheduledToolboxTalks.objects.create(
            master=selected_master,
            description=selected_description if selected_master is None else None,
            date=scheduled_date,
            is_all_employees=is_all_employees
        )

        if selected_master is None:
            create_custom_toolbox_folders(scheduled)

        # -----------------------------
        # Assignment type: All Employees
        # -----------------------------
        if assignment_type == 'all_employees':
            scheduled.notes = (
                "All Employees"
                if selected_master else
                "Custom -All Employees"
            )
            scheduled.save()

            messages.success(request, 'Toolbox Talk assigned to all employees.')
            return redirect('toolbox_talk_assign')

        # -----------------------------
        # Assignment type: Employees
        # -----------------------------
        elif assignment_type == 'employees':
            if not employee_ids:
                scheduled.delete()
                messages.error(request, 'Please select at least one employee.')
                return render(request, 'toolbox_talk_assign.html', context)

            valid_employees = Employees.objects.filter(
                id__in=employee_ids,
                active=True,
                job_title__description="Painter"
            )

            ScheduledToolboxTalkEmployees.objects.bulk_create([
                ScheduledToolboxTalkEmployees(
                    scheduled=scheduled,
                    employee=emp
                )
                for emp in valid_employees
            ])

            scheduled.notes = (
                "Certain Employees"
                if selected_master else
                "Custom-Certain Employees"
            )
            scheduled.save()

            messages.success(request, 'Toolbox Talk assigned to selected employees.')
            return redirect('toolbox_talk_assign')

        # -----------------------------
        # Assignment type: Job
        # -----------------------------
        elif assignment_type == 'job':
            if not job_number:
                scheduled.delete()
                messages.error(request, 'Please select a job.')
                return render(request, 'toolbox_talk_assign.html', context)

            entries = ClockSharkTimeEntry.objects.filter(
                job_id=job_number
            ).exclude(
                employee_first_name__isnull=True
            ).exclude(
                employee_last_name__isnull=True
            )

            matched_employees = []
            seen_ids = set()

            for entry in entries:
                emp = Employees.objects.filter(
                    active=True,
                    job_title__description="Painter",
                    first_name__iexact=entry.employee_first_name,
                    last_name__iexact=entry.employee_last_name
                ).first()

                if emp and emp.id not in seen_ids:
                    seen_ids.add(emp.id)
                    matched_employees.append(emp)

            if not matched_employees:
                scheduled.delete()
                messages.error(request, 'No matching active employees were found from ClockShark for that job.')
                return render(request, 'toolbox_talk_assign.html', context)

            ScheduledToolboxTalkEmployees.objects.bulk_create([
                ScheduledToolboxTalkEmployees(
                    scheduled=scheduled,
                    employee=emp,
                    job_id=job_number
                )
                for emp in matched_employees
            ])

            job_obj = Jobs.objects.filter(job_number=job_number).first()
            job_label = f"{job_obj.job_number}" if job_obj else str(job_number)

            scheduled.notes = (
                f"For Job {job_label}"
                if selected_master else
                f"Custom-For Job {job_label}"
            )
            scheduled.save()

            messages.success(request, 'Toolbox Talk assigned to job.')
            return redirect('toolbox_talk_assign')

        # -----------------------------
        # Assignment type: Subcontractor Employees
        # -----------------------------
        elif assignment_type == 'sub_employees':
            if not subcontractor_employee_id:
                scheduled.delete()
                messages.error(request, 'Please choose a subcontractor.')
                return render(request, 'toolbox_talk_assign.html', context)

            if not sub_employee_ids:
                scheduled.delete()
                messages.error(request, 'Please select at least one subcontractor employee.')
                return render(request, 'toolbox_talk_assign.html', context)

            valid_sub_employees = Subcontractor_Employees.objects.filter(
                id__in=sub_employee_ids,
                subcontractor_id=subcontractor_employee_id,
                is_active=True,
                has_access_to_toolbox=True
            )

            ScheduledToolboxTalkSubEmployees.objects.bulk_create([
                ScheduledToolboxTalkSubEmployees(
                    scheduled=scheduled,
                    employee=emp,
                    job=None
                )
                for emp in valid_sub_employees
            ])

            sub = Subcontractors.objects.filter(id=subcontractor_employee_id).first()
            company = sub.company if sub else "Unknown Subcontractor"

            scheduled.notes = (
                f"Assigned to {company}"
                if selected_master else
                f"Custom-Assigned to {company}"
            )
            scheduled.save()

            messages.success(request, 'Toolbox Talk assigned to selected subcontractor employees.')
            return redirect('toolbox_talk_assign')

        # -----------------------------
        # Assignment type: Subcontractor Jobs
        # -----------------------------
        elif assignment_type == 'sub_jobs':
            if not subcontractor_job_id:
                scheduled.delete()
                messages.error(request, 'Please choose a subcontractor.')
                return render(request, 'toolbox_talk_assign.html', context)

            if not sub_job_id:
                scheduled.delete()
                messages.error(request, 'Please select at least one subcontractor job.')
                return render(request, 'toolbox_talk_assign.html', context)

            valid_job_ids = Subcontracts.objects.filter(
                    subcontractor_id=subcontractor_job_id,
                    is_closed=False,
                    job_number__is_closed=False,
                    job_number=sub_job_id
                ).values_list('job_number', flat=True).distinct()


            if not valid_job_ids:
                scheduled.delete()
                messages.error(request, 'No valid open jobs were found for that subcontractor.')
                return render(request, 'toolbox_talk_assign.html', context)

            assignments = Subcontractor_Job_Assignments.objects.filter(
                job_id__in=valid_job_ids,
                employee__subcontractor_id=subcontractor_job_id,
                employee__is_active=True,
                employee__has_access_to_toolbox=True
            ).select_related('employee', 'job')

            create_rows = []
            seen = set()

            for assignment in assignments:
                key = (scheduled.id, assignment.employee.id, assignment.job.pk)
                if key in seen:
                    continue
                seen.add(key)

                create_rows.append(
                    ScheduledToolboxTalkSubEmployees(
                        scheduled=scheduled,
                        employee=assignment.employee,
                        job=assignment.job
                    )
                )

            if not create_rows:
                scheduled.delete()
                messages.error(request, 'No active subcontractor employees were assigned to the selected job(s).')
                return render(request, 'toolbox_talk_assign.html', context)

            ScheduledToolboxTalkSubEmployees.objects.bulk_create(create_rows)

            sub = Subcontractors.objects.filter(id=subcontractor_job_id).first()
            company = sub.company if sub else "Unknown Subcontractor"

            job_list = ", ".join(str(x) for x in valid_job_ids[:5])
            if len(valid_job_ids) > 5:
                job_list += "..."

            scheduled.notes = (
                f"For job {job_list}"
                if selected_master else
                f"Custom-for job {job_list}"
            )
            scheduled.save()

            messages.success(request, 'Toolbox Talk assigned to subcontractor employees on the selected job(s).')
            return redirect('toolbox_talk_assign')

        else:
            scheduled.delete()
            messages.error(request, 'Please select an assignment type.')
            return render(request, 'toolbox_talk_assign.html', context)

    return render(request, 'toolbox_talk_assign.html', context)


@login_required
@require_GET
def ajax_subcontractor_employees(request):
    subcontractor_id = request.GET.get('subcontractor_id')

    results = []
    if subcontractor_id:
        employees = Subcontractor_Employees.objects.filter(
            subcontractor_id=subcontractor_id,
            is_active=True,
            has_access_to_toolbox=True
        ).order_by('name')

        results = [
            {
                'id': x.id,
                'name': x.name or f'Employee #{x.id}'
            }
            for x in employees
        ]

    return JsonResponse({'results': results})


@require_GET
def ajax_subcontractor_jobs(request):
    subcontractor_id = request.GET.get('subcontractor_id')

    results = []
    if subcontractor_id:
        rows = Subcontracts.objects.filter(
            subcontractor_id=subcontractor_id,
            is_closed=False,
            job_number__is_closed=False
        ).select_related('job_number').order_by(
            'job_number__job_number'
        ).distinct()

        seen = set()
        for row in rows:
            job = row.job_number
            if job.pk in seen:
                continue
            seen.add(job.pk)

            results.append({
                'id': job.job_number,
                'label': f'{job.job_number} - {job.job_name}'
            })

    return JsonResponse({'results': results})


def participation_ajax(request):
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        if 'scheduled_toolbox_talk_id' not in request.GET:
            return HttpResponse(
                json.dumps({'error': 'Missing scheduled_toolbox_talk_id'}),
                content_type='application/json',
                status=400
            )

        send_data = {}

        x = ScheduledToolboxTalks.objects.get(id=request.GET['scheduled_toolbox_talk_id'])

        incomplete_people = []
        completed_people = []
        assignment_type = ""
        job_info = ""

        description = x.master.description if x.master else (x.description or "Custom Toolbox Talk")

        employee_assignments = ScheduledToolboxTalkEmployees.objects.filter(
            scheduled=x
        ).select_related('employee', 'job')

        sub_assignments = ScheduledToolboxTalkSubEmployees.objects.filter(
            scheduled=x
        ).select_related('employee', 'employee__subcontractor', 'job')

        # Build job info for header
        sub_job = sub_assignments.exclude(job__isnull=True).first()
        emp_job = employee_assignments.exclude(job__isnull=True).first()

        if sub_job and sub_job.job:
            job_info = f"{sub_job.job.job_number} {sub_job.job.job_name}"
        elif emp_job and emp_job.job:
            job_info = f"{emp_job.job.job_number} {emp_job.job.job_name}"

        # Certain regular employees
        if employee_assignments.exists():
            jobs_used = employee_assignments.exclude(job__isnull=True)

            if jobs_used.exists():
                assignment_type = "Assigned by Job"
            else:
                assignment_type = "Certain Employees"

            for row in employee_assignments:
                y = row.employee

                completed = CompletedToolboxTalks.objects.filter(
                    master=x,
                    employee=y
                ).order_by('-date').first()

                label = f"{y.first_name} {y.last_name}"

                if completed:
                    completed_people.append({
                        'name': label,
                        'completed_date': completed.date.strftime('%m/%d/%y') if completed.date else ""
                    })
                else:
                    incomplete_people.append({
                        'name': label
                    })

        # Subcontractor employees / jobs
        elif sub_assignments.exists():
            jobs_used = sub_assignments.exclude(job__isnull=True)

            if jobs_used.exists():
                assignment_type = "Subcontractor Job Assignment"
            else:
                assignment_type = "Subcontractor Employees"

            for row in sub_assignments:
                y = row.employee
                if not y.has_access_to_toolbox:
                    continue
                completed = CompletedSubToolboxTalks.objects.filter(
                    master=x,
                    employee=y
                ).order_by('-date').first()

                label = y.name or f"Employee #{y.id}"

                if completed:
                    completed_people.append({
                        'name': label,
                        'completed_date': completed.date.strftime('%m/%d/%y') if completed.date else ""
                    })
                else:
                    incomplete_people.append({
                        'name': label
                    })

        # All employees
        elif x.is_all_employees:
            assignment_type = "All Employees"

            target_employees = Employees.objects.filter(
                active=True,
                date_added__lte=x.date,
                job_title__description="Painter"
            ).order_by('last_name', 'first_name')

            for y in target_employees:
                completed = CompletedToolboxTalks.objects.filter(
                    master=x,
                    employee=y
                ).order_by('-date').first()

                label = f"{y.first_name} {y.last_name}"

                if completed:
                    completed_people.append({
                        'name': label,
                        'completed_date': completed.date.strftime('%m/%d/%y') if completed.date else ""
                    })
                else:
                    incomplete_people.append({
                        'name': label
                    })

        else:
            assignment_type = "Unassigned"

        send_data['assignment_type'] = assignment_type
        send_data['description'] = description
        send_data['date'] = x.date.strftime('%Y-%m-%d') if x.date else ""
        send_data['job_info'] = job_info
        send_data['people'] = incomplete_people
        send_data['completed_people'] = completed_people
        send_data['english_file'] = get_uploaded_toolbox_file(x, "English")
        send_data['spanish_file'] = get_uploaded_toolbox_file(x, "Spanish")

        return HttpResponse(json.dumps(send_data), content_type='application/json')

def upload_toolbox_file(request):
    if request.method == 'POST':
        fileitem = request.FILES.get('upload_file')
        language = request.POST.get('language')
        scheduled_id = request.POST.get('scheduled_id')

        if not scheduled_id:
            messages.error(request, 'No scheduled toolbox talk was selected.')
            return redirect('scheduled_toolbox_talks')

        if not fileitem:
            messages.error(request, 'Please choose a file to upload.')
            return redirect('scheduled_toolbox_talks')

        scheduled = ScheduledToolboxTalks.objects.get(id=scheduled_id)

        rel_path, abs_path = get_scheduled_toolbox_folder(scheduled, language)

        os.makedirs(abs_path, exist_ok=True)

        # delete existing file
        for f in os.listdir(abs_path):
            os.remove(os.path.join(abs_path, f))

        fn = os.path.basename(fileitem.name)
        filepath = os.path.join(abs_path, fn)

        with open(filepath, 'wb') as f:
            f.write(fileitem.read())

        return redirect('scheduled_toolbox_talks')

def get_scheduled_toolbox_folder(scheduled, language):
    if scheduled.master:
        rel_path = os.path.join("toolbox_talks", str(scheduled.master.id), language)
    else:
        rel_path = os.path.join("custom_toolbox_talks", str(scheduled.id), language)

    abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)
    return rel_path, abs_path

def get_uploaded_toolbox_file(scheduled, language):
    rel_path, abs_path = get_scheduled_toolbox_folder(scheduled, language)

    if not os.path.exists(abs_path):
        return None

    for fn in os.listdir(abs_path):
        full_path = os.path.join(abs_path, fn)
        if os.path.isfile(full_path):
            return {
                'filename': fn,
                'url': os.path.join(settings.MEDIA_URL, rel_path, fn).replace("\\", "/")
            }

    return None



def scheduled_toolbox_report(request, scheduled_id):
    scheduled = ScheduledToolboxTalks.objects.get(id=scheduled_id)

    if scheduled.master:
        topic = scheduled.master.description
    else:
        topic = scheduled.description or "Custom Toolbox Talk"

    job = None

    sub_row = ScheduledToolboxTalkSubEmployees.objects.filter(
        scheduled=scheduled,
        job__isnull=False
    ).select_related('job').first()

    emp_row = ScheduledToolboxTalkEmployees.objects.filter(
        scheduled=scheduled,
        job__isnull=False
    ).select_related('job').first()

    if sub_row:
        job = sub_row.job
    elif emp_row:
        job = emp_row.job

    job_info = f"{job.job_number} {job.job_name}" if job else ""
    # # Job info for header only
    # job_info = ""
    # job_numbers = list(
    #     ScheduledToolboxTalkSubEmployees.objects.filter(
    #         scheduled=scheduled,
    #         job__isnull=False
    #     ).values_list('job__job_number', flat=True).distinct()
    # )
    # if job_numbers:
    #     job_info = ", ".join(str(x) for x in job_numbers if x)

    rows = []

    employee_assignments = ScheduledToolboxTalkEmployees.objects.filter(
        scheduled=scheduled
    ).select_related('employee')

    sub_assignments = ScheduledToolboxTalkSubEmployees.objects.filter(
        scheduled=scheduled
    ).select_related('employee', 'job', 'employee__subcontractor')

    # Certain regular employees
    if employee_assignments.exists():
        for row in employee_assignments:
            emp = row.employee

            completed = CompletedToolboxTalks.objects.filter(
                master=scheduled,
                employee=emp
            ).order_by('-date').first()

            if not completed:
                continue

            rows.append({
                'employee_name': f"{emp.first_name} {emp.last_name}",
                'completed_date': completed.date,
            })

    # Subcontractor employees / subcontractor job assignments
    elif sub_assignments.exists():
        seen = set()

        for row in sub_assignments:
            emp = row.employee

            if emp.id in seen:
                continue
            seen.add(emp.id)

            completed = CompletedSubToolboxTalks.objects.filter(
                master=scheduled,
                employee=emp
            ).order_by('-date').first()

            if not completed:
                continue

            rows.append({
                'employee_name': emp.name or f"Employee #{emp.id}",
                'completed_date': completed.date,
            })

    # All employees
    elif scheduled.is_all_employees:
        target_employees = Employees.objects.filter(
            active=True,
            date_added__lte=scheduled.date,
            job_title__description="Painter"
        ).order_by('last_name', 'first_name')

        for emp in target_employees:
            completed = CompletedToolboxTalks.objects.filter(
                master=scheduled,
                employee=emp
            ).order_by('-date').first()

            if not completed:
                continue

            rows.append({
                'employee_name': f"{emp.first_name} {emp.last_name}",
                'completed_date': completed.date,
            })

    # Optional: sort by completed date, newest first
    rows = sorted(rows, key=lambda x: x['completed_date'], reverse=True)

    context = {
        'topic': topic,
        'scheduled_date': scheduled.date,
        'job_info': job_info,
        'rows': rows,
    }

    template = get_template('print_scheduled_toolbox_report.html')
    html = template.render(context)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="scheduled_toolbox_report_{scheduled.id}.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse("Error generating PDF", status=500)

    return response



@login_required
@require_GET
def ajax_job_sorted_employees(request):
    job_number = request.GET.get('job_number')

    results = []

    active_painters = Employees.objects.filter(
        active=True,
        job_title__description="Painter"
    ).order_by('last_name', 'first_name')

    if not job_number:
        results = [
            {
                'id': emp.id,
                'label': f'{emp.first_name} {emp.last_name}'
            }
            for emp in active_painters
        ]
        return JsonResponse({'results': results})

    # Pull ClockShark entries for this job and get latest clock-in per name
    clock_rows = (
        ClockSharkTimeEntry.objects.filter(
            job_id=job_number
        )
        .exclude(employee_first_name__isnull=True)
        .exclude(employee_last_name__isnull=True)
        .values('employee_first_name', 'employee_last_name')
        .annotate(last_clock_in=Max('clock_in'))
        .order_by('-last_clock_in', 'employee_last_name', 'employee_first_name')
    )

    used_employee_ids = set()

    # 1. Employees who clocked into the selected job, most recent first
    for row in clock_rows:
        match = Employees.objects.filter(
            active=True,
            job_title__description="Painter",
            first_name__iexact=row['employee_first_name'],
            last_name__iexact=row['employee_last_name']
        ).order_by('last_name', 'first_name').first()

        if not match:
            continue

        if match.id in used_employee_ids:
            continue

        used_employee_ids.add(match.id)

        last_clock_in = row['last_clock_in']
        label = f"{match.first_name} {match.last_name}"
        if last_clock_in:
            label += f" - last clocked in {last_clock_in.strftime('%m/%d/%y')}"

        results.append({
            'id': match.id,
            'label': label
        })

    # 2. Remaining active painters who have not clocked into that job
    remaining_employees = active_painters.exclude(id__in=used_employee_ids)

    for emp in remaining_employees:
        results.append({
            'id': emp.id,
            'label': f'{emp.first_name} {emp.last_name}'
        })

    return JsonResponse({'results': results})

@login_required
@transaction.atomic
def delete_scheduled_toolbox_talk(request):
    if request.method != 'POST':
        return redirect('scheduled_toolbox_talks')

    scheduled_id = request.POST.get('scheduled_id')
    if not scheduled_id:
        messages.error(request, 'No scheduled toolbox talk was selected.')
        return redirect('scheduled_toolbox_talks')

    scheduled = ScheduledToolboxTalks.objects.filter(id=scheduled_id).first()
    if not scheduled:
        messages.error(request, 'Scheduled toolbox talk not found.')
        return redirect('scheduled_toolbox_talks')

    # Delete related records first
    CompletedSubToolboxTalks.objects.filter(master=scheduled).delete()
    ViewedSubToolboxTalks.objects.filter(master=scheduled).delete()

    CompletedToolboxTalks.objects.filter(master=scheduled).delete()
    ViewedToolboxTalks.objects.filter(master=scheduled).delete()

    ScheduledToolboxTalkEmployees.objects.filter(scheduled=scheduled).delete()
    ScheduledToolboxTalkSubEmployees.objects.filter(scheduled=scheduled).delete()

    # If it is a custom scheduled talk, remove its folder too
    if not scheduled.master:
        folder_path = os.path.join(settings.MEDIA_ROOT, "custom_toolbox_talks", str(scheduled.id))
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path, ignore_errors=True)

    scheduled.delete()

    messages.success(request, 'Scheduled toolbox talk deleted.')
    return redirect('scheduled_toolbox_talks')
