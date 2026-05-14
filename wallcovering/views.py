from decimal import Decimal, InvalidOperation
from datetime import date
from django.apps import apps
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import render, get_object_or_404, redirect
from employees.models import Employees
from equipment.models import Vendors, VendorCategory
from .models import (
    Wallcovering,
    OrderItems,
    WallcoveringDelivery,
    ReceivedItems,
    Packages,
    OutgoingWallcovering,
    OutgoingItem,
    WallcoveringNotes,
    WallcoveringPricing
)
from submittals.models import SubmittalItems, SubmittalApprovals



def wallcovering_home(request):
    wallcoverings = Wallcovering.objects.select_related(
        "job_number",
        "vendor"
    ).filter(job_number__is_closed=False).order_by(
        "job_number__job_name",
        "code"
    )

    return render(request, "wallcovering_home.html", {
        "wallcoverings": wallcoverings,
    })


def wallcovering_detail(request, wallcovering_id):
    wallcovering = get_object_or_404(Wallcovering, id=wallcovering_id)

    pricing = WallcoveringPricing.objects.filter(
        wallcovering=wallcovering
    ).order_by("-quote_date", "-id")

    # Orders tied to this wallcovering
    order_items = OrderItems.objects.filter(
        wallcovering=wallcovering
    ).select_related('order').order_by('-order__id')

    order_groups = []

    related_order_ids = OrderItems.objects.filter(
        link_to_wallcovering=wallcovering
    ).values_list(
        "order_id", flat=True
    ).distinct()

    for order_id in related_order_ids:
        all_items = OrderItems.objects.filter(
            order_id=order_id,
            link_to_wallcovering=wallcovering
        ).select_related(
            "order",
            "wallcovering"
        ).order_by("id")

        first_item = all_items.first()

        if not first_item:
            continue

        wc_item = all_items.filter(
            wallcovering=wallcovering
        ).first()

        order_groups.append({
            "order": first_item.order,
            "wallcovering_item": wc_item,
            "all_items": all_items,
        })

    other_order_items_raw = OrderItems.objects.filter(
        link_to_wallcovering=wallcovering,
        wallcovering__isnull=True
    ).order_by("item_description")

    other_order_items = {}

    for item in other_order_items_raw:
        key = item.item_description or "No Description"

        if key not in other_order_items:
            other_order_items[key] = {
                "description": key,
                "quantity": Decimal("0.00"),
                "received": Decimal("0.00"),
                "unit": item.unit or "",
            }

        other_order_items[key]["quantity"] += item.quantity or Decimal("0.00")
        other_order_items[key]["received"] += item.quantity_received() or Decimal("0.00")

    for item in other_order_items.values():
        item["remaining"] = item["quantity"] - item["received"]
        item["packages_received"] = 0
        item["packages_sent"] = 0
        item["sent_percentage"] = 0
        item["status"] = "Not Ordered"

    for item in other_order_items.values():

        matching_packages = Packages.objects.filter(
            orderitem__link_to_wallcovering=wallcovering,
            orderitem__wallcovering__isnull=True,
            orderitem__item_description=item["description"]
        ).distinct()

        packages_received = 0
        packages_sent = 0

        for package in matching_packages:
            packages_received += package.quantity_received or 0
            packages_sent += package.total_sent() or 0

        item["packages_received"] = packages_received
        item["packages_sent"] = packages_sent

        if item["received"] <= 0:
            item["status"] = "Ordered"

        elif item["received"] < item["quantity"]:
            item["status"] = "Partially Received"

        else:
            item["status"] = "Received"

        if packages_received > 0:

            item["sent_percentage"] = int(
                round((packages_sent / packages_received) * 100)
            )

            if packages_sent >= packages_received:
                item["status"] = "Sent to Job"

            elif packages_sent > 0:
                item["status"] = "Partial Sent to Job"


    # Deliveries tied through orders
    deliveries = WallcoveringDelivery.objects.filter(
        order__orderitems2__link_to_wallcovering=wallcovering
    ).distinct().order_by('-date')

    # Received items
    received_items = ReceivedItems.objects.filter(
        order_item__link_to_wallcovering=wallcovering
    ).select_related(
        'order_item',
        'wallcovering_delivery',
        'wallcovering_delivery__order'
    ).order_by('-wallcovering_delivery__date', 'id')

    for received_item in received_items:
        received_item.related_packages = Packages.objects.filter(
            delivery=received_item.wallcovering_delivery,
            orderitem=received_item.order_item
        ).order_by('id')

    receipt_groups = []

    deliveries_for_receiving = WallcoveringDelivery.objects.filter(
        foreign_receiveditems1__order_item__link_to_wallcovering=wallcovering
    ).distinct().order_by("-date", "-id")

    for delivery in deliveries_for_receiving:
        delivery_received_items = ReceivedItems.objects.filter(
            wallcovering_delivery=delivery,
            order_item__link_to_wallcovering=wallcovering
        ).select_related(
            "order_item"
        ).order_by("id")

        receipt_items = []

        for received_item in delivery_received_items:
            related_packages = Packages.objects.filter(
                delivery=delivery,
                orderitem=received_item.order_item
            ).order_by("id")

            receipt_items.append({
                "received_item": received_item,
                "packages": related_packages,
            })

        receipt_groups.append({
            "delivery": delivery,
            "items": receipt_items,
        })

    # Packages
    packages = Packages.objects.filter(
        delivery__order__orderitems2__link_to_wallcovering=wallcovering
    ).select_related('delivery').distinct().order_by('-delivery__date')

    # Outgoing (sent to job)
    outgoing_events = OutgoingWallcovering.objects.filter(
        outgoingitem__package__orderitem__link_to_wallcovering=wallcovering
    ).distinct().order_by('-date')

    outgoing_items = OutgoingItem.objects.filter(
        package__orderitem__link_to_wallcovering=wallcovering
    ).select_related(
        'package',
        'package__orderitem',
        'outgoing_event'
    ).distinct().order_by(
        '-outgoing_event__date',
        'package__orderitem__item_description',
        'id'
    )

    # Notes (all types)
    notes = WallcoveringNotes.objects.filter(
        pattern=wallcovering
    ).select_related('user').order_by('-date', '-id')

    sent_to_job_groups = []

    outgoing_events = OutgoingWallcovering.objects.filter(
        outgoingitem__package__orderitem__link_to_wallcovering=wallcovering
    ).distinct().order_by("-date", "-id")

    for event in outgoing_events:
        sent_items = OutgoingItem.objects.filter(
            outgoing_event=event,
            package__orderitem__link_to_wallcovering=wallcovering
        ).select_related(
            "package",
            "package__orderitem"
        ).order_by(
            "package__orderitem__item_description",
            "package__contents",
            "id"
        )

        combined_items = {}

        for sent_item in sent_items:
            orderitem = sent_item.package.orderitem

            description = orderitem.item_description or "No Description"
            contents = sent_item.package.contents or ""

            key = (
                description.strip().lower(),
                contents.strip().lower(),
            )

            if key not in combined_items:
                combined_items[key] = {
                    "description": description,
                    "contents": contents,
                    "type": sent_item.package.type,
                    "quantity_sent": 0,
                    "notes": [],
                }

            combined_items[key]["quantity_sent"] += sent_item.quantity_sent or 0

            note = (sent_item.package.notes or "").strip()
            if note and note not in combined_items[key]["notes"]:
                combined_items[key]["notes"].append(note)

        sent_to_job_groups.append({
            "event": event,
            "items": combined_items.values(),
        })

    submittal_items = SubmittalItems.objects.filter(
        wallcovering_id=wallcovering,
        is_no_longer_used=False
    ).order_by("id")

    submittal_rows = []

    for item in submittal_items:
        approvals = SubmittalApprovals.objects.filter(
            submittalitem=item,
            submittal__isnull=False
        ).select_related("submittal").order_by("-id")

        approval = approvals.first()

        if not approval:
            status = "Not Sent"
        elif approval.is_approved is True:
            status = "Approved"
        elif approval.is_approved is False:
            status = "Rejected"
        else:
            status = "Sent"

        submittal_rows.append({
            "item": item,
            "approval": approval,
            "status": status,
        })

    context = {
        'wallcovering': wallcovering,
        'order_items': order_items,
        'deliveries': deliveries,
        'received_items': received_items,
        'packages': packages,
        'outgoing_events': outgoing_events,
        'outgoing_items': outgoing_items,
        'notes': notes,
        'pricing': pricing,
        'today': date.today(),
        'order_groups': order_groups,
        'other_order_items': other_order_items.values(),
        "receipt_groups": receipt_groups,
        "sent_to_job_groups": sent_to_job_groups,
        "submittal_rows": submittal_rows,
    }

    return render(request, 'wallcovering_detail.html', context)


