from django.urls import path

from . import views


urlpatterns = [
path("jobs_home", views.jobs_home, name='jobs_home'),
]