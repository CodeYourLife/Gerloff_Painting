from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
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
path("get_directory_contents/<id> <value> <app>", views.get_directory_contents, name='get_directory_contents'),
path("update_equipment/<id>", views.update_equipment, name='update_equipment'),
path("request_pickup/<jobnumber> <item> <pickup> <status>", views.request_pickup, name='request_pickup'),
path("complete_pickup/<pickup>", views.complete_pickup, name='complete_pickup')

]

# only in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)