def wallcovering_new(request):
    Jobs = apps.get_model('jobs', 'Jobs')

    jobs = Jobs.objects.filter(is_closed=False).order_by('job_name')
    vendors = Vendors.objects.filter(category__category="Wallcovering Supplier").order_by('company_name')
    if request.method == "POST":
        job_number_value = request.POST.get("job_number")
        vendor_input = (request.POST.get("vendor") or "").strip()

        selected_job = Jobs.objects.get(job_number=job_number_value)

        # Get correct vendor category
        vendor_category = VendorCategory.objects.get(
            category="Wallcovering Supplier"
        )

        vendor_obj = None

        if vendor_input:
            # 🔥 ONLY search within Wallcovering Supplier category
            vendor_obj = Vendors.objects.filter(
                company_name__iexact=vendor_input,
                category=vendor_category
            ).first()

            # If not found → create it in correct category
            if not vendor_obj:
                vendor_obj = Vendors.objects.create(
                    company_name=vendor_input,
                    category=vendor_category
                )

        wallcovering = Wallcovering.objects.create(
            job_number=selected_job,
            vendor=vendor_obj,
            code=request.POST.get("code"),
            pattern=request.POST.get("pattern"),
            estimated_quantity=request.POST.get("estimated_quantity") or 0,
            estimated_unit=request.POST.get("estimated_unit"),
            roll_width=request.POST.get("roll_width"),
            roll_length=request.POST.get("roll_length"),
            vertical_repeat=request.POST.get("vertical_repeat"),
            cut_charge=request.POST.get("cut_charge"),
            notes=request.POST.get("notes"),
            is_owner_furnished=bool(request.POST.get("is_owner_furnished")),
            is_random_reverse=bool(request.POST.get("is_random_reverse")),
            is_repeat=bool(request.POST.get("is_repeat")),
            increment_requirement=request.POST.get("increment_requirement"),
        )

        return redirect("wallcovering_detail", wallcovering_id=wallcovering.id)

    return render(request, 'wallcovering_new.html', {
        'jobs': jobs,'vendors': vendors
    })


