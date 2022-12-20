from django.urls import path

from . import views


urlpatterns = [
path("subcontractors_home", views.subcontractors_home, name='subcontractors_home'),
]