from django.urls import path

from . import views


urlpatterns = [
path("register", views.register, name='register'),
path("jobs_home", views.jobs_home, name='jobs_home'),
path('job_page/<jobnumber>', views.job_page, name='job_page'),
path('book_new_job', views.book_new_job, name='book_new_job'),
]