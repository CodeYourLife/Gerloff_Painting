from django.urls import path
from . import views

urlpatterns = [
    path("registration", views.registration, name='registration'),
    path("forgot_password", views.forgotPassword, name='forgot_password'),
    path("verify_pin", views.verifyPin, name='verify_pin'),
    path('login', views.login, name='login'),
    path('logout', views.logout, name='logout'),
]