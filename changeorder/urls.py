from django.urls import path

from . import views



urlpatterns = [
    path('extra_work_ticket/<id>', views.extra_work_ticket, name='extra_work_ticket'),
]
