
from equipment.models import Vendors, VendorContact, VendorCategory
from rentals.models import Rentals, RentalNotes
from jobs.models import Jobs
from django.shortcuts import render, redirect
from .tables import RentalsTable
from django_tables2 import RequestConfig
from django.contrib.auth.decorators import login_required
import json
from django.core.serializers.json import DjangoJSONEncoder
from datetime import date
from console.misc import createfolder
import os
import os.path
from django.conf import settings
from django.http import HttpResponse

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
    pms_json = json.dumps(list(VendorContact.objects.values('name', 'id', 'company')), cls=DjangoJSONEncoder)
    if request.method == 'POST':
        if request.POST['select_company'] == 'add_new':
            vendor = Vendors.objects.create(company_name = request.POST['new_client'],category=VendorCategory.objects.get(category = "Equipment Rental"),company_phone=request.POST['new_client_phone'],company_email=request.POST['new_client_bid_email'])
        else:
            vendor = Vendors.objects.get(id=request.POST['select_company'])
        rental = Rentals.objects.create(company=vendor, job_number=Jobs.objects.get(job_number=request.POST['select_job']),item=request.POST['item'],on_rent_date=request.POST['on_rent_date'], notes = request.POST['notes'])
        if request.POST['select_pm'] != 'no_rep':
            if request.POST['select_pm'] == 'add_new':
                rental.rep = VendorContact.objects.create(company=vendor,name=request.POST['new_pm'],email=request.POST['new_pm_email'],phone=request.POST['new_pm_phone'])
            else:
                rental.rep = VendorContact.objects.get(id = request.POST['select_pm'])

        if request.POST['purchase_order'] != '':rental.purchase_order=request.POST['purchase_order']
        if request.POST['notes']!= '': rental.notes=request.POST['notes']
        if request.POST['day_price']!= '': rental.day_price=request.POST['day_price']
        if request.POST['week_price']!= '':rental.week_price=request.POST['week_price']
        if request.POST['month_price']!= '':rental.month_price=request.POST['month_price']
        rental.save()
        RentalNotes.objects.create(rental=rental,date=date.today(),user=request.user.first_name + " " + request.user.last_name,note="New Rental Added. " + request.POST['notes'])
        createfolder("rentals/" + str(rental.id))

        return redirect("rental_page",id=rental.id,reverse='NO')
    else:
        return render(request, "rental_new.html", {'jobs':jobs,'vendors':vendors,'data':pms_json})


@login_required(login_url='/accounts/login')
def rental_page(request,id,reverse):
    rental = Rentals.objects.get(id=id)
    reverse = reverse
    reps = VendorContact.objects.filter(company=rental.company)
    vendor = rental.company
    notes = RentalNotes.objects.filter(rental=rental)
    path = os.path.join(settings.MEDIA_ROOT, "rentals", str(rental.id))
    foldercontents =  os.listdir(path)
    if request.method == 'POST':
        if 'form_1' in request.POST:
            if request.POST['select_pm'] != 'no_rep':
                if request.POST['select_pm'] == 'add_new':
                    rental.rep = VendorContact.objects.create(company=vendor,name=request.POST['new_pm'],email=request.POST['new_pm_email'],phone=request.POST['new_pm_phone'])
                else:
                    rental.rep = VendorContact.objects.get(id = request.POST['select_pm'])
            if request.POST['purchase_order'] != '':
                rental.purchase_order=request.POST['purchase_order']
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
        if 'rental_note' in request.POST:
            RentalNotes.objects.create(rental=rental, date=date.today(),
                                       user=request.user.first_name + " " + request.user.last_name,
                                       note=request.POST['rental_note'])
        if 'upload_file' in request.FILES:
            fileitem = request.FILES['upload_file']
            fn = os.path.basename(fileitem.name)
            fn2 = os.path.join(settings.MEDIA_ROOT, "rentals", str(rental.id), fn)
            open(fn2, 'wb').write(fileitem.file.read())
        return redirect("rental_page", id=rental.id, reverse='YES')
    return render(request, "rental_page.html", {'rental': rental, 'reverse':reverse,'reps':reps,'notes':notes,'foldercontents':foldercontents})