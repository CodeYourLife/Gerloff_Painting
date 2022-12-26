from django.urls import path

from . import views


urlpatterns = [
path("wallcovering_home", views.wallcovering_home, name='wallcovering_home'),
path("wallcovering_order/<id> <job_number>", views.wallcovering_order, name='wallcovering_order'),
path("wallcovering_pattern/<id>", views.wallcovering_pattern, name='wallcovering_pattern'),
path("wallcovering_status/<table_type> <id>", views.wallcovering_status, name='wallcovering_status'),
]