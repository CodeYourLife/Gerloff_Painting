from django.urls import path

from . import views

urlpatterns = [

    path('', views.index, name='index'),
    path('register_user', views.register_user, name='register_user'),
    path('warehouse_home', views.warehouse_home, name='warehouse_home'),
    path('seperate_test', views.seperate_test, name='seperate_test'),
    path('import_csv', views.import_csv, name='import_csv'),
    path('admin_home', views.admin_home, name='admin_home'),
    path('grant_web_access', views.grant_web_access, name='grant_web_access'),
    path('reset_databases', views.reset_databases, name='reset_databases'),
    path('import_job', views.import_job, name='import_job'),

]