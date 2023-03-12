from django.urls import path

from . import views


urlpatterns = [
path("employees_home", views.employees_home, name='employees_home'),
path("employees_page/<id>", views.employees_page, name='employees_page'),
path("training", views.training, name='training'),
path("my_page", views.my_page, name='my_page'),
path("certifications", views.certifications, name='certifications'),
path("add_new_employee", views.add_new_employee, name='add_new_employee'),
path("assessments/<id>", views.assessments, name='assessments'),
path("production_reports", views.production_reports, name='production_reports'),
path("classes", views.classes, name='classes'),
path("exams", views.exams, name='exams'),
path("mentorships", views.mentorships, name='mentorships'),
]