from django.utils import timezone
from django.views import generic
from django.views.generic import ListView
from console.models import *
from console.models import Rentals
from django.contrib.auth.models import User, auth
from django.shortcuts import render, redirect
from json import dumps
import json
from django.core.serializers.json import DjangoJSONEncoder
from datetime import date
from django_tables2 import SingleTableView
from .tables import RentalsTable
from django_tables2 import RequestConfig
# Create your views here.

def rentals_home(request):
    table = RentalsTable(Rentals.objects.filter(is_closed=False))
    RequestConfig(request).configure(table)
    return render(request, "rentals_home.html", {'table': table})

def rental_new(request,jobnumber):
    if jobnumber == "ALL":
        jobs = Jobs.objects.all()
    else:
        jobs = Jobs.objects.filter(job_number=id)
    vendors = Vendors.objects.filter(category__category="Equipment Rental")

    if request.method == 'POST':
        rental = Rentals.objects.create(company=Vendors.objects.get(id=request.POST['select_vendor']), job_number=Jobs.objects.get(job_number=request.POST['select_job']),item=request.POST['item'],on_rent_date=request.POST['on_rent_date'])
        rental = Rentals.objects.latest('id')
        posted = True
        if request.POST['purchase_order'] != '':
            rental.purchase_order=request.POST['purchase_order']
            rental.save()
        if request.POST['notes']!= '':
            rental.notes=request.POST['notes']
            rental.save()
        if request.POST['day_price']!= '':
            rental.day_price=request.POST['day_price']
            rental.save()
        if request.POST['week_price']!= '':
            rental.week_price=request.POST['week_price']
            rental.save()
        if request.POST['month_price']!= '':
            rental.month_price=request.POST['month_price']
            rental.save()
        return redirect("rental_page",id=rental.id,reverse='NO')
    else:
        return render(request, "rental_new.html", {'jobs':jobs,'vendors':vendors})


def rental_page(request,id,reverse):
    rental = Rentals.objects.get(id=id)
    reverse = reverse
    if request.method == 'POST':
        if request.POST['purchase_order'] != '':
            rental.purchase_order=request.POST['purchase_order']
            rental.save()
        if request.POST['notes']!= '':
            rental.notes=request.POST['notes']
            rental.save()
        if request.POST['off_rent_date'] != '':
            rental.off_rent_date=request.POST['off_rent_date']
            rental.save()
        if request.POST['off_rent_number']!= '':
            rental.off_rent_number=request.POST['off_rent_number']
            rental.save()
        if request.POST['day_price']!= '':
            rental.day_price=request.POST['day_price']
            rental.save()
        if request.POST['week_price']!= '':
            rental.week_price=request.POST['week_price']
            rental.save()
        if request.POST['month_price']!= '':
            rental.month_price=request.POST['month_price']
            rental.save()
        return redirect("rental_page", id=rental.id, reverse='YES')
    return render(request, "rental_page.html", {'rental': rental, 'reverse':reverse})