def wallcovering_edit(request, wallcovering_id):
    Jobs = apps.get_model('jobs', 'Jobs')

    wallcovering = get_object_or_404(Wallcovering, id=wallcovering_id)

    jobs = Jobs.objects.filter(is_closed=False).order_by('job_name')

    vendors = Vendors.objects.filter(
        category__category="Wallcovering Supplier"
    ).order_by('company_name')

    if request.method == "POST":
        job_number_value = request.POST.get("job_number")
        vendor_input = (request.POST.get("vendor") or "").strip()

        selected_job = Jobs.objects.get(job_number=job_number_value)

        vendor_category = VendorCategory.objects.get(
            category="Wallcovering Supplier"
        )

        vendor_obj = Vendors.objects.filter(
            company_name__iexact=vendor_input,
            category=vendor_category
        ).first()

        if not vendor_obj:
            vendor_obj = Vendors.objects.create(
                company_name=vendor_input,
                category=vendor_category
            )

        wallcovering.job_number = selected_job
        wallcovering.vendor = vendor_obj
        wallcovering.code = request.POST.get("code")
        wallcovering.pattern = request.POST.get("pattern")
        wallcovering.estimated_quantity = request.POST.get("estimated_quantity") or 0
        wallcovering.estimated_unit = request.POST.get("estimated_unit")
        wallcovering.roll_width = request.POST.get("roll_width")
        wallcovering.roll_length = request.POST.get("roll_length")
        wallcovering.vertical_repeat = request.POST.get("vertical_repeat")
        wallcovering.cut_charge = request.POST.get("cut_charge")
        wallcovering.notes = request.POST.get("notes")
        wallcovering.is_owner_furnished = bool(request.POST.get("is_owner_furnished"))
        wallcovering.is_random_reverse = bool(request.POST.get("is_random_reverse"))
        wallcovering.is_repeat = bool(request.POST.get("is_repeat"))
        wallcovering.increment_requirement = request.POST.get("increment_requirement")
        wallcovering.save()

        return redirect("wallcovering_detail", wallcovering_id=wallcovering.id)

    return render(request, 'wallcovering_edit.html', {
        'wallcovering': wallcovering,
        'jobs': jobs,
        'vendors': vendors,
    })


def get_next_po_number():
    PurchaseOrderNumber = apps.get_model('subcontractors', 'PurchaseOrderNumber')

    with transaction.atomic():
        po_counter = PurchaseOrderNumber.objects.select_for_update().first()

        if not po_counter:
            po_counter = PurchaseOrderNumber.objects.create(next_po_number=1)

        po_number = po_counter.next_po_number
        po_counter.next_po_number = po_number + 1
        po_counter.save()

    return po_number


def clean_decimal(value):
    if value in [None, ""]:
        return Decimal("0.00")

    value = str(value).replace("$", "").replace(",", "").strip()

    try:
        return Decimal(value).quantize(Decimal("0.01"))
    except InvalidOperation:
        return Decimal("0.00")


