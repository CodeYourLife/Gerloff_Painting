from django.utils import timezone
from django.views import generic
from django.views.generic import ListView
from console.models import *
from django.contrib.auth.models import User, auth
from django.shortcuts import render, redirect
from json import dumps
import json
from django.core.serializers.json import DjangoJSONEncoder
from datetime import date
from django_tables2 import SingleTableView
from equipment.tables import WallcoveringPriceTable
# Create your views here.

def wallcovering_home(request):
    wc_not_ordereds=Wallcovering.objects.exclude(orderitems1__item_description__isnull=False) #wallcovering not ordered yet
    wc_ordereds = Orders.objects.filter(is_satisfied=False) #orders not received yet
    received_deliveries = WallcoveringDelivery.objects.all()
    jobsite_deliveries =  OutgoingWallcovering.objects.all()
    packages = Packages.objects.filter(is_all_delivered_to_job=False) #items in warehouse not delivered to job yet
    return render(request, "wallcovering_home.html", {'wc_not_ordereds': wc_not_ordereds,'wc_ordereds': wc_ordereds, 'received_deliveries':received_deliveries ,'jobsite_deliveries':jobsite_deliveries ,'packages':packages})

def wallcovering_pattern(request, id):
    selectedpattern = Wallcovering.objects.get(id=id)
    table = WallcoveringPriceTable(WallcoveringPricing.objects.filter(wallcovering__id = id))
    jobs = Jobs.objects.all()
    vendors = Vendors.objects.all()
    if request.method == 'POST':
        if 'pricing1_price' in request.POST:
            new_price = WallcoveringPricing(wallcovering = selectedpattern, quote_date=request.POST['pricing1_date'],
                                            min_yards=request.POST['pricing1_yards_tier1'],
                                            price=request.POST['pricing1_price'],
                                            unit=request.POST['pricing_unit'],
                                            note=request.POST['pricing_note'])
            new_price.save()
        else:
            selectedpattern.job_number = Jobs.objects.get(job_number=request.POST['job_select'])
            selectedpattern.code = request.POST['code']
            selectedpattern.vendor = Vendors.objects.get(id = request.POST['vendor'])
            selectedpattern.pattern = request.POST['pattern']
            selectedpattern.estimated_quantity = request.POST['estimated_quantity']
            selectedpattern.estimated_unit = request.POST['estimated_unit']
            selectedpattern.cut_charge = request.POST['cut_charge']
            selectedpattern.roll_width = request.POST['roll_width']
            selectedpattern.vertical_repeat = request.POST['vertical_repeat']
            selectedpattern.notes = request.POST['notes']
            if 'is_random_reverse' in request.POST:
                selectedpattern.is_random_reverse = True
            else:
                selectedpattern.is_random_reverse = False
            if 'is_repeat' in request.POST:
                selectedpattern.is_repeat = True
            else:
                selectedpattern.is_repeat = False
            selectedpattern.save()


    return render(request, "wallcovering_pattern.html", {'selectedpattern': selectedpattern, 'jobs': jobs, 'vendors': vendors, 'table': table })
