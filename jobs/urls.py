from django.urls import path
from .views import clockshark_webhook
from . import views


urlpatterns = [
    path("register", views.register, name='register'),
    path("jobs_home", views.jobs_home, name='jobs_home'),
    path('job_page/<jobnumber>', views.job_page, name='job_page'),
    path('job_page/<jobnumber>/file-email', views.file_job_email, name='file_job_email'),
    path('job_page/<jobnumber>/emails', views.job_emails, name='job_emails'),
    path('api/file-outlook-email/', views.file_outlook_email_api, name='file_outlook_email_api'),
    path('outlook-addin/', views.outlook_addin_taskpane, name='outlook_addin_taskpane'),
    path('outlook-addin/manifest.xml', views.outlook_addin_manifest, name='outlook_addin_manifest'),
    path('book_new_job', views.book_new_job, name='book_new_job'),
    path('update_job_info/<jobnumber>', views.update_job_info, name='update_job_info'),
    path('change_start_date/<jobnumber> <previous> <super> <filter>', views.change_start_date, name='change_start_date'),
    path('change_gpsuper/<jobnumber> <previous>', views.change_gpsuper, name='change_gpsuper'),
    path('upload_new_job', views.upload_new_job, name='upload_new_job'),
    path('activate_sub_job/<jobnumber>', views.activate_sub_job, name='activate_sub_job'),
    path('audit_MC_open_jobs', views.audit_MC_open_jobs, name='audit_MC_open_jobs'),
    path("webhooks/clockshark/",clockshark_webhook, name="clockshark_webhook"),
    path('new_jobsite_safety_inspection', views.new_jobsite_safety_inspection, name='new_jobsite_safety_inspection'),
    path('jobsite_safety_inspection_detail<inspection_id>', views.jobsite_safety_inspection_detail, name='jobsite_safety_inspection_detail'),
    path('close_job/<job_number>', views.close_job, name='close_job'),
    path('jobs_ready_to_close', views.jobs_ready_to_close, name='jobs_ready_to_close'),
    path('complete-work-order/', views.complete_work_order, name='complete_work_order'),
    path('import_super_from_mc/', views.import_super_from_mc, name='import_super_from_mc'),
    path('import_pm_from_mc/', views.import_pm_from_mc, name='import_pm_from_mc'),
    path('change-estimator-pm-ajax/', views.change_estimator_pm_ajax, name='change_estimator_pm_ajax'),
    path(
            "clockshark/unmapped-jobs/",
            views.clockshark_unmapped_jobs,
            name="clockshark_unmapped_jobs"
        ),
    path(
        "clockshark/map-job/",
        views.clockshark_map_job,
        name="clockshark_map_job"
    ),
    path(
        "clockshark/job/<str:job_number>/weekly/",
        views.clockshark_job_weekly_hours,
        name="clockshark_job_weekly_hours"
    ),
path(
    'get-client-employees-ajax/',
    views.get_client_employees_ajax,
    name='get_client_employees_ajax'
),
path(
    'get-client-employee-ajax/',
    views.get_client_employee_ajax,
    name='get_client_employee_ajax'
),
path(
    "upload-from-excel/",
    views.upload_new_job_from_excel,
    name="upload_new_job_from_excel"
),
path(
    'upload_new_job_path_from_excel/',
    views.upload_new_job_path_from_excel,
    name='upload_new_job_path_from_excel'
),
path(
    'upload-new-job-review/',
    views.upload_new_job_review,
    name='upload_new_job_review'
),
path(
    "upload_job_cost_billing_report/",
    views.upload_job_cost_billing_report,
    name="upload_job_cost_billing_report"
),
]
