from django.urls import path

from . import views


urlpatterns = [
path("subcontractor_home", views.subcontractor_home, name='subcontractor_home'),
path("connect", views.connect, name='connect'),
path("subcontractor_payments", views.subcontractor_payments, name='subcontractor_payments'),
path("new_subcontractor_payment", views.new_subcontractor_payment, name='new_subcontractor_payment'),
path("", views.connect, name='connect'),
path("portal/<sub_id> <contract_id>", views.portal, name='portal'),
path("subcontract/<id>", views.subcontract, name='subcontract'),
path("subcontractor/<id>", views.subcontractor, name='subcontractor'),
path("subcontractor_new", views.subcontractor_new, name='subcontractor_new'),
path("subcontracts_new", views.subcontracts_new, name='subcontracts_new'),
path("subcontracts_home", views.subcontracts_home, name='subcontracts_home'),
path("subcontract_invoices/<subcontract_id> <item_id>", views.subcontract_invoices, name='subcontract_invoices'),
path("subcontractor_invoice_new/<subcontract_id>", views.subcontractor_invoice_new, name='subcontractor_invoice_new'),
path("portal_invoice_new/<subcontract_id>", views.portal_invoice_new, name='portal_invoice_new'),
path("sub_change_orders", views.sub_change_orders, name='sub_change_orders'),
path("build_subcontractor_approvers", views.build_subcontractor_approvers, name='build_subcontractor_approvers'),
path("subcontractor_approvers/<subcontractor_id>", views.subcontractor_approvers, name='subcontractor_approvers'),
path("subcontractor_portal_select_changeorder/<job_number> <subcontractor_id><employee_id>", views.subcontractor_portal_select_changeorder, name='subcontractor_portal_select_changeorder'),
path("subcontractor_portal_select_job_for_ticket/<subcontractor_id><employee_id>", views.subcontractor_portal_select_job_for_ticket, name='subcontractor_portal_select_job_for_ticket'),
path("subcontractor_portal_create_ticket/<changeorder_id> <subcontractor_id><employee_id2>", views.subcontractor_portal_create_ticket, name='subcontractor_portal_create_ticket'),
path("subcontractor_portal_select_ticket_for_signature/<subcontractor_id><employee_id>", views.subcontractor_portal_select_ticket_for_signature, name='subcontractor_portal_select_ticket_for_signature'),
path("subcontractor_portal_get_signature/<changeorder_id> <subcontractor_id><employee_id>", views.subcontractor_portal_get_signature, name='subcontractor_portal_get_signature'),
path("subcontractor_portal_email_for_signature/<changeorder_id> <subcontractor_id><employee_id>", views.subcontractor_portal_email_for_signature, name='subcontractor_portal_email_for_signature'),
path("subcontractor_portal_ewt_edit/<changeorder_id> <subcontractor_id><employee_id2>", views.subcontractor_portal_ewt_edit, name='subcontractor_portal_ewt_edit'),
path("subcontractor_portal_email_signed_ticket/<changeorder_id> <subcontractor_id><employee_id>", views.subcontractor_portal_email_signed_ticket, name='subcontractor_portal_email_signed_ticket'),
path("subcontractor_payment_print/<id>", views.subcontractor_payment_print, name='subcontractor_payment_print'),
path('portal/employees/<int:sub_id>/',views.subcontractor_employee_management,name='subcontractor_employee_management'),
path('subs/employee_ajax/', views.subcontractor_employee_ajax, name='subcontractor_employee_ajax'),
path('subs/employee_update/', views.subcontractor_employee_update, name='subcontractor_employee_update'),
path('subs/employee_remove/', views.subcontractor_employee_remove, name='subcontractor_employee_remove'),
path('subs/employee_assign_job/', views.assign_subcontractor_employee_job, name='assign_subcontractor_employee_job'),
path('subs/employee_create/',views.subcontractor_employee_create,name='subcontractor_employee_create'),
path('subs/employee_remove_job/',views.remove_subcontractor_employee_job,name='remove_subcontractor_employee_job'),
path("subcontractor_employee_portal/<employee_id>", views.subcontractor_employee_portal, name='subcontractor_employee_portal'),
path(
    'subcontractor_employee_portal/<int:employee_id>/',
    views.subcontractor_employee_portal,
    name='subcontractor_employee_portal'
),
path(
    'complete_subcontractor_toolbox_talk/',
    views.complete_subcontractor_toolbox_talk,
    name='complete_subcontractor_toolbox_talk'
),
path(
    'subcontractor_toolbox_file/<int:scheduled_id>/<str:language>/<int:employee_id>/',
    views.subcontractor_toolbox_file,
    name='subcontractor_toolbox_file'
),
]