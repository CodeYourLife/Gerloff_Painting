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
from .tables import *
from json import dumps
import json
from django.core.serializers.json import DjangoJSONEncoder
# Create your views here.


def post_wallcovering_order(request):
    print("hi")
    return render(request, "index")


def wallcovering_order(request, id, job_number):
    jobs = Jobs.objects.filter(status="Open")
    vendors = Vendors.objects.all()
    vendors1 = Vendors.objects.values()
    if job_number == "ALL":
        selectedjob = 0
        if id == "ALL":
            selectedwc = 0
            selectedpricing = 0
            selectedvendor = 0
            wallcovering = Wallcovering.objects.filter(job_number__status="Open")
            pricing = WallcoveringPricing.objects.filter(wallcovering__job_number__status="Open")
            wallcovering1 = Wallcovering.objects.values('id','job_number__job_number','code','vendor__id','vendor__company_name','pattern','estimated_quantity', 'estimated_unit').filter(job_number__status="Open")
            pricing1 = WallcoveringPricing.objects.values('wallcovering__id','quote_date','min_yards','price','unit').filter(wallcovering__job_number__status="Open")
    else:
        selectedjob = Jobs.objects.get(job_number=job_number)
        wallcovering = Wallcovering.objects.filter(job_number__job_number=job_number)
        pricing = WallcoveringPricing.objects.filter(wallcovering__job_number__job_number=job_number)
        wallcovering1 = Wallcovering.objects.values('id','job_number__job_number','code','vendor__id','vendor__company_name','pattern','estimated_quantity', 'estimated_unit').filter(job_number__job_number=job_number)
        pricing1 = WallcoveringPricing.objects.values('wallcovering__id','quote_date','min_yards','price','unit').filter(wallcovering__job_number__job_number=job_number)
        if id == "ALL":
            selectedwc = 0
            selectedpricing = 0
            selectedvendor = 0
        else:
            selectedwc = Wallcovering.objects.get(id=id)
            selectedpricing = WallcoveringPricing.objects.filter(wallcovering__id=id)
            selectedvendor = Vendors.objects.get(wallcovering__id=id)
    wallcovering_json = json.dumps(list(wallcovering1), cls=DjangoJSONEncoder)
    pricing_json = json.dumps(list(pricing1), cls=DjangoJSONEncoder)
    vendors_json = json.dumps(list(vendors1), cls=DjangoJSONEncoder)
    return render(request, "wallcovering_order.html", {'vendors':vendors,'vendors_json':vendors_json,'wallcovering_json':wallcovering_json,'pricing_json':pricing_json, 'selectedwc':selectedwc, 'selectedpricing':selectedpricing, 'selectedjob':selectedjob, 'jobs': jobs,'wallcovering': wallcovering, 'pricing': pricing, 'selectedvendor': selectedvendor})


def wallcovering_home(request):
    #wc_only_open_jobs = Wallcovering.objects.filter(job_number__status = "Open").order_by(-job_number)
    wc_table = []
    xjob_name = "NA"
    xcode = "NA"
    xordered = 0
    xdateordered = "NA"
    xreceivedall = "NA"
    xreceived = 0
    xdatereceived = ""
    xtojob = 0
    for x in Wallcovering.objects.filter(job_number__status = "Open").order_by('-job_number'):
        xjob_name = "NA"
        xcode = "NA"
        xordered = 0
        xdateordered = "NA"
        xreceivedall = "NA"
        xreceived = 0
        xdatereceived = ""
        xtojob = 0

        xjob_name = x.job_number.job_name
        xcode = x.code
        #orderinformation ->

        for orderitem in OrderItems.objects.filter(wallcovering=x):

            xordered = xordered + orderitem.quantity

            xdateordered = orderitem.order.date_ordered
            if orderitem.is_satisfied == False:
                xreceivedall = "NO"
            else:
                if xreceivedall != "NO":
                    xreceivedall = "YES"

        #received information
        match = False
        for order in Orders.objects.filter(job_number = x.job_number):
            for orderitem in OrderItems.objects.filter(order = order):
                if orderitem.wallcovering == x:
                        match = True
            if match == True:
                for receivedpackage in Packages.objects.filter(delivery__order = order):
                    xreceived = xreceived + receivedpackage.quantity_received
                    xdatereceived = receivedpackage.delivery.date
                    for sentpackage in OutgoingItem.objects.filter(package = receivedpackage):
                        xtojob = xtojob + sentpackage.quantity_sent


        wc_table.append(
            {
            'job_name': xjob_name,
            'job_number': x.job_number.job_number,
            'code':xcode,
            'qty_ordered' : xordered,
            'date_ordered' : xdateordered,
            'is_received_all' : xreceivedall,
            'packages_received' : xreceived,
            'date_received' : xdatereceived,
            'packages_to_job' : xtojob,
            'id' : x.id,
            })
    wc_not_ordereds=Wallcovering.objects.exclude(orderitems1__item_description__isnull=False) #wallcovering not ordered yet
    wc_ordereds = OrderItems.objects.filter(is_satisfied=False) #orders not received yet
    received_deliveries = WallcoveringDelivery.objects.all()
    jobsite_deliveries =  OutgoingItem.objects.all()
    packages = []
    for y in Packages.objects.filter(delivery__order__job_number__status = "Open" ):
        print("THIS HERE")
        print(y.id)
        sentquantity = 0
        match = False
        for x in OutgoingItem.objects.filter(package = y):
            sentquantity = sentquantity + x.quantity_sent
        if sentquantity == y.quantity_received:
            match = True
        if match == False:
            packages.append(y)
    #packages = Packages.objects.filter(is_all_delivered_to_job=False) #items in warehouse not delivered to job yet
    return render(request, "wallcovering_home.html", {'wc_table':wc_table, 'wc_not_ordereds': wc_not_ordereds,'wc_ordereds': wc_ordereds, 'received_deliveries':received_deliveries ,'jobsite_deliveries':jobsite_deliveries ,'packages':packages})

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

def wallcovering_status(request, table_type, id):
    if table_type == 'Outgoing':
        table = OutgoingWallcoveringTable(OutgoingItem.objects.filter(id=id))
        return render(request, "wallcovering_status.html", {'table': table})