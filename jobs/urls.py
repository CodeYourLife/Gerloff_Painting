from django.urls import path

from . import views


urlpatterns = [
    path("register", views.register, name='register'),
    path("jobs_home", views.jobs_home, name='jobs_home'),
    path('job_page/<jobnumber>', views.job_page, name='job_page'),
    path('book_new_job', views.book_new_job, name='book_new_job'),
    path('update_job_info/<jobnumber>', views.update_job_info, name='update_job_info'),
    path('change_start_date/<jobnumber> <previous>', views.change_start_date, name='change_start_date'),
]