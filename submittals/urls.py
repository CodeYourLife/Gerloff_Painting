from django.urls import path

from . import views


urlpatterns = [
path("submittals_home", views.submittals_home, name='submittals_home'),
path("submittals_new", views.submittals_new, name='submittals_new'),
path("submittals_page/<id>", views.submittals_page, name='submittals_page'),
]