def wallcovering_add_order(request, wallcovering_id):
    Orders = apps.get_model('jobs', 'Orders')

    wallcovering = get_object_or_404(Wallcovering, id=wallcovering_id)

    pricing = WallcoveringPricing.objects.filter(
        wallcovering=wallcovering
    ).order_by("-quote_date", "-id")

    default_description = f"{wallcovering.code or ''} {wallcovering.pattern or ''}".strip()

    if request.method == "POST":
        po_number_int = get_next_po_number()
        po_number = f"TR{po_number_int}"

        default_description = f"{wallcovering.code or ''} {wallcovering.pattern or ''}".strip()

        order = Orders.objects.create(
            po_number=po_number,
            job_number=wallcovering.job_number,
            vendor=wallcovering.vendor,
            description=default_description,
            date_ordered=request.POST.get("date_ordered") or date.today(),
            notes=request.POST.get("order_notes"),
        )

        # MAIN WALLCOVERING ITEM - this is the ONLY item linked to Wallcovering
        main_quantity = clean_decimal(request.POST.get("main_quantity"))
        main_unit = (request.POST.get("main_unit") or "").strip()
        main_price = clean_decimal(request.POST.get("main_price"))
        if main_quantity > Decimal("0.00") and main_unit and main_price is not None:
            OrderItems.objects.create(
                order=order,
                wallcovering=wallcovering,
                quantity=clean_decimal(request.POST.get("main_quantity")),
                unit=request.POST.get("main_unit"),
                price=clean_decimal(request.POST.get("main_price")),
                item_description=default_description,
                item_notes=request.POST.get("main_item_notes"),
                link_to_wallcovering = wallcovering,
            )

        # EXTRA ITEMS - paste, adhesive, sundries, etc.
        descriptions = request.POST.getlist("extra_description[]")
        quantities = request.POST.getlist("extra_quantity[]")
        units = request.POST.getlist("extra_unit[]")
        prices = request.POST.getlist("extra_price[]")
        notes = request.POST.getlist("extra_notes[]")

        for i in range(len(descriptions)):
            description = (descriptions[i] or "").strip()
            quantity = clean_decimal(quantities[i] if i < len(quantities) else "")
            unit = (units[i] if i < len(units) else "").strip()
            price = clean_decimal(prices[i] if i < len(prices) else "")
            item_note = notes[i] if i < len(notes) else ""

            if description == "" and quantity == Decimal("0.00"):
                continue

            OrderItems.objects.create(
                order=order,
                wallcovering=None,  # important
                quantity=quantity,
                unit=unit,
                price=price,
                item_description=description,
                item_notes=item_note,
                link_to_wallcovering=wallcovering,
            )

        return redirect("wallcovering_detail", wallcovering_id=wallcovering.id)

    return render(request, "wallcovering_add_order.html", {
        "wallcovering": wallcovering,
        "today": date.today(),
        "pricing": pricing,
        "default_description": default_description,
    })




def wallcovering_add_pricing(request, wallcovering_id):
    wallcovering = get_object_or_404(Wallcovering, id=wallcovering_id)

    if request.method == "POST":
        WallcoveringPricing.objects.create(
            wallcovering=wallcovering,
            quote_date=request.POST.get("quote_date") or date.today(),
            min_yards=request.POST.get("min_yards") or None,
            price=clean_decimal(request.POST.get("price")),
            unit=request.POST.get("unit"),
            note=request.POST.get("note"),
        )

    return redirect("wallcovering_detail", wallcovering_id=wallcovering.id)

def wallcovering_receive(request, wallcovering_id=None):
    wallcovering = None

    if wallcovering_id:
        wallcovering = get_object_or_404(Wallcovering, id=wallcovering_id)

    if wallcovering:
        related_orders = OrderItems.objects.filter(
            wallcovering=wallcovering
        ).values_list(
            "order_id", flat=True
        ).distinct()

        open_order_items = OrderItems.objects.filter(
            order_id__in=related_orders,
            is_satisfied=False
        ).select_related(
            'order',
            'wallcovering',
            'order__job_number'
        ).order_by(
            'order__po_number',
            'id'
        )
    else:
        open_order_items = OrderItems.objects.filter(
            is_satisfied=False,
            order__orderitems2__wallcovering__isnull=False
        ).select_related(
            'order',
            'wallcovering',
            'order__job_number'
        ).distinct().order_by(
            'order__job_number__job_name',
            'order__po_number',
            'id'
        )

    selected_item = None

    if wallcovering:
        selected_item = open_order_items.filter(
            wallcovering=wallcovering
        ).first()

    if request.method == "POST":
        receipt_date = request.POST.get("date") or date.today()
        receipt_notes = request.POST.get("notes")

        order_item_ids = request.POST.getlist("order_item[]")
        quantities = request.POST.getlist("quantity[]")

        package_orderitem_ids = request.POST.getlist("package_orderitem[]")
        package_types = request.POST.getlist("package_type[]")
        package_contents = request.POST.getlist("package_contents[]")
        package_quantities = request.POST.getlist("package_quantity[]")
        package_notes = request.POST.getlist("package_notes[]")

        valid_received_rows = []

        for i in range(len(order_item_ids)):
            order_item_id = order_item_ids[i]
            quantity = clean_decimal(quantities[i] if i < len(quantities) else "")

            if not order_item_id or quantity <= 0:
                continue

            order_item = get_object_or_404(OrderItems, id=order_item_id)

            valid_received_rows.append({
                "order_item": order_item,
                "quantity": quantity,
            })

        if not valid_received_rows:
            messages.error(request, "You must receive at least one item.")
            return redirect(request.path)

        first_order = valid_received_rows[0]["order_item"].order

        for row in valid_received_rows:
            if row["order_item"].order != first_order:
                messages.error(request, "All received items must be from the same PO / order.")
                return redirect(request.path)

        for row in valid_received_rows:
            order_item = row["order_item"]

            has_package = False

            for i in range(len(package_types)):
                package_orderitem_id = package_orderitem_ids[i] if i < len(package_orderitem_ids) else None
                quantity_received = package_quantities[i] if i < len(package_quantities) else ""

                if not package_orderitem_id:
                    continue

                try:
                    package_qty = int(quantity_received or 0)
                except:
                    package_qty = 0

                if (
                        str(package_orderitem_id) == str(order_item.id)
                        and package_qty > 0
                ):
                    has_package = True
                    break

            if not has_package:
                messages.error(
                    request,
                    f"You must enter at least one package for {order_item.item_description}."
                )
                return redirect(request.path)

        delivery = WallcoveringDelivery.objects.create(
            order=first_order,
            date=receipt_date,
            notes=receipt_notes,
        )

        for row in valid_received_rows:
            order_item = row["order_item"]
            quantity = row["quantity"]

            ReceivedItems.objects.create(
                wallcovering_delivery=delivery,
                order_item=order_item,
                quantity=quantity,
            )

            if order_item.quantity_received() >= (order_item.quantity or Decimal("0.00")):
                order_item.is_satisfied = True
                order_item.save()

        for i in range(len(package_types)):
            package_orderitem_id = package_orderitem_ids[i] if i < len(package_orderitem_ids) else None
            package_type = (package_types[i] if i < len(package_types) else "").strip()
            contents = (package_contents[i] if i < len(package_contents) else "").strip()
            quantity_received = package_quantities[i] if i < len(package_quantities) else ""
            notes = package_notes[i] if i < len(package_notes) else ""

            if not package_orderitem_id:
                continue

            if not package_type and not contents and not quantity_received:
                continue

            package_orderitem = get_object_or_404(OrderItems, id=package_orderitem_id)

            Packages.objects.create(
                delivery=delivery,
                orderitem=package_orderitem,
                type=package_type,
                contents=contents,
                quantity_received=int(quantity_received or 0),
                notes=notes,
            )

        if wallcovering:
            return redirect("wallcovering_detail", wallcovering_id=wallcovering.id)

        messages.success(request, "Wallcovering receipt saved.")
        return redirect("wallcovering_receive")

    return render(request, "wallcovering_receive.html", {
        "wallcovering": wallcovering,
        "open_order_items": open_order_items,
        "selected_item": selected_item,
        "today": date.today(),
    })



