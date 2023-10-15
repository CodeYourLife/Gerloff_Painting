from django.urls import path

from . import views



urlpatterns = [
    path('extra_work_ticket/<id>', views.extra_work_ticket, name='extra_work_ticket'),
    path('process_ewt/<id>', views.process_ewt, name='process_ewt'),
    path('change_order_home', views.change_order_home, name='change_order_home'),
    path('change_order_new/<jobnumber>', views.change_order_new, name='change_order_new'),
    path('change_order_send/<id>', views.change_order_send, name='change_order_send'),
    path('view_ewt/<id>', views.view_ewt, name='view_ewt'),
    path('print_ticket/<id> <status>', views.print_ticket, name='print_ticket'),
    path('price_ewt/<id>', views.price_ewt, name='price_ewt'),
    path('print_TMProposal/<id>', views.print_TMProposal, name='print_TMProposal'),
]
