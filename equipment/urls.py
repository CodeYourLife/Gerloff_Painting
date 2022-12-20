from django.urls import path

from . import views


urlpatterns = [
path("equipment_page/<id>", views.equipment_page, name='equipment_page'),
path("equipment_home", views.equipment_home, name='equipment_home'),
]