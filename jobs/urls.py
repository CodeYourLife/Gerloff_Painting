from django.urls import path

from . import views


urlpatterns = [
    path("register", views.register, name='register'),
    path("jobs_home", views.jobs_home, name='jobs_home'),
    path('job_page/<jobnumber>', views.job_page, name='job_page'),
    path('book_new_job', views.book_new_job, name='book_new_job'),
    path('update_job_info/<jobnumber>', views.update_job_info, name='update_job_info'),
    path('change_start_date/<jobnumber> <previous> <super> <filter>', views.change_start_date, name='change_start_date'),
    path('change_gpsuper/<jobnumber> <previous>', views.change_gpsuper, name='change_gpsuper'),
    path('upload_new_job', views.upload_new_job, name='upload_new_job'),
    path('activate_sub_job/<jobnumber>', views.activate_sub_job, name='activate_sub_job'),
    path('audit_MC_open_jobs', views.audit_MC_open_jobs, name='audit_MC_open_jobs'),
]