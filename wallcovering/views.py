from console.misc import Email
from decimal import Decimal, InvalidOperation
from datetime import date
from django.apps import apps
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
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
    WallcoveringPricing,
    Pending_Orders,
    Pending_Order_Items
)
from submittals.models import SubmittalItems, SubmittalApprovals
from changeorder.models import Wallcovering_Change_Orders

import os
from io import BytesIO

import openpyxl
from django.conf import settings
from django.http import HttpResponse, JsonResponse, FileResponse, Http404
from django.db.models import Count, Q
from django.utils.text import get_valid_filename


DEFAULT_BOOKING_WALLCOVERING_PATTERN = "Default at Booking-Please Complete"


def wallcovering_home(request):
    selected_filter = request.GET.get("filter", "all")

    wallcoverings = Wallcovering.objects.select_related(
        "job_number",
        "vendor"
    ).annotate(
        user_note_count=Count(
            "wallcoveringnotes",
            filter=Q(wallcoveringnotes__note__isnull=False) & ~Q(wallcoveringnotes__note=""),
            distinct=True
        )
    ).filter(
        job_number__is_closed=False
    ).order_by(
        "job_number__job_name",
        "code"
    )

    wallcovering_list = []

    for wc in wallcoverings:
        submittal_status = wc.submittal_status()
        ordering_status = wc.ordering_status()
        sent_status = wc.sent_status()
        display_quantity = wc.display_quantity()

        include_wc = True

        has_approved_cop_not_ordered = Wallcovering_Change_Orders.objects.filter(
            wallcovering=wc,
            is_ordered=False,
            change_order__is_approved=True
        ).exists()

        # Exclude voided / owner furnished wallcovering from all filtered views
        if selected_filter != "all" and (wc.is_void or wc.is_owner_furnished):
            include_wc = False

        elif selected_filter == "not_approved":
            include_wc = submittal_status != "Approved"


        elif selected_filter == "approved_not_ordered":

            include_wc = (

                    (

                            submittal_status == "Approved"

                            and ordering_status == "Not Ordered"

                    )

                    or has_approved_cop_not_ordered

            )

        elif selected_filter == "not_delivered":
            include_wc = ordering_status in [
                "Ordered",
                "Partially Received",
            ]

        if include_wc:
            linked_cop_items = (
                Wallcovering_Change_Orders.objects
                .filter(wallcovering=wc)
                .select_related("change_order")
            )

            attention_cop_items = linked_cop_items.filter(
                Q(is_ordered=False) |
                Q(change_order__is_approved=False)
            ).order_by("change_order__cop_number", "id")

            wc.change_order_badge_text = ""
            wc.change_order_badge_class = ""
            wc.order_approval_badge_text = ""
            wc.order_approval_badge_class = ""

            has_pending_order_approval = Pending_Orders.objects.filter(
                pending_order_items__link_to_wallcovering=wc,
                date_approved__isnull=True,
                is_ordered=False
            ).exists()

            has_approved_pending_order = Pending_Orders.objects.filter(
                pending_order_items__link_to_wallcovering=wc,
                date_approved__isnull=False,
                is_ordered=False
            ).exists()

            if has_approved_pending_order:
                wc.order_approval_badge_text = "Pending Order Approved!"
                wc.order_approval_badge_class = "badge badge-info"
            elif has_pending_order_approval:
                wc.order_approval_badge_text = "Order Approval Required"
                wc.order_approval_badge_class = "badge badge-warning"

            attention_count = attention_cop_items.count()

            if attention_count > 1:
                wc.change_order_badge_text = "Multiple COPs"
                wc.change_order_badge_class = "badge badge-danger"

            elif attention_count == 1:
                cop_link = attention_cop_items.first()
                cop = cop_link.change_order
                cop_number = cop.cop_number

                if cop_link.is_ordered and not cop.is_approved:
                    wc.change_order_badge_text = f"COP{cop_number} - Ordered, Not Approved"
                    wc.change_order_badge_class = "badge badge-warning"

                elif not cop_link.is_ordered and not cop.is_approved:
                    wc.change_order_badge_text = f"COP{cop_number} Not Approved"
                    wc.change_order_badge_class = "badge badge-warning"

                elif not cop_link.is_ordered and cop.is_approved:
                    wc.change_order_badge_text = f"COP{cop_number} Not Ordered"
                    wc.change_order_badge_class = "badge badge-danger"

            wc.submittal_status = submittal_status
            wc.ordering_status = ordering_status
            wc.sent_status = sent_status
            wc.display_quantity = display_quantity

            wallcovering_list.append(wc)

    return render(request, "wallcovering_home.html", {
        "wallcoverings": wallcovering_list,
        "selected_filter": selected_filter,
    })


