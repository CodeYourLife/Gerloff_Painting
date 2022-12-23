from django.urls import path

from . import views


urlpatterns = [

    path('super_home', views.super_home, name='super_home'),
    path('filter_super', views.filter_super, name='filter_super'),

]
