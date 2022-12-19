from django.urls import path

from . import views

urlpatterns = [
    path('book_new_job', views.book_new_job, name='book_new_job'),
    path("register",views.register,name='register'),
    path('', views.index, name='index'),
    path('register_user', views.register_user, name='register_user'),
    path('login', views.login, name='login'),
    path('logout', views.logout, name='logout'),
]