from django.urls import path

from . import views



urlpatterns = [
    path('extra_work_ticket/<id>', views.extra_work_ticket, name='extra_work_ticket'),
    path('process_ewt/<id>', views.process_ewt, name='process_ewt'),
    path('change_order_home', views.change_order_home, name='change_order_home'),
    path('change_order_new/<jobnumber>', views.change_order_new, name='change_order_new'),
]
