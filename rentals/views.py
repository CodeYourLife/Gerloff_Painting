from equipment.models import Vendors
from rentals.models import Rentals
from jobs.models import Jobs
from django.shortcuts import render, redirect
from .tables import RentalsTable
from django_tables2 import RequestConfig
from django.contrib.auth.decorators import login_required
# Create your views here.

@login_required(login_url='/accounts/login')
def rentals_home(request):
    table = RentalsTable(Rentals.objects.filter(is_closed=False).order_by('off_rent_date','job_number'))
    RequestConfig(request).configure(table)
    return render(request, "rentals_home.html", {'table': table})

@login_required(login_url='/accounts/login')
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


@login_required(login_url='/accounts/login')
def rental_page(request,id,reverse):
    rental = Rentals.objects.get(id=id)
    reverse = reverse
    if request.method == 'POST':
        print(request.POST)
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
        if 'is_closed' in request.POST:
            rental.is_closed = True
            rental.save()
        return redirect("rental_page", id=rental.id, reverse='YES')
    return render(request, "rental_page.html", {'rental': rental, 'reverse':reverse})