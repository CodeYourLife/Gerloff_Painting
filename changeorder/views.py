from django.shortcuts import render
from django.views.generic import ListView
from console.models import *
from django.shortcuts import render, redirect

# Create your views here.

def extra_work_ticket(request,id):
    if request.method == 'GET':
        changeorder = ChangeOrders.objects.get(id=id)
        return render(request, "extra_work_ticket.html", {'changeorder': changeorder})