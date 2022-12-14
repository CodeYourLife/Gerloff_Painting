from django.urls import path

from . import views

from .views import JobsListView, jobs_list

urlpatterns = [
    path('JobsListView', JobsListView.as_view(), name='JobsListView'),
    path('jobs_list', views.jobs_list, name='jobs_list'),
    path('select_super', views.select_super, name='select_super'),
    path('goto_super', views.goto_super, name='goto_super'),
    path('testtable', views.testtable, name='testtable'),
    path('filter_super', views.filter_super, name='filter_super'),
    path('job_page/<jobnumber>', views.job_page,name='job_page'),
]
