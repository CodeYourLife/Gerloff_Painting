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
]