def wallcovering_send_to_job(request, wallcovering_id):
    wallcovering = get_object_or_404(Wallcovering, id=wallcovering_id)

    available_packages = []

    packages = Packages.objects.filter(
        orderitem__link_to_wallcovering=wallcovering
    ).select_related(
        "delivery",
        "delivery__order",
        "orderitem"
    ).order_by(
        "delivery__date",
        "id"
    )

    for package in packages:
        sent = package.total_sent()
        received = package.quantity_received or 0
        remaining = received - sent

        if remaining > 0:
            package.sent_to_date = sent
            package.remaining_to_send = remaining
            available_packages.append(package)

    if request.method == "POST":
        send_date = request.POST.get("date") or date.today()
        delivered_by = request.POST.get("delivered_by")
        notes = request.POST.get("notes")

        package_ids = request.POST.getlist("package[]")
        quantities = request.POST.getlist("quantity_sent[]")


        valid_rows = []

        for i in range(len(package_ids)):
            package_id = package_ids[i]
            quantity_raw = quantities[i] if i < len(quantities) else ""


            if not package_id or not quantity_raw:
                continue

            try:
                quantity_sent = int(quantity_raw)
            except ValueError:
                quantity_sent = 0

            if quantity_sent <= 0:
                continue

            package = get_object_or_404(Packages, id=package_id)

            remaining = (package.quantity_received or 0) - package.total_sent()

            if quantity_sent > remaining:
                messages.error(
                    request,
                    f"You cannot send {quantity_sent} packages of {package.contents}. Only {remaining} remain."
                )
                return redirect(request.path)

            valid_rows.append({
                "package": package,
                "quantity_sent": quantity_sent,

            })

        if not valid_rows:
            messages.error(request, "You must select at least one package to send.")
            return redirect(request.path)

        outgoing_event = OutgoingWallcovering.objects.create(
            job_number=wallcovering.job_number,
            delivered_by=delivered_by,
            notes=notes,
            date=send_date,
        )

        for row in valid_rows:
            OutgoingItem.objects.create(
                outgoing_event=outgoing_event,
                package=row["package"],
                quantity_sent=row["quantity_sent"],
            )

        return redirect("wallcovering_detail", wallcovering_id=wallcovering.id)

    return render(request, "wallcovering_send_to_job.html", {
        "wallcovering": wallcovering,
        "available_packages": available_packages,
        "today": date.today(),
    })


def wallcovering_add_note(request, wallcovering_id):
    wallcovering = get_object_or_404(Wallcovering, id=wallcovering_id)

    if request.method == "POST":
        note_text = (request.POST.get("note") or "").strip()

        if not note_text:
            messages.error(request, "Note cannot be blank.")
            return redirect("wallcovering_detail", wallcovering_id=wallcovering.id)

        employee = Employees.objects.filter(user=request.user).first()

        if not employee:
            messages.error(request, "Could not find your employee record.")
            return redirect("wallcovering_detail", wallcovering_id=wallcovering.id)

        WallcoveringNotes.objects.create(
            pattern=wallcovering,
            date=date.today(),
            user=employee,
            note=note_text,
        )

        messages.success(request, "Note added.")

    return redirect("wallcovering_detail", wallcovering_id=wallcovering.id)

