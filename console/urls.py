from django.urls import path

from . import views
#git
urlpatterns = [
    path('', views.index, name='index'),
    path("base", views.base, name='base'),
    path('register_user', views.register_user, name='register_user'),
    path('warehouse_home', views.warehouse_home, name='warehouse_home'),
    path('pending_employee_tasks', views.pending_employee_tasks, name='pending_employee_tasks'),
    path(
        'pending_employee_tasks/update_certification',
        views.update_pending_employee_task_certification,
        name='update_pending_employee_task_certification'
    ),
    path('expired_certifications', views.expired_certifications, name='expired_certifications'),
    path('seperate_test', views.seperate_test, name='seperate_test'),
    path('import_csv', views.import_csv, name='import_csv'),
    path('admin_home', views.admin_home, name='admin_home'),
    path('import_certifications', views.import_certifications, name='import_certifications'),
    path('grant_web_access', views.grant_web_access, name='grant_web_access'),
    path('grant_subcontractor_web_access', views.grant_subcontractor_web_access, name='grant_subcontractor_web_access'),
    path('reset_databases', views.reset_databases, name='reset_databases'),
    path('create_folders', views.create_folders, name='create_folders'),
    path('customize', views.customize, name='customize'),
    path('client_info/<id>', views.client_info, name='client_info'),
    path('client_job_info/<id>', views.client_job_info, name='client_job_info'),
    path('tm_prices_master', views.tm_prices_master, name='tm_prices_master'),
    path('import_change_orders', views.import_change_orders, name='import_change_orders'),
    path('job_prices/<job_number>', views.job_prices, name='job_prices'),
    path('export_jobs_ar_closed_csv', views.export_jobs_ar_closed_csv, name='export_jobs_ar_closed_csv'),
    path('grant_web_access/<int:id>/', views.grant_web_access, name='grant_web_access_with_id'),
    path(
        'vendor-management/',
        views.vendor_management,
        name='vendor_management'
    ),
    path("client_cleanup_report", views.client_cleanup_report, name="client_cleanup_report"),
    path(
        "client_merge_review/<int:client_1_id>/<int:client_2_id>",
        views.client_merge_review,
        name="client_merge_review"
    ),

    path(
        "client_employee_merge_review/<int:employee_1_id>/<int:employee_2_id>",
        views.client_employee_merge_review,
        name="client_employee_merge_review"
    ),
]
