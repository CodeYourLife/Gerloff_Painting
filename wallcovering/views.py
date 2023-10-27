from equipment.models import Vendors
from wallcovering.models import Packages, Wallcovering, WallcoveringPricing
from jobs.models import Jobs
from django.shortcuts import render, redirect
import json
from django.core.serializers.json import DjangoJSONEncoder
from datetime import date
from .tables import *
import json
from django.core.serializers.json import DjangoJSONEncoder
from .filters import OrderItemsFilter
from django.contrib.auth.decorators import login_required

@login_required(login_url='/accounts/login')
def wallcovering_send_all(request):
    table = OutgoingWallcoveringTable(OutgoingItem.objects.filter(outgoing_event__job_number__is_closed=False))
    return render(request, "wallcovering_send_all.html", {'table':table})

@login_required(login_url='/accounts/login')
def wallcovering_receive_all(request):
    table = ReceivedTable(ReceivedItems.objects.filter(wallcovering_delivery__order__job_number__is_closed=False))
    return render(request, "wallcovering_receive_all.html", {'table':table})

@login_required(login_url='/accounts/login')
def wallcovering_order_all(request):
    table = OrdersTable(Orders.objects.filter(job_number__status = "Open"))
    return render(request, "wallcovering_order_all.html", {'table':table})

@login_required(login_url='/accounts/login')
def wallcovering_send(request, jobnumber):
    if request.method == 'POST':
        if 'select_job' in request.POST:
            return redirect('wallcovering_send', jobnumber= request.POST['select_job'])
        else:
            delivery = OutgoingWallcovering.objects.create(job_number=Jobs.objects.get(job_number=jobnumber),delivered_by=request.POST['delivered_by'],notes =request.POST['delivery_note'],date =date.today())
            delivery = OutgoingWallcovering.objects.latest('id')
            for y in range(1, int(request.POST["number_packages"]) + 1):
                item=OutgoingItem.objects.create(outgoing_event=delivery, package=Packages.objects.get(id=request.POST['select_package' + str(y)]),description = request.POST['description'+ str(y)], quantity_sent=request.POST['quantity_sent'+ str(y)])
            return redirect('job_page', jobnumber=jobnumber)
    if jobnumber == 'ALL':
        already_picked = 'ALL'
        jobs =[]
        for x in Jobs.objects.filter(is_closed=False,orders__isnull=False).distinct():
            b=0
            for y in Orders.objects.filter(job_number=x.job_number):
                if int(y.packages_received()) > int(y.packages_sent()):
                    b=1
            if b != 0:
                jobs.append(x)
        packages = []
        for y in Packages.objects.filter(delivery__order__job_number__is_closed=False):
            if int(y.total_sent())<int(y.quantity_received):
                thisdict = {"id": y.id,"date":y.delivery.date, "type": y.type,"contents":y.contents,"quantity_received":y.quantity_received,"notes": y.notes,"total_sent":int(y.total_sent()),"available": int(y.quantity_received)-int(y.total_sent())}
                packages.append(thisdict)
    else:
        already_picked = jobnumber
        jobs =Jobs.objects.filter(job_number=jobnumber)
        packages = []
        for y in Packages.objects.filter(delivery__order__job_number__job_number=jobnumber):
            if int(y.total_sent())<int(y.quantity_received):
                thisdict = {"id": y.id,"date":y.delivery.date, "type": y.type,"contents":y.contents,"quantity_received":y.quantity_received,"notes": y.notes,"total_sent":int(y.total_sent()),"available": int(y.quantity_received)-int(y.total_sent())}
                packages.append(thisdict)
    packages_json = json.dumps(list(packages), cls=DjangoJSONEncoder)
    return render(request, "wallcovering_send.html", {'packages':packages, 'packages_json':packages_json, 'jobs':jobs, 'already_picked':already_picked})

@login_required(login_url='/accounts/login')
def wallcovering_receive(request,orderid):
    if request.method == 'POST':
        delivery = WallcoveringDelivery.objects.create(order=Orders.objects.get(id=orderid),date=date.today(),notes = request.POST['delivery_note'])
        delivery = WallcoveringDelivery.objects.latest('id')
        for y in range(1,int(request.POST["number_items"])+1):
            item = ReceivedItems.objects.create(wallcovering_delivery=delivery, order_item = OrderItems.objects.get(id =request.POST['select_item' + str(y)]),quantity =request.POST['quantity' + str(y)])
        for y in range(1, int(request.POST["number_packages"]) + 1):
            package = Packages.objects.create(delivery=delivery, type= request.POST['package_type' + str(y)], contents=request.POST['package_contents' + str(y)],quantity_received=request.POST['package_quantity_received' + str(y)],notes=request.POST['package_notes' + str(y)])
        return redirect('wallcovering_order', id=orderid)
    if orderid == 'ALL':
        already_picked = 'ALL'
        open_orders = []
        open_order_items = []
        for y in Orders.objects.filter(job_number__is_closed=False):
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

@login_required(login_url='/accounts/login')
def wallcovering_order(request,id):
    order = Orders.objects.get(id=id)
    orderstable = OrdersTable(Orders.objects.filter(id=id))
    orderitemstable=OrderItemsTable(OrderItems.objects.filter(order=order))
    packagestable = PackagesTable(Packages.objects.filter(delivery__order=order))
    receiptstable = ReceivedTable(ReceivedItems.objects.filter(order_item__order=order))
    jobdeliveriestable = JobDeliveriesTable(OutgoingItem.objects.filter(package__delivery__order=order))

    return render(request, "wallcovering_order.html", {'orderstable': orderstable, 'orderitemstable':orderitemstable, 'packagestable':packagestable,'receiptstable':receiptstable,'jobdeliveriestable':jobdeliveriestable,'currentorder':order})

