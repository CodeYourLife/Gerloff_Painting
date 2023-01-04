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
from .filters import OrderItemsFilter
from django_tables2 import RequestConfig
# Create your views here.


def wallcovering_receive(request,orderid):
    if orderid == 'ALL':
        already_picked = 'ALL'
        open_orders = []
        open_order_items = []
        for y in Orders.objects.filter(job_number__status="Open"):
            b=0
            for x in OrderItems.objects.filter(order = y):
                if int(x.quantity_received()) < int(x.quantity):
                    b=1
                    open_order_items.append(x)
            if b==1:
                open_orders.append(y)
        items_json = []
    else:
        already_picked = Orders.objects.get(id=orderid)
        open_orders = Orders.objects.filter(id=orderid)
        open_order_items = []
        items_json = []
        for x in OrderItems.objects.filter(order=already_picked):
            if int(x.quantity_received()) < int(x.quantity):
                open_order_items.append(x)
                thisdict = {"id": x.id,'item_description':x.item_description, 'quantity':x.quantity,'unit':x.unit,'quantity_received':int(x.quantity_received())}
                items_json.append(thisdict)
    items_json = json.dumps(list(items_json), cls=DjangoJSONEncoder)
    return render(request, "wallcovering_receive.html", {'open_orders':open_orders,'open_order_items':open_order_items,'already_picked':already_picked,'items_json':items_json})
def wallcovering_order(request,id):
    order = Orders.objects.get(id=id)
    orderstable = OrdersTable(Orders.objects.filter(id=id))
    orderitemstable=OrderItemsTable(OrderItems.objects.filter(order=order))
    packagestable = PackagesTable(Packages.objects.filter(delivery__order=order))
    receiptstable = ReceivedTable(ReceivedItems.objects.filter(order_item__order=order))
    jobdeliveriestable = JobDeliveriesTable(OutgoingItem.objects.filter(package__delivery__order=order))
    return render(request, "wallcovering_order.html", {'orderstable': orderstable, 'orderitemstable':orderitemstable, 'packagestable':packagestable,'receiptstable':receiptstable,'jobdeliveriestable':jobdeliveriestable})

def post_wallcovering_order(request):
    new_order = Orders(job_number=Jobs.objects.get(job_number=request.POST["select_job"]),description=request.POST["description"],vendor=Vendors.objects.get(id=request.POST["select_vendor"]),date_ordered=date.today())
    new_order.save()
    new_order = Orders.objects.latest('id')
    if 'po_number' in request.POST:
        new_order.po_number = request.POST["po_number"]
        new_order.save()
    print("Number of Rows")
    print(request.POST["number_rows"])
    for y in range (0,int(request.POST["number_rows"])+1):
        print(y)
        x=str(y)
        new_item = OrderItems(order =new_order,item_description=request.POST["item_description"+x], quantity=request.POST["quantity"+x],unit=request.POST["unit"+x], price=request.POST["price"+x])
        new_item.save()
        new_item= OrderItems.objects.latest('id')
        if 'notes'+x in request.POST:
            new_item.item_notes = request.POST["notes"+x]
            new_item.save()
        if 'select_wallcovering'+x in request.POST:
            new_item.wallcovering = Wallcovering.objects.get(id=request.POST["select_wallcovering" + x])
            new_item.save()

    return redirect('wallcovering_order',id=new_order.id)

