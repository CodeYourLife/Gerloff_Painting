from django.urls import path

from . import views


urlpatterns = [
path("wallcovering_home", views.wallcovering_home, name='wallcovering_home'),
path("post_wallcovering_order", views.post_wallcovering_order, name='post_wallcovering_order'),
path("wallcovering_order_new/<id> <job_number>", views.wallcovering_order_new, name='wallcovering_order_new'),
path("wallcovering_pattern/<id>", views.wallcovering_pattern, name='wallcovering_pattern'),
path("wallcovering_pattern_new", views.wallcovering_pattern_new, name='wallcovering_pattern_new'),
path("wallcovering_status/<table_type> <id>", views.wallcovering_status, name='wallcovering_status'),
path("wallcovering_order/<id>", views.wallcovering_order, name='wallcovering_order'),
path("wallcovering_receive/<orderid>", views.wallcovering_receive, name='wallcovering_receive'),
path("wallcovering_send/<jobnumber>", views.wallcovering_send, name='wallcovering_send'),
path("wallcovering_pattern_all", views.wallcovering_pattern_all, name='wallcovering_pattern_all'),
path("wallcovering_order_all", views.wallcovering_order_all, name='wallcovering_order_all'),
path("wallcovering_receive_all", views.wallcovering_receive_all, name='wallcovering_receive_all'),
path("wallcovering_send_all", views.wallcovering_send_all, name='wallcovering_send_all'),
]