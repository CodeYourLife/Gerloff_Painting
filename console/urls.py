from django.urls import path

from . import views
#git
urlpatterns = [
    path('', views.index, name='index'),
    path("base", views.base, name='base'),
    path('register_user', views.register_user, name='register_user'),
    path('warehouse_home', views.warehouse_home, name='warehouse_home'),
    path('seperate_test', views.seperate_test, name='seperate_test'),
    path('import_csv', views.import_csv, name='import_csv'),
    path('admin_home', views.admin_home, name='admin_home'),
    path('grant_web_access', views.grant_web_access, name='grant_web_access'),
    path('grant_subcontractor_web_access', views.grant_subcontractor_web_access, name='grant_subcontractor_web_access'),
    path('reset_databases', views.reset_databases, name='reset_databases'),
    path('create_folders', views.create_folders, name='create_folders'),
    path('customize', views.customize, name='customize'),
    path('client_info/<id>', views.client_info, name='client_info'),
    path('client_job_info/<id>', views.client_job_info, name='client_job_info'),
]
