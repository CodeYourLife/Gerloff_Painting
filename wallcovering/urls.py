from django.urls import path
from . import views


urlpatterns = [
    path('', views.wallcovering_home, name='wallcovering_home'),
    path('wallcovering_detail/<int:wallcovering_id>', views.wallcovering_detail, name='wallcovering_detail'),
    path('wallcovering_new', views.wallcovering_new, name='wallcovering_new'),
    path('wallcovering_edit/<int:wallcovering_id>', views.wallcovering_edit, name='wallcovering_edit'),
    path('wallcovering_add_order/<int:wallcovering_id>', views.wallcovering_add_order, name='wallcovering_add_order'),
    path('wallcovering_pending_order/<int:pending_order_id>', views.wallcovering_pending_order, name='wallcovering_pending_order'),
    path('wallcovering_add_pricing/<int:wallcovering_id>', views.wallcovering_add_pricing, name='wallcovering_add_pricing'),
    path('wallcovering_delete_pricing/<int:wallcovering_id>/<int:pricing_id>', views.wallcovering_delete_pricing, name='wallcovering_delete_pricing'),
    path('wallcovering_receive', views.wallcovering_receive, name='wallcovering_receive'),
    path('wallcovering_receive/<int:wallcovering_id>', views.wallcovering_receive, name='wallcovering_receive_for_wallcovering'),
    path('wallcovering_send_to_job/<int:wallcovering_id>', views.wallcovering_send_to_job, name='wallcovering_send_to_job'),
    path('wallcovering_add_note/<int:wallcovering_id>', views.wallcovering_add_note, name='wallcovering_add_note'),
    path('wallcovering_order_edit/<int:order_id>', views.wallcovering_order_edit, name='wallcovering_order_edit'),
    path('wallcovering_receipt_edit/<int:delivery_id>', views.wallcovering_receipt_edit, name='wallcovering_receipt_edit'),
    path('wallcovering_sent_edit/<int:sent_id>', views.wallcovering_sent_edit, name='wallcovering_sent_edit'),
    path("vendor_edit/<int:vendor_id>/edit/", views.vendor_edit, name="vendor_edit"),
    path(
        "wallcovering/<int:id>/job-tag/print/",
        views.wallcovering_job_tag_print,
        name="wallcovering_job_tag_print"
    ),
    path(
        "wallcovering/<int:wallcovering_id>/print-labels/",
        views.wallcovering_print_labels,
        name="wallcovering_print_labels"
    ),
    path(
        "wallcovering/<int:wallcovering_id>/pricing-files/",
        views.wallcovering_pricing_files,
        name="wallcovering_pricing_files"
    ),
    path(
        "wallcovering/<int:wallcovering_id>/pricing-files/upload/",
        views.wallcovering_pricing_upload,
        name="wallcovering_pricing_upload"
    ),
    path(
        "wallcovering/<int:wallcovering_id>/pricing-files/download/",
        views.wallcovering_pricing_download,
        name="wallcovering_pricing_download"
    ),
]
