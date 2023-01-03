from django.urls import path

from . import views


urlpatterns = [
path("equipment_page/<id>", views.equipment_page, name='equipment_page'),
path("equipment_home", views.equipment_home, name='equipment_home'),
path("equipment_new", views.equipment_new, name='equipment_new'),
path("equipment_batch_outgoing/<status>", views.equipment_batch_outgoing, name='equipment_batch_outgoing'),
path("equipment_remove_from_outgoing_cart/<id>", views.equipment_remove_from_outgoing_cart, name='equipment_remove_from_outgoing_cart'),
path("equipment_remove_from_incoming_cart/<id>", views.equipment_remove_from_incoming_cart, name='equipment_remove_from_incoming_cart'),
path("equipment_add_to_outgoing/<id>", views.equipment_add_to_outgoing, name='equipment_add_to_outgoing'),
path("equipment_add_to_incoming/<id>", views.equipment_add_to_incoming, name='equipment_add_to_incoming'),
]