def wallcovering_order_edit(request, order_id):
    Orders = apps.get_model('jobs', 'Orders')
    order = get_object_or_404(Orders, id=order_id)

    wallcovering = OrderItems.objects.filter(
        order=order,
        link_to_wallcovering__isnull=False
    ).first().link_to_wallcovering

    order_items = OrderItems.objects.filter(order=order).order_by("id")

    pricing = WallcoveringPricing.objects.filter(
        wallcovering=wallcovering
    ).order_by("-quote_date", "-id")

    default_description = f"{wallcovering.code or ''} {wallcovering.pattern or ''}".strip()

    main_item = order_items.filter(wallcovering=wallcovering).first()
    extra_items = order_items.filter(wallcovering__isnull=True)

    if request.method == "POST":
        order.date_ordered = request.POST.get("date_ordered") or date.today()
        order.notes = request.POST.get("order_notes")
        order.save()

        main_quantity = clean_decimal(request.POST.get("main_quantity"))
        main_unit = (request.POST.get("main_unit") or "").strip()
        main_price = clean_decimal(request.POST.get("main_price"))
        main_notes = request.POST.get("main_item_notes")

        main_item = OrderItems.objects.filter(
            order=order,
            wallcovering=wallcovering
        ).first()

        if main_quantity > Decimal("0.00") and main_unit and main_price is not None:
            if main_item:
                main_item.quantity = main_quantity
                main_item.unit = main_unit
                main_item.price = main_price
                main_item.item_description = default_description
                main_item.item_notes = main_notes
                main_item.link_to_wallcovering = wallcovering
                main_item.save()
            else:
                OrderItems.objects.create(
                    order=order,
                    wallcovering=wallcovering,
                    link_to_wallcovering=wallcovering,
                    quantity=main_quantity,
                    unit=main_unit,
                    price=main_price,
                    item_description=default_description,
                    item_notes=main_notes,
                )

        extra_item_ids = request.POST.getlist("extra_item_id[]")
        descriptions = request.POST.getlist("extra_description[]")
        quantities = request.POST.getlist("extra_quantity[]")
        units = request.POST.getlist("extra_unit[]")
        prices = request.POST.getlist("extra_price[]")
        notes = request.POST.getlist("extra_notes[]")

        submitted_extra_ids = []

        for i in range(len(descriptions)):
            extra_item_id = extra_item_ids[i] if i < len(extra_item_ids) else ""
            description = (descriptions[i] or "").strip()
            quantity = clean_decimal(quantities[i] if i < len(quantities) else "")
            unit = (units[i] if i < len(units) else "").strip()
            price = clean_decimal(prices[i] if i < len(prices) else "")
            item_note = notes[i] if i < len(notes) else ""

            if not description and quantity <= Decimal("0.00"):
                continue

            if extra_item_id:
                extra_item = get_object_or_404(
                    OrderItems,
                    id=extra_item_id,
                    order=order
                )

                extra_item.wallcovering = None
                extra_item.link_to_wallcovering = wallcovering
                extra_item.quantity = quantity
                extra_item.unit = unit
                extra_item.price = price
                extra_item.item_description = description
                extra_item.item_notes = item_note
                extra_item.save()

                submitted_extra_ids.append(extra_item.id)

            else:
                extra_item = OrderItems.objects.create(
                    order=order,
                    wallcovering=None,
                    link_to_wallcovering=wallcovering,
                    quantity=quantity,
                    unit=unit,
                    price=price,
                    item_description=description,
                    item_notes=item_note,
                )

                submitted_extra_ids.append(extra_item.id)

        return redirect("wallcovering_detail", wallcovering_id=wallcovering.id)

    return render(request, "wallcovering_add_order.html", {
        "is_edit": True,
        "order": order,
        "wallcovering": wallcovering,
        "pricing": pricing,
        "default_description": default_description,
        "main_item": main_item,
        "extra_items": extra_items,
        "today": date.today(),
    })

