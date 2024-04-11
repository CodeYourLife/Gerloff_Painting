from django.urls import path
from django.views.decorators.csrf import csrf_exempt
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
    path('price_old_ewt/<id>', views.price_old_ewt, name='price_old_ewt'),
    path('preview_TMProposal/<id>', views.print_TMProposal, name='preview_TMProposal'),
    path('getChangeorderFolder', views.getChangeorderFolder, name='getChangeorderFolder'),
    path('uploadFile', csrf_exempt(views.uploadFile), name='uploadFile'),
    path('downloadFile', csrf_exempt(views.downloadFile), name='downloadFile'),
    path('email_signed_ticket/<changeorder>', views.email_signed_ticket, name='email_signed_ticket'),
    path('batch_approve_co/<id>', views.batch_approve_co, name='batch_approve_co'),
    path('email_for_signature/<id>', views.email_for_signature, name='email_for_signature'),
]
