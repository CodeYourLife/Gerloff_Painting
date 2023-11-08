from django.urls import path

from . import views


urlpatterns = [

    path('super_home/<super>', views.super_home, name='super_home'),
    path('filter_super', views.filter_super, name='filter_super'),
    path('super_ajax', views.super_ajax, name='super_ajax'),
]
