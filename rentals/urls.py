from django.urls import path

from . import views


urlpatterns = [
path("rentals_home", views.rentals_home, name='rentals_home'),
path("rental_ajax", views.rental_ajax, name='rental_ajax'),
path("rental_new/<jobnumber>", views.rental_new, name='rental_new'),
path("rental_page/<id> <reverse>", views.rental_page, name='rental_page'),#reverse = 'YES' or 'NO'
]