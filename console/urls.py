from django.urls import path

from . import views

urlpatterns = [

    path('', views.index, name='index'),
    path('register_user', views.register_user, name='register_user'),
    path('login', views.login, name='login'),
    path('logout', views.logout, name='logout'),
    path('warehouse_home', views.warehouse_home, name='warehouse_home'),
]