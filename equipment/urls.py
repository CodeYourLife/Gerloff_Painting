from django.urls import path

from . import views


urlpatterns = [
path("equipment_page/<id>", views.equipment_page, name='equipment_page'),
]