def wallcovering_receipt_edit(request, delivery_id):
    delivery = get_object_or_404(WallcoveringDelivery, id=delivery_id)

    first_received = ReceivedItems.objects.filter(
        wallcovering_delivery=delivery
    ).select_related(
        "order_item",
        "order_item__link_to_wallcovering"
    ).first()

    if not first_received:
        messages.error(request, "This receipt does not have any received items.")
        return redirect("wallcovering_home")

    wallcovering = first_received.order_item.link_to_wallcovering

    received_items = ReceivedItems.objects.filter(
        wallcovering_delivery=delivery
    ).select_related(
        "order_item",
        "order_item__order",
        "order_item__wallcovering",
        "order_item__link_to_wallcovering"
    ).order_by("id")

    open_order_items = OrderItems.objects.filter(
        link_to_wallcovering=wallcovering
    ).select_related(
        "order",
        "wallcovering",
        "order__job_number"
    ).order_by(
        "order__po_number",
        "id"
    )

    for received_item in received_items:
        received_item.related_packages = Packages.objects.filter(
            delivery=delivery,
            orderitem=received_item.order_item
        ).order_by("id")

    if request.method == "POST":
        receipt_date = request.POST.get("date") or date.today()
        receipt_notes = request.POST.get("notes")

        order_item_ids = request.POST.getlist("order_item[]")
        quantities = request.POST.getlist("quantity[]")

        package_orderitem_ids = request.POST.getlist("package_orderitem[]")
        package_types = request.POST.getlist("package_type[]")
        package_contents = request.POST.getlist("package_contents[]")
        package_quantities = request.POST.getlist("package_quantity[]")
        package_notes = request.POST.getlist("package_notes[]")

        valid_received_rows = []

        for i in range(len(order_item_ids)):
            order_item_id = order_item_ids[i]
            quantity = clean_decimal(quantities[i] if i < len(quantities) else "")

            if not order_item_id or quantity <= Decimal("0.00"):
                continue

            order_item = get_object_or_404(
                OrderItems,
                id=order_item_id,
                link_to_wallcovering=wallcovering
            )

            valid_received_rows.append({
                "order_item": order_item,
                "quantity": quantity,
            })

        if not valid_received_rows:
            messages.error(request, "You must receive at least one item.")
            return redirect(request.path)

        # Every received item must have at least one package.
        for row in valid_received_rows:
            order_item = row["order_item"]
            has_package = False

            for i in range(len(package_types)):
                package_orderitem_id = package_orderitem_ids[i] if i < len(package_orderitem_ids) else None
                quantity_received = package_quantities[i] if i < len(package_quantities) else ""

                try:
                    package_qty = int(quantity_received or 0)
                except ValueError:
                    package_qty = 0

                if str(package_orderitem_id) == str(order_item.id) and package_qty > 0:
                    has_package = True
                    break

            if not has_package:
                messages.error(
                    request,
                    f"You must enter at least one package for {order_item.item_description}."
                )
                return redirect(request.path)

        delivery.date = receipt_date
        delivery.notes = receipt_notes
        delivery.save()

        # Do not delete packages that have been sent.
        sent_package_ids = OutgoingItem.objects.filter(
            package__delivery=delivery
        ).values_list(
            "package_id",
            flat=True
        )

        posted_package_ids = request.POST.getlist("package_id[]")

        existing_packages = Packages.objects.filter(
            delivery=delivery
        )

        for package in existing_packages:
            if str(package.id) not in posted_package_ids:
                if package.id in sent_package_ids:
                    messages.error(
                        request,
                        f"Cannot remove package '{package.contents}' because some of it has already been sent to the job."
                    )
                    return redirect(request.path)
                package.delete()

        # Rebuild received items. These are safe to delete because packages reference orderitem, not ReceivedItems.
        ReceivedItems.objects.filter(
            wallcovering_delivery=delivery
        ).delete()

        for row in valid_received_rows:
            ReceivedItems.objects.create(
                wallcovering_delivery=delivery,
                order_item=row["order_item"],
                quantity=row["quantity"],
            )

        for i in range(len(package_types)):
            package_id = posted_package_ids[i] if i < len(posted_package_ids) else ""
            package_orderitem_id = package_orderitem_ids[i] if i < len(package_orderitem_ids) else None
            package_type = (package_types[i] if i < len(package_types) else "").strip()
            contents = (package_contents[i] if i < len(package_contents) else "").strip()
            quantity_received = package_quantities[i] if i < len(package_quantities) else ""
            notes = package_notes[i] if i < len(package_notes) else ""

            if not package_orderitem_id:
                continue

            try:
                package_qty = int(quantity_received or 0)
            except ValueError:
                package_qty = 0

            if not package_type and not contents and package_qty <= 0:
                continue

            package_orderitem = get_object_or_404(
                OrderItems,
                id=package_orderitem_id,
                link_to_wallcovering=wallcovering
            )

            if package_id:
                package = get_object_or_404(
                    Packages,
                    id=package_id,
                    delivery=delivery
                )

                if package.id in sent_package_ids and package_qty < package.total_sent():
                    messages.error(
                        request,
                        f"Package '{package.contents}' cannot have received quantity less than sent quantity."
                    )
                    return redirect(request.path)

                package.orderitem = package_orderitem
                package.type = package_type
                package.contents = contents
                package.quantity_received = package_qty
                package.notes = notes
                package.save()

            else:
                Packages.objects.create(
                    delivery=delivery,
                    orderitem=package_orderitem,
                    type=package_type,
                    contents=contents,
                    quantity_received=package_qty,
                    notes=notes,
                )

        return redirect("wallcovering_detail", wallcovering_id=wallcovering.id)

    return render(request, "wallcovering_receive.html", {
        "is_edit": True,
        "delivery": delivery,
        "wallcovering": wallcovering,
        "open_order_items": open_order_items,
        "received_items": received_items,
        "today": date.today(),
    })


