from equipment.models import Vendors, VendorContact, VendorCategory
from rentals.models import Rentals, RentalNotes
from jobs.models import Jobs, Clients, ClientEmployees, Email_Errors
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
from employees.models import *
from django.http import HttpResponse
from console.misc import Email
from equipment.filters import RentalsFilter
from wallcovering.views import get_next_po_number

# Create your views here.

@login_required(login_url='/accounts/login')
def rentals_home(request):
    send_data = {}
    if request.method == 'GET':
        if 'closed_filter' in request.GET: send_data['closed_filter'] = True
    filtered_rentals = RentalsFilter(request.GET,
                                     queryset=Rentals.objects.filter(is_closed=False).order_by('job_number', 'company'))
    # rentals = Rentals.objects.filter(is_closed=False).order_by('job_number', 'company')
    rentals=[]
    for x in filtered_rentals.qs:
        rentals.append({'rental':x,'next_period':x.next_period(),'current_duration':x.current_duration(),'colorize':x.colorize()})

    send_data['rentals'] = rentals
    send_data['waiting_for_invoice'] = Rentals.objects.filter(off_rent_number__isnull=False, is_closed=False).count()
    return render(request, "rentals_home.html", send_data)


@login_required(login_url='/accounts/login')
def rental_new(request, jobnumber):
    if jobnumber == "ALL":
        jobs = Jobs.objects.filter(is_closed=False).order_by('job_name')
    else:
        jobs = Jobs.objects.filter(job_number=jobnumber).order_by('job_name')

    vendors = Vendors.objects.filter(
        category__category="Equipment Rental"
    ).order_by("company_name")

    vendor_data = []

    for vendor in vendors:
        vendor_data.append({
            "id": vendor.id,
            "company_name": vendor.company_name or "",
            "company_phone": vendor.company_phone or "",
            "company_email": vendor.company_email or "",
            "contacts": [
                {
                    "id": contact.id,
                    "name": contact.name or "",
                    "phone": contact.phone or "",
                    "email": contact.email or "",
                }
                for contact in VendorContact.objects.filter(company=vendor).order_by("name")
            ]
        })

    equipment_rental_category = VendorCategory.objects.get(category="Equipment Rental")

    if request.method == 'POST':

        selected_company = request.POST.get('select_company', '')
        selected_job = request.POST.get('select_job', '')
        selected_rep = request.POST.get('select_pm', 'no_rep')

        if selected_company == 'add_new':
            equipment_rental_category = VendorCategory.objects.get(
                category="Equipment Rental"
            )

            vendor = Vendors.objects.create(
                company_name=request.POST.get('new_client', '').strip(),
                category=equipment_rental_category,
                company_phone=request.POST.get('new_client_phone', '').strip(),
                company_email=request.POST.get('new_client_bid_email', '').strip()
            )

        else:
            vendor = Vendors.objects.get(id=selected_company)

            # Do NOT overwrite existing vendor info here.
            # Existing vendor info is only displayed on the page.

        po_number_int = get_next_po_number()
        po_number = f"TR{po_number_int}"

        rental = Rentals.objects.create(
            company=vendor,
            job_number=Jobs.objects.get(job_number=selected_job),
            item=request.POST.get('item', '').strip(),
            on_rent_date=request.POST.get('on_rent_date'),
            notes=request.POST.get('notes', '').strip(),
            purchase_order=po_number
        )

        if selected_rep != 'no_rep':

            if selected_rep == 'add_new':
                rental.rep = VendorContact.objects.create(
                    company=vendor,
                    name=request.POST.get('new_pm', '').strip(),
                    email=request.POST.get('new_pm_email', '').strip(),
                    phone=request.POST.get('new_pm_phone', '').strip()
                )

            else:
                rep = VendorContact.objects.get(
                    id=selected_rep,
                    company=vendor
                )

                # This allows the page to populate rep info and save any edits.
                rep.name = request.POST.get('new_pm', rep.name).strip()
                rep.phone = request.POST.get('new_pm_phone', rep.phone).strip()
                rep.email = request.POST.get('new_pm_email', rep.email).strip()
                rep.save()

                rental.rep = rep

        if request.POST.get('day_price', '').strip() != '':
            rental.day_price = request.POST.get('day_price').strip()

        if request.POST.get('week_price', '').strip() != '':
            rental.week_price = request.POST.get('week_price').strip()

        if request.POST.get('month_price', '').strip() != '':
            rental.month_price = request.POST.get('month_price').strip()

        rental.save()

        RentalNotes.objects.create(
            rental=rental,
            date=date.today(),
            user=Employees.objects.get(user=request.user),
            note="New Rental Added. " + request.POST.get('notes', '').strip()
        )

        createfolder("rentals/" + str(rental.id))

        return redirect("rental_page", id=rental.id, reverse='NO')

    return render(request, "rental_new.html", {
        'jobs': jobs,
        'vendors': vendors,
        'vendor_data': json.dumps(vendor_data, cls=DjangoJSONEncoder),
        'equipment_rental_category': equipment_rental_category,
    })


