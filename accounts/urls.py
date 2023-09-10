from django.urls import path
from . import views

urlpatterns = [
    path("registration", views.registration, name='registration'),
    path("verify_pin", views.verifyPin, name='verify_pin'),
    path("add_employee", views.addEmployee, name='add_employee'),
    path("addNewEmployee", views.addNewEmployee, name='addNewEmployee'),
]