def wallcovering_sent_edit(request, sent_id):
    outgoing_event = get_object_or_404(OutgoingWallcovering, id=sent_id)

    first_item = OutgoingItem.objects.filter(
        outgoing_event=outgoing_event
    ).select_related(
        "package__orderitem__link_to_wallcovering"
    ).first()

    if not first_item:
        messages.error(request, "This delivery does not have any sent items.")
        return redirect("wallcovering_home")

    wallcovering = first_item.package.orderitem.link_to_wallcovering

    outgoing_items = OutgoingItem.objects.filter(
        outgoing_event=outgoing_event
    ).select_related(
        "package",
        "package__orderitem",
        "package__delivery",
        "package__delivery__order"
    ).order_by("id")

    available_packages = []

    packages = Packages.objects.filter(
        orderitem__link_to_wallcovering=wallcovering
    ).select_related(
        "delivery",
        "delivery__order",
        "orderitem"
    ).order_by(
        "delivery__date",
        "id"
    )

    for package in packages:
        current_event_sent = OutgoingItem.objects.filter(
            outgoing_event=outgoing_event,
            package=package
        ).aggregate(
            total=Sum("quantity_sent")
        )["total"] or 0

        sent_other = package.total_sent() - current_event_sent
        received = package.quantity_received or 0
        remaining = received - sent_other

        if remaining > 0:
            package.sent_to_date = sent_other
            package.remaining_to_send = remaining
            available_packages.append(package)

    if request.method == "POST":
        send_date = request.POST.get("date") or date.today()
        delivered_by = request.POST.get("delivered_by")
        notes = request.POST.get("notes")

        package_ids = request.POST.getlist("package[]")
        quantities = request.POST.getlist("quantity_sent[]")

        valid_rows = []

        for i in range(len(package_ids)):
            package_id = package_ids[i]
            quantity_raw = quantities[i] if i < len(quantities) else ""

            if not package_id or not quantity_raw:
                continue

            try:
                quantity_sent = int(quantity_raw)
            except ValueError:
                quantity_sent = 0

            if quantity_sent <= 0:
                continue

            package = get_object_or_404(
                Packages,
                id=package_id,
                orderitem__link_to_wallcovering=wallcovering
            )

            current_event_sent = OutgoingItem.objects.filter(
                outgoing_event=outgoing_event,
                package=package
            ).aggregate(
                total=Sum("quantity_sent")
            )["total"] or 0

            sent_other = package.total_sent() - current_event_sent
            remaining = (package.quantity_received or 0) - sent_other

            if quantity_sent > remaining:
                messages.error(
                    request,
                    f"You cannot send {quantity_sent} packages of {package.contents}. Only {remaining} remain."
                )
                return redirect(request.path)

            valid_rows.append({
                "package": package,
                "quantity_sent": quantity_sent,
            })

        if not valid_rows:
            messages.error(request, "You must select at least one package to send.")
            return redirect(request.path)

        outgoing_event.date = send_date
        outgoing_event.delivered_by = delivered_by
        outgoing_event.notes = notes
        outgoing_event.save()

        OutgoingItem.objects.filter(
            outgoing_event=outgoing_event
        ).delete()

        for row in valid_rows:
            OutgoingItem.objects.create(
                outgoing_event=outgoing_event,
                package=row["package"],
                quantity_sent=row["quantity_sent"],
            )

        return redirect("wallcovering_detail", wallcovering_id=wallcovering.id)

    return render(request, "wallcovering_send_to_job.html", {
        "is_edit": True,
        "outgoing_event": outgoing_event,
        "outgoing_items": outgoing_items,
        "wallcovering": wallcovering,
        "available_packages": available_packages,
        "today": date.today(),
    })




def vendor_edit(request, vendor_id=None):
    allowed_categories = [
        "Equipment Rental",
        "Wallcovering Supplier",
    ]

    vendor_categories = VendorCategory.objects.filter(
        category__in=allowed_categories
    ).order_by("category")

    if vendor_id:
        vendor = get_object_or_404(Vendors, id=vendor_id)
        page_title = "Edit Vendor"
    else:
        vendor = None
        page_title = "Add Vendor"

    if request.method == "POST":
        company_name = request.POST.get("company_name", "").strip()
        category_id = request.POST.get("category")
        company_phone = request.POST.get("company_phone", "").strip()
        company_email = request.POST.get("company_email", "").strip()

        category = None
        if category_id:
            category = get_object_or_404(
                VendorCategory,
                id=category_id,
                category__in=allowed_categories
            )

        if vendor is None:
            vendor = Vendors()

        vendor.company_name = company_name
        vendor.category = category
        vendor.company_phone = company_phone
        vendor.company_email = company_email
        vendor.save()

        return redirect("wallcovering_home")

    return render(request, "vendor_edit.html", {
        "vendor": vendor,
        "vendor_categories": vendor_categories,
        "page_title": page_title,
    })