def wallcovering_detail(request, wallcovering_id):
    wallcovering = get_object_or_404(Wallcovering, id=wallcovering_id)
    if request.method == "POST":
        if "save_wallcovering_change_orders" in request.POST:
            employee = Employees.objects.filter(user=request.user).first()

            linked_change_orders = Wallcovering_Change_Orders.objects.filter(
                wallcovering=wallcovering
            ).select_related(
                "change_order"
            )

            changes_made = False

            for link in linked_change_orders:
                old_quantity_added = link.quantity_added
                old_units = link.units or ""
                old_notes = link.notes or ""
                old_is_ordered = link.is_ordered

                quantity_raw = request.POST.get(f"quantity_added_{link.id}", "").strip()
                units = request.POST.get(f"units_{link.id}", "").strip()
                notes = request.POST.get(f"notes_{link.id}", "").strip()
                is_ordered = request.POST.get(f"is_ordered_{link.id}") == "on"

                quantity_added = None
                if quantity_raw:
                    try:
                        quantity_added = Decimal(quantity_raw)
                    except InvalidOperation:
                        messages.error(request, "Please enter valid quantities.")
                        return redirect("wallcovering_detail", wallcovering_id=wallcovering.id)

                if (
                    old_quantity_added != quantity_added or
                    old_units != units or
                    old_notes != notes or
                    old_is_ordered != is_ordered
                ):
                    link.quantity_added = quantity_added
                    link.units = units or None
                    link.notes = notes or None
                    link.is_ordered = is_ordered
                    link.save()

                    changes_made = True

            if changes_made:
                WallcoveringNotes.objects.create(
                    pattern=wallcovering,
                    date=date.today(),
                    user=employee,
                    note="Updated change order wallcovering information."
                )

                messages.success(request, "Change order wallcovering information updated.")
            else:
                messages.warning(request, "No change order information was changed.")

            return redirect("wallcovering_detail", wallcovering_id=wallcovering.id)
        if "void_wallcovering" in request.POST:
            employee = Employees.objects.filter(user=request.user).first()
            if not wallcovering.is_void:
                wallcovering.is_void = True
                wallcovering.save()
                WallcoveringNotes.objects.create(
                    pattern=wallcovering,
                    date=date.today(),
                    user=employee,
                    note="Wallcovering marked as No Longer Used."
                )

                messages.success(request, "Wallcovering marked as No Longer Used.")
            else:
                wallcovering.is_void = False
                wallcovering.save()
                WallcoveringNotes.objects.create(
                    pattern=wallcovering,
                    date=date.today(),
                    user=employee,
                    note="Wallcovering marked as being used again."
                )

                messages.success(request, "Wallcovering marked as being used again.")

            return redirect("wallcovering_detail", wallcovering_id=wallcovering.id)
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
        all_approvals = SubmittalApprovals.objects.filter(
            submittalitem=item
        ).select_related("submittal").order_by("-id")

        linked_approvals = all_approvals.filter(
            submittal__isnull=False
        )

        latest_linked_approval = linked_approvals.first()

        has_unlinked_approval = all_approvals.filter(
            submittal__isnull=True
        ).exists()

        if not all_approvals.exists():
            status = "Not Sent"
            approval = None

        elif has_unlinked_approval:
            status = "Not Sent"
            approval = latest_linked_approval

        elif latest_linked_approval and latest_linked_approval.is_approved is True:
            status = "Approved"
            approval = latest_linked_approval

        elif latest_linked_approval and latest_linked_approval.is_approved is False:
            status = "Rejected"
            approval = latest_linked_approval

        elif latest_linked_approval:
            status = "Sent"
            approval = latest_linked_approval

        else:
            status = "Not Sent"
            approval = None

        submittal_rows.append({
            "item": item,
            "approval": approval,
            "status": status,
            "has_unlinked_approval": has_unlinked_approval,
        })

    label_packages = Packages.objects.filter(
        orderitem__wallcovering=wallcovering
    ).select_related(
        "delivery",
        "orderitem",
        "orderitem__wallcovering",
        "orderitem__wallcovering__job_number",
        "orderitem__wallcovering__vendor",
    ).order_by(
        "delivery__date",
        "id"
    )

    linked_change_orders = Wallcovering_Change_Orders.objects.filter(
        wallcovering=wallcovering
    ).select_related(
        "change_order",
        "change_order__job_number"
    ).order_by(
        "-change_order__id",
        "-id"
    )

    pending_order_groups = []
    pending_orders = Pending_Orders.objects.filter(
        pending_order_items__link_to_wallcovering=wallcovering,
        date_approved__isnull=True,
        is_ordered=False
    ).select_related(
        "job_number",
        "vendor",
        "requested_by",
        "approved_by"
    ).distinct().order_by("-date_requested", "-id")

    for pending_order in pending_orders:
        pending_order_groups.append({
            "order": pending_order,
            "all_items": Pending_Order_Items.objects.filter(
                pending_order=pending_order
            ).order_by("id"),
        })

    approved_order_groups = []
    approved_orders = Pending_Orders.objects.filter(
        pending_order_items__link_to_wallcovering=wallcovering,
        date_approved__isnull=False,
        is_ordered=False
    ).select_related(
        "job_number",
        "vendor",
        "requested_by",
        "approved_by"
    ).distinct().order_by("-date_approved", "-id")

    for approved_order in approved_orders:
        approved_order_groups.append({
            "order": approved_order,
            "all_items": Pending_Order_Items.objects.filter(
                pending_order=approved_order
            ).order_by("id"),
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
        "label_packages": label_packages,
        "linked_change_orders": linked_change_orders,
        "pending_order_groups": pending_order_groups,
        "approved_order_groups": approved_order_groups,
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

        wallcovering_defaults = {
            "job_number": selected_job,
            "vendor": vendor_obj,
            "code": request.POST.get("code"),
            "pattern": request.POST.get("pattern"),
            "estimated_quantity": request.POST.get("estimated_quantity") or 0,
            "estimated_unit": request.POST.get("estimated_unit"),
            "roll_width": request.POST.get("roll_width"),
            "roll_length": request.POST.get("roll_length"),
            "vertical_repeat": request.POST.get("vertical_repeat"),
            "cut_charge": request.POST.get("cut_charge"),
            "notes": request.POST.get("notes"),
            "is_owner_furnished": bool(request.POST.get("is_owner_furnished")),
            "is_random_reverse": bool(request.POST.get("is_random_reverse")),
            "is_repeat": bool(request.POST.get("is_repeat")),
            "increment_requirement": request.POST.get("increment_requirement"),
        }

        wallcovering = Wallcovering.objects.filter(
            job_number=selected_job,
            pattern=DEFAULT_BOOKING_WALLCOVERING_PATTERN,
            is_void=False
        ).first()

        if wallcovering:
            for field, value in wallcovering_defaults.items():
                setattr(wallcovering, field, value)
            wallcovering.save()
            messages.success(request, "Updated the default wallcovering created at booking.")
        else:
            wallcovering = Wallcovering.objects.create(**wallcovering_defaults)
        if wallcovering.code:
            description = f"{wallcovering.code} {wallcovering.vendor.company_name} {wallcovering.pattern}"
        else:
            description = f"{wallcovering.vendor.company_name}"
        if wallcovering.is_owner_furnished == False:
            existing_submittal = SubmittalItems.objects.filter(description = "Wallcovering Submittal",job_number=selected_job).first()
            if existing_submittal:
                existing_submittal.description = f"{description} Product Data"
                existing_submittal.wallcovering = wallcovering
                existing_submittal.notes = ""
                existing_submittal.save()
            else:
                SubmittalItems.objects.create(wallcovering_id=wallcovering,description =f"{description} Product Data",job_number=selected_job)
            SubmittalItems.objects.create(wallcovering_id=wallcovering, description=f"{description} Samples",job_number=selected_job)

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


def get_submitted_po_number(request):
    custom_po_number = (request.POST.get("custom_po_number") or "").strip()

    if custom_po_number:
        return custom_po_number

    return f"TR{get_next_po_number()}"


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
        main_quantity = clean_decimal(request.POST.get("main_quantity"))
        main_unit = (request.POST.get("main_unit") or "").strip()
        main_price = clean_decimal(request.POST.get("main_price"))
        main_item_notes = request.POST.get("main_item_notes")

        descriptions = request.POST.getlist("extra_description[]")
        quantities = request.POST.getlist("extra_quantity[]")
        units = request.POST.getlist("extra_unit[]")
        prices = request.POST.getlist("extra_price[]")
        notes = request.POST.getlist("extra_notes[]")

        extra_items = []
        for i in range(len(descriptions)):
            description = (descriptions[i] or "").strip()
            quantity = clean_decimal(quantities[i] if i < len(quantities) else "")
            unit = (units[i] if i < len(units) else "").strip()
            price = clean_decimal(prices[i] if i < len(prices) else "")
            item_note = notes[i] if i < len(notes) else ""

            if description == "" and quantity == Decimal("0.00"):
                continue

            extra_items.append({
                "description": description,
                "quantity": quantity,
                "unit": unit,
                "price": price,
                "item_note": item_note,
            })

        has_main_item = main_quantity > Decimal("0.00") and main_unit and main_price is not None

        if "send_for_approval" in request.POST:
            requestor_notes = (request.POST.get("requestor_notes") or "").strip()

            if not has_main_item and not extra_items:
                messages.error(request, "Please enter the main wallcovering item or at least one additional PO item.")
                return redirect("wallcovering_add_order", wallcovering_id=wallcovering.id)

            employee = Employees.objects.filter(user=request.user).first()

            with transaction.atomic():
                pending_order = Pending_Orders.objects.create(
                    job_number=wallcovering.job_number,
                    vendor=wallcovering.vendor,
                    description=default_description,
                    date_ordered=request.POST.get("date_ordered") or date.today(),
                    notes=request.POST.get("order_notes"),
                    date_requested=date.today(),
                    requested_by=employee,
                    requestor_notes=requestor_notes,
                )

                if has_main_item:
                    Pending_Order_Items.objects.create(
                        pending_order=pending_order,
                        wallcovering=wallcovering,
                        quantity=main_quantity,
                        unit=main_unit,
                        price=main_price,
                        item_description=default_description,
                        item_notes=main_item_notes,
                        link_to_wallcovering=wallcovering,
                    )

                for item in extra_items:
                    Pending_Order_Items.objects.create(
                        pending_order=pending_order,
                        wallcovering=None,
                        quantity=item["quantity"],
                        unit=item["unit"],
                        price=item["price"],
                        item_description=item["description"],
                        item_notes=item["item_note"],
                        link_to_wallcovering=wallcovering,
                    )

            current_user_email = ""
            if employee and employee.email:
                current_user_email = employee.email.strip().lower()
            elif request.user.email:
                current_user_email = request.user.email.strip().lower()

            recipients = []
            seen_recipients = set()

            def add_recipient(email, skip_if_current_user=False):
                if not email:
                    return

                cleaned_email = email.strip()
                normalized_email = cleaned_email.lower()

                if normalized_email == "lee@gerloffpainting.com":
                    return

                if skip_if_current_user and normalized_email == current_user_email:
                    return

                try:
                    validate_email(cleaned_email)
                except ValidationError:
                    return

                if normalized_email in seen_recipients:
                    return

                recipients.append(cleaned_email)
                seen_recipients.add(normalized_email)

            add_recipient("bridgette@gerloffpainting.com")
            add_recipient("joe@gerloffpainting.com")

            if wallcovering.job_number.project_manager:
                add_recipient(wallcovering.job_number.project_manager.email)

            if wallcovering.job_number.estimator:
                add_recipient(wallcovering.job_number.estimator.email)

            email_lines = [
                f"Job Name: {wallcovering.job_number.job_name}",
                f"Project Manager: {wallcovering.job_number.project_manager or ''}",
                "",
                "You have a pending wallcovering order that needs approval",
                "",
                "Pending Order Items:",
            ]

            pending_items = Pending_Order_Items.objects.filter(
                pending_order=pending_order
            ).order_by("id")

            note_lines = [
                "Order Approval Requested.",
                "",
                "Pending Order Items:",
            ]

            for item in pending_items:
                note_lines.append(
                    f"Description: {item.item_description}, Quantity: {item.quantity}, Unit: {item.unit}, Price: {item.price}"
                )
                email_lines.append(
                    f"- {item.quantity} {item.unit} of {item.item_description}"
                )

            if requestor_notes:
                email_lines.extend([
                    "",
                    "Requestor Notes:",
                    requestor_notes,
                ])

            if requestor_notes:
                note_lines.extend([
                    "",
                    f"Requestor Notes: {requestor_notes}",
                ])

            note_lines.extend([
                "",
                f"Email Recipients: {', '.join(recipients) if recipients else 'None'}",
            ])

            if employee:
                WallcoveringNotes.objects.create(
                    pattern=wallcovering,
                    date=date.today(),
                    user=employee,
                    note="\r\n".join(note_lines)[:2000],
                )
            else:
                messages.error(request, "Could not add an approval note because your employee record was not found.")

            email_lines.extend([
                "",
                f"http://gp-webserver/wallcovering/wallcovering_detail/{wallcovering.id}",
            ])

            if recipients:
                sender = employee.email if employee and employee.email else "bridgette@gerloffpainting.com"

                try:
                    Email.sendEmail(
                        "Pending Wallcovering Approval Needed",
                        "\r\n".join(email_lines),
                        recipients,
                        False,
                        sender
                    )
                    messages.success(request, "Approval email sent.")
                except:
                    messages.error(request, "There was a problem sending the approval email.")
            else:
                messages.error(request, "No approval email recipients were found.")

            messages.success(request, "Wallcovering order sent for approval.")
            return redirect("wallcovering_detail", wallcovering_id=wallcovering.id)

        po_number = get_submitted_po_number(request)

        default_description = f"{wallcovering.code or ''} {wallcovering.pattern or ''}".strip()
        if wallcovering.vendor.company_email:
            lines = [f"Send this email to {wallcovering.vendor}: - {wallcovering.vendor.company_email}",]
        else:
            lines = [f"Send this email to {wallcovering.vendor}. No Email is entered in Trinity..", ]

        lines2 = [f"New Wallcovering Order", ]
        lines.extend([
            "",
            f"Hello I would like to place an order",
            "",
            f"Job Name: {wallcovering.job_number.job_name}",
            f"Vendor: {wallcovering.vendor.company_name}",
            f"PO#: {po_number}",
            "",])
        lines2.extend([
            "",
            f"Job Name: {wallcovering.job_number.job_name}",
            f"PO#: {po_number}",
            "", ])
        order = Orders.objects.create(
            po_number=po_number,
            job_number=wallcovering.job_number,
            vendor=wallcovering.vendor,
            description=default_description,
            date_ordered=request.POST.get("date_ordered") or date.today(),
            notes=request.POST.get("order_notes"),
        )

        # MAIN WALLCOVERING ITEM - this is the ONLY item linked to Wallcovering
        if has_main_item:
            OrderItems.objects.create(
                order=order,
                wallcovering=wallcovering,
                quantity=main_quantity,
                unit=main_unit,
                price=main_price,
                item_description=default_description,
                item_notes=main_item_notes,
                link_to_wallcovering = wallcovering,
            )
            lines.extend([
                f"{main_quantity} {main_unit} of {wallcovering.code} {wallcovering.vendor.company_name} {wallcovering.pattern}",
                "",])
            lines2.extend([
                f"{main_quantity} {main_unit} of {wallcovering.code} {wallcovering.vendor.company_name} {wallcovering.pattern}",
                "", ])
        # EXTRA ITEMS - paste, adhesive, sundries, etc.
        for item in extra_items:
            OrderItems.objects.create(
                order=order,
                wallcovering=None,  # important
                quantity=item["quantity"],
                unit=item["unit"],
                price=item["price"],
                item_description=item["description"],
                item_notes=item["item_note"],
                link_to_wallcovering=wallcovering,
            )
            lines.extend([
                f"{item['quantity']} {item['unit']} of {item['description']}",
                "", ])
            lines2.extend([
                f"{item['quantity']} {item['unit']} of {item['description']}",
                "", ])
        subject = "Wallcovering Purchase Order"
        employee = Employees.objects.filter(user=request.user).first()
        if employee and employee.email:
            recipient = [employee.email]
            sender = employee.email
        else:
            recipient = ["bridgette@gerloffpainting.com"]
            sender = "bridgette@gerloffpainting.com"
        new_email_message = "\r\n".join(lines)
        try:
            Email.sendEmail(subject, new_email_message, recipient, False, sender)
            messages.success(request, "Please Forward the Order Email to the Vendor ")
        except:
            messages.error(request,
                           "There was a problem sending the email, you will have to manually send the order.")
        #----NEW EMAIL TO WAREHOUSE----
        #-----------------------------
        #------------------------------
        subject = "New Wallcovering Order"
        recipient = ["bridgette@gerloffpainting.com", "warehouse@gerloffpainting.com"]

        if employee and employee.email:
            sender = employee.email

            if employee.email not in recipient:
                recipient.append(employee.email)
        else:
            sender = "bridgette@gerloffpainting.com"
        new_email_message = "\r\n".join(lines2)
        try:
            Email.sendEmail(subject, new_email_message, recipient, False, sender)
            messages.success(request, "Email Sent to Warehouse")
        except:
            messages.error(request,
                           "There was a problem sending the email to the warehouse, you will have to manually send email")

        return redirect("wallcovering_detail", wallcovering_id=wallcovering.id)

    return render(request, "wallcovering_add_order.html", {
        "wallcovering": wallcovering,
        "today": date.today(),
        "pricing": pricing,
        "default_description": default_description,
    })




def wallcovering_pending_order(request, pending_order_id):
    Orders = apps.get_model('jobs', 'Orders')

    pending_order = get_object_or_404(
        Pending_Orders.objects.select_related(
            "job_number",
            "vendor",
            "requested_by",
            "approved_by"
        ),
        id=pending_order_id,
        is_ordered=False
    )

    first_item = Pending_Order_Items.objects.filter(
        pending_order=pending_order,
        link_to_wallcovering__isnull=False
    ).select_related("link_to_wallcovering").first()

    if not first_item:
        messages.error(request, "This pending order is not linked to a wallcovering.")
        return redirect("wallcovering_home")

    wallcovering = first_item.link_to_wallcovering
    default_description = f"{wallcovering.code or ''} {wallcovering.pattern or ''}".strip()

    pricing = WallcoveringPricing.objects.filter(
        wallcovering=wallcovering
    ).order_by("-quote_date", "-id")

    linked_change_orders = Wallcovering_Change_Orders.objects.filter(
        wallcovering=wallcovering,
        is_ordered=False,
        change_order__is_approved=True
    ).select_related("change_order").order_by("change_order__cop_number", "id")

    def get_posted_items():
        main_quantity = clean_decimal(request.POST.get("main_quantity"))
        main_unit = (request.POST.get("main_unit") or "").strip()
        main_price = clean_decimal(request.POST.get("main_price"))
        main_item_notes = request.POST.get("main_item_notes")

        descriptions = request.POST.getlist("extra_description[]")
        quantities = request.POST.getlist("extra_quantity[]")
        units = request.POST.getlist("extra_unit[]")
        prices = request.POST.getlist("extra_price[]")
        notes = request.POST.getlist("extra_notes[]")

        extra_items = []
        for i in range(len(descriptions)):
            description = (descriptions[i] or "").strip()
            quantity = clean_decimal(quantities[i] if i < len(quantities) else "")
            unit = (units[i] if i < len(units) else "").strip()
            price = clean_decimal(prices[i] if i < len(prices) else "")
            item_note = notes[i] if i < len(notes) else ""

            if description == "" and quantity == Decimal("0.00"):
                continue

            extra_items.append({
                "description": description,
                "quantity": quantity,
                "unit": unit,
                "price": price,
                "item_note": item_note,
            })

        has_main_item = main_quantity > Decimal("0.00") and main_unit and main_price is not None

        return {
            "main_quantity": main_quantity,
            "main_unit": main_unit,
            "main_price": main_price,
            "main_item_notes": main_item_notes,
            "extra_items": extra_items,
            "has_main_item": has_main_item,
        }

    def replace_pending_items(posted_items):
        Pending_Order_Items.objects.filter(pending_order=pending_order).delete()

        if posted_items["has_main_item"]:
            Pending_Order_Items.objects.create(
                pending_order=pending_order,
                wallcovering=wallcovering,
                quantity=posted_items["main_quantity"],
                unit=posted_items["main_unit"],
                price=posted_items["main_price"],
                item_description=default_description,
                item_notes=posted_items["main_item_notes"],
                link_to_wallcovering=wallcovering,
            )

        for item in posted_items["extra_items"]:
            Pending_Order_Items.objects.create(
                pending_order=pending_order,
                wallcovering=None,
                quantity=item["quantity"],
                unit=item["unit"],
                price=item["price"],
                item_description=item["description"],
                item_notes=item["item_note"],
                link_to_wallcovering=wallcovering,
            )

    def get_pending_order_changes(posted_items):
        changes = []
        posted_date_ordered = request.POST.get("date_ordered") or date.today()
        posted_order_notes = request.POST.get("order_notes") or ""

        existing_date_ordered = pending_order.date_ordered.isoformat() if pending_order.date_ordered else ""
        if str(posted_date_ordered) != existing_date_ordered:
            changes.append(f"Date Ordered changed from {existing_date_ordered or 'blank'} to {posted_date_ordered or 'blank'}")

        if posted_order_notes != (pending_order.notes or ""):
            changes.append("Order Notes changed.")

        existing_items = list(Pending_Order_Items.objects.filter(
            pending_order=pending_order
        ).order_by("id"))

        existing_main = next((item for item in existing_items if item.wallcovering_id == wallcovering.id), None)

        if existing_main or posted_items["has_main_item"]:
            if not existing_main:
                changes.append("Main wallcovering item added.")
            elif not posted_items["has_main_item"]:
                changes.append("Main wallcovering item removed.")
            else:
                main_comparisons = [
                    ("Main Quantity", existing_main.quantity, posted_items["main_quantity"]),
                    ("Main Unit", existing_main.unit or "", posted_items["main_unit"]),
                    ("Main Price", existing_main.price, posted_items["main_price"]),
                    ("Main Notes", existing_main.item_notes or "", posted_items["main_item_notes"] or ""),
                ]

                for label, old_value, new_value in main_comparisons:
                    if str(old_value or "") != str(new_value or ""):
                        changes.append(f"{label} changed from {old_value or 'blank'} to {new_value or 'blank'}")

        existing_extra_items = [
            {
                "description": item.item_description or "",
                "quantity": item.quantity,
                "unit": item.unit or "",
                "price": item.price,
                "item_note": item.item_notes or "",
            }
            for item in existing_items
            if item.wallcovering_id is None
        ]

        posted_extra_items = posted_items["extra_items"]

        if len(existing_extra_items) != len(posted_extra_items):
            changes.append(f"Additional item count changed from {len(existing_extra_items)} to {len(posted_extra_items)}")

        for index, posted_item in enumerate(posted_extra_items):
            if index >= len(existing_extra_items):
                changes.append(f"Additional item added: {posted_item['description']}")
                continue

            existing_item = existing_extra_items[index]
            comparisons = [
                ("Description", existing_item["description"], posted_item["description"]),
                ("Quantity", existing_item["quantity"], posted_item["quantity"]),
                ("Unit", existing_item["unit"], posted_item["unit"]),
                ("Price", existing_item["price"], posted_item["price"]),
                ("Notes", existing_item["item_note"], posted_item["item_note"]),
            ]

            for label, old_value, new_value in comparisons:
                if str(old_value or "") != str(new_value or ""):
                    changes.append(
                        f"Additional item {index + 1} {label} changed from {old_value or 'blank'} to {new_value or 'blank'}"
                    )

        if len(existing_extra_items) > len(posted_extra_items):
            for removed_item in existing_extra_items[len(posted_extra_items):]:
                changes.append(f"Additional item removed: {removed_item['description'] or 'No Description'}")

        return changes

    if request.method == "POST":
        posted_items = get_posted_items()

        if not posted_items["has_main_item"] and not posted_items["extra_items"]:
            messages.error(request, "Please enter the main wallcovering item or at least one additional PO item.")
            return redirect("wallcovering_pending_order", pending_order_id=pending_order.id)

        employee = Employees.objects.filter(user=request.user).first()

        if not pending_order.date_approved:
            unanswered_change_orders = [
                link for link in linked_change_orders
                if request.POST.get(f"change_order_quantity_included_{link.id}") not in ("yes", "no")
            ]

            if unanswered_change_orders:
                messages.error(
                    request,
                    "Please answer whether each approved change order quantity is included in this order."
                )
                return redirect("wallcovering_pending_order", pending_order_id=pending_order.id)

            approver_notes = (request.POST.get("approver_notes") or "").strip()
            changes = get_pending_order_changes(posted_items)

            with transaction.atomic():
                pending_order.date_ordered = request.POST.get("date_ordered") or date.today()
                pending_order.notes = request.POST.get("order_notes")
                pending_order.date_approved = date.today()
                pending_order.approved_by = employee
                pending_order.approver_notes = approver_notes
                pending_order.save()
                replace_pending_items(posted_items)

                for link in linked_change_orders:
                    if request.POST.get(f"change_order_quantity_included_{link.id}") == "yes":
                        link.is_ordered = True
                        link.save(update_fields=["is_ordered"])

            sender = employee.email if employee and employee.email else "bridgette@gerloffpainting.com"
            approval_recipients = ["bridgette@gerloffpainting.com"]

            if employee and employee.email:
                approver_email = employee.email.strip()
                if approver_email.lower() not in [email.lower() for email in approval_recipients]:
                    approval_recipients.append(approver_email)

            approval_lines = [
                "Order is approved",
            ]

            if approver_notes:
                approval_lines.extend([
                    "",
                    "Approver Notes:",
                    approver_notes,
                ])

            if changes:
                approval_lines.extend(["", "Changes Made:"])
                approval_lines.extend([f"- {change}" for change in changes])

            if linked_change_orders:
                approval_lines.extend(["", "Change Order Quantities:"])
                for link in linked_change_orders:
                    included_response = request.POST.get(f"change_order_quantity_included_{link.id}")
                    included_text = "Included" if included_response == "yes" else "Not Included"
                    approval_lines.append(
                        f"- COP {link.change_order.cop_number} - {link.change_order.description or ''}: {included_text}"
                    )

            if employee:
                WallcoveringNotes.objects.create(
                    pattern=wallcovering,
                    date=date.today(),
                    user=employee,
                    note="\r\n".join(approval_lines)[:2000],
                )
            else:
                messages.error(request, "Could not add an approval note because your employee record was not found.")

            try:
                Email.sendEmail(
                    "Order is approved",
                    "\r\n".join(approval_lines),
                    approval_recipients,
                    False,
                    sender
                )
                messages.success(request, "Order approved and email sent.")
            except:
                messages.error(request, "Order approved, but there was a problem sending the approval email.")

            return redirect("wallcovering_detail", wallcovering_id=wallcovering.id)

        po_number = get_submitted_po_number(request)

        with transaction.atomic():
            pending_order.date_ordered = request.POST.get("date_ordered") or date.today()
            pending_order.notes = request.POST.get("order_notes")
            pending_order.is_ordered = True
            pending_order.save()
            replace_pending_items(posted_items)

            order = Orders.objects.create(
                po_number=po_number,
                job_number=wallcovering.job_number,
                vendor=wallcovering.vendor,
                description=default_description,
                date_ordered=pending_order.date_ordered,
                notes=pending_order.notes,
            )

            if posted_items["has_main_item"]:
                OrderItems.objects.create(
                    order=order,
                    wallcovering=wallcovering,
                    quantity=posted_items["main_quantity"],
                    unit=posted_items["main_unit"],
                    price=posted_items["main_price"],
                    item_description=default_description,
                    item_notes=posted_items["main_item_notes"],
                    link_to_wallcovering=wallcovering,
                )

            for item in posted_items["extra_items"]:
                OrderItems.objects.create(
                    order=order,
                    wallcovering=None,
                    quantity=item["quantity"],
                    unit=item["unit"],
                    price=item["price"],
                    item_description=item["description"],
                    item_notes=item["item_note"],
                    link_to_wallcovering=wallcovering,
                )

        vendor_name = wallcovering.vendor.company_name if wallcovering.vendor else ""
        vendor_email = wallcovering.vendor.company_email if wallcovering.vendor else ""

        if vendor_email:
            lines = [f"Send this email to {wallcovering.vendor}: - {vendor_email}"]
        else:
            lines = [f"Send this email to {wallcovering.vendor}. No Email is entered in Trinity.."]

        lines2 = ["New Wallcovering Order"]
        lines.extend([
            "",
            "Hello I would like to place an order",
            "",
            f"Job Name: {wallcovering.job_number.job_name}",
            f"Vendor: {vendor_name}",
            f"PO#: {po_number}",
            "",
        ])
        lines2.extend([
            "",
            f"Job Name: {wallcovering.job_number.job_name}",
            f"PO#: {po_number}",
            "",
        ])

        if posted_items["has_main_item"]:
            item_line = (
                f"{posted_items['main_quantity']} {posted_items['main_unit']} "
                f"of {wallcovering.code} {vendor_name} {wallcovering.pattern}"
            )
            lines.extend([item_line, ""])
            lines2.extend([item_line, ""])

        for item in posted_items["extra_items"]:
            item_line = f"{item['quantity']} {item['unit']} of {item['description']}"
            lines.extend([item_line, ""])
            lines2.extend([item_line, ""])

        if employee and employee.email:
            recipient = [employee.email]
            sender = employee.email
        else:
            recipient = ["bridgette@gerloffpainting.com"]
            sender = "bridgette@gerloffpainting.com"

        try:
            Email.sendEmail("Wallcovering Purchase Order", "\r\n".join(lines), recipient, False, sender)
            messages.success(request, "Please Forward the Order Email to the Vendor ")
        except:
            messages.error(request, "There was a problem sending the email, you will have to manually send the order.")

        warehouse_recipients = ["bridgette@gerloffpainting.com", "warehouse@gerloffpainting.com"]
        if employee and employee.email and employee.email not in warehouse_recipients:
            warehouse_recipients.append(employee.email)

        try:
            Email.sendEmail("New Wallcovering Order", "\r\n".join(lines2), warehouse_recipients, False, sender)
            messages.success(request, "Email Sent to Warehouse")
        except:
            messages.error(request, "There was a problem sending the email to the warehouse, you will have to manually send email")

        messages.success(request, f"Order {po_number} created.")
        return redirect("wallcovering_detail", wallcovering_id=wallcovering.id)

    pending_items = Pending_Order_Items.objects.filter(
        pending_order=pending_order
    ).order_by("id")

    main_item = pending_items.filter(wallcovering=wallcovering).first()
    extra_items = pending_items.filter(wallcovering__isnull=True)

    return render(request, "wallcovering_add_order.html", {
        "pending_order_review": True,
        "pending_order": pending_order,
        "wallcovering": wallcovering,
        "pricing": pricing,
        "default_description": default_description,
        "main_item": main_item,
        "extra_items": extra_items,
        "linked_change_orders": linked_change_orders,
        "today": date.today(),
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
        # =========================
        # EMAIL SUPERINTENDENT / USER / BRIDGETTE
        # =========================
        job = first_order.job_number

        recipients = ["bridgette@gerloffpainting.com"]

        if job.superintendent and job.superintendent.email:
            recipients.append(job.superintendent.email)

        employee = Employees.objects.filter(user=request.user).first()
        if employee and employee.email:
            recipients.append(employee.email)

        # Remove duplicates / blanks
        recipients = list(dict.fromkeys([x for x in recipients if x]))

        sender = employee.email if employee and employee.email else "bridgette@gerloffpainting.com"

        received_lines = []

        for row in valid_received_rows:
            order_item = row["order_item"]
            quantity = row["quantity"]

            wc = order_item.wallcovering

            received_lines.append(
                f"- {wc.code if wc and wc.code else ''} "
                f"{wc.vendor.company_name if wc and wc.vendor else ''} "
                f"{wc.pattern if wc and wc.pattern else ''} "
                f"({order_item.item_description}) "
                f"Qty Received: {quantity}"
            )

        package_lines = []

        packages = Packages.objects.filter(
            delivery=delivery
        ).select_related(
            "orderitem",
            "orderitem__wallcovering"
        ).order_by("id")

        for package in packages:
            package_lines.append(
                f"- {package.type or ''} "
                f"Qty: {package.quantity_received or 0} "
                f"Contents: {package.contents or ''} "
                f"Notes: {package.notes or ''}"
            )

        email_message = (
            f"Wallcovering has been received for:\n\n"
            f"{job.job_number} - {job.job_name}\n\n"
            f"PO: {first_order.po_number}\n"
            f"Date Received: {receipt_date}\n\n"
            f"Received Items:\n"
            + "\n".join(received_lines)
        )

        if receipt_notes:
            email_message += f"\n\nReceipt Notes:\n{receipt_notes}"

        if package_lines:
            email_message += (
                f"\n\nPackages:\n"
                + "\n".join(package_lines)
            )

        try:
            Email.sendEmail(
                f"Wallcovering Received - {job.job_number} {job.job_name}",
                email_message,
                recipients,
                False,
                sender
            )
            messages.success(request, "Wallcovering receipt saved and email sent to superintendent.")
        except:
            messages.warning(
                request,
                "Wallcovering receipt saved, but the email was not sent to superintendent."
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
        custom_po_number = (request.POST.get("custom_po_number") or "").strip()
        if custom_po_number:
            order.po_number = custom_po_number

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
        page_title = "Edit Wallcovering Vendor"
    else:
        vendor = None
        page_title = "Add Wallcovering Vendor"

    if request.method == "POST":
        if vendor:
            company_name = request.POST.get("company_name", "").strip()
            company_phone = request.POST.get("company_phone", "").strip()
            company_email = request.POST.get("company_email", "").strip()
            vendor.company_name = company_name
            vendor.company_phone = company_phone
            vendor.company_email = company_email
            vendor.save()

        return redirect("wallcovering_home")

    return render(request, "vendor_edit.html", {
        "vendor": vendor,
        "vendor_categories": vendor_categories,
        "page_title": page_title,
    })

def wallcovering_job_tag_print(request, id):
    selected_wallcovering = Wallcovering.objects.get(id=id)

    include_pattern = request.GET.get("include_pattern") == "yes"

    return render(request, "wallcovering_job_tag_print.html", {
        "wallcovering": selected_wallcovering,
        "include_pattern": include_pattern,
    })


def wallcovering_print_labels(request, wallcovering_id):
    wallcovering = get_object_or_404(Wallcovering, id=wallcovering_id)

    if request.method != "POST":
        return redirect("wallcovering_detail", wallcovering_id=wallcovering.id)

    package_ids = request.POST.getlist("package_ids")

    selected_packages = Packages.objects.filter(
        id__in=package_ids,
        orderitem__wallcovering=wallcovering
    ).select_related(
        "delivery",
        "orderitem",
        "orderitem__wallcovering",
        "orderitem__wallcovering__job_number",
        "orderitem__wallcovering__vendor",
    ).order_by(
        "delivery__date",
        "id"
    )

    labels_to_print = []

    for package in selected_packages:
        selected_wallcovering = package.orderitem.wallcovering
        job = selected_wallcovering.job_number

        total_packages = package.quantity_received or 0

        delivery_date = ""
        if package.delivery and package.delivery.date:
            delivery_date = package.delivery.date.strftime("%m/%d/%y")

        contents_notes_parts = []

        if package.contents:
            contents_notes_parts.append(package.contents)

        if package.notes:
            contents_notes_parts.append(package.notes)

        contents_notes = " - ".join(contents_notes_parts)

        contents_line = f"Rec'd {delivery_date}"

        if contents_notes:
            contents_line += f" - {contents_notes}"

        for package_number in range(1, total_packages + 1):
            labels_to_print.append({
                "job_line": f"{job.job_number} {job.job_name}",
                "wallcovering_line": (
                    f"{selected_wallcovering.code or ''} "
                    f"{selected_wallcovering.vendor.company_name if selected_wallcovering.vendor else ''} "
                    f"{selected_wallcovering.pattern or ''}"
                ).strip(),
                "contents_line": contents_line,
                "package_type": package.type or "",
                "package_number": package_number,
                "total_packages": total_packages,
            })

    if not labels_to_print:
        return redirect("wallcovering_detail", wallcovering_id=wallcovering.id)

    return render(request, "wallcovering_label_print.html", {
        "wallcovering": wallcovering,
        "labels_to_print": labels_to_print,
    })




def _wallcovering_quotes_folder(wallcovering_id):
    return os.path.join(settings.MEDIA_ROOT, "wallcovering_quotes", str(wallcovering_id))


def wallcovering_pricing_files(request, wallcovering_id):
    wallcovering = get_object_or_404(Wallcovering, id=wallcovering_id)

    folder = _wallcovering_quotes_folder(wallcovering.id)
    os.makedirs(folder, exist_ok=True)

    files = []
    for file_name in sorted(os.listdir(folder), reverse=True):
        full_path = os.path.join(folder, file_name)
        if not os.path.isfile(full_path):
            continue

        files.append({
            "name": file_name,
            "size": os.path.getsize(full_path),
        })

    explorer_path = rf"\\gp-webserver\trinity\wallcovering_quotes\{wallcovering.id}"

    return JsonResponse({
        "files": files,
        "folder_path": explorer_path,
    })


def wallcovering_pricing_upload(request, wallcovering_id):
    wallcovering = get_object_or_404(Wallcovering, id=wallcovering_id)

    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=405)

    uploaded_file = request.FILES.get("file")
    if not uploaded_file:
        return JsonResponse({"ok": False, "error": "No file uploaded"}, status=400)

    folder = _wallcovering_quotes_folder(wallcovering.id)
    os.makedirs(folder, exist_ok=True)

    original_name = os.path.basename(uploaded_file.name)
    original_base, original_ext = os.path.splitext(original_name)
    requested_name = request.POST.get("file_name", "").strip() or original_base
    requested_base = os.path.splitext(os.path.basename(requested_name))[0] or original_base
    dated_name = f"{date.today().strftime('%m-%d-%Y')} - {requested_base}{original_ext}"
    safe_name = get_valid_filename(dated_name)
    file_path = os.path.join(folder, safe_name)

    base_name, ext = os.path.splitext(safe_name)
    counter = 1
    while os.path.exists(file_path):
        file_path = os.path.join(folder, f"{base_name}_{counter}{ext}")
        counter += 1

    with open(file_path, "wb+") as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)

    return JsonResponse({"ok": True})


def wallcovering_pricing_download(request, wallcovering_id):
    wallcovering = get_object_or_404(Wallcovering, id=wallcovering_id)

    file_name = request.GET.get("file", "").strip()
    if not file_name:
        raise Http404("File not specified")

    safe_name = os.path.basename(file_name)
    folder = _wallcovering_quotes_folder(wallcovering.id)
    file_path = os.path.join(folder, safe_name)

    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        raise Http404("File not found")

    return FileResponse(open(file_path, "rb"), as_attachment=False, filename=safe_name)
