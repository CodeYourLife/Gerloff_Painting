from django.contrib.auth.decorators import login_required
from employees.models import *
from django.shortcuts import render, redirect
import json
from django.core.serializers.json import DjangoJSONEncoder
from datetime import date, timedelta
from equipment.models import Inventory
from jobs.models import Jobs, JobNotes
from django.http import HttpResponse
from console.misc import createfolder
import json
import os
from django.conf import settings
from media.utilities import MediaUtilities


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
            print(request.POST)
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
                    print(x)
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
    print(request.POST)
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


@login_required(login_url='/accounts/login')
def my_page(request):
    employee = Employees.objects.get(user=request.user)
    if request.method == 'POST':
        if 'nickname' in request.POST:
            employee.nickname = request.POST['nickname']
            employee.phone = request.POST['phone']
            employee.email = request.POST['email']
            employee.save()
        if 'selected_file' in request.POST:
            if request.POST['selected_file'] == "pumpkin":
                selected_talk = ScheduledToolboxTalks.objects.get(id=request.POST['selected_language'])
                CompletedToolboxTalks.objects.create(employee=employee, date=date.today(), master=selected_talk)
            else:
                id = str(request.POST['selected_id'] + "/" + request.POST['selected_language'])
                return MediaUtilities().getDirectoryContents(id, request.POST['selected_file'], 'toolbox_talks')
    send_data = {}
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
    if employee.job_title.description == "Painter":
        toolbox_talks_required = []
        toolbox_talks_required_count = 0
        folder_name = settings.MEDIA_ROOT
        for x in ScheduledToolboxTalks.objects.filter(date__lte = date.today(), date__gte = employee.date_added):
            if not CompletedToolboxTalks.objects.filter(employee=employee,master=x).exists():
                toolbox_talks_required_count += 1
                toolbox_talk=x.master
                path = folder_name + "/toolbox_talks/" + str(toolbox_talk.id) + "/Spanish"
                for entry in os.listdir(path):
                    full_path = os.path.join(path, entry)
                    if os.path.isfile(full_path):
                        spanish = entry
                path = folder_name + "/toolbox_talks/" + str(toolbox_talk.id) + "/English"
                for entry in os.listdir(path):
                    full_path = os.path.join(path, entry)
                    if os.path.isfile(full_path):
                        english = entry
                toolbox_talks_required.append({'id':x.master.id, 'item':x.id,'description': str(x.master.id) + "- " + x.master.description,'date':x.date, 'english': english, 'spanish': spanish})
        send_data['toolbox_talks_required'] = toolbox_talks_required
        send_data['toolbox_talks_required_count'] = toolbox_talks_required_count
    return render(request, "my_page.html", send_data)


@login_required(login_url='/accounts/login')
def certifications(request, id):
    send_data = {}
    send_data['certifications'] = Certifications.objects.all()
    send_data['actions'] = CertificationActionRequired.objects.all()
    if id != 'ALL':
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
    return render(request, "certifications.html", send_data)


@login_required(login_url='/accounts/login')
def new_certification(request):
    send_data = {}
    send_data['employees'] = Employees.objects.filter(active=True)
    send_data['jobs'] = Jobs.objects.filter(is_closed=False)
    send_data['categories'] = CertificationCategories.objects.all()
    send_data['actions'] = CertificationActionRequired.objects.all()
    if request.method == 'POST':
        print(request.POST)
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
    return render(request, 'safety_home.html')

def toolbox_talks_master(request):
    send_data = {}
    toolboxtalks = []
    folder_name = settings.MEDIA_ROOT
    for x in ToolboxTalks.objects.all():
        path = folder_name + "/toolbox_talks/" + str(x.id) + "/Spanish"
        spanish = "Need to upload"
        english = "Need to upload"
        for entry in os.listdir(path):
            print("test")
            print(entry)
            full_path = os.path.join(path, entry)
            if os.path.isfile(full_path):
                print("test2")
                print(entry)
                spanish = entry
        path = folder_name + "/toolbox_talks/" + str(x.id) + "/English"
        for entry in os.listdir(path):
            full_path = os.path.join(path, entry)
            if os.path.isfile(full_path):
                english = entry
        print(spanish)
        print(english)
        toolboxtalks.append({'id':x.id, 'description': x.description,'english': english, 'spanish': spanish})
    send_data['toolboxtalks']= toolboxtalks
    if request.method == 'POST':
        print(request.POST)
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
        if ScheduledToolboxTalks.objects.all().exists():
            latest_object = ScheduledToolboxTalks.objects.all().order_by('-date')[0]
            next_date = latest_object.date + timedelta(days=7)
        for x in ToolboxTalks.objects.all():
            ScheduledToolboxTalks.objects.create(master=x, date=next_date)
            next_date = next_date + timedelta(days=7)
    send_data = {}
    toolboxtalks = []
    for x in ScheduledToolboxTalks.objects.all():
        if x.date >= next_monday_date:
            ratio = "Not Issued Yet"
        else:
            total_painters = Employees.objects.filter(date_added__lte=x.date, job_title__description = "Painter").count()
            painters_completed = 0
            for y in Employees.objects.filter(date_added__lte=x.date, job_title__description = "Painter"):
                if CompletedToolboxTalks.objects.filter(master=x, employee=y).exists():
                    painters_completed += 1
            ratio = str(painters_completed) + " of " + str(total_painters)
        description = str(x.master.id) + " - " + x.master.description
        toolboxtalks.append({'Item':x.id, 'description': description, 'date': x.date, 'ratio': ratio})
    send_data['toolboxtalks']= toolboxtalks
    return render(request, 'scheduled_toolbox_talks.html', send_data)