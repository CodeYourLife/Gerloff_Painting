from django.urls import path

from . import views


urlpatterns = [
path("rentals_home", views.rentals_home, name='rentals_home'),
]