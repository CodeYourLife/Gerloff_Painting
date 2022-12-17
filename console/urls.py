from django.urls import path

from . import views

urlpatterns = [
    path('book_new_job', views.book_new_job, name='book_new_job'),
    path("register",views.register,name='register'),
    path('', views.index, name='index'),
    path('tester', views.tester, name='tester')
]