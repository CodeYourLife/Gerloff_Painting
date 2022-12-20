from django.urls import path

from . import views


urlpatterns = [
path("employees_home", views.employees_home, name='employees_home'),
]