@login_required(login_url='/accounts/login')
def post_wallcovering_order(request):
    new_order = Orders(job_number=Jobs.objects.get(job_number=request.POST["select_job"]),description=request.POST["description"],vendor=Vendors.objects.get(id=request.POST["select_vendor"]),date_ordered=date.today())
    new_order.save()
    new_order = Orders.objects.latest('id')
    if 'po_number' in request.POST:
        new_order.po_number = request.POST["po_number"]
        new_order.save()
    for y in range (0,int(request.POST["number_rows"])+1):
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

@login_required(login_url='/accounts/login')
def wallcovering_order_new(request, id, job_number):
    jobs = Jobs.objects.filter(is_closed=False)
    vendors = Vendors.objects.filter(category__category="Wallcovering Supplier")
    vendors1 = Vendors.objects.filter(category__category="Wallcovering Supplier").values()
    if job_number == "ALL":
        selectedjob = 0
        if id == "ALL":
            selectedwc = 0
            selectedpricing = 0
            selectedvendor = 0
            wallcovering = Wallcovering.objects.filter(job_number__is_closed=False)
            pricing = WallcoveringPricing.objects.filter(wallcovering__job_number__is_closed=False)
            wallcovering1 = Wallcovering.objects.values('id','job_number__job_number','code','vendor__id','vendor__company_name','pattern','estimated_quantity', 'estimated_unit').filter(job_number__is_closed=False)
            pricing1 = WallcoveringPricing.objects.values('wallcovering__id','quote_date','min_yards','price','unit','id').filter(wallcovering__job_number__is_closed=False)
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


@login_required(login_url='/accounts/login')
def wallcovering_home(request):
    wc_table = Wallcovering.objects.filter(job_number__is_closed=False)
    # wc_table = []
    # xjob_name = "NA"
    # xcode = "NA"
    # xordered = 0
    # xdateordered = "NA"
    # xreceivedall = "NA"
    # xreceived = 0
    # xdatereceived = ""
    # xtojob = 0
    # for x in Wallcovering.objects.filter(job_number__status = "Open").order_by('-job_number'):
    #     xjob_name = "NA"
    #     xcode = "NA"
    #     xordered = 0
    #     xdateordered = "NA"
    #     xreceivedall = "NA"
    #     xreceived = 0
    #     xdatereceived = ""
    #     xtojob = 0
    #
    #     xjob_name = x.job_number.job_name
    #     xcode = x.code
    #     #orderinformation ->
    #
    #     for orderitem in OrderItems.objects.filter(wallcovering=x):
    #         xordered = xordered + orderitem.quantity
    #         xdateordered = orderitem.order.date_ordered
    #         if orderitem.is_satisfied == False:
    #             xreceivedall = "NO"
    #         else:
    #             if xreceivedall != "NO":
    #                 xreceivedall = "YES"
    #
    #     #received information
    #     match = False
    #     for order in Orders.objects.filter(job_number = x.job_number):
    #         for orderitem in OrderItems.objects.filter(order = order):
    #             if orderitem.wallcovering == x:
    #                     match = True
    #         if match == True:
    #             for receivedpackage in Packages.objects.filter(delivery__order = order):
    #                 xreceived = xreceived + receivedpackage.quantity_received
    #                 xdatereceived = receivedpackage.delivery.date
    #                 for sentpackage in OutgoingItem.objects.filter(package = receivedpackage):
    #                     xtojob = xtojob + sentpackage.quantity_sent
    #
    #
    #     wc_table.append(
    #         {
    #         'job_name': xjob_name,
    #         'job_number': x.job_number.job_number,
    #         'code':xcode,
    #         'qty_ordered' : xordered,
    #         'date_ordered' : xdateordered,
    #         'is_received_all' : xreceivedall,
    #         'packages_received' : xreceived,
    #         'date_received' : xdatereceived,
    #         'packages_to_job' : xtojob,
    #         'id' : x.id,
    #         })
    wc_not_ordereds=Wallcovering.objects.exclude(orderitems1__item_description__isnull=False) #wallcovering not ordered yet
    wc_ordereds = OrderItems.objects.filter(is_satisfied=False) #orders not received yet
    received_deliveries = WallcoveringDelivery.objects.all()
    jobsite_deliveries =  OutgoingItem.objects.all()
    all_orders = OrderItemsFilter(request.GET, queryset =OrderItems.objects.filter(order__job_number__is_closed=False).distinct())
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

@login_required(login_url='/accounts/login')
def wallcovering_pattern_all(request):
    table = WallcoveringPatternsTable(Wallcovering.objects.filter(job_number__status = "Open"))
    return render(request, "wallcovering_pattern_all.html", {'table':table})

@login_required(login_url='/accounts/login')
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

@login_required(login_url='/accounts/login')
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

@login_required(login_url='/accounts/login')
def wallcovering_status(request, table_type, id):
    if table_type == 'Outgoing':
        table = OutgoingWallcoveringTable(OutgoingItem.objects.filter(id=id))
        return render(request, "wallcovering_status.html", {'table': table})