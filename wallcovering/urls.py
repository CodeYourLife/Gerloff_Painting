from django.urls import path
from . import views


urlpatterns = [
    path('', views.wallcovering_home, name='wallcovering_home'),
    path('wallcovering_detail/<int:wallcovering_id>', views.wallcovering_detail, name='wallcovering_detail'),
    path('wallcovering_new', views.wallcovering_new, name='wallcovering_new'),
    path('wallcovering_edit/<int:wallcovering_id>', views.wallcovering_edit, name='wallcovering_edit'),
    path('wallcovering_add_order/<int:wallcovering_id>', views.wallcovering_add_order, name='wallcovering_add_order'),
    path('wallcovering_add_pricing/<int:wallcovering_id>', views.wallcovering_add_pricing, name='wallcovering_add_pricing'),
    path('wallcovering_receive', views.wallcovering_receive, name='wallcovering_receive'),
    path('wallcovering_receive/<int:wallcovering_id>', views.wallcovering_receive, name='wallcovering_receive_for_wallcovering'),
    path('wallcovering_send_to_job/<int:wallcovering_id>', views.wallcovering_send_to_job, name='wallcovering_send_to_job'),
    path('wallcovering_add_note/<int:wallcovering_id>', views.wallcovering_add_note, name='wallcovering_add_note'),
    path('wallcovering_order_edit/<int:order_id>', views.wallcovering_order_edit, name='wallcovering_order_edit'),
    path('wallcovering_receipt_edit/<int:delivery_id>', views.wallcovering_receipt_edit, name='wallcovering_receipt_edit'),
    path('wallcovering_sent_edit/<int:sent_id>', views.wallcovering_sent_edit, name='wallcovering_sent_edit'),
    path("vendor_edit/<int:vendor_id>/edit/", views.vendor_edit, name="vendor_edit"),
]