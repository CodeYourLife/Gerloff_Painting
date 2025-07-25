from django.urls import path

from . import views


urlpatterns = [
path("employees_home", views.employees_home, name='employees_home'),
path("employees_page/<id>", views.employees_page, name='employees_page'),
path("training", views.training, name='training'),
path("my_page", views.my_page, name='my_page'),
path("certifications/<id>", views.certifications, name='certifications'),
path("new_certification", views.new_certification, name='new_certification'),
path("add_new_employee", views.add_new_employee, name='add_new_employee'),
path("assessments/<id>", views.assessments, name='assessments'),
path("production_reports/<id>", views.production_reports, name='production_reports'),
path("classes/<id>", views.classes, name='classes'),
path("new_class", views.new_class, name='new_class'),
path("exams/<id>", views.exams, name='exams'),
path("new_exam", views.new_exam, name='new_exam'),
path("mentorships/<id>", views.mentorships, name='mentorships'),
path("new_mentorship", views.new_mentorship, name='new_mentorship'),
path("new_assessment/<id>", views.new_assessment, name='new_assessment'),
path("new_production_report/<jobnumber>", views.new_production_report, name='new_production_report'),
path("write_ups/<id>", views.write_ups, name='write_ups'),
path("write_ups_new", views.write_ups_new, name='write_ups_new'),
path("employee_notes/<employee>", views.employee_notes, name='employee_notes'),
path("daily_reports/<id>", views.daily_reports, name='daily_reports'),
]