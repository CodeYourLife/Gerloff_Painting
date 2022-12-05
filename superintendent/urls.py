from django.urls import path

from . import views

from .views import JobsListView, jobs_list

urlpatterns = [
    path('JobsListView', JobsListView.as_view()),
    path('jobs_list', views.jobs_list),
    path('select_super', views.select_super),
    path('goto_super', views.goto_super),
]
