from django.urls import path

from . import views



urlpatterns = [
    path('extra_work_ticket/<id>', views.extra_work_ticket, name='extra_work_ticket'),
    path('process_ewt/<id>', views.process_ewt, name='process_ewt'),
]