def rental_ajax(request):
    if request.is_ajax():
        send_data = {}
        if 'rep_id' in request.GET:
            send_data['phone'] = VendorContact.objects.get(id=request.GET['rep_id']).phone
            send_data['email'] = VendorContact.objects.get(id=request.GET['rep_id']).email
            send_data['name'] = VendorContact.objects.get(id=request.GET['rep_id']).name
        if 'vendor_id' in request.GET:
            send_data['phone'] = Vendors.objects.get(id=request.GET['vendor_id']).company_phone
            send_data['email'] = Vendors.objects.get(id=request.GET['vendor_id']).company_email
            send_data['name'] = Vendors.objects.get(id=request.GET['vendor_id']).company_name
        if 'client_id' in request.GET:
            send_data['phone'] = Clients.objects.get(id=request.GET['client_id']).phone
            send_data['email'] = Clients.objects.get(id=request.GET['client_id']).bid_email
            send_data['name'] = Clients.objects.get(id=request.GET['client_id']).company
        if 'client_pm_id' in request.GET:
            send_data['phone'] = ClientEmployees.objects.get(person_pk=request.GET['client_pm_id']).phone
            send_data['email'] = ClientEmployees.objects.get(person_pk=request.GET['client_pm_id']).email
            send_data['name'] = ClientEmployees.objects.get(person_pk=request.GET['client_pm_id']).name
        return HttpResponse(json.dumps(send_data))


@login_required(login_url='/accounts/login')
def rental_page(request, id, reverse):
    send_data = {}
    if Email_Errors.objects.filter(user=request.user.first_name + " " + request.user.last_name).exists():
        send_data['error_message']= Email_Errors.objects.filter(user=request.user.first_name + " " + request.user.last_name).last().error
    Email_Errors.objects.filter(user=request.user.first_name + " " + request.user.last_name).delete()
    rental = Rentals.objects.get(id=id)
    reverse = reverse
    reps = VendorContact.objects.filter(company=rental.company)
    vendor = rental.company
    notes = RentalNotes.objects.filter(rental=rental)
    path = os.path.join(settings.MEDIA_ROOT, "rentals", str(rental.id))
    try:
        foldercontents = os.listdir(path)
    except:
        createfolder("rentals/" + str(rental.id))
        foldercontents = os.listdir(path)
    if request.method == 'POST':
        if 'off_rent_note' in request.POST:
            rental.requested_off_rent = True
            rental.save()
            RentalNotes.objects.create(rental=rental, date=date.today(),
                                       user=Employees.objects.get(user=request.user),
                                       note="Please call off-rent. " + request.POST['off_rent_note'])
            message = "Please call off this rental. " + rental.item + ". From Job -" + rental.job_number.job_name + "\n " + \
                      request.POST['off_rent_note']
            Email_Errors.objects.filter(user=request.user.first_name + " " + request.user.last_name).delete()
            check_sender = Employees.objects.filter(user=request.user).first() if request.user.is_authenticated else None
            sender = check_sender.email if check_sender else "operations@gerloffpainting.com"
            try:
                Email.sendEmail("Call Off Rent", message, ["warehouse@gerloffpainting.com"], False,sender)
                error_message = "Your email to call off rent was sent successfully!"
            except:
                error_message = "ERROR! Your email was not sent.  Please call the warehouse and let them know to call it off rent."
            Email_Errors.objects.create(user=request.user.first_name + " " + request.user.last_name, error=error_message,
                                        date=date.today())
        if 'form_1' in request.POST:
            note = ""
            rental.company.company_phone = request.POST['company_phone']
            rental.company.company_email = request.POST['company_email']
            rental.company.save()
            if request.POST['select_pm'] != 'no_rep':
                if request.POST['select_pm'] == 'add_new':
                    rental.rep = VendorContact.objects.create(company=vendor, name=request.POST['new_pm'],
                                                              email=request.POST['new_pm_email'],
                                                              phone=request.POST['new_pm_phone'])
                else:
                    rental.rep = VendorContact.objects.get(id=request.POST['select_pm'])
                    rental.rep.name = request.POST['new_pm']
                    rental.rep.email = request.POST['new_pm_email']
                    rental.rep.phone = request.POST['new_pm_phone']
                    rental.rep.save()
            else:
                if rental.rep:
                    rental.rep = None
            if request.POST['purchase_order'] != '':
                note = "Purchase Order Entered. "
                rental.purchase_order = request.POST['purchase_order']
            if request.POST['off_rent_date'] != '':
                note = note + " Off Rent Date Entered. "
                rental.off_rent_date = request.POST['off_rent_date']
            if request.POST['off_rent_number'] != '':
                note = note + " Off Rent Number Entered. "
                rental.off_rent_number = request.POST['off_rent_number']
            if request.POST['day_price'] != '':
                note = note + " Day Price Entered. "
                rental.day_price = request.POST['day_price']
            if request.POST['week_price'] != '':
                note = note + " Week Price Entered. "
                rental.week_price = request.POST['week_price']
            if request.POST['month_price'] != '':
                note = note + " Month Price Entered. "
                rental.month_price = request.POST['month_price']
            if 'is_closed' in request.POST:
                note = note + " Billed. "
                rental.is_closed = True
            if note != "":
                note = note + " " + request.POST['rental_notes']
                RentalNotes.objects.create(rental=rental, date=date.today(),
                                           user=Employees.objects.get(user=request.user),
                                           note=note)
            rental.save()
        if 'rental_note' in request.POST:
            RentalNotes.objects.create(rental=rental, date=date.today(),
                                       user=Employees.objects.get(user=request.user),
                                       note=request.POST['rental_note'])
        if 'upload_file' in request.FILES:
            fileitem = request.FILES['upload_file']
            fn = os.path.basename(fileitem.name)
            fn2 = os.path.join(settings.MEDIA_ROOT, "rentals", str(rental.id), fn)
            open(fn2, 'wb').write(fileitem.file.read())
        return redirect("rental_page", id=rental.id, reverse='YES')
    send_data['rental']=rental
    send_data['reverse'] =reverse
    send_data['reps'] =reps
    send_data['notes'] =notes
    send_data['foldercontents'] =foldercontents
    return render(request, "rental_page.html", send_data)