def wallcovering_order_new(request, id, job_number):
    jobs = Jobs.objects.filter(status="Open")
    vendors = Vendors.objects.filter(category__category="Wallcovering Supplier")
    vendors1 = Vendors.objects.filter(category__category="Wallcovering Supplier").values()
    if job_number == "ALL":
        selectedjob = 0
        if id == "ALL":
            selectedwc = 0
            selectedpricing = 0
            selectedvendor = 0
            wallcovering = Wallcovering.objects.filter(job_number__status="Open")
            pricing = WallcoveringPricing.objects.filter(wallcovering__job_number__status="Open")
            wallcovering1 = Wallcovering.objects.values('id','job_number__job_number','code','vendor__id','vendor__company_name','pattern','estimated_quantity', 'estimated_unit').filter(job_number__status="Open")
            pricing1 = WallcoveringPricing.objects.values('wallcovering__id','quote_date','min_yards','price','unit','id').filter(wallcovering__job_number__status="Open")
    else:
        selectedjob = Jobs.objects.get(job_number=job_number)
        wallcovering = Wallcovering.objects.filter(job_number__job_number=job_number)
        pricing = WallcoveringPricing.objects.filter(wallcovering__job_number__job_number=job_number)
        wallcovering1 = Wallcovering.objects.values('id','job_number__job_number','code','vendor__id','vendor__company_name','pattern','estimated_quantity', 'estimated_unit').filter(job_number__job_number=job_number)
        pricing1 = WallcoveringPricing.objects.values('wallcovering__id','quote_date','min_yards','price','unit','id').filter(wallcovering__job_number__job_number=job_number)
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
    return render(request, "wallcovering_order_new.html", {'vendors':vendors,'vendors_json':vendors_json,'wallcovering_json':wallcovering_json,'pricing_json':pricing_json, 'selectedwc':selectedwc, 'selectedpricing':selectedpricing, 'selectedjob':selectedjob, 'jobs': jobs,'wallcovering': wallcovering, 'pricing': pricing, 'selectedvendor': selectedvendor})


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
    all_orders = OrderItemsFilter(request.GET, queryset =OrderItems.objects.filter(order__job_number__status="Open"))
    table2 = CombinedOrdersTable(all_orders.qs)
    has_filter = any(field in request.GET for field in set(all_orders.get_fields()))
    packages = []
    for y in Packages.objects.filter(delivery__order__job_number__status = "Open" ):
        sentquantity = 0
        match = False
        for x in OutgoingItem.objects.filter(package = y):
            sentquantity = sentquantity + x.quantity_sent
        if sentquantity == y.quantity_received:
            match = True
        if match == False:
            packages.append(y)
    #packages = Packages.objects.filter(is_all_delivered_to_job=False) #items in warehouse not delivered to job yet
    return render(request, "wallcovering_home.html", {'has_filter':has_filter,'all_orders':all_orders,'wc_table':wc_table, 'wc_not_ordereds': wc_not_ordereds,'wc_ordereds': wc_ordereds, 'received_deliveries':received_deliveries ,'jobsite_deliveries':jobsite_deliveries ,'packages':packages, 'table2':table2})


def wallcovering_pattern_new(request):
    jobs = Jobs.objects.all()
    vendors = Vendors.objects.filter(category__category="Wallcovering Supplier")
    selectedpattern = 'NEW'
    table = []
    orderstable = []
    receivedtable = []
    jobdeliveriestable = []
    packagestable = []
    if request.method == 'POST':
        selectedpattern = Wallcovering.objects.create(
            job_number=Jobs.objects.get(job_number=request.POST['job_select']), code=request.POST['code'],
            vendor=Vendors.objects.get(id=request.POST['vendor']), pattern=request.POST['pattern'])
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
        table = WallcoveringPriceTable(WallcoveringPricing.objects.filter(wallcovering__id=selectedpattern.id))
        orderstable="SKIP"
    return render(request, "wallcovering_pattern.html", {'jobdeliveriestable':jobdeliveriestable,'packagestable':packagestable, 'receivedtable':receivedtable,'orderstable':orderstable,'selectedpattern': selectedpattern, 'jobs': jobs, 'vendors': vendors, 'table': table })
def wallcovering_pattern(request, id):
    jobs = Jobs.objects.all()
    vendors = Vendors.objects.filter(category__category="Wallcovering Supplier")
    selectedpattern = Wallcovering.objects.get(id=id)
    table = WallcoveringPriceTable(WallcoveringPricing.objects.filter(wallcovering__id = id))
    orderstable= OrderItemsTable(OrderItems.objects.filter(wallcovering__id=id))
    receivedtable= ReceivedTable(ReceivedItems.objects.filter(order_item__wallcovering__id=id))
    packages_table=[]
    jobdeliveries=[]
    for x in Orders.objects.filter(orderitems2__wallcovering__id=id).distinct():
        print(x.id)
        for y in Packages.objects.filter(delivery__order=x):
            packages_table.append(y)
            for z in OutgoingItem.objects.filter(package = y):
                    jobdeliveries.append(z)
    packagestable= PackagesTable(packages_table)
    jobdeliveriestable= JobDeliveriesTable(jobdeliveries)
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

    return render(request, "wallcovering_pattern.html", {'jobdeliveriestable':jobdeliveriestable,'packagestable':packagestable, 'receivedtable':receivedtable,'orderstable':orderstable,'selectedpattern': selectedpattern, 'jobs': jobs, 'vendors': vendors, 'table': table })

def wallcovering_status(request, table_type, id):
    if table_type == 'Outgoing':

        table = OutgoingWallcoveringTable(OutgoingItem.objects.filter(id=id))
        return render(request, "wallcovering_status.html", {'table': table})