from django.urls import path

from . import views


urlpatterns = [
path("employees_home", views.employees_home, name='employees_home'),
path("employees_page/<id>", views.employees_page, name='employees_page'),
path("training", views.training, name='training'),
path("my_page", views.my_page, name='my_page'),
path("certifications", views.certifications, name='certifications'),
path("add_new_employee", views.add_new_employee, name='add_new_employee'),
]