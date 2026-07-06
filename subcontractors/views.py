from console.models import *
from django.shortcuts import render, redirect
import json
from types import SimpleNamespace
from changeorder.views import link_callback
from datetime import datetime,date
from decimal import Decimal, InvalidOperation
from django.core.serializers.json import DjangoJSONEncoder
from employees.views import get_scheduled_toolbox_folder, get_uploaded_toolbox_file
from wallcovering.models import Wallcovering, OrderItems
from subcontractors.models import *
from jobs.models import *
from equipment.filters import SubcontractsFilter
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q, Sum
from django.http import JsonResponse, HttpResponse, FileResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import get_template, render_to_string
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.utils.timezone import now
from django.utils.text import get_valid_filename
from employees.models import *
import datetime
import os
from datetime import date
from console.misc import Email
from dateutil.relativedelta import relativedelta
from xhtml2pdf import pisa
from media.utilities import MediaUtilities
from subcontractors import toolbox_views as sub_toolbox


SUB_RESPIRATOR_SECTION_MODELS = {
    1: RespiratorClearance1,
    2: RespiratorClearance2,
    3: RespiratorClearance3,
    4: RespiratorClearance4,
    5: RespiratorClearance5,
    6: RespiratorClearance6,
}


def _sub_respirator_section_defaults(section_number):
    section_model = SUB_RESPIRATOR_SECTION_MODELS[section_number]
    values = {}

    for field in section_model._meta.fields:
        if field.name in ("id", "main"):
            continue
        values[field.name] = field.get_default()

    return values


def _sub_respirator_section_data(clearance, section_number):
    values = _sub_respirator_section_defaults(section_number)
    saved_values = (clearance.form_data or {}).get(str(section_number), {})
    values.update(saved_values)
    return SimpleNamespace(**values)


def _save_sub_respirator_section(clearance, section_number, post_data):
    allowed_fields = _sub_respirator_section_defaults(section_number).keys()
    form_data = clearance.form_data or {}
    section_data = form_data.get(str(section_number), {})

    for field_name in allowed_fields:
        if field_name in post_data:
            section_data[field_name] = post_data.get(field_name)

    form_data[str(section_number)] = section_data
    clearance.form_data = form_data
    clearance.save(update_fields=["form_data"])


def _duplicate_sub_employee_name(base_name, subcontractor):
    duplicate_name = f"{base_name} 2"
    suffix = 2

    while Subcontractor_Employees.objects.filter(
        subcontractor=subcontractor,
        name__iexact=duplicate_name
    ).exists():
        suffix += 1
        duplicate_name = f"{base_name} {suffix}"

    return duplicate_name


def _complete_subcontractor_toolbox_talk(employee, scheduled_talk, job):
    completed_talk, created = CompletedSubToolboxTalks.objects.get_or_create(
        employee=employee,
        master=scheduled_talk,
        job=job,
        defaults={
            'date': date.today(),
            'is_excused': False,
        }
    )

    if not created and completed_talk.is_excused:
        completed_talk.is_excused = False
        completed_talk.date = date.today()
        completed_talk.save(update_fields=['is_excused', 'date'])

    return completed_talk


def _complete_subcontractor_job_toolbox_talk(scheduled_talk, subcontractor, job):
    completed_talk, created = CompletedSubToolboxJobTalks.objects.get_or_create(
        scheduled=scheduled_talk,
        subcontractor=subcontractor,
        job=job,
        defaults={
            'is_excused': False,
        }
    )

    if not created and completed_talk.is_excused:
        completed_talk.is_excused = False
        completed_talk.save(update_fields=['is_excused'])

    return completed_talk


def _has_sub_employee_toolbox_record(employee, scheduled_talk, job=None):
    query = CompletedSubToolboxTalks.objects.filter(
        employee=employee,
        master=scheduled_talk
    )

    if job is not None:
        query = query.filter(job=job)

    if query.exists():
        return True

    attended_query = CompletedSubToolboxJobTalkEmployees.objects.filter(
        employee=employee,
        completed__scheduled=scheduled_talk,
        completed__is_excused=False
    )

    if job is not None:
        attended_query = attended_query.filter(completed__job=job)

    return attended_query.exists()


def _get_completed_sub_employee_toolbox_talk_ids(employee, assigned_ids, jobs):
    individual_ids = set(
        CompletedSubToolboxTalks.objects
        .filter(
            employee=employee,
            master_id__in=assigned_ids,
            job__in=jobs,
            is_excused=False
        )
        .values_list('master_id', flat=True)
        .distinct()
    )

    attended_group_ids = set(
        CompletedSubToolboxJobTalkEmployees.objects
        .filter(
            employee=employee,
            completed__scheduled_id__in=assigned_ids,
            completed__job__in=jobs,
            completed__is_excused=False
        )
        .values_list('completed__scheduled_id', flat=True)
        .distinct()
    )

    return individual_ids | attended_group_ids


def _get_completed_sub_employee_ids_for_job_talk(scheduled_talk, job, employees):
    individual_ids = set(
        CompletedSubToolboxTalks.objects
        .filter(
            master=scheduled_talk,
            job=job,
            employee__in=employees,
            is_excused=False
        )
        .values_list('employee_id', flat=True)
        .distinct()
    )

    attended_ids = set(
        CompletedSubToolboxJobTalkEmployees.objects
        .filter(
            completed__scheduled=scheduled_talk,
            completed__job=job,
            completed__is_excused=False,
            employee__in=employees
        )
        .values_list('employee_id', flat=True)
        .distinct()
    )

    return individual_ids | attended_ids


def _sub_employee_has_completed_scheduled_talk_anywhere(employee, scheduled_talk):
    if CompletedSubToolboxTalks.objects.filter(
        employee=employee,
        master=scheduled_talk,
        is_excused=False
    ).exists():
        return True

    return CompletedSubToolboxJobTalkEmployees.objects.filter(
        employee=employee,
        completed__scheduled=scheduled_talk,
        completed__is_excused=False
    ).exists()


def _has_sub_job_toolbox_record(scheduled_talk, subcontractor, job):
    return CompletedSubToolboxJobTalks.objects.filter(
        scheduled=scheduled_talk,
        subcontractor=subcontractor,
        job=job
    ).exists()


def _get_first_subcontractor_invoice_date(subcontract):
    return (
        SubcontractorInvoice.objects
        .filter(subcontract=subcontract)
        .order_by('date', 'id')
        .values_list('date', flat=True)
        .first()
    )


def _get_all_employee_toolbox_talks_for_subcontract(subcontract, end_date=None, start_date=None):
    first_invoice_date = _get_first_subcontractor_invoice_date(subcontract)
    if not first_invoice_date:
        return ScheduledToolboxTalks.objects.none()

    query = ScheduledToolboxTalks.objects.filter(
        is_all_employees=True,
        date__isnull=False,
        date__gt=first_invoice_date,
    )

    if end_date is not None:
        query = query.filter(date__lte=end_date)

    if start_date is not None:
        query = query.filter(date__gte=start_date)

    return query


def _get_toolbox_talks_for_delegated_subcontract(subcontract, employee, end_date=None):
    start_date = _sub_employee_assignment_start_date(employee, subcontract)
    if not start_date:
        return ScheduledToolboxTalks.objects.none()

    all_employee_talks = _get_all_employee_toolbox_talks_for_subcontract(
        subcontract,
        end_date=end_date,
        start_date=start_date
    )

    explicit_job_talk_ids = ScheduledToolboxTalkSubJobs.objects.filter(
        subcontractor=subcontract.subcontractor,
        job=subcontract.job_number,
        subcontractor__is_toolbox_required=True,
        scheduled__date__isnull=False,
        scheduled__date__gte=start_date,
    ).values_list('scheduled_id', flat=True)

    explicit_employee_talk_ids = ScheduledToolboxTalkSubEmployees.objects.filter(
        employee=employee,
        job=subcontract.job_number,
        employee__subcontractor__is_toolbox_required=True,
        scheduled__date__isnull=False,
        scheduled__date__gte=start_date,
    ).values_list('scheduled_id', flat=True)

    if end_date is not None:
        explicit_job_talk_ids = explicit_job_talk_ids.filter(scheduled__date__lte=end_date)
        explicit_employee_talk_ids = explicit_employee_talk_ids.filter(scheduled__date__lte=end_date)

    scheduled_ids = set(all_employee_talks.values_list('id', flat=True))
    scheduled_ids.update(explicit_job_talk_ids)
    scheduled_ids.update(explicit_employee_talk_ids)

    return ScheduledToolboxTalks.objects.filter(id__in=scheduled_ids)


def _backfill_delegated_job_toolbox_completions(subcontract):
    assigned_employee_ids = Subcontractor_Job_Assignments.objects.filter(
        job=subcontract.job_number,
        employee__subcontractor=subcontract.subcontractor,
        employee__is_active=True,
        employee__has_access_to_toolbox=True,
        employee__date_enrolled__isnull=False
    ).values_list('employee_id', flat=True)

    assigned_employees = Subcontractor_Employees.objects.filter(
        id__in=assigned_employee_ids
    ).distinct()

    created_count = 0
    today = date.today()

    for employee in assigned_employees:
        scheduled_talks = _get_toolbox_talks_for_delegated_subcontract(
            subcontract,
            employee,
            end_date=today
        )

        for scheduled_talk in scheduled_talks:
            if scheduled_talk.date and employee.date_enrolled > scheduled_talk.date:
                continue

            if CompletedSubToolboxTalks.objects.filter(
                employee=employee,
                master=scheduled_talk,
                job=subcontract.job_number
            ).exists():
                continue

            if not _sub_employee_has_completed_scheduled_talk_anywhere(
                employee,
                scheduled_talk
            ):
                continue

            _complete_subcontractor_toolbox_talk(
                employee,
                scheduled_talk,
                subcontract.job_number
            )
            created_count += 1

    return created_count


def _close_delegated_job_toolbox_completions_before_undelegate(subcontract):
    assigned_employee_ids = Subcontractor_Job_Assignments.objects.filter(
        job=subcontract.job_number,
        employee__subcontractor=subcontract.subcontractor,
        employee__is_active=True,
        employee__has_access_to_toolbox=True,
        employee__date_enrolled__isnull=False
    ).values_list('employee_id', flat=True)

    assigned_employees = Subcontractor_Employees.objects.filter(
        id__in=assigned_employee_ids
    ).distinct()

    if not assigned_employees.exists():
        return 0

    scheduled_ids = set()
    today = date.today()

    for employee in assigned_employees:
        scheduled_ids.update(
            _get_toolbox_talks_for_delegated_subcontract(
                subcontract,
                employee,
                end_date=today
            ).values_list('id', flat=True)
        )

    closed_count = 0

    for scheduled_talk in ScheduledToolboxTalks.objects.filter(id__in=scheduled_ids):
        applicable_employees = assigned_employees.filter(
            date_enrolled__lte=scheduled_talk.date
        )
        if not applicable_employees.exists():
            continue

        employee_ids = set(applicable_employees.values_list('id', flat=True))

        completed_ids = _get_completed_sub_employee_ids_for_job_talk(
            scheduled_talk,
            subcontract.job_number,
            applicable_employees
        )
        excused_ids = set(
            CompletedSubToolboxTalks.objects
            .filter(
                master=scheduled_talk,
                job=subcontract.job_number,
                employee__in=applicable_employees,
                is_excused=True
            )
            .values_list('employee_id', flat=True)
            .distinct()
        )

        if employee_ids - completed_ids - excused_ids:
            continue

        completed_job_talk, created = CompletedSubToolboxJobTalks.objects.get_or_create(
            scheduled=scheduled_talk,
            subcontractor=subcontract.subcontractor,
            job=subcontract.job_number,
            defaults={
                'is_excused': False,
            }
        )

        if not created and completed_job_talk.is_excused:
            completed_job_talk.is_excused = False
            completed_job_talk.save(update_fields=['is_excused'])
            closed_count += 1
        elif created:
            closed_count += 1

    return closed_count


def _complete_attendee_delegated_jobs_for_same_talk(employee, scheduled_talk, completed_job):
    if (
        not employee or
        not employee.has_access_to_toolbox or
        not employee.subcontractor or
        not employee.subcontractor.is_toolbox_required or
        not employee.date_enrolled or
        (scheduled_talk.date and employee.date_enrolled > scheduled_talk.date)
    ):
        return 0

    completed_count = 0
    assigned_jobs = (
        Subcontractor_Job_Assignments.objects
        .filter(
            employee=employee,
            job__is_closed=False,
            job__is_active=True,
            job__is_labor_done=False
        )
        .exclude(job=completed_job)
        .select_related('job')
    )

    for assignment in assigned_jobs:
        subcontract = Subcontracts.objects.filter(
            subcontractor=employee.subcontractor,
            job_number=assignment.job,
            is_closed=False,
            subcontractor__is_toolbox_required=True,
            job_number__is_closed=False,
            job_number__is_active=True,
            job_number__is_labor_done=False
        ).first()

        if not subcontract:
            continue

        if not _subcontractor_employee_delegation_effective(
            employee.subcontractor,
            subcontract,
            scheduled_talk.date
        ):
            continue

        if not _get_toolbox_talks_for_delegated_subcontract(
            subcontract,
            employee,
            end_date=scheduled_talk.date
        ).filter(id=scheduled_talk.id).exists():
            continue

        existing = CompletedSubToolboxTalks.objects.filter(
            employee=employee,
            master=scheduled_talk,
            job=assignment.job
        ).first()

        _complete_subcontractor_toolbox_talk(
            employee,
            scheduled_talk,
            assignment.job
        )

        if not existing or existing.is_excused:
            completed_count += 1

    return completed_count


def _get_subcontractor_employee_delegation(subcontractor, subcontract):
    return SubcontractorEmployeeDelegation.objects.filter(
        subcontractor=subcontractor,
        subcontract=subcontract
    ).first()


def _subcontractor_employee_delegation_effective(subcontractor, subcontract, scheduled_date=None):
    delegation = _get_subcontractor_employee_delegation(subcontractor, subcontract)
    return bool(delegation)


def _sub_employee_assignment_start_date(sub_employee, subcontract):
    return sub_employee.date_enrolled


def _subcontract_has_delegated_employee_for_date(subcontract, scheduled_date):
    if not _subcontractor_employee_delegation_effective(
        subcontract.subcontractor,
        subcontract,
        scheduled_date
    ):
        return False

    return Subcontractor_Job_Assignments.objects.filter(
        job=subcontract.job_number,
        employee__subcontractor=subcontract.subcontractor,
        employee__is_active=True,
        employee__has_access_to_toolbox=True,
        employee__date_enrolled__isnull=False,
        employee__date_enrolled__lte=scheduled_date
    ).exists()


def _subcontractor_portal_tm_ticket_action(changeorder, subcontractor):
    if changeorder.created_by_subcontractor_id != subcontractor.id:
        return None

    if changeorder.need_ticket():
        return "create"

    if not changeorder.needs_ticket_signed():
        return None

    return "sign"


def _get_delegated_active_toolbox_jobs_for_sub_employee(sub_employee, job=None, effective_date=None):
    if (
        not sub_employee.has_access_to_toolbox or
        not sub_employee.subcontractor or
        not sub_employee.subcontractor.is_toolbox_required
    ):
        return []

    assignments = Subcontractor_Job_Assignments.objects.filter(
        employee=sub_employee,
        job__is_closed=False,
        job__is_active=True,
        job__is_labor_done=False
    ).select_related('job')

    if job is not None:
        assignments = assignments.filter(job=job)

    delegated_jobs = []
    seen = set()
    for assignment in assignments:
        subcontract = Subcontracts.objects.filter(
            subcontractor=sub_employee.subcontractor,
            job_number=assignment.job,
            is_closed=False,
            subcontractor__is_toolbox_required=True,
            job_number__is_closed=False,
            job_number__is_active=True,
            job_number__is_labor_done=False
        ).first()

        if not subcontract:
            continue

        if not _subcontractor_employee_delegation_effective(
            subcontractor=sub_employee.subcontractor,
            subcontract=subcontract,
            scheduled_date=effective_date
        ):
            continue

        if assignment.job_id in seen:
            continue
        seen.add(assignment.job_id)
        delegated_jobs.append(assignment.job)

    return delegated_jobs


def wallcovering_subcontract_json(wallcovering):
    def format_yardage(value):
        if value is None:
            return ''
        return f"{Decimal(value):,.2f}".rstrip("0").rstrip(".")

    def join_names(names):
        names = [name for name in names if name]
        if not names:
            return ''
        if len(names) == 1:
            return names[0]
        if len(names) == 2:
            return f"{names[0]} and {names[1]}"
        return f"{', '.join(names[:-1])}, and {names[-1]}"

    vendor = wallcovering.vendor.company_name if wallcovering.vendor else ''
    quantity_ordered = wallcovering.quantity_ordered()
    install_yardage = wallcovering.install_yardage
    estimated_quantity = wallcovering.estimated_quantity
    install_description = wallcovering.code or f"{vendor} {wallcovering.pattern or ''}".strip()
    install_quantity = ''
    already_subcontracted = (
        SubcontractItems.objects
        .filter(
            wallcovering_id=wallcovering,
            SOV_is_lump_sum=False
        )
        .aggregate(total=Sum("SOV_total_ordered"))
        .get("total")
    ) or Decimal("0.00")
    subcontracted_rows = (
        SubcontractItems.objects
        .filter(
            wallcovering_id=wallcovering,
            SOV_is_lump_sum=False
        )
        .values("subcontract__subcontractor__company")
        .annotate(total=Sum("SOV_total_ordered"))
        .order_by("subcontract__subcontractor__company")
    )
    subcontracted_names = [
        row["subcontract__subcontractor__company"]
        for row in subcontracted_rows
        if row["total"]
    ]
    lump_sum_names = list(
        SubcontractItems.objects
        .filter(
            wallcovering_id=wallcovering,
            SOV_is_lump_sum=True
        )
        .select_related("subcontract__subcontractor")
        .values_list("subcontract__subcontractor__company", flat=True)
        .distinct()
        .order_by("subcontract__subcontractor__company")
    )
    has_lump_sum_assignment = bool(lump_sum_names)
    remaining_install_quantity = ''

    if install_yardage:
        install_quantity = f"{install_yardage:.2f}"
    elif quantity_ordered:
        install_quantity = f"{quantity_ordered:.2f}"
    elif estimated_quantity:
        install_quantity = str(estimated_quantity)

    target_quantity = install_yardage or quantity_ordered
    if not target_quantity and estimated_quantity:
        target_quantity = Decimal(str(estimated_quantity))

    if target_quantity and not has_lump_sum_assignment:
        remaining_install_quantity = f"{max(target_quantity - already_subcontracted, Decimal('0.00')):.2f}"

    if install_yardage:
        target_source = "scheduled to install"
    elif quantity_ordered:
        target_source = "ordered"
    elif estimated_quantity:
        target_source = "estimated"
    else:
        target_source = ""

    assignment_parts = []
    if already_subcontracted:
        assignment_parts.append(
            f"{format_yardage(already_subcontracted)} yards has already been assigned to {join_names(subcontracted_names)}"
        )
    if has_lump_sum_assignment:
        assignment_parts.append(
            f"lump sum assigned to {join_names(lump_sum_names)}"
        )

    if target_quantity and assignment_parts:
        helper_text = f"{format_yardage(target_quantity)} yards {target_source}. " + ", and ".join(assignment_parts) + "."
    elif target_quantity:
        helper_text = f"{format_yardage(target_quantity)} yards {target_source}, none has been subcontracted yet."
    elif assignment_parts:
        helper_text = ", and ".join(assignment_parts).capitalize() + "."
    else:
        helper_text = "No install or ordered yardage is available."

    return {
        'id': wallcovering.id,
        'code': wallcovering.code or '',
        'vendor': vendor or '',
        'pattern': wallcovering.pattern or '',
        'estimated_unit': wallcovering.estimated_unit or '',
        'quantity_ordered': f"{quantity_ordered:.2f}" if quantity_ordered else '',
        'install_yardage': f"{install_yardage:.2f}" if install_yardage else '',
        'estimated_quantity': str(estimated_quantity) if estimated_quantity else '',
        'install_description': install_description,
        'install_quantity': install_quantity,
        'remaining_install_quantity': remaining_install_quantity,
        'has_lump_sum_assignment': has_lump_sum_assignment,
        'assignment_helper_text': helper_text,
        'install_unit': wallcovering.ordered_unit() or '',
    }


def _subcontract_files_folder(subcontract_id):
    return os.path.join(settings.MEDIA_ROOT, "subcontracts", str(subcontract_id))


@login_required(login_url='/accounts/login')
def subcontract_files(request, subcontract_id):
    subcontract = get_object_or_404(Subcontracts, id=subcontract_id)

    folder = _subcontract_files_folder(subcontract.id)
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

    explorer_path = rf"\\gp-webserver\trinity\subcontracts\{subcontract.id}"

    return JsonResponse({
        "files": files,
        "folder_path": explorer_path,
    })


@login_required(login_url='/accounts/login')
def subcontract_file_upload(request, subcontract_id):
    subcontract = get_object_or_404(Subcontracts, id=subcontract_id)

    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=405)

    uploaded_file = request.FILES.get("file")
    if not uploaded_file:
        return JsonResponse({"ok": False, "error": "No file uploaded"}, status=400)

    folder = _subcontract_files_folder(subcontract.id)
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


@login_required(login_url='/accounts/login')
def subcontract_file_download(request, subcontract_id):
    subcontract = get_object_or_404(Subcontracts, id=subcontract_id)

    file_name = request.GET.get("file", "").strip()
    if not file_name:
        raise Http404("File not specified")

    safe_name = os.path.basename(file_name)
    folder = _subcontract_files_folder(subcontract.id)
    file_path = os.path.join(folder, safe_name)

    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        raise Http404("File not found")

    return FileResponse(open(file_path, "rb"), as_attachment=False, filename=safe_name)


def sub_change_orders(request):
    send_data = {}
    send_data['unapproved_change_orders'] = SubcontractItems.objects.filter(is_approved=False,
                                                                            subcontract__is_closed=False).order_by(
        'subcontract__subcontractor', 'subcontract')

    return render(request, "sub_change_orders.html", send_data)


def portal(request, sub_id, contract_id):
    send_data = {}
    selected_sub = Subcontractors.objects.get(id=sub_id)
    send_data['selected_sub'] = selected_sub
    outstanding_tm_tickets = 0

    job_numbers = Subcontracts.objects.filter(
        subcontractor=selected_sub,
        is_closed=False
    ).values_list('job_number', flat=True)

    all_changeorders = ChangeOrders.objects.filter(
        job_number__in=job_numbers,
        is_closed=False,
    ).order_by('cop_number').distinct()


    for co in all_changeorders:
        if _subcontractor_portal_tm_ticket_action(co, selected_sub):
            outstanding_tm_tickets += 1

    send_data['outstanding_tm_tickets'] = outstanding_tm_tickets
    subcontracts = []
    if contract_id == 'ALL':
        today = datetime.date.today()
        this_friday = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=4)
        last_saturday = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(
            days=4) - datetime.timedelta(days=6)
        if today.weekday() > 4:
            this_friday += datetime.timedelta(days=7)
            last_saturday += datetime.timedelta(days=7)
        send_data['this_friday'] = this_friday
        send_data['last_saturday'] = last_saturday
        for x in Subcontracts.objects.filter(is_closed=False,
                                             subcontractor=selected_sub):
            total_contract_amount = "$" + f"{int(x.total_contract_amount()):,d}"
            total_billed = "$" + f"{int(x.total_billed()):,d}"
            #
            total_paid ="$" + f"{int(x.total_paid()):,d}"
            pay_amount_this_week="$" + f"{int(x.pay_amount_this_week()):,d}"
            retainage_this_week="$" + f"{0-int(x.retainage_this_week()):,d}"
            approved_this_week="$" + f"{int(x.amount_this_week()):,d}"
            billed_this_week="$" + f"{int(x.original_request()):,d}"
            total_retainage_prior="$" + f"{int(x.total_retainage_prior()):,d}"
            total_billed_prior="$" + f"{int(x.total_billed_prior()):,d}"
            your_retainage = "$" + f"{0-int(x.original_retainage_request()):,d}"
            calculate_total_billed_this_week = int(x.original_request()) - int(x.original_retainage_request())
            total_billed_this_week = "$" + f"{int(calculate_total_billed_this_week):,d}"
            retainage_negative = False
            if float(x.retainage_this_week()) < 0:
                retainage_negative = True
            subcontracts.append({'is_invoiced':x.is_invoiced_this_week(), 'is_approved':x.is_approved_this_week(), 'your_retainage':your_retainage,'total_paid': total_paid, 'pay_amount_this_week': pay_amount_this_week,
                                 'retainage_negative': retainage_negative,
                                 'retainage_this_week': retainage_this_week,
                                 'approved_this_week': approved_this_week, 'billed_this_week': billed_this_week,
                                 'total_retainage_prior': total_retainage_prior,
                                 'total_billed_prior': total_billed_prior, 'invoice_ready': x.invoice_ready(),
                                 'invoice_pending': x.invoice_pending(),
                                 'job_name': x.job_number.job_name,
                                 'job_number': x.job_number.job_number,
                                 'subcontractor': x.subcontractor.company, 'subcontractor_id': x.subcontractor.id,
                                 'po_number': x.po_number, 'id': x.id,
                                 'percent_complete': format(x.percent_complete(), ".0%"),
                                 'total_contract_amount': total_contract_amount, 'total_billed': total_billed,'total_billed_this_week':total_billed_this_week})
        send_data['subcontracts'] = subcontracts
        toolbox_talks_required = sub_toolbox.get_subcontractor_portal_required_talks(
            selected_sub,
            through_date=datetime.date.today()
        )
        send_data['toolbox_talks_required'] = toolbox_talks_required
        send_data['toolbox_talks_required_count'] = len(toolbox_talks_required)
        send_data['sub_employees'] = Subcontractor_Employees.objects.filter(
            subcontractor=selected_sub,
            is_active=True
        ).order_by('name')
    else:
        selected_contract = Subcontracts.objects.get(id=contract_id)
        if SubcontractorInvoice.objects.filter(subcontract=selected_contract, is_sent=False).exists():
            send_data['pending_invoices_exist'] = True
        if selected_contract.percent_complete() >= 1:
            send_data['retainage_allowed']=True
        send_data['selected_contract'] = selected_contract
        invoices=[]
        for x in SubcontractorInvoice.objects.filter(subcontract=selected_contract):
            if x.retainage > 0:
                retainage_positive=True
            else:
                retainage_positive=False
            invoices.append({'invoice':x, 'total_pay_amount': x.final_amount - x.retainage,'retainage_positive':retainage_positive, 'retainage_formatted':"$" + f"{0-int(x.retainage):,d}"})
        invoices = sorted(
            invoices,
            key=lambda x: int(x['invoice'].pay_app_number),
            reverse=True
        )
        send_data['invoices'] = invoices
        items = []
        number_items = 0
        for x in SubcontractItems.objects.filter(subcontract=selected_contract).order_by('id'):
            number_items = number_items + 1
            totalcost = float(x.total_cost())
            totalbilled = float(x.total_billed())
            totalordered = float(x.SOV_total_ordered)
            quantitybilled = float(x.quantity_billed())
            remainingcost = totalcost - totalbilled
            remainingqnty = totalordered - quantitybilled
            if totalcost==0:
                percentage=0
            else:
                percentage = (totalbilled / totalcost) * 100
            totalordered = f"{int(x.SOV_total_ordered):,d}"
            items.append({'is_approved': x.is_approved, 'percentage': str(round(percentage, 2)),
                          'remainingqnty': remainingqnty, 'remainingcost': remainingcost, 'id': x.id,
                          'SOV_description': x.SOV_description, 'SOV_is_lump_sum': x.SOV_is_lump_sum,
                          'SOV_unit': x.SOV_unit, 'SOV_total_ordered': totalordered, 'SOV_rate': x.SOV_rate,
                          'notes': x.notes, 'quantity_billed': float(x.quantity_billed()),
                          'total_billed': round(x.total_billed(), 2), 'total_cost': round(x.total_cost(), 2)})
        send_data['items'] = items

    return render(request, "portal.html", send_data)


def subcontractor_resp_clearance(request, sub_id):
    selected_sub = get_object_or_404(Subcontractors, id=sub_id)

    if request.method == "POST" and request.POST.get("start_clearance"):
        sub_employee = None
        employee_name = (request.POST.get("employee_name") or "").strip()
        sub_employee_id = request.POST.get("sub_employee_id")
        duplicate_choice = request.POST.get("duplicate_choice")
        duplicate_employee_id = request.POST.get("duplicate_employee_id")
        selected_language = request.POST.get("language") if request.POST.get("language") in ("English", "Spanish") else "English"

        if sub_employee_id:
            sub_employee = get_object_or_404(
                Subcontractor_Employees,
                id=sub_employee_id,
                subcontractor=selected_sub
            )
            employee_name = sub_employee.name

        if not sub_employee and not employee_name:
            messages.error(request, "Select an existing employee or type a new employee name.")
            return redirect("subcontractor_resp_clearance", sub_id=selected_sub.id)

        if not sub_employee:
            existing_employee = (
                Subcontractor_Employees.objects
                .filter(subcontractor=selected_sub, name__iexact=employee_name)
                .order_by("-is_active", "id")
                .first()
            )

            if existing_employee and not duplicate_choice:
                clearances = (
                    SubcontractorRespiratorClearance.objects
                    .filter(subcontractor=selected_sub)
                    .select_related("employee", "subcontractor")
                    .order_by("employee_name", "-date_created", "-id")
                )

                return render(request, "sub_respirator_clearance.html", {
                    "selected_sub": selected_sub,
                    "sub_employees": Subcontractor_Employees.objects.filter(
                        subcontractor=selected_sub,
                        is_active=True
                    ).order_by("name"),
                    "clearances": clearances,
                    "duplicate_employee_name": employee_name,
                    "duplicate_employee": existing_employee,
                    "selected_language": selected_language,
                })

            if duplicate_choice == "same":
                sub_employee = get_object_or_404(
                    Subcontractor_Employees,
                    id=duplicate_employee_id,
                    subcontractor=selected_sub
                )
                employee_name = sub_employee.name
            else:
                new_employee_name = employee_name
                if existing_employee:
                    new_employee_name = _duplicate_sub_employee_name(employee_name, selected_sub)

                sub_employee = Subcontractor_Employees.objects.create(
                    subcontractor=selected_sub,
                    name=new_employee_name,
                    date_enrolled=date.today(),
                    is_active=True,
                )
                employee_name = sub_employee.name

        if sub_employee and not sub_employee.is_active:
            sub_employee.is_active = True
            sub_employee.date_enrolled = sub_employee.date_enrolled or date.today()
            sub_employee.save(update_fields=["is_active", "date_enrolled"])

        clearance = SubcontractorRespiratorClearance.objects.create(
            subcontractor=selected_sub,
            employee=sub_employee,
            employee_name=employee_name,
            date_created=date.today(),
            language=selected_language,
        )

        return redirect(
            "subcontractor_resp_clearance_section",
            sub_id=selected_sub.id,
            clearance_id=clearance.id,
            section_number=0
        )

    clearances = (
        SubcontractorRespiratorClearance.objects
        .filter(subcontractor=selected_sub)
        .select_related("employee", "subcontractor")
        .order_by("employee_name", "-date_created", "-id")
    )

    return render(request, "sub_respirator_clearance.html", {
        "selected_sub": selected_sub,
        "sub_employees": Subcontractor_Employees.objects.filter(
            subcontractor=selected_sub,
            is_active=True
        ).order_by("name"),
        "clearances": clearances,
    })


def subcontractor_resp_clearance_section(request, sub_id, clearance_id, section_number):
    selected_sub = get_object_or_404(Subcontractors, id=sub_id)
    clearance = get_object_or_404(
        SubcontractorRespiratorClearance,
        id=clearance_id,
        subcontractor=selected_sub
    )

    section_number = int(section_number)

    if section_number == 0:
        if request.method == "POST":
            clearance.gender = request.POST.get("gender")
            clearance.height = request.POST.get("height")
            clearance.weight = request.POST.get("weight")
            clearance.phone = request.POST.get("phone")
            clearance.birth_date = request.POST.get("birth_date") or None
            clearance.save(update_fields=[
                "gender",
                "height",
                "weight",
                "phone",
                "birth_date",
            ])
            return redirect(
                "subcontractor_resp_clearance_section",
                sub_id=selected_sub.id,
                clearance_id=clearance.id,
                section_number=1
            )

        template_name = "sub_respirator_clearance_section0_spanish.html" if clearance.language == "Spanish" else "sub_respirator_clearance_section0.html"
        return render(request, template_name, {
            "selected_sub": selected_sub,
            "clearance": clearance,
        })

    if section_number not in SUB_RESPIRATOR_SECTION_MODELS:
        messages.error(request, "Respirator clearance section could not be found.")
        return redirect("subcontractor_resp_clearance", sub_id=selected_sub.id)

    if request.method == "POST":
        _save_sub_respirator_section(clearance, section_number, request.POST)

        if section_number == 6:
            clearance.date_completed = date.today()
            clearance.is_physician_required = request.POST.get("physician") == "Yes"
            clearance.is_physician_actually_required = request.POST.get("physician") == "Yes"
            clearance.save(update_fields=[
                "date_completed",
                "is_physician_required",
                "is_physician_actually_required",
            ])

            try:
                Email.sendEmail(
                    "Subcontractor Respirator Clearance Completed",
                    (
                        "Respirator Clearance Completed.\n"
                        f"Subcontractor: {selected_sub.company}\n"
                        f"Employee: {clearance.employee_display_name}"
                    ),
                    ["skip@gerloffpainting.com", "bridgette@gerloffpainting.com"],
                    False,
                    selected_sub.email or "operations@gerloffpainting.com"
                )
            except Exception:
                messages.warning(
                    request,
                    "Respirator clearance was completed, but the notification email could not be sent."
                )

            messages.success(request, "Respirator clearance submitted for approval.")
            return redirect("subcontractor_resp_clearance", sub_id=selected_sub.id)

        return redirect(
            "subcontractor_resp_clearance_section",
            sub_id=selected_sub.id,
            clearance_id=clearance.id,
            section_number=section_number + 1
        )

    template_name = f"sub_respirator_clearance_section{section_number}.html"
    if clearance.language == "Spanish":
        template_name = f"sub_respirator_clearance_section{section_number}_spanish.html"

    return render(request, template_name, {
        "selected_sub": selected_sub,
        "clearance": clearance,
        "part1": _sub_respirator_section_data(clearance, section_number),
    })


def subcontractor_resp_clearance_completed(request, sub_id, clearance_id):
    selected_sub = get_object_or_404(Subcontractors, id=sub_id)
    clearance = get_object_or_404(
        SubcontractorRespiratorClearance,
        id=clearance_id,
        subcontractor=selected_sub
    )

    return render(request, "sub_respirator_clearance_completed.html", {
        "selected_sub": selected_sub,
        "clearance": clearance,
        "main": clearance,
        "part1": _sub_respirator_section_data(clearance, 1),
        "part2": _sub_respirator_section_data(clearance, 2),
        "part3": _sub_respirator_section_data(clearance, 3),
        "part4": _sub_respirator_section_data(clearance, 4),
        "part5": _sub_respirator_section_data(clearance, 5),
        "part6": _sub_respirator_section_data(clearance, 6),
    })


def subcontractor_resp_clearance_review(request, sub_id, clearance_id):
    selected_sub = get_object_or_404(Subcontractors, id=sub_id)
    clearance = get_object_or_404(
        SubcontractorRespiratorClearance,
        id=clearance_id,
        subcontractor=selected_sub
    )

    if request.method == "POST":
        existing_notes = clearance.notes or ""

        if "note" in request.POST:
            note = (request.POST.get("note") or "").strip()
            if note:
                clearance.notes = existing_notes + f"\n{date.today()} - {note}"
                clearance.save(update_fields=["notes"])
            return redirect("subcontractor_resp_clearance_review", sub_id=selected_sub.id, clearance_id=clearance.id)

        if "change_expiration_date" in request.POST:
            old_expiration_date = clearance.date_expires
            new_expiration_date = request.POST.get("expiration_date")
            clearance.date_expires = new_expiration_date or None
            clearance.notes = (
                existing_notes
                + "\n"
                + f"{date.today()} - Expiration date changed from "
                + (old_expiration_date.strftime("%m/%d/%Y") if old_expiration_date else "None")
                + f" to {new_expiration_date}"
            )
            clearance.save(update_fields=["date_expires", "notes"])
            return redirect("subcontractor_resp_clearance_review", sub_id=selected_sub.id, clearance_id=clearance.id)

        if request.POST.get("submit_status") == "Approved":
            clearance.approved_for_use = True
            clearance.date_approved = date.today()
            clearance.date_expires = date.today() + relativedelta(years=1)

            if request.POST.get("is_physician_required") == "Yes":
                clearance.is_physician_actually_required = True
                clearance.physician_approved = True
            else:
                clearance.is_physician_actually_required = False
                clearance.physician_approved = False

            clearance.notes = existing_notes + f"\n{date.today()} - Approved for Respirator Use"
            clearance.save()
        else:
            if request.POST.get("is_physician_required") == "No":
                clearance.is_physician_actually_required = False
            if request.POST.get("is_physician_required") == "Yes":
                clearance.is_physician_actually_required = True

            clearance.notes = (
                existing_notes
                + "\n"
                + f"{date.today()} - Not Approved Yet. "
                + f"Physician Required? - {request.POST.get('is_physician_required')}. "
                + f"Physician Approved? - {request.POST.get('physician_approved')}"
            )
            clearance.save()

        return redirect("safety_home")

    respirator_sections = [
        (f"Section {section_number}", bool((clearance.form_data or {}).get(str(section_number))))
        for section_number in range(1, 7)
    ]
    sections_completed = sum(1 for section_name, is_complete in respirator_sections if is_complete)
    total_sections = len(respirator_sections)

    return render(request, "sub_respirator_clearance_review.html", {
        "selected_sub": selected_sub,
        "clearance": clearance,
        "respirator_sections": respirator_sections,
        "sections_completed": sections_completed,
        "total_sections": total_sections,
        "not_completed_yet": not bool(clearance.date_completed),
        "approved_for_use": clearance.approved_for_use,
        "notes": [line for line in (clearance.notes or "").splitlines() if line.strip()],
    })


def connect(request):
    send_data = {}
    if request.method == 'POST':
        send_data = {}
        if 'login_now' in request.POST:
            username = request.POST['username'].strip()
            password = request.POST['password']
            selected_sub = Subcontractors.objects.filter(username__iexact=username, password=password).first()
            if selected_sub:
                return redirect('portal', sub_id=selected_sub.id, contract_id='ALL')

            selected_employee = Subcontractor_Employees.objects.filter(
                username__iexact=username,
                password1=password
            ).first()
            if selected_employee:
                return redirect('subcontractor_employee_portal', employee_id=selected_employee.id)

            send_data['message'] = "Username or password not valid"
            return render(request, "portal_registration.html", send_data)

        if 'enter_pin' in request.POST:
            send_data['enter_pin'] = True
            return render(request, "portal_registration.html", send_data)
        if 'pin' in request.POST:
            if Subcontractors.objects.filter(pin=request.POST['pin']).exists():
                selected_sub = Subcontractors.objects.get(pin=request.POST['pin'])
                if selected_sub.username:
                    send_data['message'] = "Someone has already registered with that PIN"
                    send_data['enter_pin'] = True
                else:
                    send_data['selected_sub'] = selected_sub
                    send_data['register_now'] = True
            else:
                send_data['message'] = "PIN NOT CORRECT"
                send_data['enter_pin'] = True
            return render(request, "portal_registration.html", send_data)
        if 'new_username' in request.POST:
            selected_sub = Subcontractors.objects.get(id=request.POST['selected_sub'])
            new_username = request.POST['new_username'].strip()
            username_exists_in_subcontractors = Subcontractors.objects.filter(
                username__iexact=new_username
            ).exclude(id=selected_sub.id).exists()
            username_exists_in_employees = Subcontractor_Employees.objects.filter(
                username__iexact=new_username
            ).exists()
            username_exists_in_django_users = User.objects.filter(
                username__iexact=new_username
            ).exists()

            if username_exists_in_subcontractors or username_exists_in_employees or username_exists_in_django_users:
                send_data['message'] = "That Username has already been used"
                send_data['selected_sub'] = selected_sub
                send_data['register_now'] = True
                return render(request, "portal_registration.html", send_data)
            else:
                selected_sub.username = new_username
                selected_sub.password = request.POST['password']
                selected_sub.save()
                return redirect('portal', sub_id=selected_sub.id, contract_id='ALL')
    return render(request, "portal_registration.html", send_data)


@login_required(login_url='/accounts/login')
def subcontractor_invoice_new(request, subcontract_id):
    today = datetime.date.today()
    friday = today + datetime.timedelta((4 - today.weekday()) % 7)
    if today.weekday() == 4 or today.weekday() == 3 or today.weekday() == 2: friday = friday + timedelta(7)
    subcontract = Subcontracts.objects.get(id=subcontract_id)
    items = []
    for x in SubcontractItems.objects.filter(subcontract=subcontract).select_related("wallcovering_id").order_by('id'):
        totalcost = float(x.total_cost())
        totalbilled = float(x.total_billed())
        totalbilledandpending = float(x.total_billed_and_pending())
        totalordered = float(x.SOV_total_ordered)
        quantitybilled = float(x.quantity_billed())
        quantitybilledandpending = float(x.quantity_billed_and_pending())
        remainingcost = totalcost - totalbilled
        remainingqnty = totalordered - quantitybilled
        if x.SOV_is_lump_sum == True:
            #1
            # items.append({'is_approved': x.is_approved, 'remainingqnty': remainingqnty, 'remainingcost': remainingcost,
            #               'id': x.id,
            #               'SOV_description': x.SOV_description, 'SOV_is_lump_sum': x.SOV_is_lump_sum,
            #               'SOV_unit': x.SOV_unit, 'SOV_total_ordered': x.SOV_total_ordered, 'SOV_rate': x.SOV_rate,
            #               'notes': x.notes, 'quantity_billed': float(x.quantity_billed()),
            #               'total_billed': round(x.total_billed(), 2), 'total_cost': round(x.total_cost(), 2)})
            items.append({'is_approved': x.is_approved, 'remainingqnty': remainingqnty, 'remainingcost': remainingcost,
                          'id': x.id,
                          'SOV_description': x.SOV_description, 'SOV_is_lump_sum': x.SOV_is_lump_sum,
                          'SOV_unit': x.SOV_unit, 'SOV_total_ordered': x.SOV_total_ordered, 'SOV_rate': x.SOV_rate,
                          'notes': x.notes, 'quantity_billed': float(x.quantity_billed_and_pending()),
                          'total_billed': round(x.total_billed_and_pending(), 2), 'total_cost': round(x.total_cost(), 2)})
        else:
            # items.append({'is_approved': x.is_approved, 'remainingqnty': remainingqnty, 'remainingcost': remainingcost,
            #               'id': x.id,
            #               'SOV_description': x.SOV_description, 'SOV_is_lump_sum': x.SOV_is_lump_sum,
            #               'SOV_unit': x.SOV_unit, 'SOV_total_ordered': x.SOV_total_ordered, 'SOV_rate': x.SOV_rate,
            #               'notes': x.notes, 'quantity_billed': int(x.quantity_billed()),
            #               'total_billed': round(x.total_billed(), 2), 'total_cost': round(x.total_cost(), 2)})
            items.append({'is_approved': x.is_approved, 'remainingqnty': remainingqnty, 'remainingcost': remainingcost,
                          'id': x.id,
                          'SOV_description': x.SOV_description, 'SOV_is_lump_sum': x.SOV_is_lump_sum,
                          'SOV_unit': x.SOV_unit, 'SOV_total_ordered': x.SOV_total_ordered, 'SOV_rate': x.SOV_rate,
                          'notes': x.notes, 'quantity_billed': int(x.quantity_billed_and_pending()),
                          'total_billed': round(x.total_billed_and_pending(), 2), 'total_cost': round(x.total_cost(), 2)})
    if SubcontractorInvoice.objects.filter(subcontract=subcontract).exists():
        next_number = SubcontractorInvoice.objects.filter(subcontract=subcontract).latest(
            'pay_app_number').pay_app_number + 1
    else:
        next_number = 1
    if request.method == 'POST':
        if 'subcontract_note' in request.POST:
            if SubcontractorInvoice.objects.filter(subcontract=subcontract, is_sent=False).exists():
                check_function = False
                for x in SubcontractorInvoice.objects.filter(subcontract=subcontract, is_sent=False):
                    if x.pay_app_number == next_number:
                        check_function = True
                if check_function:
                    return redirect('subcontract_invoices', subcontract_id=subcontract_id, item_id='ALL')
            current_job = subcontract.job_number
            current_job.is_active = True
            current_job.save()
            invoice_total = 0
            if subcontract.job_number.is_wage_scale:
                if not subcontract.is_certified_payroll_email_sent:
                    email_body = "New Subcontractor Invoice on a Certified Payroll Job! " + str(
                        subcontract.subcontractor.company) + "\n Job: " + str(
                        subcontract.job_number.job_name)
                    check_sender = Employees.objects.filter(user=request.user).first() if request.user.is_authenticated else None
                    sender = check_sender.email if check_sender else "operations@gerloffpainting.com"
                    try:
                        Email.sendEmail("New Sub Invoice on Certified Payroll Job", email_body,
                                        ['admin2@gerloffpainting.com', 'bridgette@gerloffpainting.com', 'joe@gerloffpainting.com'],
                                        False,sender)
                        success = True
                        subcontract.is_certified_payroll_email_sent = True
                        subcontract.save()
                    except:
                        success = False
            invoice = SubcontractorInvoice.objects.create(date=date.today(), pay_app_number=next_number,
                                                          subcontract=subcontract, pay_date=friday)
            for x in SubcontractItems.objects.filter(subcontract=subcontract, is_approved=True):
                if request.POST['quantity' + str(x.id)] != '':
                    SubcontractorInvoiceItem.objects.create(invoice=invoice, sov_item=x,
                                                            quantity=request.POST['quantity' + str(x.id)],
                                                            notes=request.POST['note' + str(x.id)])
                    SubcontractorOriginalInvoiceItem.objects.create(invoice=invoice, sov_item=x,
                                                                    quantity=request.POST['quantity' + str(x.id)],
                                                                    notes=request.POST['note' + str(x.id)])
                    current_job = subcontract.job_number
                    current_job.is_active = True
                    current_job.save()
                # elif request.POST['note' + str(x.id)] != '':
                #     SubcontractorInvoiceItem.objects.create(invoice=invoice, sov_item=x, quantity=0,
                #                                             notes=request.POST['note' + str(x.id)])
                #     SubcontractorOriginalInvoiceItem.objects.create(invoice=invoice, sov_item=x,
                #                                                     quantity=request.POST['quantity' + str(x.id)],
                #                                                     notes=request.POST['note' + str(x.id)])
            SubcontractNotes.objects.create(subcontract=subcontract, date=date.today(),
                                            user=Employees.objects.get(user=request.user),
                                            note="New Invoice- " + request.POST['subcontract_note'], invoice=invoice)
            # Email.sendEmail('test', 'test body', 'joe@gerloffpainting.com')

            for x in SubcontractorInvoiceItem.objects.filter(invoice=invoice):
                invoice_total += x.total_cost()
            invoice.final_amount = invoice_total
            invoice.original_amount = invoice_total
            if subcontract.is_retainage == True:
                invoice.retainage = invoice_total * subcontract.retainage_percentage
            else:
                invoice.retainage = 0

            # invoice.final_amount = invoice_total
            # if invoice.subcontract.is_retainage: invoice.retainage = float(invoice_total) * float(.1)
            invoice.save()
            approver_employee_ids = set()

            # Employees directly linked as subcontract approvers
            approver_employee_ids.update(
                Subcontract_Approvers.objects
                .filter(subcontract=subcontract, employee__isnull=False)
                .values_list("employee_id", flat=True)
            )

            # Add job superintendent only if Superintendent is a required approver role
            superintendent_required = Subcontract_Approvers.objects.filter(
                subcontract=subcontract,
                job_description="Superintendent"
            ).exists()

            if superintendent_required and subcontract.job_number.superintendent_id:
                approver_employee_ids.add(subcontract.job_number.superintendent_id)

            # Create InvoiceApprovals without duplicates
            InvoiceApprovals.objects.bulk_create([
                InvoiceApprovals(
                    invoice=invoice,
                    employee_id=employee_id,
                )
                for employee_id in approver_employee_ids
            ])
            return redirect('subcontract_invoices', subcontract_id=subcontract_id, item_id='ALL')
    return render(request, "subcontractor_invoice_new.html",
                  {'next_number': next_number, 'items': items, 'subcontract': subcontract})


def portal_invoice_new(request, subcontract_id):
    today = datetime.date.today()
    friday = today + datetime.timedelta((4 - today.weekday()) % 7)
    if today.weekday() == 4 or today.weekday() == 3 or today.weekday() == 2: friday = friday + timedelta(7)
    subcontract = Subcontracts.objects.get(id=subcontract_id)
    if SubcontractorInvoice.objects.filter(subcontract=subcontract).exists():
        next_number = SubcontractorInvoice.objects.filter(subcontract=subcontract).latest(
            'pay_app_number').pay_app_number + 1
    else:
        next_number = 1
    if request.method == 'POST':
        # return redirect('portal', sub_id=subcontract.subcontractor.id, contract_id=subcontract_id)
        # if SubcontractorInvoice.objects.filter(subcontract=subcontract, is_sent=False).exists():
        #     return redirect('portal', sub_id=subcontract.subcontractor.id, contract_id=subcontract_id)
        if 'retainage_request' in request.POST:
            if SubcontractorInvoice.objects.filter(subcontract=subcontract, is_sent=False).exists():
                return redirect('portal', sub_id=subcontract.subcontractor.id, contract_id=subcontract_id)
            current_job = subcontract.job_number
            current_job.is_active = True
            current_job.save()
            total_retainage= float(subcontract.total_retainage())
            if subcontract.job_number.is_wage_scale:
                if not subcontract.is_certified_payroll_email_sent:
                    email_body = "New Subcontractor Invoice on a Certified Payroll Job! " + str(
                        subcontract.subcontractor.company) + "\n Job: " + str(
                        subcontract.job_number.job_name)
                    check_sender = Employees.objects.filter(user=request.user).first() if request.user.is_authenticated else None
                    sender = check_sender.email if check_sender else "operations@gerloffpainting.com"
                    try:
                        Email.sendEmail("New Sub Invoice on Certified Payroll Job", email_body,
                                        ['admin2@gerloffpainting.com', 'bridgette@gerloffpainting.com', 'joe@gerloffpainting.com'],
                                        False,sender)
                        success = True
                        subcontract.is_certified_payroll_email_sent = True
                        subcontract.save()
                    except:
                        success = False
            invoice = SubcontractorInvoice.objects.create(date=date.today(), pay_app_number=next_number,
                                                          subcontract=subcontract, pay_date=friday, original_amount=0, final_amount=0, retainage=0-total_retainage, original_retainage_amount=0-total_retainage, is_release_retainage=True,release_retainage=total_retainage,retainage_note="Requested from portal")
            SubcontractNotes.objects.create(subcontract=subcontract, date=date.today(),
                                            user=Employees.objects.get(id=42),
                                            note="Retainage Request From Portal",
                                            invoice=invoice)

            approver_employee_ids = set()

            # Employees directly linked as subcontract approvers
            approver_employee_ids.update(
                Subcontract_Approvers.objects
                .filter(subcontract=subcontract, employee__isnull=False)
                .values_list("employee_id", flat=True)
            )

            # Add job superintendent only if Superintendent is a required approver role
            superintendent_required = Subcontract_Approvers.objects.filter(
                subcontract=subcontract,
                job_description="Superintendent"
            ).exists()

            if superintendent_required and subcontract.job_number.superintendent_id:
                approver_employee_ids.add(subcontract.job_number.superintendent_id)

            # Create InvoiceApprovals without duplicates
            InvoiceApprovals.objects.bulk_create([
                InvoiceApprovals(
                    invoice=invoice,
                    employee_id=employee_id,
                )
                for employee_id in approver_employee_ids
            ])

            email_body = "Retainage Request Entered For " + str(subcontract.subcontractor.company) + "\n Job: " + str(
                subcontract.job_number.job_name)
            check_sender = Employees.objects.filter(user=request.user).first() if request.user.is_authenticated else None
            sender = check_sender.email if check_sender else "operations@gerloffpainting.com"
            try:
                Email.sendEmail("New Retainage Request", email_body,
                                ['admin2@gerloffpainting.com', 'bridgette@gerloffpainting.com'],
                                False,sender)
                success = True
            except:
                success = False
            return redirect('portal', sub_id=subcontract.subcontractor.id, contract_id=subcontract_id)
    items = []
    for x in SubcontractItems.objects.filter(subcontract=subcontract).order_by('id'):
        totalcost = float(x.total_cost())
        totalbilled = float(x.total_billed())
        totalordered = float(x.SOV_total_ordered)
        quantitybilled = float(x.quantity_billed())
        remainingcost = totalcost - totalbilled
        remainingqnty = totalordered - quantitybilled
        if x.SOV_is_lump_sum == True:
            items.append({'is_approved': x.is_approved, 'remainingqnty': remainingqnty, 'remainingcost': remainingcost,
                          'id': x.id,
                          'SOV_description': x.SOV_description, 'SOV_is_lump_sum': x.SOV_is_lump_sum,
                          'SOV_unit': x.SOV_unit, 'SOV_total_ordered': x.SOV_total_ordered, 'SOV_rate': x.SOV_rate,
                          'notes': x.notes, 'quantity_billed': float(x.quantity_billed()),
                          'total_billed': round(x.total_billed(), 2), 'total_cost': round(x.total_cost(), 2)})
        else:
            items.append({'is_approved': x.is_approved, 'remainingqnty': remainingqnty, 'remainingcost': remainingcost,
                          'id': x.id,
                          'SOV_description': x.SOV_description, 'SOV_is_lump_sum': x.SOV_is_lump_sum,
                          'SOV_unit': x.SOV_unit, 'SOV_total_ordered': x.SOV_total_ordered, 'SOV_rate': x.SOV_rate,
                          'notes': x.notes, 'quantity_billed': int(x.quantity_billed()),
                          'total_billed': round(x.total_billed(), 2), 'total_cost': round(x.total_cost(), 2)})

    if request.method == 'POST':
        if 'subcontract_note' in request.POST:
            if SubcontractorInvoice.objects.filter(subcontract=subcontract, is_sent=False).exists():
                return redirect('portal', sub_id=subcontract.subcontractor.id, contract_id=subcontract_id)
            invoice_total = 0
            if subcontract.job_number.is_wage_scale:
                if not subcontract.is_certified_payroll_email_sent:
                    email_body = "New Subcontractor Invoice on a Certified Payroll Job! " + str(
                        subcontract.subcontractor.company) + "\n Job: " + str(
                        subcontract.job_number.job_name)
                    check_sender = Employees.objects.filter(user=request.user).first() if request.user.is_authenticated else None
                    sender = check_sender.email if check_sender else "operations@gerloffpainting.com"
                    try:
                        Email.sendEmail("New Sub Invoice on Certified Payroll Job", email_body,
                                        ['admin2@gerloffpainting.com', 'bridgette@gerloffpainting.com', 'joe@gerloffpainting.com'],
                                        False,sender)
                        success = True
                        subcontract.is_certified_payroll_email_sent = True
                        subcontract.save()
                    except:
                        success = False
            invoice = SubcontractorInvoice.objects.create(date=date.today(), pay_app_number=next_number,
                                                          subcontract=subcontract, pay_date=friday)
            for x in SubcontractItems.objects.filter(subcontract=subcontract, is_approved=True):
                if request.POST['quantity' + str(x.id)] != '':
                    SubcontractorInvoiceItem.objects.create(invoice=invoice, sov_item=x,
                                                            quantity=request.POST['quantity' + str(x.id)],
                                                            notes=request.POST['note' + str(x.id)])
                    SubcontractorOriginalInvoiceItem.objects.create(invoice=invoice, sov_item=x,
                                                                    quantity=request.POST['quantity' + str(x.id)],
                                                                    notes=request.POST['note' + str(x.id)])
                    current_job = subcontract.job_number
                    current_job.is_active = True
                    current_job.save()
                    # if x.SOV_is_lump_sum:
                    #     invoice_total += float(request.POST['quantity' + str(x.id)])
                    # else:
                    #     invoice_total += float(request.POST['quantity' + str(x.id)]) * x.SOV_rate
                elif request.POST['note' + str(x.id)] != '':
                    SubcontractorInvoiceItem.objects.create(invoice=invoice, sov_item=x, quantity=0,
                                                            notes=request.POST['note' + str(x.id)])
                    SubcontractorOriginalInvoiceItem.objects.create(invoice=invoice, sov_item=x,
                                                                    quantity=request.POST['quantity' + str(x.id)],
                                                                    notes=request.POST['note' + str(x.id)])
                    current_job = subcontract.job_number
                    current_job.is_active = True
                    current_job.save()
            SubcontractNotes.objects.create(subcontract=subcontract, date=date.today(),
                                            user=Employees.objects.get(id=42),
                                            note="New Invoice From Portal- " + request.POST['subcontract_note'],
                                            invoice=invoice)
            for x in SubcontractorInvoiceItem.objects.filter(invoice=invoice):
                invoice_total += x.total_cost()
            invoice.final_amount = invoice_total
            invoice.original_amount = invoice_total
            if subcontract.is_retainage == True:
                invoice.retainage = invoice_total * subcontract.retainage_percentage
                invoice.original_retainage_amount = invoice_total * subcontract.retainage_percentage
            else:
                invoice.retainage = 0
                invoice.original_retainage_amount = 0
            # # Email.sendEmail('test', 'test body', 'joe@gerloffpainting.com')
            # invoice.final_amount = invoice_total
            # if invoice.subcontract.is_retainage: invoice.retainage = float(invoice_total) * float(.1)
            invoice.save()
            approver_employee_ids = set()

            # Employees directly linked as subcontract approvers
            approver_employee_ids.update(
                Subcontract_Approvers.objects
                .filter(subcontract=subcontract, employee__isnull=False)
                .values_list("employee_id", flat=True)
            )

            # Add job superintendent only if Superintendent is a required approver role
            superintendent_required = Subcontract_Approvers.objects.filter(
                subcontract=subcontract,
                job_description="Superintendent"
            ).exists()

            if superintendent_required and subcontract.job_number.superintendent_id:
                approver_employee_ids.add(subcontract.job_number.superintendent_id)

            # Create InvoiceApprovals without duplicates
            InvoiceApprovals.objects.bulk_create([
                InvoiceApprovals(
                    invoice=invoice,
                    employee_id=employee_id,
                )
                for employee_id in approver_employee_ids
            ])
            email_body = "New Invoice Entered For " + str(subcontract.subcontractor.company) + "\n Job: " + str(
                subcontract.job_number.job_name)
            check_sender = Employees.objects.filter(user=request.user).first() if request.user.is_authenticated else None
            sender = check_sender.email if check_sender else "operations@gerloffpainting.com"
            try:
                Email.sendEmail("New invoice", email_body,
                                ['admin2@gerloffpainting.com', 'bridgette@gerloffpainting.com'],
                                False,sender)
                success = True
            except:
                success = False
            return redirect('portal', sub_id=subcontract.subcontractor.id, contract_id=subcontract_id)
    return render(request, "portal_invoice_new.html",
                  {'friday': friday, 'next_number': next_number, 'items': items, 'subcontract': subcontract})


@login_required(login_url='/accounts/login')
def subcontract_invoices(request, subcontract_id, item_id):
    send_data = {}
    subcontract = Subcontracts.objects.get(id=subcontract_id)
    send_data['subcontract'] = subcontract
    note2 = ""
    current_employee = Employees.objects.get(user=request.user)
    if item_id != 'ALL':
        selected_invoice = SubcontractorInvoice.objects.get(id=item_id)
        approvers = InvoiceApprovals.objects.filter(invoice=selected_invoice)
    if request.method == 'POST':
        if 'sync_subcontract_approvers' in request.POST:
            added_count = 0
            skipped_count = 0

            for approver in Subcontract_Approvers.objects.filter(subcontract=subcontract):

                employee_to_add = None

                if approver.employee:
                    employee_to_add = approver.employee

                elif approver.job_description == "Superintendent":
                    employee_to_add = subcontract.job_number.superintendent

                if employee_to_add:
                    already_exists = InvoiceApprovals.objects.filter(
                        invoice=selected_invoice,
                        employee=employee_to_add
                    ).exists()

                    if not already_exists:
                        InvoiceApprovals.objects.create(
                            invoice=selected_invoice,
                            employee=employee_to_add,
                            is_reviewed=False,
                            is_approved=False,
                            made_changes=False,
                            notes="Added from Subcontract Approvers"
                        )
                        added_count += 1
                    else:
                        skipped_count += 1
                else:
                    skipped_count += 1

            SubcontractNotes.objects.create(
                subcontract=subcontract,
                date=date.today(),
                user=current_employee,
                note=f"Synced subcontract approvers to invoice. {added_count} approver(s) added. {skipped_count} skipped.",
                invoice=selected_invoice
            )

            return redirect(request.path)

        if 'edit_invoice' in request.POST:
            send_data['edit_now'] = True
        if 'other_approver' in request.POST:
            send_data['other_approve'] = InvoiceApprovals.objects.get(id=request.POST['other_approver'])
        if 'invoice_notes' in request.POST:
            SubcontractNotes.objects.create(subcontract=subcontract, date=date.today(),
                                            user=Employees.objects.get(user=request.user),
                                            note=request.POST['invoice_notes'], invoice=selected_invoice)
        if 'change_notes' in request.POST:  # could be approved with changes or editing invoice
            note2 = ""
            if 'change_notes' in request.POST: note2 += request.POST['change_notes'] + ". "
            if 'retainage_adjust' in request.POST:
                selected_invoice.is_release_retainage = True
                selected_invoice.release_retainage = request.POST['retainage_adjust']
                selected_invoice.retainage_note = request.POST['retainage_note']
                note2 += "Retainage changed from " + str(selected_invoice.retainage) + " to " + str(
                    request.POST['this_retainage']) + ". " + request.POST['retainage_note'] + ". "
            selected_invoice.retainage = request.POST['this_retainage']
            for x in SubcontractItems.objects.filter(subcontract=subcontract):
                if request.POST['quantity' + str(x.id)] != '':
                    if SubcontractorInvoiceItem.objects.filter(invoice=selected_invoice, sov_item=x).exists():
                        item = SubcontractorInvoiceItem.objects.get(invoice=selected_invoice, sov_item=x)
                        if float(item.quantity) != float(request.POST['quantity' + str(x.id)]):
                            note2 += x.SOV_description + "- changed from " + str(item.quantity) + " to " + str(
                                request.POST['quantity' + str(x.id)]) + ". "
                        item.quantity = request.POST['quantity' + str(x.id)]
                        item.notes = request.POST['note' + str(x.id)]
                        item.save()
                    else:
                        SubcontractorInvoiceItem.objects.create(invoice=selected_invoice, sov_item=x,
                                                                quantity=request.POST['quantity' + str(x.id)],
                                                                notes=request.POST['note' + str(x.id)])
                        note2 += x.SOV_description + "- added to invoice. Quantity: " + str(
                            request.POST['quantity' + str(x.id)]) + ". "
                else:
                    if SubcontractorInvoiceItem.objects.filter(invoice=selected_invoice, sov_item=x).exists():
                        item = SubcontractorInvoiceItem.objects.get(invoice=selected_invoice, sov_item=x)
                        if item.quantity != 0:
                            note2 += x.SOV_description + "- changed from " + str(item.quantity) + " to 0. "
                        item.quantity = 0
                        item.notes = request.POST['note' + str(x.id)]
                        item.save()
        if 'approved' in request.POST or 'change_notes' in request.POST:  # invoice is approved
            invoicetotal = 0
            for x in SubcontractorInvoiceItem.objects.filter(invoice=selected_invoice):
                invoicetotal = invoicetotal + x.total_cost()
            selected_invoice.final_amount = invoicetotal
        if ('approved' in request.POST) or ('approved_with_changes' in request.POST) or (
                'reject_notes' in request.POST):
            approved = True
            if 'is_other_approver_id' in request.POST:
                other_approval = InvoiceApprovals.objects.get(id=request.POST['is_other_approver_id'])
                current_employee = other_approval.employee
            for x in approvers:
                if x.employee == current_employee:
                    x.date = date.today()
                    x.is_reviewed = True
                    if 'approved' in request.POST:
                        x.is_approved = True
                        x.made_changes = False
                    if 'approved_with_changes' in request.POST:
                        x.is_approved = True
                        x.made_changes = False
                    if 'reject_notes' in request.POST:
                        x.is_approved = False
                        x.made_changes = False
                        approved = False
                    x.save()
                elif x.is_approved == False:
                    approved = False
            if approved == True:
                selected_invoice.is_sent = True
                email_body = selected_invoice.subcontract.subcontractor.company + " invoice for " + selected_invoice.subcontract.job_number.job_name + " has been approved."
                check_sender = Employees.objects.filter(user=request.user).first() if request.user.is_authenticated else None
                sender = check_sender.email if check_sender else "operations@gerloffpainting.com"
                try:
                    Email.sendEmail("Invoice Approved", email_body,
                                    ['admin2@gerloffpainting.com', 'bridgette@gerloffpainting.com'], False,sender)
                    success = True
                except:
                    success = False
            # this is the new part 4.14.24 that emails victor after supers approve
            today = datetime.date.today()
            this_friday = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=4)
            ready_for_victor = True
            ready_for_gene = True
            late_invoices_ready_for_victor = True
            late_invoices_ready_for_gene = True
            late_invoices_remaining = 0
            if InvoiceApprovals.objects.filter(is_approved=False, invoice__pay_date__gt=this_friday).exists():
                current_invoices_remaining = InvoiceApprovals.objects.filter(is_approved=False,
                                                                             invoice__pay_date__gt=this_friday).count()
            if InvoiceApprovals.objects.filter(is_approved=False, invoice__pay_date__lte=this_friday).exists():
                current_invoices_remaining = InvoiceApprovals.objects.filter(is_approved=False,
                                                                             invoice__pay_date__lte=this_friday).count()
            if selected_invoice.pay_date == this_friday:
                if InvoiceApprovals.objects.filter(is_approved=False, invoice__pay_date__lte=this_friday).exists():
                    for x in InvoiceApprovals.objects.filter(is_approved=False, invoice__pay_date__lte=this_friday):
                        if x.employee.job_title.description == "Superintendent" and x.employee.first_name != "Victor":
                            ready_for_victor = False
                            ready_for_gene = False
                        if x.employee.first_name == "Victor":
                            ready_for_gene = False
                    this_week_status = Weekly_Approvals.objects.latest('id')
                    if ready_for_victor == True:
                        if this_week_status.victor_email_sent == False:

                            if InvoiceApprovals.objects.filter(is_approved=False, invoice__pay_date__lte=this_friday,
                                                               employee__first_name="Victor").exists():
                                try:
                                    message = "Subcontractor Invoices are Ready for Victor Approval. There are " + str(
                                        late_invoices_remaining) + " Late Invoices that still need approval!"

                                    # Email.sendEmail("Invoices Ready For Approval",
                                    #                 message,
                                    #                 ['joe@gerloffpainting.com', 'bridgette@gerloffpainting.com',
                                    #                  'admin2@gerloffpainting.com', 'victor@gerloffpainting.com'],
                                    #                 False)
                                    success = True
                                    this_week_status.victor_email_sent = True
                                    this_week_status.save()
                                except:
                                    success = False
                    if ready_for_gene == True:
                        if this_week_status.gene_email_sent == False:
                            if InvoiceApprovals.objects.filter(is_approved=False, invoice__pay_date__lte=this_friday,
                                                               employee__first_name="Gene").exists():
                                try:
                                    message = "Subcontractor Invoices are Ready for Gene Approval. There are " + str(
                                        late_invoices_remaining) + " Late Invoices that still need approval!"
                                    # Email.sendEmail("Invoices Ready For Approval",
                                    #                 message,
                                    #                 ['joe@gerloffpainting.com', 'bridgette@gerloffpainting.com',
                                    #                  'admin2@gerloffpainting.com', 'gene@gerloffpainting.com'],
                                    #                 False)
                                    this_week_status.gene_email_sent = True
                                    this_week_status.save()
                                    success = True
                                except:
                                    success = False
                                this_week_status.gene_email_sent = True
                                this_week_status.save()

                else:
                    try:
                        # Email.sendEmail("All Invoices are Approved",
                        #                 "All Invoices that were turned in on time, are approved",
                        #                 ['joe@gerloffpainting.com', 'bridgette@gerloffpainting.com',
                        #                  'admin2@gerloffpainting.com', 'gene@gerloffpainting.com',
                        #                  'victor@gerloffpainting.com'], False)
                        success = True
                    except:
                        success = False
            else:
                ready_for_victor = True
                ready_for_gene = True
                if InvoiceApprovals.objects.filter(is_approved=False).exists():
                    for x in InvoiceApprovals.objects.filter(is_approved=False):
                        if x.employee.job_title.description == "Superintendent" and x.employee.first_name != "Victor":
                            ready_for_victor = False
                            ready_for_gene = False
                        if x.employee.first_name == "Victor":
                            ready_for_gene = False
                    this_week_status = Weekly_Approvals.objects.latest('id')
                    if ready_for_victor:
                        if this_week_status.victor_email_sent:

                            if InvoiceApprovals.objects.filter(is_approved=False,
                                                               employee__first_name="Victor").exists():
                                try:
                                    message = "Late Invoices are Ready for Victor Approval."
                                    # Email.sendEmail("Invoices Ready For Approval",
                                    #                 message,
                                    #                 ['joe@gerloffpainting.com', 'bridgette@gerloffpainting.com',
                                    #                  'admin2@gerloffpainting.com', 'victor@gerloffpainting.com'],
                                    #                 False)
                                    success = True
                                except:
                                    success = False
                    if ready_for_gene:
                        if this_week_status.gene_email_sent:
                            if InvoiceApprovals.objects.filter(is_approved=False,
                                                               employee__first_name="Gene").exists():
                                try:
                                    message = "Late Invoices are Ready for Gene Approval."
                                    # Email.sendEmail("Invoices Ready For Approval",
                                    #                 message,
                                    #                 ['joe@gerloffpainting.com', 'bridgette@gerloffpainting.com',
                                    #                  'admin2@gerloffpainting.com', 'gene@gerloffpainting.com'],
                                    #                 False)
                                    success = True
                                except:
                                    success = False
                                this_week_status.gene_email_sent = True
                                this_week_status.save()

                else:
                    try:
                        # Email.sendEmail("All Invoices are Approved",
                        #                 "All Invoices, including late invoices, are approved",
                        #                 ['joe@gerloffpainting.com', 'bridgette@gerloffpainting.com',
                        #                  'admin2@gerloffpainting.com', 'gene@gerloffpainting.com',
                        #                  'victor@gerloffpainting.com'], False)
                        success = True
                    except:
                        success = False
            if 'reject_notes' in request.POST:
                for x in SubcontractorInvoiceItem.objects.filter(invoice=selected_invoice):
                    x.quantity = 0
                    x.notes = "Rejected"
                    x.save()
                selected_invoice.final_amount = 0
                selected_invoice.is_sent = True
                selected_invoice.release_retainage = 0
                selected_invoice.retainage = 0
                selected_invoice.save()
                for x in approvers:
                    x.date = date.today()
                    x.is_reviewed = True
                    x.is_approved = True
                    x.made_changes = True
                    x.save()
                email_body = selected_invoice.subcontract.subcontractor.company + " invoice for " + selected_invoice.subcontract.job_number.job_name + " has been rejected by " + current_employee.first_name + ". " + \
                             request.POST['reject_notes']

                check_sender = Employees.objects.filter(user=request.user).first() if request.user.is_authenticated else None
                sender = check_sender.email if check_sender else "operations@gerloffpainting.com"
                try:
                    Email.sendEmail("Invoice Rejected", email_body,
                                    ['admin2@gerloffpainting.com', 'bridgette@gerloffpainting.com'], False,sender)
                    send_data['error_message'] = "Rejection Email Successfully Sent!"
                except:
                    send_data['error_message'] = "ERROR! Email not sent.  Please tell the office this was rejected."
        selected_invoice.save()
        # make notes below 2
        if 'approved' in request.POST or 'approved_with_changes' in request.POST or 'reject_notes' in request.POST or 'editing_now' in request.POST:  # make note
            current_employee = Employees.objects.get(user=request.user)
            first = "Invoice " + str(selected_invoice.pay_app_number)
            if 'approved' in request.POST: second = "Approved."
            if 'approved_with_changes' in request.POST: second = "Approved with changes."
            if 'reject_notes' in request.POST: second = "Rejected. " + request.POST['reject_notes'] + "."
            if 'editing_now' in request.POST: second = "Edited."
            third = note2
            fourth = ""
            if 'is_other_approver_id' in request.POST:
                other_approval = InvoiceApprovals.objects.get(id=request.POST['is_other_approver_id']).employee
                fourth = "On behalf of " + str(other_approval)
            note = first + " " + second + " " + third + " " + fourth
            SubcontractNotes.objects.create(subcontract=subcontract, date=date.today(),
                                            user=current_employee,
                                            note=note,
                                            invoice=selected_invoice)
            if 'approved_with_changes' in request.POST:
                check_sender = Employees.objects.filter(user=request.user).first() if request.user.is_authenticated else None
                sender = check_sender.email if check_sender else "operations@gerloffpainting.com"
                try:
                    Email.sendEmail("Invoice Changed", str(selected_invoice) + ". " + note + ". Changed by " + str(Employees.objects.get(user=request.user)),
                                    ['admin2@gerloffpainting.com', 'bridgette@gerloffpainting.com'], False,sender)
                    send_data['error_message'] = "Invoiced Changed Email Successfully Sent!"
                except:
                    send_data['error_message'] = "ERROR! Email not sent.  Please tell the office that you made changes to this invoice."
    # build the HTML page
    if item_id == 'ALL':
        invoices = SubcontractorInvoice.objects.filter(subcontract=subcontract).order_by('id')
        send_data['invoices'] = invoices
    else:
        items = []
        invoices = SubcontractorInvoice.objects.filter(id=item_id)
        send_data['invoices'] = invoices
        selected_invoice = SubcontractorInvoice.objects.get(id=item_id)
        send_data['selected_invoice'] = selected_invoice
        invoice_items = []
        if selected_invoice.is_release_retainage:
            invoice_items.append({'description':"Release Retainage",'billed':selected_invoice.release_retainage,'notes':selected_invoice.retainage_note, 'sov_item':0,'quantity':0})
        for x in SubcontractorInvoiceItem.objects.filter(invoice=selected_invoice):
            if x.sov_item.SOV_is_lump_sum:
                invoice_items.append({'description': x.sov_item.SOV_description, 'billed': "$" + str(x.quantity),
                                  'notes': x.notes,'sov_item': x.sov_item.id,'quantity':x.quantity})
            else:
                invoice_items.append({'description': x.sov_item.SOV_description, 'billed': str(x.quantity) + " " + str(x.sov_item.SOV_unit),
                                      'notes': x.notes,'sov_item': x.sov_item.id,'quantity':x.quantity})
        # invoice_items = SubcontractorInvoiceItem.objects.filter(invoice=selected_invoice)
        send_data['invoice_items'] = invoice_items
        notes = SubcontractNotes.objects.filter(subcontract=subcontract, invoice=selected_invoice)
        send_data['notes'] = notes
        other_retainage = 0
        previously_billed = 0
        for x in SubcontractorInvoice.objects.filter(subcontract=subcontract).exclude(id=item_id):
            if x.retainage: other_retainage += x.retainage
            if x.final_amount: previously_billed += x.final_amount
        send_data['previously_billed'] = previously_billed
        send_data['total_billed'] = previously_billed + selected_invoice.final_amount
        send_data['other_retainage'] = other_retainage
        send_data['total_retainage'] = other_retainage + selected_invoice.retainage
        send_data['total_contract'] = subcontract.total_contract_amount()
        send_data['invoice_total_after_retainage'] = selected_invoice.final_amount - selected_invoice.retainage
        if InvoiceApprovals.objects.filter(employee=Employees.objects.get(user=request.user), invoice=selected_invoice,
                                           is_approved=False).exists():
            send_data['me_approve'] = True
        elif InvoiceApprovals.objects.filter(invoice=selected_invoice, is_approved=False).exists():
            send_data['other_approvers'] = InvoiceApprovals.objects.filter(invoice=selected_invoice, is_approved=False)
        approvalcheck = InvoiceApprovals.objects.filter(invoice=selected_invoice, is_approved=True)
        if not approvalcheck:
            send_data['no_approvals_yet'] = True
        for x in SubcontractItems.objects.filter(subcontract=subcontract):
            totalcost = float(x.total_cost())
            totalbilled = float(x.total_billed())
            totalordered = float(x.SOV_total_ordered)
            quantitybilled = float(x.quantity_billed())
            remainingcost = totalcost - totalbilled
            remainingqnty = totalordered - quantitybilled
            invoiced = SubcontractorInvoiceItem.objects.filter(invoice=selected_invoice, sov_item=x).exists()
            if invoiced:
                if x.SOV_is_lump_sum:
                    special = (float(SubcontractorInvoiceItem.objects.get(invoice=selected_invoice,sov_item=x).quantity) / totalcost) * 100
                    if totalcost == 0:
                        percentage = 0
                    else:
                        percentage = ((float(SubcontractorInvoiceItem.objects.get(invoice=selected_invoice, sov_item=x).quantity) + totalbilled) / totalcost) * 100
                else:
                    special = int(SubcontractorInvoiceItem.objects.get(invoice=selected_invoice,sov_item=x).quantity) * x.SOV_rate

                    if totalcost == 0:
                        percentage = 0
                    else:
                        percentage = ((float(SubcontractorInvoiceItem.objects.get(invoice=selected_invoice,
                                                                              sov_item=x).quantity) + quantitybilled) / totalordered) * 100
            else:
                special = 0
                if totalcost == 0:
                    percentage = 0
                else:
                    percentage = (totalbilled / totalcost) * 100
            items.append(
                {'percentage': str(round(percentage, 2)), 'special': str(round(special, 2)), 'invoiced': invoiced,
                 'remainingqnty': remainingqnty, 'remainingcost': remainingcost, 'id': x.id,
                 'SOV_description': x.SOV_description, 'SOV_is_lump_sum': x.SOV_is_lump_sum,
                 'SOV_unit': x.SOV_unit, 'SOV_total_ordered': x.SOV_total_ordered, 'SOV_rate': x.SOV_rate,
                 'notes': x.notes, 'quantity_billed': float(x.quantity_billed()),
                 'total_billed': round(x.total_billed(), 2), 'total_cost': round(x.total_cost(), 2)})
            send_data['items'] = items
    return render(request, "subcontract_invoices.html", send_data)


@login_required(login_url='/accounts/login')
def subcontractor_home(request):
    # for x in Subcontracts.objects.filter(is_closed=False):
    #     ready_to_close = True
    #     if int(x.total_contract_amount()) == int(0):
    #         ready_to_close = False
    #     if int(x.total_billed()) != int(x.total_contract_amount()):
    #         ready_to_close = False
    #     if int(x.total_retainage()) != 0:
    #         ready_to_close = False
    #     if ready_to_close == True:
    #         print("CLOSING")
    #         print(x)
    #         x.is_closed = True
    #         x.save()
    #         SubcontractNotes.objects.create(subcontract=x, date=date.today(),user=Employees.objects.get(user=request.user),note="Subcontract Paid and Closed. Total Contract=$" + str(x.total_contract_amount()) + ". Total Billed =$" + str(x.total_billed()) + ". Total Retainage =$" + str(x.total_retainage()))

    send_data = {}
    approval_counts = {}
    approval_counts_two = {}
    today = datetime.date.today()
    this_friday = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=4)
    super_approvals_needed = 0
    victor_approvals_needed = 0
    for x in InvoiceApprovals.objects.filter(is_approved=False, invoice__pay_date__lte=this_friday):
        name = str(x.employee.first_name + " " + x.employee.last_name)
        employee = x.employee
        if employee.job_title.description == "Superintendent" and employee.first_name != "Victor":
            super_approvals_needed += 1
        if employee.first_name == 'Victor':
            victor_approvals_needed += 1
        if name in approval_counts:
            approval_counts[name] += 1
        else:
            approval_counts[name] = 1
        if employee in approval_counts_two:
            approval_counts_two[employee] += 1
        else:
            approval_counts_two[employee] = 1
    if request.method == 'POST':
        if 'invoices_entered' in request.POST:
            this_week_status = Weekly_Approvals.objects.latest('id')
            this_week_status.invoices_entered = True
            this_week_status.date_invoices_entered = date.today()
            this_week_status.notes = request.POST['invoice_notes']
            this_week_status.save()
            if victor_approvals_needed == 0 and super_approvals_needed == 0:
                email_body = "Gene, the Subcontractor Invoices are Ready for Your Approval!"
                recipients = ["gene@gerloffpainting.com", "joe@gerloffpainting.com",
                              "bridgette@gerloffpainting.com", "admin2@gerloffpainting.com"]
            if super_approvals_needed == 0 and victor_approvals_needed != 0:
                email_body = "Victor, the Subcontractor Invoices are Ready for Your Approval!"
                recipients = ["victor@gerloffpainting.com", "joe@gerloffpainting.com",
                              "bridgette@gerloffpainting.com", "admin2@gerloffpainting.com"]
            check_sender = Employees.objects.filter(user=request.user).first() if request.user.is_authenticated else None
            sender = check_sender.email if check_sender else "operations@gerloffpainting.com"
            try:
                Email.sendEmail("Invoice Approval Required", email_body, recipients, False,sender)
                send_data['success'] = True
            except:
                send_data['failed'] = True
            if super_approvals_needed != 0:
                for x in approval_counts_two:
                    if x.job_title.description == "Superintendent" and x.first_name != "Victor":
                        recipients = ["joe@gerloffpainting.com", "bridgette@gerloffpainting.com",
                                      "admin2@gerloffpainting.com"]
                        if x.email:
                            recipients.append(x.email)
                            email_body = "You have " + str(
                                approval_counts_two[x]) + " Subcontractor Invoices to Approve in Trinity!"
                        else:
                            email_body = x.first_name + " Has " + str(approval_counts_two[
                                                                          x]) + " Invoices to Approve in Trinity, However There is No Email Address on File!"
                        check_sender = Employees.objects.filter(user=request.user).first() if request.user.is_authenticated else None
                        sender = check_sender.email if check_sender else "operations@gerloffpainting.com"
                        try:
                            Email.sendEmail("Invoice Approval Required", email_body, recipients, False,sender)
                            send_data['success'] = True
                        except:
                            send_data['failed'] = True
        else:
            subcontractor = Subcontractors.objects.get(id=request.POST['subcontractor_id'])
            if 'contact' in request.POST:
                if 'contact' in request.POST:
                    subcontractor.contact = request.POST['contact']
                    subcontractor.phone = request.POST['phone']
                    subcontractor.email = request.POST['email']
                    subcontractor.notes = request.POST['notes']
                if 'is_inactive' in request.POST:
                    subcontractor.is_inactive = True
                else:
                    subcontractor.is_inactive = False
                if 'is_toolbox_required' in request.POST:
                    subcontractor.is_toolbox_required = True
                else:
                    subcontractor.is_toolbox_required = False
                subcontractor.save()
            if 'insurance' in request.POST:
                if request.POST['insurance'] != "":
                    subcontractor.insurance_expire_date = request.POST['insurance']
                if request.POST['w9_form_date'] != "":
                    subcontractor.w9_form_date = request.POST['w9_form_date']
                if request.POST['business_license_expiration_date'] != "":
                    subcontractor.business_license_expiration_date = request.POST['business_license_expiration_date']

                if 'has_workers_comp' in request.POST:
                    subcontractor.has_workers_comp = True
                else:
                    subcontractor.has_workers_comp = False
                if 'has_auto_insurance' in request.POST:
                    subcontractor.has_auto_insurance = True
                else:
                    subcontractor.has_auto_insurance = False
                if 'has_w9_form' in request.POST:
                    subcontractor.has_w9_form = True
                else:
                    subcontractor.has_w9_form = False
                if 'has_business_license' in request.POST:
                    subcontractor.has_business_license = True
                else:
                    subcontractor.has_business_license = False
                if 'is_signed_labor_agreement' in request.POST:
                    subcontractor.is_signed_labor_agreement = True
                else:
                    subcontractor.is_signed_labor_agreement = False
            subcontractor.save()

            if 'go_back_to_subcontracts' in request.POST:
                return redirect('subcontracts_home')
            if 'go_back_to_subcontract' in request.POST:
                return redirect('subcontract', id=request.POST['go_back_to_subcontract'])
            return redirect('subcontractor_home')

    subcontractors = []
    for x in Subcontractors.objects.filter(is_inactive=False):
        subcontractors.append({'id': x.id, 'company': x.company, 'active_contracts': x.active_contracts(),
                               'pending_invoices': x.pending_invoices(),'is_toolbox_required': x.is_toolbox_required,})
    send_data['subcontractors'] = subcontractors
    send_data['subcontractor_count'] = Subcontractors.objects.filter(is_inactive=False).count()
    send_data['contracts_count'] = Subcontracts.objects.filter(is_closed=False).count()
    send_data['approvals_count'] = SubcontractorInvoice.objects.filter(is_sent=False).count()
    send_data['approved'] = SubcontractorInvoice.objects.filter(is_sent=True, processed=False)
    send_data['approved_count'] = SubcontractorInvoice.objects.filter(is_sent=True, processed=False).count()
    all_invoices = []
    for x in SubcontractorInvoice.objects.filter(is_sent=False):
        all_invoices.append({'contract_id': x.subcontract.id, 'id': x.id, 'job_name': x.subcontract.job_number.job_name,
                             'company': x.subcontract.subcontractor, 'amount': x.final_amount,
                             'approvals_needed': x.approvals_needed(), 'pay_date': x.pay_date,
                             'number': x.pay_app_number})
    send_data['all_invoices'] = all_invoices
    my_invoices = []
    my_approvals_count = 0
    for x in SubcontractorInvoice.objects.filter(is_sent=False):
        if InvoiceApprovals.objects.filter(invoice=x, employee=Employees.objects.get(user=request.user),
                                           is_approved=False).exists():
            my_approvals_count += 1
            my_invoices.append(
                {'contract_id': x.subcontract.id, 'id': x.id, 'job_name': x.subcontract.job_number.job_name,
                 'company': x.subcontract.subcontractor, 'amount': x.final_amount,
                 'approvals_needed': x.approvals_needed(), 'pay_date': x.pay_date, 'number': x.pay_app_number})
    send_data['my_approvals_count'] = my_approvals_count
    send_data['my_invoices'] = my_invoices
    send_data['approval_counts'] = approval_counts
    send_data['late_invoices'] = SubcontractorInvoice.objects.filter(pay_date__gt=this_friday)

    this_week_status = Weekly_Approvals.objects.latest('id')
    days_since_monday = today - this_week_status.Monday
    if days_since_monday.days >= 7:
        this_week_status = Weekly_Approvals.objects.create(Monday=today - datetime.timedelta(days=today.weekday()))
    send_data['this_week_status'] = this_week_status

    return render(request, "subcontractor_home.html", send_data)


@login_required(login_url='/accounts/login')
def subcontract(request, id):
    send_data = {}
    subcontract = Subcontracts.objects.get(id=id)
    current_job = subcontract.job_number
    send_data["change_orders_for_linking"] = ChangeOrders.objects.filter(
    job_number=subcontract.job_number
).order_by("-cop_number")
    send_data['approvers']=Subcontract_Approvers.objects.filter(subcontract=subcontract)
    send_data['employees']=Employees.objects.all()
    if not current_job.is_closed:
        send_data['job_open']= True
    if subcontract.is_entire_paint_job:
        send_data['is_entire_paint_job'] = True
    invoices = []
    for x in SubcontractorInvoice.objects.filter(subcontract=subcontract).order_by('id'):
        if x.retainage > 0:
            retainage_positive = True
        else:
            retainage_positive = False
        retainage = "$" + f"{0-int(x.retainage):,d}"
        invoices.append(
            {'retainage':retainage, 'invoice': x, 'total_pay_amount': x.final_amount - x.retainage, 'retainage_positive': retainage_positive})
    send_data['invoices'] = invoices
    # send_data['invoices'] = SubcontractorInvoice.objects.filter(subcontract=subcontract).order_by('id')
    items = []
    number_items = 0
    for x in SubcontractItems.objects.filter(subcontract=subcontract).order_by('id'):
        change_order_id = None
        change_order_status = None
        change_order_number = None

        if x.change_order:
            change_order_id = x.change_order.id
            change_order_status = x.change_order.status()
            change_order_number = x.change_order.cop_number
        number_items = number_items + 1
        totalcost = float(x.total_cost())
        totalbilled = float(x.total_billed())
        totalbilledandpending = float(x.total_billed_and_pending())
        totalordered = float(x.SOV_total_ordered)
        quantitybilled = float(x.quantity_billed())
        remainingcost = totalcost - totalbilled
        remainingqnty = totalordered - quantitybilled
        if totalcost == 0:
            percentage = 0
            percentage2 = 0
        else:
            percentage = (totalbilled / totalcost) * 100
            percentage2 = (totalbilledandpending / totalcost) * 100
        items.append(
            {'is_approved': x.is_approved, 'date': x.date.strftime("%m/%d/%y"), 'percentage': str(round(percentage, 2)),'percentage2': str(round(percentage2, 2)),
             'remainingqnty': remainingqnty, 'remainingcost': remainingcost, 'id': x.id,
             'SOV_description': x.SOV_description, 'SOV_is_lump_sum': x.SOV_is_lump_sum,
             'SOV_unit': x.SOV_unit, 'SOV_total_ordered': x.SOV_total_ordered, 'SOV_rate': x.SOV_rate,
             'notes': x.notes, 'quantity_billed': float(x.quantity_billed()),
             'total_billed': round(x.total_billed(), 2), 'total_cost': round(x.total_cost(), 2),'change_order_status': change_order_status,
            'change_order_number': change_order_number,'change_order_id': change_order_id,
             'wallcovering_pk': x.wallcovering_id.id if x.wallcovering_id else '',
             'wallcovering_code': x.wallcovering_id.code if x.wallcovering_id and x.wallcovering_id.code else '',
             'is_wallcovering_linked': bool(x.wallcovering_id),})
    send_data['items'] = items
    send_data['number_items'] = number_items
    send_data['wallcovering_link_options'] = Wallcovering.objects.filter(
        job_number=subcontract.job_number
    ).select_related("vendor").order_by("code", "pattern")

    def format_yardage(value):
        if value is None:
            return ''
        return f"{Decimal(value):,.2f}".rstrip("0").rstrip(".")

    def join_names(names):
        names = [name for name in names if name]
        if not names:
            return ''
        if len(names) == 1:
            return names[0]
        if len(names) == 2:
            return f"{names[0]} and {names[1]}"
        return f"{', '.join(names[:-1])}, and {names[-1]}"

    def wallcovering_subcontract_history(wallcovering):
        history_parts = []
        non_lump_rows = (
            SubcontractItems.objects
            .filter(
                wallcovering_id=wallcovering,
                SOV_is_lump_sum=False
            )
            .values("subcontract__subcontractor__company")
            .annotate(total=Sum("SOV_total_ordered"))
            .order_by("subcontract__subcontractor__company")
        )

        for row in non_lump_rows:
            if row["total"]:
                history_parts.append(
                    f"{format_yardage(row['total'])} yards assigned to {row['subcontract__subcontractor__company']}"
                )

        lump_sum_names = list(
            SubcontractItems.objects
            .filter(
                wallcovering_id=wallcovering,
                SOV_is_lump_sum=True
            )
            .values_list("subcontract__subcontractor__company", flat=True)
            .distinct()
            .order_by("subcontract__subcontractor__company")
        )

        if lump_sum_names:
            history_parts.append(f"lump sum assigned to {join_names(lump_sum_names)}")

        return ", ".join(history_parts)

    wallcovering_shortage_rows = []
    linked_wallcovering_ids = (
        SubcontractItems.objects
        .filter(
            subcontract=subcontract,
            wallcovering_id__isnull=False,
            SOV_is_lump_sum=False
        )
        .values_list("wallcovering_id", flat=True)
        .distinct()
    )

    for wallcovering in Wallcovering.objects.filter(id__in=linked_wallcovering_ids).select_related("vendor"):
        if SubcontractItems.objects.filter(
            wallcovering_id=wallcovering,
            SOV_is_lump_sum=True
        ).exists():
            continue

        target_quantity = wallcovering.install_yardage
        target_source = "Install Yardage"

        if not target_quantity:
            target_quantity = wallcovering.quantity_ordered()
            target_source = "Ordered Yardage"

        if not target_quantity:
            continue

        subcontracted_quantity = (
            SubcontractItems.objects
            .filter(
                wallcovering_id=wallcovering,
                SOV_is_lump_sum=False
            )
            .aggregate(total=Sum("SOV_total_ordered"))
            .get("total")
        ) or Decimal("0.00")

        if target_quantity > subcontracted_quantity:
            wallcovering_shortage_rows.append({
                "wallcovering_url": reverse("wallcovering_detail", args=[wallcovering.id]),
                "description": wallcovering.code or f"{wallcovering.vendor.company_name if wallcovering.vendor else ''} {wallcovering.pattern or ''}".strip(),
                "target_quantity": target_quantity,
                "target_source": target_source,
                "subcontracted_quantity": subcontracted_quantity,
            })

    send_data["wallcovering_shortage_rows"] = wallcovering_shortage_rows

    wallcovering_order_after_subcontract_rows = []
    lump_sum_wallcovering_ids = (
        SubcontractItems.objects
        .filter(
            subcontract=subcontract,
            wallcovering_id__isnull=False,
            SOV_is_lump_sum=True
        )
        .values_list("wallcovering_id", flat=True)
        .distinct()
    )

    for wallcovering in Wallcovering.objects.filter(id__in=lump_sum_wallcovering_ids).select_related("vendor"):
        latest_order = (
            OrderItems.objects
            .filter(
                Q(wallcovering=wallcovering) |
                Q(link_to_wallcovering=wallcovering),
                order__date_ordered__isnull=False
            )
            .select_related("order")
            .order_by("-order__date_ordered", "-order__id")
            .first()
        )

        if not latest_order:
            continue

        latest_subcontract_item = (
            SubcontractItems.objects
            .filter(
                wallcovering_id=wallcovering
            )
            .order_by("-date", "-id")
            .first()
        )

        if not latest_subcontract_item:
            continue

        if not SubcontractItems.objects.filter(
            wallcovering_id=wallcovering,
            SOV_is_lump_sum=True,
            date__lt=latest_order.order.date_ordered
        ).exists():
            continue

        wallcovering_order_after_subcontract_rows.append({
            "wallcovering_url": reverse("wallcovering_detail", args=[wallcovering.id]),
            "description": wallcovering.code or f"{wallcovering.vendor.company_name if wallcovering.vendor else ''} {wallcovering.pattern or ''}".strip(),
            "subcontract_history": wallcovering_subcontract_history(wallcovering),
            "latest_subcontract_item_date": latest_subcontract_item.date,
            "order_date": latest_order.order.date_ordered,
        })

    send_data["wallcovering_order_after_subcontract_rows"] = wallcovering_order_after_subcontract_rows
    send_data['notes'] = SubcontractNotes.objects.filter(subcontract=subcontract).order_by('id')
    send_data['total_retainage'] = 0-subcontract.total_retainage_approved()
    send_data['retainage_to_release'] = subcontract.total_retainage_approved()
    send_data['total_pending'] = subcontract.total_pending_amount()
    send_data['total_billed_and_pending'] = float(subcontract.total_billed())
    send_data['total_retainage_pending'] = 0-subcontract.total_retainage_pending()
    send_data['final_retainage'] = 0- float(subcontract.total_retainage())
    if subcontract.invoice_pending(): send_data['is_invoice_pending'] = True
    if Wallcovering.objects.filter(job_number=subcontract.job_number):
        wallcovering = Wallcovering.objects.filter(job_number=subcontract.job_number)
        wallcovering_json1 = []
        for x in wallcovering:
            wallcovering_json1.append(wallcovering_subcontract_json(x))
        send_data['wallcovering_json'] = json.dumps(list(wallcovering_json1), cls=DjangoJSONEncoder)
    if request.method == 'POST':
        for x in request.POST:
            if x[0:14] == 'deleteapprover':
                item_number = x[14:len(x)]
                Subcontract_Approvers.objects.get(id=item_number).delete()
                return redirect('subcontract', id=id)
            if x == 'add_new_approver':
                if request.POST['add_new'] == 'Superintendent':
                    if not Subcontract_Approvers.objects.filter(subcontract=subcontract,
                                                                  job_description="Superintendent").exists():
                        Subcontract_Approvers.objects.create(subcontract=subcontract,
                                                               job_description="Superintendent")
                else:
                    employee = Employees.objects.get(id=request.POST['add_new'])
                    if not Subcontract_Approvers.objects.filter(subcontract=subcontract,
                                                                  employee=employee).exists():
                        Subcontract_Approvers.objects.create(subcontract=subcontract, employee=employee)
                return redirect('subcontract', id=id)
        if "link_cop_now" in request.POST:
            item_id = request.POST.get("link_cop_item_id")
            changeorder_id = request.POST.get("link_cop_changeorder_id")

            item = SubcontractItems.objects.get(
                id=item_id,
                subcontract=subcontract
            )

            changeorder = ChangeOrders.objects.get(
                id=changeorder_id,
                job_number=subcontract.job_number
            )

            item.change_order = changeorder
            item.save()

            SubcontractNotes.objects.create(
                subcontract=subcontract,
                date=date.today(),
                user=Employees.objects.get(user=request.user),
                note=f"Item {item.SOV_description} linked to COP #{changeorder.cop_number}."
            )

            messages.success(
                request,
                f"Item linked to COP #{changeorder.cop_number}."
            )

            return redirect("subcontract", id=subcontract.id)
        if "remove_cop_now" in request.POST:
            item_id = request.POST.get("link_cop_item_id")

            item = SubcontractItems.objects.get(
                id=item_id,
                subcontract=subcontract
            )

            old_cop_number = item.change_order.cop_number if item.change_order else None
            item.change_order = None
            item.save()

            SubcontractNotes.objects.create(
                subcontract=subcontract,
                date=date.today(),
                user=Employees.objects.get(user=request.user),
                note=f"Item {item.SOV_description} unlinked from COP #{old_cop_number}." if old_cop_number else f"Item {item.SOV_description} had no COP link to remove."
            )

            messages.success(request, "COP link removed.")

            return redirect("subcontract", id=subcontract.id)
        if "link_wc_now" in request.POST:
            item_id = request.POST.get("link_wc_item_id")
            wallcovering_id = request.POST.get("link_wc_wallcovering_id")

            item = SubcontractItems.objects.get(
                id=item_id,
                subcontract=subcontract
            )

            wallcovering = Wallcovering.objects.get(
                id=wallcovering_id,
                job_number=subcontract.job_number
            )

            item.wallcovering_id = wallcovering
            item.save()

            SubcontractNotes.objects.create(
                subcontract=subcontract,
                date=date.today(),
                user=Employees.objects.get(user=request.user),
                note=f"Item {item.SOV_description} linked to wallcovering {wallcovering.code or wallcovering.pattern}."
            )

            messages.success(
                request,
                "Item linked to wallcovering."
            )

            return redirect("subcontract", id=subcontract.id)
        if "remove_wc_now" in request.POST:
            item_id = request.POST.get("link_wc_item_id")

            item = SubcontractItems.objects.get(
                id=item_id,
                subcontract=subcontract
            )

            old_wallcovering = item.wallcovering_id
            item.wallcovering_id = None
            item.save()

            SubcontractNotes.objects.create(
                subcontract=subcontract,
                date=date.today(),
                user=Employees.objects.get(user=request.user),
                note=f"Item {item.SOV_description} unlinked from wallcovering {old_wallcovering.code or old_wallcovering.pattern}." if old_wallcovering else f"Item {item.SOV_description} had no wallcovering link to remove."
            )

            messages.success(request, "Wallcovering link removed.")

            return redirect("subcontract", id=subcontract.id)
        if 'retainage_percentage' in request.POST:
            if 'is_entire_paint_job' in request.POST:
                subcontract.is_entire_paint_job = True
                subcontract.save()
                # current_job.is_painting_subbed = True
                # current_job.save()
            else:
                subcontract.is_entire_paint_job = False
                subcontract.save()
                # if current_job.is_entire_job_subbed():
                #     current_job.is_painting_subbed = True
                # else:
                #     current_job.is_painting_subbed = False
                # current_job.save()
        if 'retainage_released' in request.POST:
            today = datetime.date.today()
            friday = today + datetime.timedelta((4 - today.weekday()) % 7)
            if SubcontractorInvoice.objects.filter(subcontract=subcontract).exists():
                next_number = SubcontractorInvoice.objects.filter(subcontract=subcontract).latest(
                    'pay_app_number').pay_app_number + 1
            else:
                next_number = 1
            if today.weekday() == 4 or today.weekday() == 3 or today.weekday() == 2: friday = friday + timedelta(7)
            if subcontract.job_number.is_wage_scale:
                if not subcontract.is_certified_payroll_email_sent:
                    email_body = "New Subcontractor Invoice on a Certified Payroll Job! " + str(
                        subcontract.subcontractor.company) + "\n Job: " + str(
                        subcontract.job_number.job_name)
                    check_sender = Employees.objects.filter(user=request.user).first() if request.user.is_authenticated else None
                    sender = check_sender.email if check_sender else "operations@gerloffpainting.com"
                    try:
                        Email.sendEmail("New Sub Invoice on Certified Payroll Job", email_body,
                                        ['admin2@gerloffpainting.com', 'bridgette@gerloffpainting.com', 'joe@gerloffpainting.com'],
                                        False,sender)
                        success = True
                        subcontract.is_certified_payroll_email_sent = True
                        subcontract.save()
                    except:
                        success = False
            invoice = SubcontractorInvoice.objects.create(date=date.today(), pay_app_number=next_number,
                                                          subcontract=subcontract, pay_date=friday, final_amount=0,
                                                          retainage=0 - float(request.POST['retainage_released']),
                                                          notes=request.POST['new_note'], release_retainage=0 - float(
                    request.POST['retainage_released']), is_release_retainage=True, original_amount=0)
            SubcontractNotes.objects.create(subcontract=subcontract, date=date.today(),
                                            user=Employees.objects.get(user=request.user),
                                            note="Retainage released- " + request.POST['new_note'],
                                            invoice=invoice)
            for x in Subcontract_Approvers.objects.filter(subcontract=subcontract):
                if x.employee:
                    InvoiceApprovals.objects.create(employee=x.employee, invoice=invoice)
            for x in Subcontract_Approvers.objects.filter(subcontract=subcontract):
                if x.job_description:
                    if x.job_description == "Superintendent":
                        if subcontract.job_number.superintendent:
                            job_super = subcontract.job_number.superintendent
                            if not InvoiceApprovals.objects.filter(invoice=invoice, employee=job_super).exists():
                                InvoiceApprovals.objects.create(employee=job_super, invoice=invoice)
            return redirect('subcontract', id=id)

        subcontract_notes=""
        subcontract_changed = False

        if 'change_header' in request.POST: #they changed info in the header
            if subcontract.po_number != request.POST['po_number']:
                subcontract_notes += f"PO Number changed from {subcontract.po_number} to {request.POST['po_number']}"
                subcontract_changed = True
            subcontract.po_number = request.POST['po_number']
            new_date = date.fromisoformat(request.POST['issued_date'])
            if subcontract.date != new_date:
                subcontract_notes += f"PO Date changed from {subcontract.date} to {request.POST['issued_date']}"
                subcontract_changed = True
            subcontract.date = request.POST['issued_date']
            if 'is_retainage' in request.POST:
                if not subcontract.is_retainage:
                    subcontract_notes += f"Retainage now being held"
                    subcontract_changed = True
                subcontract.is_retainage = True
            else:
                if subcontract.is_retainage:
                    subcontract_notes += f"Retainage not being held anymore"
                    subcontract_changed = True
                subcontract.is_retainage = False
            if subcontract.retainage_percentage != Decimal(request.POST['retainage_percentage']):
                subcontract_notes += f"Retainage changed from {subcontract.retainage_percentage} to {request.POST['retainage_percentage']}"
                subcontract_changed = True
            subcontract.retainage_percentage = request.POST['retainage_percentage']
            if 'is_closed' in request.POST:
                if not subcontract.is_closed:
                    subcontract_notes += f"Subcontract closed"
                    subcontract_changed = True
                subcontract.is_closed = True
            else:
                if subcontract.is_closed:
                    subcontract_notes += f"Subcontract Re-Opened"
                    subcontract_changed = True
                subcontract.is_closed = False
            subcontract.save()
            if subcontract_changed:
                SubcontractNotes.objects.create(subcontract=subcontract, date=date.today(),
                                                user=Employees.objects.get(user=request.user),
                                                note=subcontract_notes)
            return redirect("subcontract", subcontract.id)
        if 'edit_now' in request.POST: #they want to edited a row
            send_data['edit_row'] = request.POST['edit_existing_item']
            if request.POST['edit_existing_item'] != 'None Selected':
                item = SubcontractItems.objects.get(id=request.POST['edit_existing_item'])
                if item.invoice_item2.exists():
                    send_data['invoiced_already'] = True
        if 'save_now' in request.POST:#edited a row
            item = SubcontractItems.objects.get(id=request.POST['item_edited'])
            if item.SOV_description != request.POST['SOV_description']:
                subcontract_notes += f"SOV description changed from {item.SOV_description} to {request.POST['SOV_description']}. "
                subcontract_changed = True
            item.SOV_description = request.POST['SOV_description']
            if 'SOV_total_ordered' in request.POST:
                if item.SOV_total_ordered != Decimal(request.POST['SOV_total_ordered']):
                    subcontract_notes += f"{request.POST['SOV_description']} order quantity changed from {item.SOV_total_ordered} to {request.POST['SOV_total_ordered']}. "
                    subcontract_changed = True
                item.SOV_total_ordered = request.POST['SOV_total_ordered']
            if 'SOV_rate' in request.POST:
                if item.SOV_rate != Decimal(request.POST['SOV_rate']):
                    subcontract_notes += f"{request.POST['SOV_description']} rate changed from {item.SOV_rate} to {request.POST['SOV_rate']}. "
                    subcontract_changed = True
                item.SOV_rate = request.POST['SOV_rate']
                if item.SOV_is_lump_sum:
                    item.SOV_total_ordered = request.POST['SOV_rate']
            if 'is_approved' in request.POST:
                if not item.is_approved:
                    subcontract_notes += f"{request.POST['SOV_description']} Approved For Future Billing. "
                    subcontract_changed = True
                item.is_approved = True
            else:
                if item.is_approved:
                    subcontract_notes += f"{request.POST['SOV_description']} No Longer Approved For Future Billing. "
                    subcontract_changed = True
                item.is_approved = False
            if item.notes != request.POST['notes']:
                subcontract_notes += f"{request.POST['SOV_description']} - Changed Note from - {item.notes} to - {request.POST['notes']}. "
                subcontract_changed = True
            item.notes = request.POST['notes']
            item.save()
            if subcontract_changed:
                SubcontractNotes.objects.create(subcontract=subcontract, date=date.today(),
                                                user=Employees.objects.get(user=request.user),
                                                note=subcontract_notes)
                subject = f"Job {subcontract.job_number.job_number} -PO#{subcontract.po_number} - Changed"
                body = subcontract_notes
                recipients = ["admin2@gerloffpainting.com", "bridgette@gerloffpainting.com"]
                check_sender = Employees.objects.filter(user=request.user).first() if request.user.is_authenticated else None
                sender = check_sender.email if check_sender else "operations@gerloffpainting.com"
                try:
                    Email.sendEmail(subject,body, recipients, False,sender)
                    messages.success(
                        request,
                        f"Email Successfully Sent"
                    )
                except:
                    messages.error(request,
                                   f"There was an error sending email. Please tell Viktoria that you {subcontract_notes}")
            return redirect("subcontract", subcontract.id)
        if 'delete_now' in request.POST:
            item = SubcontractItems.objects.get(id=request.POST['delete_existing_item'])
            subcontract_notes = f"{item.SOV_description} - ({item.SOV_total_ordered} {item.SOV_unit}) - (${item.SOV_rate} {item.SOV_unit}) - {item.notes}- deleted. "
            SubcontractNotes.objects.create(subcontract=subcontract, date=date.today(),
                                            user=Employees.objects.get(user=request.user),
                                            note=subcontract_notes)
            item.delete()
            subject = f"Job {subcontract.job_number.job_number} -PO#{subcontract.po_number} - Changed"
            body = subcontract_notes
            recipients = ["admin2@gerloffpainting.com", "bridgette@gerloffpainting.com"]
            check_sender = Employees.objects.filter(user=request.user).first() if request.user.is_authenticated else None
            sender = check_sender.email if check_sender else "operations@gerloffpainting.com"
            try:
                Email.sendEmail(subject, body, recipients, False,sender)
                messages.success(
                    request,
                    f"Email Successfully Sent"
                )
            except:
                messages.error(request,
                               f"There was an error sending email. Please tell Viktoria that you {subcontract_notes}")
            return redirect("subcontract", subcontract.id)
        if 'added_row' in request.POST:
            subcontract.is_closed = False
            subcontract.save()
            for x in range(1, int(request.POST['number_items']) + 1):
                if 'item_type' + str(x) in request.POST:
                    if request.POST['item_type' + str(x)] == "Per Unit":
                        item = SubcontractItems.objects.create(subcontract=subcontract,
                                                               SOV_description=request.POST[
                                                                   'item_description' + str(x)],
                                                               SOV_unit=request.POST['item_unit' + str(x)],
                                                               SOV_total_ordered=request.POST[
                                                                   'item_quantity' + str(x)],
                                                               SOV_rate=request.POST['item_price' + str(x)],
                                                               notes=request.POST['item_notes' + str(x)],
                                                               date=date.today())
                        if 'wallcovering_number' + str(x) in request.POST:
                            if request.POST['wallcovering_number' + str(x)] != 'no_wc_selected':
                                item.wallcovering_id = Wallcovering.objects.get(
                                    id=request.POST['wallcovering_number' + str(x)])
                                item.save()
                    else:
                        item = SubcontractItems.objects.create(subcontract=subcontract,
                                                               SOV_description=request.POST[
                                                                   'item_description' + str(x)],
                                                               SOV_is_lump_sum=True, SOV_unit="Lump Sum",
                                                               SOV_total_ordered=request.POST[
                                                                   'item_price' + str(x)],
                                                               SOV_rate=request.POST['item_price' + str(x)],
                                                               notes=request.POST['item_notes' + str(x)],
                                                               date=date.today())
                        if 'wallcovering_number' + str(x) in request.POST:
                            if request.POST['wallcovering_number' + str(x)] != 'no_wc_selected':
                                item.wallcovering_id = Wallcovering.objects.get(
                                    id=request.POST['wallcovering_number' + str(x)])
                                item.save()
                    subcontract_notes = f"Item {item.SOV_description} added. "
                    SubcontractNotes.objects.create(subcontract=subcontract, date=date.today(),
                                                    user=Employees.objects.get(user=request.user),
                                                    note=subcontract_notes)
                    subject = f"Job {subcontract.job_number.job_number} -PO#{subcontract.po_number} - Changed"
                    body = subcontract_notes
                    recipients = ["admin2@gerloffpainting.com", "bridgette@gerloffpainting.com"]
                    check_sender = Employees.objects.filter(user=request.user).first() if request.user.is_authenticated else None
                    sender = check_sender.email if check_sender else "operations@gerloffpainting.com"
                    try:
                        Email.sendEmail(subject, body, recipients, False,sender)
                        messages.success(
                            request,
                            f"Email Successfully Sent"
                        )
                    except:
                        messages.error(request,
                                       f"There was an error sending email. Please tell Viktoria that you {subcontract_notes}")
            return redirect("subcontract", subcontract.id)
        if 'new_note' in request.POST:
            SubcontractNotes.objects.create(subcontract=subcontract, date=date.today(),
                                            user=Employees.objects.get(user=request.user),
                                            note=request.POST['new_note'])
            send_data['notes'] = SubcontractNotes.objects.filter(subcontract=subcontract)
            return redirect("subcontract", subcontract.id)

    subcontract = Subcontracts.objects.get(id=id)
    send_data['subcontract'] = subcontract
    send_data['percent_complete'] = format(subcontract.percent_complete(), ".0%")
    send_data['total_contract'] = "{:,}".format(round(subcontract.total_contract_amount(), 2))
    send_data['total_billed'] = "{:,}".format(round(subcontract.total_approved(), 2))
    send_data['subcontract_date'] = str(subcontract.date)
    return render(request, "subcontract.html", send_data)


@login_required(login_url='/accounts/login')
def subcontractor(request, id):
    response = redirect('/')
    return response


@login_required(login_url='/accounts/login')
def subcontractor_new(request):
    if request.method == 'POST':
        signed = False
        if 'is_signed_labor_agreement' in request.POST:
            signed = True
        new_sub = Subcontractors.objects.create(company=request.POST['subcontractor'], contact=request.POST['contact'],
                                                phone=request.POST['phone'], email=request.POST['email'],
                                                is_signed_labor_agreement=signed, notes=request.POST['notes'])
        new_sub.save()
        for y in Standard_Approvers.objects.all():
            if y.employee:
                Subcontractor_Approvers.objects.create(subcontractor=new_sub, employee=y.employee)
            if y.job_description:
                Subcontractor_Approvers.objects.create(subcontractor=new_sub, job_description=y.job_description)
        return redirect('subcontractor', id=new_sub.id)
    return render(request, "subcontractor_new.html")


@login_required(login_url='/accounts/login')
def subcontracts_new(request):
    send_data = {}
    send_data['subcontractors'] = Subcontractors.objects.all()

    def select_job(job_number):
        selectedjob = Jobs.objects.get(job_number=job_number)
        send_data['selectedjob'] = selectedjob
        wallcovering = Wallcovering.objects.filter(job_number__job_number=job_number)
        if wallcovering:
            wallcovering_json1 = []
            for x in wallcovering:
                wallcovering_json1.append(wallcovering_subcontract_json(x))
            send_data['wallcovering_json'] = json.dumps(list(wallcovering_json1), cls=DjangoJSONEncoder)
        else:
            send_data['wallcovering_json'] = 'None'

    if request.method == 'POST':
        if 'form1' in request.POST:
            select_job(request.POST['select_job'])
            return render(request, "subcontracts_new.html", send_data)
        else:
            if request.POST['po_number'] == "":
                nextPO = PurchaseOrderNumber.objects.get(id=1)
                po_number = "TR" + str(nextPO.next_po_number)
                nextPO.next_po_number += 1
                nextPO.save()
            else:
                po_number = request.POST['po_number']
            subcontractor1 = Subcontractors.objects.get(id=request.POST['select_subcontractor'])
            subcontract1 = Subcontracts.objects.create(
                job_number=Jobs.objects.get(job_number=request.POST['selected_job']),
                subcontractor=subcontractor1,
                po_number=po_number, date=date.today(), retainage_percentage=0, is_retainage=False)
            SubcontractNotes.objects.create(subcontract=subcontract1, date=date.today(),
                                            user=Employees.objects.get(user=request.user),
                                            note="New Contract- " + request.POST['subcontract_notes'])
            for y in Subcontractor_Approvers.objects.filter(subcontractor=subcontractor1):
                if y.employee:
                    Subcontract_Approvers.objects.create(subcontract=subcontract1, employee=y.employee)
                if y.job_description:
                    Subcontract_Approvers.objects.create(subcontract=subcontract1, job_description=y.job_description)
            message = "New Subcontract for " + subcontract1.subcontractor.company + "\n Job: " + subcontract1.job_number.job_name + "\n PO #: " + subcontract1.po_number
            check_sender = Employees.objects.filter(user=request.user).first() if request.user.is_authenticated else None
            sender = check_sender.email if check_sender else "operations@gerloffpainting.com"
            try:
                Email.sendEmail("New Subcontract", message,
                                ['joe@gerloffpainting.com', 'admin2@gerloffpainting.com',
                                 'bridgette@gerloffpainting.com'],
                                False,sender)
                success = True
            except:
                success = False
            if 'is_retainage' in request.POST:
                subcontract1.is_retainage = True
                subcontract1.retainage_percentage = request.POST['retainage_amt']
                subcontract1.save()
            if 'is_entire_job' in request.POST:
                subcontract1.is_entire_paint_job = True
                subcontract1.save()
                selectedjob = Jobs.objects.get(job_number=request.POST['selected_job'])
                selectedjob.is_painting_subbed = True
                selectedjob.save()
            for x in range(1, int(request.POST['number_items']) + 1):
                if 'item_type' + str(x) in request.POST:
                    if request.POST['item_type' + str(x)] == "Per Unit":
                        item = SubcontractItems.objects.create(subcontract=subcontract1, SOV_description=request.POST[
                            'item_description' + str(x)], SOV_unit=request.POST['item_unit' + str(x)],
                                                               SOV_total_ordered=request.POST['item_quantity' + str(x)],
                                                               SOV_rate=request.POST['item_price' + str(x)],
                                                               notes=request.POST['item_notes' + str(x)],
                                                               date=date.today())
                        if 'wallcovering_number' + str(x) in request.POST:
                            if request.POST['wallcovering_number' + str(x)] != 'no_wc_selected':
                                item.wallcovering_id = Wallcovering.objects.get(
                                    id=request.POST['wallcovering_number' + str(x)])
                                item.save()
                    else:
                        item = SubcontractItems.objects.create(subcontract=subcontract1, SOV_description=request.POST[
                            'item_description' + str(x)], SOV_is_lump_sum=True, SOV_unit="Lump Sum",
                                                               SOV_total_ordered=request.POST['item_price' + str(x)],
                                                               SOV_rate=request.POST['item_price' + str(x)],
                                                               notes=request.POST['item_notes' + str(x)],
                                                               date=date.today())
                        if 'wallcovering_number' + str(x) in request.POST:
                            if request.POST['wallcovering_number' + str(x)] != 'no_wc_selected':
                                item.wallcovering_id = Wallcovering.objects.get(
                                    id=request.POST['wallcovering_number' + str(x)])
                                item.save()
            return redirect('subcontract', id=subcontract1.id)
    if request.method == 'GET' and request.GET.get('job_number'):
        select_job(request.GET.get('job_number'))
        return render(request, "subcontracts_new.html", send_data)

    send_data['selectedjob'] = 'ALL'
    if request.method == 'GET':
        if 'search_job' in request.GET:
            send_data['jobs'] = Jobs.objects.filter(is_closed=False, job_name__icontains=request.GET['search_job'])
        else:
            send_data['jobs'] = Jobs.objects.filter(is_closed=False)
    else:
        send_data['jobs'] = Jobs.objects.filter(is_closed=False)

    return render(request, "subcontracts_new.html", send_data)


@login_required(login_url='/accounts/login')
def subcontracts_home(request):
    send_data = {}
    if request.method == 'GET':
        if 'search1' in request.GET: send_data['search1_exists'] = True  # Include Closed Subcontracts
        if 'search2' in request.GET:send_data['search2_exists'] = True #show only labor done jobs
        if 'search3' in request.GET: send_data['search3_exists'] = True #show paid 100%
    search_subcontracts = SubcontractsFilter(request.GET, queryset=Subcontracts.objects.filter())
    today = datetime.date.today()
    this_friday = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=4)
    last_saturday = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(
        days=4) - datetime.timedelta(days=6)
    if today.weekday() > 4:
        this_friday += datetime.timedelta(days=7)
        last_saturday += datetime.timedelta(days=7)
    send_data['this_friday'] = this_friday
    send_data['last_saturday'] = last_saturday
    if request.method == 'POST':
        if request.POST['subcontract_id'] != "":
            return redirect('subcontract', id=request.POST['subcontract_id'])
        if request.POST['job_number'] != "":
            return redirect('job_page', jobnumber=request.POST['job_number'])
    subcontracts = []
    for x in search_subcontracts.qs:
        total_contract_amount = "$" + f"{int(x.total_contract_amount()):,d}"
        total_billed = "$" + f"{int(x.total_billed()):,d}"
        #
        total_paid = "$" + f"{int(x.total_paid()):,d}"
        pay_amount_this_week = "$" + f"{int(x.pay_amount_this_week()):,d}"
        retainage_this_week = "$" + f"{0-int(x.retainage_this_week()):,d}"
        approved_this_week = "$" + f"{int(x.amount_this_week()):,d}"
        billed_this_week = "$" + f"{int(x.original_request()):,d}"
        total_retainage_prior = "$" + f"{0-int(x.total_retainage_prior()):,d}"
        total_billed_prior = "$" + f"{int(x.total_billed_prior()):,d}"
        retainage_negative = False
        your_retainage = "$" + f"{0 - int(x.original_retainage_request()):,d}"
        if float(x.retainage_this_week()) < 0:
            retainage_negative = True
        change_orders = SubcontractItems.objects.filter(subcontract=x, is_approved=False).count()

        if request.method == 'GET':
            if 'search3' in request.GET and x.percent_complete() >= 1:
                subcontracts.append(
                    {'is_invoiced':x.is_invoiced_this_week(), 'is_approved':x.is_approved_this_week(),'your_retainage': your_retainage, 'total_contract_amount': total_contract_amount,
                     'total_billed': total_billed, 'total_paid': total_paid,
                     'pay_amount_this_week': pay_amount_this_week,
                     'retainage_negative': retainage_negative,
                     'retainage_this_week': retainage_this_week,
                     'approved_this_week': approved_this_week, 'billed_this_week': billed_this_week,
                     'total_retainage_prior': total_retainage_prior,
                     'total_billed_prior': total_billed_prior, 'labor_done': x.job_number.is_labor_done,
                     'change_orders': change_orders,
                     'job_name': x.job_number.job_name, 'job_number': x.job_number.job_number,
                     'subcontractor': x.subcontractor.company, 'subcontractor_id': x.subcontractor.id,
                     'po_number': x.po_number, 'id': x.id, 'retainage': x.total_retainage_approved(),
                     'percent_complete': format(x.percent_complete(), ".0%")})
            elif 'search3' not in request.GET:
                subcontracts.append({'is_invoiced':x.is_invoiced_this_week(), 'is_approved':x.is_approved_this_week(), 'your_retainage':your_retainage,'total_contract_amount': total_contract_amount, 'total_billed': total_billed,'total_paid': total_paid, 'pay_amount_this_week': pay_amount_this_week,
                                     'retainage_negative': retainage_negative,
                                     'retainage_this_week': retainage_this_week,
                                     'approved_this_week': approved_this_week, 'billed_this_week': billed_this_week,
                                     'total_retainage_prior': total_retainage_prior,
                                     'total_billed_prior': total_billed_prior, 'labor_done': x.job_number.is_labor_done, 'change_orders': change_orders,
                                     'job_name': x.job_number.job_name, 'job_number': x.job_number.job_number,
                                     'subcontractor': x.subcontractor.company, 'subcontractor_id': x.subcontractor.id,
                                     'po_number': x.po_number, 'id': x.id, 'retainage': x.total_retainage_approved(),
                                     'percent_complete': format(x.percent_complete(), ".0%")})
        else:
            subcontracts.append({'is_invoiced':x.is_invoiced_this_week(), 'is_approved':x.is_approved_this_week(), 'your_retainage': your_retainage, 'total_contract_amount': total_contract_amount,
                                 'total_billed': total_billed, 'total_paid': total_paid,
                                 'pay_amount_this_week': pay_amount_this_week,
                                 'retainage_negative': retainage_negative,
                                 'retainage_this_week': retainage_this_week,
                                 'approved_this_week': approved_this_week, 'billed_this_week': billed_this_week,
                                 'total_retainage_prior': total_retainage_prior,
                                 'total_billed_prior': total_billed_prior, 'labor_done': x.job_number.is_labor_done,
                                 'change_orders': change_orders,
                                 'job_name': x.job_number.job_name, 'job_number': x.job_number.job_number,
                                 'subcontractor': x.subcontractor.company, 'subcontractor_id': x.subcontractor.id,
                                 'po_number': x.po_number, 'id': x.id, 'retainage': x.total_retainage_approved(),
                                 'percent_complete': format(x.percent_complete(), ".0%")})

        send_data['subcontracts']=subcontracts
    return render(request, "subcontracts_home.html", send_data)


def subcontractor_payments(request):
    send_data = {}
    send_data['payments'] = SubcontractorPayments.objects.all().order_by('-date')

    if Email_Errors.objects.filter(user=request.user.first_name + " " + request.user.last_name).exists():
        error_message = ""
        send_data['error_message'] = Email_Errors.objects.filter(user=request.user.first_name + " " + request.user.last_name)
        for x in Email_Errors.objects.filter(user=request.user.first_name + " " + request.user.last_name):
            error_message += "-NOTE- " + x.error
        send_data['error_message']= error_message
    Email_Errors.objects.filter(user=request.user.first_name + " " + request.user.last_name).delete()
    if request.method == 'POST':
        if 'new_payment' in request.POST:
            return redirect('new_subcontractor_payment')
    return render(request, "subcontractor_payments.html", send_data)


def new_subcontractor_payment(request):
    send_data = {}
    if request.method == 'POST':
        send_data['selected_sub'] = request.POST['select_subcontractor']
        selected_sub = Subcontractors.objects.get(id=request.POST['select_subcontractor'])
        if 'check_number' in request.POST:
            if InvoiceBatch.objects.filter(invoice__subcontract__subcontractor=selected_sub, invoice__is_sent=True,
                                           invoice__processed=False).exists():
                def money(val):
                    try:
                        return f"{Decimal(str(val).replace(',', '')):,.2f}"
                    except (InvalidOperation, TypeError, ValueError):
                        return "0.00"
                raw_final_amount = request.POST.get('final_amount', '').replace(',', '').strip()
                try:
                    final_amount = Decimal(raw_final_amount)
                except (InvalidOperation, TypeError):
                    final_amount = Decimal('0.00')
                payment = SubcontractorPayments.objects.create(subcontractor=selected_sub,
                                                               date=request.POST['pay_date'],
                                                               check_number=request.POST['check_number'],
                                                               final_amount=final_amount,
                                                               notes=request.POST['note'])

                lines = [
                    "You have a new payment.",
                    "",
                    f"Payment Amount : ${money(payment.final_amount)}",
                    f"Check Number   : {payment.check_number}",
                ]
                for x in InvoiceBatch.objects.filter(invoice__subcontract__subcontractor=selected_sub,
                                                     invoice__is_sent=True, invoice__processed=False):
                    selected_invoice = x.invoice
                    subcontract = selected_invoice.subcontract
                    selected_invoice.processed = True
                    selected_invoice.payment = payment
                    amount_paid = selected_invoice.final_amount - selected_invoice.retainage
                    selected_invoice.save()
                    lines.extend([
                        "",
                        "-" * 50,
                        f"Job                                    : {subcontract.job_number.job_name}",
                        f"Amount Paid This Week: ${money(amount_paid)}",
                        f"Total Contract Amount  : ${money(subcontract.total_contract_amount())}",
                        f"Total Paid To Date           : ${money(subcontract.total_actually_paid())}",
                    ])
                    ready_to_close = True
                    #check to see if there are open invoices still
                    if SubcontractorInvoice.objects.filter(subcontract=subcontract, processed=False).exists():
                        ready_to_close = False

                    #1 - check that all invoices (billed and pending) equal 100%
                    for x in SubcontractItems.objects.filter(subcontract=subcontract):
                        totalcost = float(x.total_cost())
                        totalbilledandpending = float(x.total_billed_and_pending())
                        if totalcost == 0:
                            percentage = 0
                        else:
                            percentage = (totalbilledandpending / totalcost) * 100

                        if percentage < 100:
                            ready_to_close = False

                    if int(subcontract.total_retainage()) != 0:
                        ready_to_close = False

                    SubcontractNotes.objects.create(subcontract=subcontract, date=date.today(),
                                                    user=Employees.objects.get(user=request.user),
                                                    note="Invoice Paid on " + str(request.POST['pay_date']) + ". " +
                                                         request.POST['note'],
                                                    invoice=selected_invoice)
                    if ready_to_close == True:
                        subcontract.is_closed = True
                        subcontract.save()
                        SubcontractNotes.objects.create(subcontract=subcontract, date=date.today(),
                                                        user=Employees.objects.get(user=request.user),
                                                        note="Subcontract Paid and Closed. Total Contract=$" + str(
                                                            subcontract.total_contract_amount()) + ". Total Billed =$" + str(
                                                            subcontract.total_billed()) + ". Total Retainage =$" + str(
                                                            subcontract.total_retainage()))
                        Email_Errors.objects.create(user=request.user.first_name + " " + request.user.last_name,
                                                    error="Subcontract " + str(subcontract) + " CLOSED!",
                                                    date=date.today())
                    selected_invoice.save()
                recipients = ["admin1@gerloffpainting.com"]
                recipients.append("admin2@gerloffpainting.com")
                recipients.append("joe@gerloffpainting.com")

                if 'send_email' in request.POST:

                    if selected_sub.email:
                        recipients.append(selected_sub.email)
                    else:
                        Email_Errors.objects.create(user=request.user.first_name + " " + request.user.last_name,
                                                    error="Email Not Sent-No Email on File for Sub",
                                                    date=date.today())
                    check_sender = Employees.objects.filter(user=request.user).first() if request.user.is_authenticated else None
                    sender = check_sender.email if check_sender else "operations@gerloffpainting.com"
                    new_email_message = "\r\n".join(lines)
                    try:
                        Email.sendEmail("New Payment " + selected_sub.company, new_email_message, recipients, False,sender)
                        messages.success(request, "Email Sent Successfully")
                    except:
                        Email_Errors.objects.create(user=request.user.first_name + " " + request.user.last_name,
                                                    error="Email Not Sent",
                                                    date=date.today())
                InvoiceBatch.objects.all().delete()
            return redirect('subcontractor_payments')
        if 'selected_invoice' in request.POST:
            InvoiceBatch.objects.create(invoice=SubcontractorInvoice.objects.get(id=request.POST['selected_invoice']))
        if 'remove_invoice' in request.POST:
            InvoiceBatch.objects.get(id=request.POST['remove_invoice']).delete()
        invoices = []
        for x in SubcontractorInvoice.objects.filter(subcontract__subcontractor=selected_sub, is_sent=True,
                                                     processed=False, batch__isnull=True):
            invoices.append(

                {'subcontact_id':x.subcontract.id,'po_number':x.subcontract.po_number,'total': x.final_amount, 'retainage': x.retainage, 'id': x.id, 'pay_app_number': x.pay_app_number,

                 'job_name': x.subcontract.job_number.job_name, 'amount': x.final_amount - x.retainage,
                 'pay_date': x.pay_date})
        send_data['invoices'] = invoices
        selected_invoices = []
        final_amount = 0
        for x in InvoiceBatch.objects.filter(invoice__subcontract__subcontractor=selected_sub, invoice__is_sent=True,
                                             invoice__processed=False):

            selected_invoices.append({'subcontact_id':x.invoice.subcontract.id, 'po_number':x.invoice.subcontract.po_number,'total': x.invoice.final_amount, 'retainage': x.invoice.retainage, 'id': x.id,

                                      'pay_app_number': x.invoice.pay_app_number,
                                      'job_name': x.invoice.subcontract.job_number.job_name,
                                      'amount': x.invoice.final_amount - x.invoice.retainage,
                                      'pay_date': x.invoice.pay_date})
            final_amount += x.invoice.final_amount - x.invoice.retainage
        send_data['final_amount'] = final_amount
        send_data['selected_invoices'] = selected_invoices
        return render(request, "new_subcontractor_payment.html", send_data)
    else:
        InvoiceBatch.objects.all().delete()
    subcontractors = []
    for x in Subcontractors.objects.all():
        if x.needs_payment() == True:
            subcontractors.append({'id': x.id, 'company': x.company})
    send_data['subcontractors'] = subcontractors
    return render(request, "new_subcontractor_payment.html", send_data)

def build_subcontractor_approvers(request):
    for x in Subcontractors.objects.all():
        if not Subcontractor_Approvers.objects.filter(subcontractor=x).exists():
            for y in Standard_Approvers.objects.all():
                if y.employee:
                    Subcontractor_Approvers.objects.create(subcontractor=x,employee=y.employee)
                if y.job_description:
                    Subcontractor_Approvers.objects.create(subcontractor=x, job_description=y.job_description)
    for x in Subcontracts.objects.all():
        if not Subcontract_Approvers.objects.filter(subcontract=x).exists():
            for y in Subcontractor_Approvers.objects.filter(subcontractor=x.subcontractor):
                if y.employee:
                    Subcontract_Approvers.objects.create(subcontract=x,employee=y.employee)
                if y.job_description:
                    Subcontract_Approvers.objects.create(subcontract=x, job_description=y.job_description)
    return redirect('admin_home')

def subcontractor_approvers(request,subcontractor_id):
    send_data={}
    subcontractor = Subcontractors.objects.get(id=subcontractor_id)
    if request.method == 'POST':
        for x in request.POST:
            if x[0:6] == 'delete':
                item_number = x[6:len(x)]
                Subcontractor_Approvers.objects.get(id=item_number).delete()
            if x == 'add_new_approver':
                if request.POST['add_new'] == 'Superintendent':
                    if not Subcontractor_Approvers.objects.filter(subcontractor=subcontractor,job_description="Superintendent").exists():
                        Subcontractor_Approvers.objects.create(subcontractor=subcontractor,job_description="Superintendent")
                else:
                    employee=Employees.objects.get(id=request.POST['add_new'])
                    if not Subcontractor_Approvers.objects.filter(subcontractor=subcontractor,employee=employee).exists():
                        Subcontractor_Approvers.objects.create(subcontractor=subcontractor,employee=employee)
    send_data['subcontractor']=subcontractor
    send_data['employees']= Employees.objects.all()
    send_data['approvers']=Subcontractor_Approvers.objects.filter(subcontractor=subcontractor)
    return render(request, "subcontractor_approvers.html", send_data)

def subcontractor_portal_select_job_for_ticket(request,subcontractor_id,employee_id):
    send_data = {}
    subcontractor = Subcontractors.objects.get(id=subcontractor_id)
    send_data['employee_id'] = employee_id
    if employee_id == "0":
        jobs = Jobs.objects.filter(
            subcontracts__subcontractor=subcontractor
        ).distinct().order_by('job_name')
    else:
        selected_employee = Subcontractor_Employees.objects.filter(id=employee_id).first()
        if selected_employee.has_access_to_TM:
            jobs = Jobs.objects.filter(
                subcontractor_job_assignments__employee=selected_employee
            ).distinct().order_by('job_name')
    job_list = []

    for job in jobs:

        changeorders = ChangeOrders.objects.filter(job_number=job)

        not_completed = 0
        not_signed = 0

        for co in changeorders:
            action = _subcontractor_portal_tm_ticket_action(co, subcontractor)

            if action == "create":
                not_completed += 1

            elif action == "sign":
                not_signed += 1

        # only show job if there is work
        if not_completed > 0 or not_signed > 0:
            job_list.append({
                "job": job,
                "not_completed": not_completed,
                "not_signed": not_signed
            })
    send_data['jobs']=job_list
    send_data['subcontractor']=subcontractor

    return render(request, "subcontractor_portal_select_job_for_ticket.html", send_data)

def subcontractor_portal_select_changeorder(request,job_number, subcontractor_id,employee_id):
    send_data = {}
    send_data['employee_id'] = employee_id
    subcontractor = Subcontractors.objects.get(id=subcontractor_id)
    job = Jobs.objects.get(job_number=job_number)

    all_changeorders = ChangeOrders.objects.filter(
        job_number=job,
        is_closed=False
    ).order_by("cop_number")

    changeorders = []

    for co in all_changeorders:

        action = _subcontractor_portal_tm_ticket_action(co, subcontractor)

        if action:
            co.portal_ticket_action = action
            changeorders.append(co)
    send_data['changeorders'] = changeorders
    send_data['subcontractor']= subcontractor
    send_data['job']= job
    return render(request, "subcontractor_portal_select_changeorder.html", send_data)

def safe_decimal(val):
    try:
        return Decimal(val or "0")
    except:
        return Decimal("0")

def subcontractor_portal_create_ticket(request,changeorder_id,subcontractor_id,employee_id2):
    send_data = {}
    send_data['employee_id'] = employee_id2
    subcontractor = Subcontractors.objects.get(id=subcontractor_id)
    change_order = ChangeOrders.objects.get(id=changeorder_id)


    # --------------------------------------------------
    # GET REQUEST
    # --------------------------------------------------
    if request.method == "GET":
        context = {
            "change_order": change_order,
            "tm_materials": TMPricesMaster.objects.filter(category="Material"),
            "tm_equipment": TMPricesMaster.objects.filter(category="Equipment"),
            "tm_sundries": TMPricesMaster.objects.filter(category="Sundries"),
            "employees": None,
            "employee_id":employee_id2,
        }

        return render(request, "subcontractor_portal_create_ticket.html", context)
    # --------------------------------------------------
    # POST REQUEST
    # --------------------------------------------------
    if request.method == "POST":

        # --------------------------------------------------
        # 1️⃣ Create EWT Header
        # --------------------------------------------------
        ewt = EWT.objects.create(
            change_order=change_order,
            week_ending=request.POST.get("week_ending"),
            notes=request.POST.get("notes"),
            completed_by=subcontractor.contact,
        )
        change_order.created_by_subcontractor=subcontractor
        change_order.save()
        ChangeOrderNotes.objects.create(cop_number=change_order, date=date.today(),
                                        user=Employees.objects.get(id=42),
                                        note="Extra Work Ticket Added")

        # --------------------------------------------------
        # 2️⃣ LABOR
        # --------------------------------------------------

        painter_count = int(request.POST.get("painter_count", 0))

        # Fetch masters safely once
        try:
            regular_master = TMPricesMaster.objects.get(item="Painter Hours")
        except TMPricesMaster.DoesNotExist:
            regular_master = None

        try:
            ot_master = TMPricesMaster.objects.get(item="Painter Hours OT")
        except TMPricesMaster.DoesNotExist:
            ot_master = None

        for i in range(1, painter_count + 1):

            employee_id = request.POST.get(f"employee_{i}")
            custom_employee = request.POST.get(f"custom_employee_{i}")
            regular_exists = request.POST.get(f"regular_exists_{i}") == "1"
            ot_exists = request.POST.get(f"ot_exists_{i}") == "1"

            # Collect daily hours safely
            reg_days = {}
            ot_days = {}

            total_regular = Decimal("0")
            total_ot = Decimal("0")

            for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
                reg_val = safe_decimal(request.POST.get(f"reg_{day}_{i}"))
                ot_val = safe_decimal(request.POST.get(f"ot_{day}_{i}"))

                reg_days[day] = reg_val or Decimal("0")
                ot_days[day] = ot_val or Decimal("0")

                total_regular += reg_days[day]
                total_ot += ot_days[day]

            # Skip completely empty painter rows
            if total_regular == 0 and total_ot == 0:
                continue

            # Safe employee lookup
            employee_obj = None
            if employee_id:
                try:
                    employee_obj = Employees.objects.get(id=employee_id)
                except Employees.DoesNotExist:
                    employee_obj = None

            # ---------------------------
            # Regular Hours Entry
            # ---------------------------
            if total_regular > 0 and regular_master:
                EWTicket.objects.create(
                    EWT=ewt,
                    master=regular_master,
                    category=regular_master.category,
                    employee=employee_obj,
                    custom_employee=custom_employee,
                    monday=reg_days["monday"],
                    tuesday=reg_days["tuesday"],
                    wednesday=reg_days["wednesday"],
                    thursday=reg_days["thursday"],
                    friday=reg_days["friday"],
                    saturday=reg_days["saturday"],
                    sunday=reg_days["sunday"],
                    ot=False,
                    units=regular_master.unit,
                    description=regular_master.item
                )

            # ---------------------------
            # OT Hours Entry
            # ---------------------------
            if total_ot > 0 and ot_master:
                EWTicket.objects.create(
                    EWT=ewt,
                    master=ot_master,
                    category=ot_master.category,
                    employee=employee_obj,
                    custom_employee=custom_employee,
                    monday=ot_days["monday"],
                    tuesday=ot_days["tuesday"],
                    wednesday=ot_days["wednesday"],
                    thursday=ot_days["thursday"],
                    friday=ot_days["friday"],
                    saturday=ot_days["saturday"],
                    sunday=ot_days["sunday"],
                    ot=True,
                    units=ot_master.unit,
                    description=ot_master.item
                )

        # --------------------------------------------------
        # 3️⃣ MATERIALS
        # --------------------------------------------------

        material_count = int(request.POST.get("material_count", 0))

        for i in range(1, material_count + 1):

            master_id = request.POST.get(f"material_master_{i}")
            desc = (request.POST.get(f"material_description_{i}") or "").strip()
            qty_raw = request.POST.get(f"material_quantity_{i}")
            units_raw = request.POST.get(f"material_units_{i}")

            qty = safe_decimal(qty_raw)

            # Skip completely empty rows
            if not qty or not desc:
                continue

            master = None
            category = None
            units = None

            # 🔹 If linked to TMPricesMaster
            if master_id and master_id != "new":

                try:
                    master = TMPricesMaster.objects.get(id=master_id)
                    category = master.category
                    units = master.unit
                except TMPricesMaster.DoesNotExist:
                    continue  # invalid master id — skip safely

            # 🔹 If Add New selected
            else:
                units = (units_raw or "").strip()

            EWTicket.objects.create(
                EWT=ewt,
                master=master,
                category="Material",
                description=desc,
                quantity=qty,
                units=units
            )

        # --------------------------------------------------
        # 4️⃣ EQUIPMENT
        # --------------------------------------------------

        equipment_count = int(request.POST.get("equipment_count", 0))

        for i in range(1, equipment_count + 1):

            master_id = request.POST.get(f"equipment_master_{i}")
            desc = (request.POST.get(f"equipment_description_{i}") or "").strip()
            qty_raw = request.POST.get(f"equipment_quantity_{i}")
            units_raw = request.POST.get(f"equipment_units_{i}")

            qty = safe_decimal(qty_raw)

            if not qty or not desc:
                continue

            master = None
            units = None

            if master_id and master_id != "new":

                try:
                    master = TMPricesMaster.objects.get(id=master_id)
                    units = master.unit
                except TMPricesMaster.DoesNotExist:
                    continue
            else:
                units = (units_raw or "").strip()

            EWTicket.objects.create(
                EWT=ewt,
                master=master,
                category="Equipment",  # 🔥 ALWAYS set category
                description=desc,
                quantity=qty,
                units=units
            )
        # --------------------------------
        # 5️⃣ SUNDRIES
        # --------------------------------
        sundries_count = int(request.POST.get("sundries_count", 0))

        for i in range(1, sundries_count + 1):

            master_id = request.POST.get(f"sundries_master_{i}")
            desc = (request.POST.get(f"sundries_description_{i}") or "").strip()
            qty_raw = request.POST.get(f"sundries_quantity_{i}")
            units_raw = request.POST.get(f"sundries_units_{i}")

            qty = safe_decimal(qty_raw)

            if not qty or not desc:
                continue

            master = None
            units = None

            if master_id and master_id != "new":
                try:
                    master = TMPricesMaster.objects.get(id=master_id)
                    units = master.unit
                except TMPricesMaster.DoesNotExist:
                    continue
            else:
                units = (units_raw or "").strip()

            EWTicket.objects.create(
                EWT=ewt,
                master=master,
                category="Sundries",  # 🔥 always set manually
                description=desc,
                quantity=qty,
                units=units
            )
        if "get_signature_now" in request.POST:
            return redirect("subcontractor_portal_get_signature", change_order.id, subcontractor_id, employee_id2)

        elif "email_signature" in request.POST:
            return redirect("subcontractor_portal_email_for_signature", change_order.id, subcontractor_id, employee_id2)

        else:
            if employee_id2 == "0":
                return redirect("portal",subcontractor.id, 'ALL')
            else:
                return redirect("subcontractor_employee_portal",employee_id2)
        # return redirect("extra_work_ticket", id=change_order.id)


def subcontractor_portal_select_ticket_for_signature(request, subcontractor_id,employee_id):
    send_data = {}
    send_data['employee_id'] = employee_id
    subcontractor = Subcontractors.objects.get(id=subcontractor_id)
    all_changeorders = ChangeOrders.objects.filter(
        created_by_subcontractor=subcontractor,
        is_closed=False
    ).order_by("cop_number")

    changeorders = []

    for co in all_changeorders:

        status = co.status()

        if status == "Ticket Not Signed":
            changeorders.append(co)
    send_data['changeorders'] = changeorders
    send_data['subcontractor']= subcontractor
    return render(request, "subcontractor_portal_select_ticket_for_signature.html", send_data)

def subcontractor_portal_get_signature(request, changeorder_id, subcontractor_id,employee_id):
    send_data = {}
    send_data['employee_id'] = employee_id
    status = "NEW"
    subcontractor = Subcontractors.objects.get(id=subcontractor_id)
    changeorder = ChangeOrders.objects.get(id=changeorder_id)
    ewt = EWT.objects.get(change_order=changeorder)
    try:
        signature = Signature.objects.get(change_order_id=id)
    except:
        signature = None
    laboritems = EWTicket.objects.filter(EWT=ewt).exclude(employee=None, custom_employee=None)
    # materials = EWTicket.objects.filter(EWT=ewt, master__category="Material")
    # equipment = EWTicket.objects.filter(EWT=ewt, master__category="Equipment")
    # sundries = EWTicket.objects.filter(EWT=ewt, master__category="Sundries")
    materials = EWTicket.objects.filter(EWT=ewt, category="Material")
    equipment = EWTicket.objects.filter(EWT=ewt, category="Equipment")
    sundries = EWTicket.objects.filter(EWT=ewt, category="Sundries")
    if request.method == 'POST':
        signatureValue = request.POST['signatureValue']
        nameValue = request.POST['signatureName']
        comments = request.POST['gc_notes']
        if signature is None:
            Signature.objects.create(change_order_id=changeorder.id, type="changeorder", name=nameValue, signature=signatureValue,
                                     date=date.today(), notes=comments)
        else:
            Signature.objects.update(change_order_id=id, type="changeorder", name=nameValue, signature=signatureValue,
                                     date=date.today(), notes=comments)
        ChangeOrderNotes.objects.create(cop_number=changeorder, date=date.today(),
                                        user=Employees.objects.get(id=42),
                                        note="Digital Signature Received. Signed by: " + request.POST[
                                            'signatureName'] + ". Comments: " + request.POST['gc_notes'])
        changeorder.is_ticket_signed = True
        changeorder.digital_ticket_signed_date = date.today()
        changeorder.save()
        signature = Signature.objects.filter(change_order_id=changeorder.id).first()
        # Build folder path
        path = os.path.join(
            settings.MEDIA_ROOT,
            "changeorder",
            f"{changeorder.job_number.job_number} COP #{changeorder.cop_number}"
        )
        # Create folder if it doesn't exist
        os.makedirs(path, exist_ok=True)

        # Build full PDF file path
        file_path = os.path.join(
            path,
            f"Signed_Extra_Work_Ticket_{date.today()}.pdf"
        )
        with open(file_path, "w+b") as result_file:
            html = render_to_string("signed_ticket_pdf.html",
                                    {'sundries': sundries, 'equipment': equipment, 'materials': materials,
                                     'laboritems': laboritems, 'ewt': ewt,
                                     'changeorder': changeorder, 'signature': signature, 'status': status,
                                     'is_emailed_link': True})
            # Create PDF
            pisa.CreatePDF(
                html,
                dest=result_file,
                link_callback=link_callback
            )
            result_file.close()
        # with open(file_path, "w+b") as result_file:
        #     pisa.CreatePDF(html, dest=result_file)
        return redirect('subcontractor_portal_email_signed_ticket', changeorder_id=changeorder.id,subcontractor_id=subcontractor_id,employee_id=employee_id)

    return render(request, "subcontractor_portal_get_signature.html",
                  {'sundries': sundries, 'equipment': equipment, 'materials': materials, 'laboritems': laboritems,
                   'ewt': ewt,
                   'changeorder': changeorder, 'signature': signature, 'status': status,'subcontractor':subcontractor,'employee_id':employee_id})



def subcontractor_portal_email_for_signature(request, changeorder_id, subcontractor_id,employee_id):
    send_data={}
    send_data['employee_id'] = employee_id
    changeorder = ChangeOrders.objects.get(id=changeorder_id)
    subcontractor = Subcontractors.objects.get(id=subcontractor_id)
    job = changeorder.job_number
    client = job.client
    if request.method == 'POST':
        # name = request.POST['recipient_name']
        # phone = request.POST['recipient_phone']
        email = request.POST['email']
        # recipient_id = request.POST['recipient']
        ewt = EWT.objects.get(change_order=changeorder)
        ewt.recipient = email
        ewt.save()
        job_name = job.job_name
        approval_path = reverse('emailed_ticket', args=[changeorder.id])
        approval_link = "http://184.183.68.156" + approval_path

        email_body = (
            f"You have received an extra work ticket from Gerloff Painting "
            f"for {changeorder.description} at {job_name}.\n\n"
            f"Please click this link to view the ticket:\n"
            f"{approval_link}"
        )
        recipients = ["joe@gerloffpainting.com"]
        recipients.append(email)
        gp_super = job.superintendent.email
        if gp_super:
            recipients.append(gp_super)
        check_sender = Employees.objects.filter(user=request.user).first() if request.user.is_authenticated else None
        sender = check_sender.email if check_sender else "bridgette@gerloffpainting.com"
        if check_sender:
            email_body += (f"\n\n"
                          f"Sincerely,"
                          f"\n"
                          f"{request.user.first_name} {request.user.last_name}"
                          f"\n"
                          f"Gerloff Painting, Inc."
                          f"\n"
                          f"(757) 857-4880"
                          )
        else:
            email_body += (f"\n\n"
                          f"Sincerely,"
                          f"\n"
                          f"Bridgette Clause"
                          f"\n"
                          f"Gerloff Painting, Inc."
                          f"\n"
                          f"(757) 857-4880"
                          )
        try:
            Email.sendEmail("Extra Work Ticket", email_body, recipients, False,sender)
            messages.success(request, "The email with the link to the extra work ticket was successfully sent!")
            ewt = EWT.objects.get(change_order=changeorder)
            ewt.recipient = email
            ewt.save()
            ChangeOrderNotes.objects.create(note="Ticket Emailed To: " + str(email),
                                            cop_number=changeorder, date=date.today(),
                                            user=Employees.objects.get(id=42))
        except Exception as e:
            messages.error(request,"ERROR! The email with the extra work ticket failed to send. Please try again later. ")
            ChangeOrderNotes.objects.create(note="Attempted to Email Ticket For Signature, But Email Failed. Tried to send to: " + str(email),
                                            cop_number=changeorder, date=date.today(),
                                            user=Employees.objects.get(id=42))
        if employee_id == "0":
            return redirect('portal', sub_id=subcontractor.id, contract_id='ALL')
        else:
            return redirect('subcontractor_employee_portal',employee_id=employee_id)
    client_employees = ClientEmployees.objects.filter(id=client,is_active=True).order_by('name')
    send_data['client_employees'] = client_employees
    return render(request, 'subcontractor_portal_email_for_signature.html',send_data)

def subcontractor_portal_ewt_edit(request, changeorder_id, subcontractor_id,employee_id2):

    send_data = {}
    send_data['employee_id'] = employee_id2
    subcontractor = Subcontractors.objects.get(id=subcontractor_id)
    change_order = ChangeOrders.objects.get(id=changeorder_id)
    send_data['changeorder'] = change_order
    send_data['subcontractor'] = subcontractor
    ewt = get_object_or_404(EWT, change_order=change_order)

    # =====================================================
    # POST — UPDATE + REBUILD
    # =====================================================
    def safe_decimal(value):
        try:
            return Decimal(value or "0")
        except:
            return Decimal("0")

    if request.method == "POST":
        with transaction.atomic():

            # --------------------------------------------------
            # 1️⃣ Update EWT Header (do NOT recreate header)
            # --------------------------------------------------
            ewt.week_ending = request.POST.get("week_ending")
            ewt.notes = request.POST.get("notes")
            ewt.completed_by = subcontractor.company
            ewt.save()

            # Optional: add a note that it was edited
            try:
                ChangeOrderNotes.objects.create(
                    cop_number=change_order,
                    date=date.today(),
                    user=Employees.objects.get(id=42),
                    note="Extra Work Ticket Updated",
                )
            except:
                pass

            # --------------------------------------------------
            # 2️⃣ Delete existing ticket rows and rebuild
            # --------------------------------------------------
            EWTicket.objects.filter(EWT=ewt).delete()

            days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

            # --------------------------------------------------
            # 3️⃣ LABOR (match create behavior: use masters + totals)
            # --------------------------------------------------
            painter_count = int(request.POST.get("painter_count", 0))

            # Fetch masters once
            regular_master = TMPricesMaster.objects.filter(item="Painter Hours").first()
            ot_master = TMPricesMaster.objects.filter(item="Painter Hours OT").first()

            for i in range(1, painter_count + 1):

                employee_id = request.POST.get(f"employee_{i}")
                custom_employee = request.POST.get(f"custom_employee_{i}")

                # Collect daily hours + totals
                reg_days = {}
                ot_days = {}
                total_regular = Decimal("0")
                total_ot = Decimal("0")

                for day in days:
                    reg_val = safe_decimal(request.POST.get(f"reg_{day}_{i}"))
                    ot_val = safe_decimal(request.POST.get(f"ot_{day}_{i}"))

                    reg_days[day] = reg_val
                    ot_days[day] = ot_val

                    total_regular += reg_val
                    total_ot += ot_val

                # Skip fully empty painter row
                if total_regular == 0 and total_ot == 0:
                    continue

                # Safe employee lookup
                employee_obj = None
                if employee_id:
                    employee_obj = Employees.objects.filter(id=employee_id).first()

                # Regular entry
                if total_regular > 0 and regular_master:
                    EWTicket.objects.create(
                        EWT=ewt,
                        master=regular_master,
                        category=regular_master.category or "Labor",
                        employee=employee_obj,
                        custom_employee=custom_employee,
                        monday=reg_days["monday"],
                        tuesday=reg_days["tuesday"],
                        wednesday=reg_days["wednesday"],
                        thursday=reg_days["thursday"],
                        friday=reg_days["friday"],
                        saturday=reg_days["saturday"],
                        sunday=reg_days["sunday"],
                        ot=False,
                        units=regular_master.unit,
                        description=regular_master.item,
                    )

                # OT entry
                if total_ot > 0 and ot_master:
                    EWTicket.objects.create(
                        EWT=ewt,
                        master=ot_master,
                        category=ot_master.category or "Labor",
                        employee=employee_obj,
                        custom_employee=custom_employee,
                        monday=ot_days["monday"],
                        tuesday=ot_days["tuesday"],
                        wednesday=ot_days["wednesday"],
                        thursday=ot_days["thursday"],
                        friday=ot_days["friday"],
                        saturday=ot_days["saturday"],
                        sunday=ot_days["sunday"],
                        ot=True,
                        units=ot_master.unit,
                        description=ot_master.item,
                    )

            # --------------------------------------------------
            # 4️⃣ MATERIALS (match create behavior: master vs new)
            # --------------------------------------------------
            material_count = int(request.POST.get("material_count", 0))

            for i in range(1, material_count + 1):
                master_id = request.POST.get(f"material_master_{i}")
                desc = (request.POST.get(f"material_description_{i}") or "").strip()
                qty = safe_decimal(request.POST.get(f"material_quantity_{i}"))
                units_raw = (request.POST.get(f"material_units_{i}") or "").strip()

                # Skip empty rows
                if qty <= 0 or not desc:
                    continue

                master = None
                units = None

                if master_id and master_id != "new":
                    master = TMPricesMaster.objects.filter(id=master_id).first()
                    if not master:
                        continue
                    units = master.unit
                else:
                    units = units_raw  # allow custom units

                EWTicket.objects.create(
                    EWT=ewt,
                    master=master,
                    category="Material",
                    description=desc,
                    quantity=qty,
                    units=units,
                )

            # --------------------------------------------------
            # 5️⃣ EQUIPMENT
            # --------------------------------------------------
            equipment_count = int(request.POST.get("equipment_count", 0))

            for i in range(1, equipment_count + 1):
                master_id = request.POST.get(f"equipment_master_{i}")
                desc = (request.POST.get(f"equipment_description_{i}") or "").strip()
                qty = safe_decimal(request.POST.get(f"equipment_quantity_{i}"))
                units_raw = (request.POST.get(f"equipment_units_{i}") or "").strip()

                if qty <= 0 or not desc:
                    continue

                master = None
                units = None

                if master_id and master_id != "new":
                    master = TMPricesMaster.objects.filter(id=master_id).first()
                    if not master:
                        continue
                    units = master.unit
                else:
                    units = units_raw

                EWTicket.objects.create(
                    EWT=ewt,
                    master=master,
                    category="Equipment",
                    description=desc,
                    quantity=qty,
                    units=units,
                )

            # --------------------------------------------------
            # 6️⃣ SUNDRIES
            # --------------------------------------------------
            sundries_count = int(request.POST.get("sundries_count", 0))

            for i in range(1, sundries_count + 1):
                master_id = request.POST.get(f"sundries_master_{i}")
                desc = (request.POST.get(f"sundries_description_{i}") or "").strip()
                qty = safe_decimal(request.POST.get(f"sundries_quantity_{i}"))
                units_raw = (request.POST.get(f"sundries_units_{i}") or "").strip()

                if qty <= 0 or not desc:
                    continue

                master = None
                units = None

                if master_id and master_id != "new":
                    master = TMPricesMaster.objects.filter(id=master_id).first()
                    if not master:
                        continue
                    units = master.unit
                else:
                    units = units_raw

                EWTicket.objects.create(
                    EWT=ewt,
                    master=master,
                    category="Sundries",
                    description=desc,
                    quantity=qty,
                    units=units,
                )
        if "get_signature_now" in request.POST:
            return redirect("subcontractor_portal_get_signature", change_order.id, subcontractor_id,employee_id2)

        elif "email_signature" in request.POST:
            return redirect("subcontractor_portal_email_for_signature", change_order.id, subcontractor_id,employee_id2)

        else:
            if employee_id2 == "0":
                return redirect('portal', sub_id=subcontractor.id, contract_id='ALL')
            else:
                return redirect('subcontractor_employee_portal', employee_id=employee_id2)



    # =====================================================
    # GET — BUILD DATA FOR TEMPLATE
    # =====================================================

    tickets = EWTicket.objects.filter(EWT=ewt)

    # ---------------- GROUP LABOR ----------------
    labor_map = {}

    for t in tickets.filter(category="Labor"):

        key = (t.employee.id if t.employee else None, t.custom_employee)

        if key not in labor_map:
            labor_map[key] = {
                "employee": t.employee,
                "custom_employee": t.custom_employee,
                "regular": None,
                "ot": None
            }

        day_data = {
            "monday": t.monday,
            "tuesday": t.tuesday,
            "wednesday": t.wednesday,
            "thursday": t.thursday,
            "friday": t.friday,
            "saturday": t.saturday,
            "sunday": t.sunday,
        }

        if t.ot:
            labor_map[key]["ot"] = day_data
        else:
            labor_map[key]["regular"] = day_data

    labor_list = list(labor_map.values())
    labor_count = len(labor_list)

    # ---------------- SIMPLE LISTS ----------------
    materials = tickets.filter(category="Material")
    equipment = tickets.filter(category="Equipment")
    sundries = tickets.filter(category="Sundries")

    # ---------------- COUNTS ----------------
    material_count = materials.count()
    equipment_count = equipment.count()
    sundries_count = sundries.count()

    return render(request, "subcontractor_portal_ewt_edit.html", {
        "ewt": ewt,
        "change_order": change_order,
        "labor_list": labor_list,
        "labor_count": labor_count,
        "materials": materials,
        "equipment": equipment,
        "sundries": sundries,
        "material_count": material_count,
        "equipment_count": equipment_count,
        "sundries_count": sundries_count,
        "tm_materials": TMPricesMaster.objects.filter(category="Material"),
        "tm_equipment": TMPricesMaster.objects.filter(category="Equipment"),
        "tm_sundries": TMPricesMaster.objects.filter(category="Sundries"),
        "employees": Employees.objects.filter(active=True),
        "employee_id": employee_id2,
    })

def subcontractor_portal_email_signed_ticket(request,changeorder_id,subcontractor_id,employee_id):
    send_data={}
    send_data['employee_id'] = employee_id
    changeorder = ChangeOrders.objects.get(id=changeorder_id)
    subcontractor = Subcontractors.objects.get(id=subcontractor_id)
    send_data = {}
    send_data['changeorder'] = changeorder
    if request.method != 'POST':
        for x in TempRecipients.objects.filter(changeorder=changeorder):
            x.delete()
    if request.method == 'POST':
        for x in request.POST:
            if x[0:11] == 'updateemail':
                person = ClientEmployees.objects.get(person_pk=x[11:len(x)])
                person.email = request.POST['email' + str(person.person_pk)]
                person.save()
            if x[0:6] == 'remove':
                person = ClientEmployees.objects.get(person_pk=x[6:len(x)])
                ClientJobRoles.objects.filter(role="Extra Work Tickets", job=changeorder.job_number,
                                              employee=person).delete()
            if x[0:10] == 'adddefault':
                person = ClientEmployees.objects.get(person_pk=x[10:len(x)])
                ClientJobRoles.objects.create(role="Extra Work Tickets", job=changeorder.job_number, employee=person)
            if x[0:10] == 'tempremove':
                person = ClientEmployees.objects.get(person_pk=x[10:len(x)])
                TempRecipients.objects.filter(changeorder=changeorder, person=person).delete()
            if x[0:7] == 'tempadd':
                if not request.POST.get(
                        "addrecipient").isdigit():  # checks to see if they are adding a new person to database
                    new_client_name = request.POST.get("addrecipient")  # typed name from dropdown
                    new_client_email = request.POST.get("new_contact_email")
                    person = ClientEmployees.objects.create(id=changeorder.job_number.client, name=new_client_name,
                                                            email=new_client_email)
                else:
                    person = ClientEmployees.objects.get(person_pk=request.POST['addrecipient'])
                TempRecipients.objects.create(person=person, changeorder=changeorder)
            if x[0:10] == 'defaultadd':
                if not request.POST.get(
                        "addrecipient").isdigit():  # checks to see if they are adding a new person to database
                    new_client_name = request.POST.get("addrecipient")  # typed name from dropdown
                    new_client_email = request.POST.get("new_contact_email")
                    person = ClientEmployees.objects.create(id=changeorder.job_number.client, name=new_client_name,
                                                            email=new_client_email)
                else:
                    person = ClientEmployees.objects.get(person_pk=request.POST['addrecipient'])
                if not ClientJobRoles.objects.filter(role="Extra Work Tickets", job=changeorder.job_number,
                                                     employee=person).exists():
                    ClientJobRoles.objects.create(role="Extra Work Tickets", job=changeorder.job_number,
                                                  employee=person)
                    TempRecipients.objects.create(person=person, changeorder=changeorder)
            if x[0:5] == 'final':
                recipients = ["bridgette@gerloffpainting.com"]
                bridgette = Employees.objects.get(first_name="Bridgette", last_name="Clause")
                current_user = Employees.objects.get(id=42)
                subcontractor_email = subcontractor.email
                if subcontractor_email:
                    recipients.append(subcontractor.email)
                if x == 'final1':
                    for y in request.POST:
                        if y[0:5] == 'email':
                            recipients.append(request.POST[y])
                ChangeOrderNotes.objects.create(cop_number=changeorder, date=date.today(),
                                                user=current_user,
                                                note="Signed Ticket emailed to " + str(recipients))
                path = os.path.join(settings.MEDIA_ROOT, "changeorder",
                                    str(changeorder.job_number.job_number) + " COP #" + str(changeorder.cop_number))
                job_name = changeorder.job_number.job_name
                check_sender = Employees.objects.filter(user=request.user).first() if request.user.is_authenticated else None
                sender = check_sender.email if check_sender else "bridgette@gerloffpainting.com"
                if check_sender:
                    email_body = (f"Please find the Signed Extra Work Ticket attached for {job_name}"
                                  f"\n\n"
                                  f"Sincerely,"
                                  f"\n"
                                  f"{request.user.first_name} {request.user.last_name}"
                                  f"\n"
                                  f"Gerloff Painting, Inc."
                                  f"\n"
                                  f"(757) 857-4880"
                                  )
                else:
                    email_body = (f"Please find the Signed Extra Work Ticket attached for {job_name}"
                                  f"\n\n"
                                  f"Sincerely,"
                                  f"\n"
                                  f"Bridgette Clause"
                                  f"\n"
                                  f"Gerloff Painting, Inc."
                                  f"\n"
                                  f"(757) 857-4880"
                                  )
                try:
                    Email.sendEmail(f"Signed Ticket {job_name}",
                                    email_body, recipients,
                                    f"{path}/Signed_Extra_Work_Ticket_{date.today()}.pdf",sender)
                    messages.success(request, "Email was successfully sent")
                except:
                    messages.error(request, "Email Failed to Send!")
                if employee_id == "0":
                    return redirect('portal', sub_id=subcontractor.id, contract_id='ALL')
                else:
                    return redirect('subcontractor_employee_portal', employee_id=employee_id)
    extra_contacts = False
    project_pm = ClientEmployees.objects.get(person_pk=changeorder.job_number.client_Pm.person_pk)
    client_list = []
    if TempRecipients.objects.filter(changeorder=changeorder, default=False).exists():
        if TempRecipients.objects.filter(changeorder=changeorder, default=True).exists():
            TempRecipients.objects.filter(changeorder=changeorder, default=True).delete()
    if not ClientJobRoles.objects.filter(role="Extra Work Tickets", job=changeorder.job_number):
        if not TempRecipients.objects.filter(changeorder=changeorder):
            TempRecipients.objects.create(person=project_pm, changeorder=changeorder, default=True)
    else:  # means there is a default person
        if not TempRecipients.objects.filter(
                changeorder=changeorder):  # this will add all default as temp recipients if there are no temp recipients
            for x in ClientJobRoles.objects.filter(role="Extra Work Tickets", job=changeorder.job_number):
                TempRecipients.objects.create(person=x.employee, changeorder=changeorder)
    for x in ClientEmployees.objects.filter(id=changeorder.job_number.client, is_active=True).order_by('name'):
        if ClientJobRoles.objects.filter(role="Extra Work Tickets", job=changeorder.job_number, employee=x).exists():
            if TempRecipients.objects.filter(changeorder=changeorder, person=x).exists():
                client_list.append(
                    {'person_pk': x.person_pk, 'name': x.name, 'default': True, 'current': True, 'email': x.email})
            else:
                extra_contacts = True
                client_list.append(
                    {'person_pk': x.person_pk, 'name': x.name, 'default': True, 'current': False, 'email': x.email})
        else:
            if TempRecipients.objects.filter(person=x, changeorder=changeorder).exists():
                client_list.append(
                    {'person_pk': x.person_pk, 'name': x.name, 'default': False, 'current': True, 'email': x.email})
            else:
                extra_contacts = True
                client_list.append(
                    {'person_pk': x.person_pk, 'name': x.name, 'default': False, 'current': False, 'email': x.email})
    client_list = sorted(client_list, key=lambda x: x['name'].lower())
    return render(request, "subcontractor_portal_email_signed_ticket.html", {'client_list': client_list,
                                                       'extra_contacts': extra_contacts, 'changeorder': changeorder,'subcontractor':subcontractor,'employee_id':employee_id})



def subcontractor_payment_print(request, id):
    payment = get_object_or_404(SubcontractorPayments, id=id)

    invoices = (
        SubcontractorInvoice.objects
        .filter(payment=payment)
        .select_related('subcontract', 'subcontract__subcontractor')
        .prefetch_related('invoice_item__sov_item')
        .order_by('subcontract__po_number', 'pay_app_number')
    )

    subcontract_ids = invoices.values_list('subcontract_id', flat=True).distinct()
    subcontracts = (
        Subcontracts.objects
        .filter(id__in=subcontract_ids)
        .select_related('subcontractor')
        .order_by('po_number')
    )

    subcontract_sections = []

    for subcontract in subcontracts:

        subcontract_invoices_for_payment = invoices.filter(subcontract=subcontract)

        invoice_total_this_check = sum(
            [inv.final_amount for inv in subcontract_invoices_for_payment if inv.final_amount],
            Decimal("0.00")
        )

        total_retainage_to_date = subcontract.total_retainage_paid()

        retainage_this_check = 0-sum(
            [inv.retainage for inv in subcontract_invoices_for_payment if inv.retainage],
            Decimal("0.00")
        )

        final_pay_amount = invoice_total_this_check + retainage_this_check

        release_retainage_amount = sum(
            [
                inv.release_retainage
                for inv in subcontract_invoices_for_payment
                if inv.is_release_retainage and inv.release_retainage
            ],
            Decimal("0.00")
        )

        subcontract_items = (
            SubcontractItems.objects
            .filter(subcontract=subcontract, is_closed=False)
            .order_by('id')
        )

        item_rows = []

        for item in subcontract_items:
            matching_invoice_items = (
                SubcontractorInvoiceItem.objects
                .filter(
                    invoice__payment=payment,
                    invoice__subcontract=subcontract,
                    sov_item=item
                )
                .select_related('invoice')
                .order_by('invoice__pay_app_number')
            )

            invoice_rows = []
            for invoice_item in matching_invoice_items:
                lump_sum_percent = None

                if item.SOV_is_lump_sum and item.SOV_total_ordered not in [None, 0]:
                    try:
                        lump_sum_percent = (invoice_item.quantity / item.SOV_total_ordered) * Decimal("100")
                    except Exception:
                        lump_sum_percent = None

                invoice_rows.append({
                    'pay_app_number': invoice_item.invoice.pay_app_number,
                    'quantity': invoice_item.quantity,
                    'lump_sum_percent': lump_sum_percent,
                })

            item_rows.append({
                'item': item,
                'invoice_rows': invoice_rows,
            })

        pay_apps = invoices.filter(subcontract=subcontract).values_list('pay_app_number', flat=True).distinct()
        if invoice_total_this_check or retainage_this_check or final_pay_amount:
            subcontract_sections.append({
                'subcontract': subcontract,
                'item_rows': item_rows,
                'pay_apps': pay_apps,
                'total_retainage_to_date': total_retainage_to_date,
                'retainage_this_check': retainage_this_check,
                'release_retainage_amount': release_retainage_amount,
                'invoice_total_this_check': invoice_total_this_check,
                'final_pay_amount': final_pay_amount,
            })

    context = {
        'payment': payment,
        'subcontract_sections': subcontract_sections,
    }
    return render(request, 'subcontractor_payment_print.html', context)


def subcontractor_employee_management(request, sub_id):
    send_data = {}

    subcontractor = Subcontractors.objects.get(id=sub_id)
    send_data['selected_sub'] = subcontractor

    employees = Subcontractor_Employees.objects.filter(
        subcontractor=subcontractor,is_active=True
    ).order_by('name')

    oldemployees = Subcontractor_Employees.objects.filter(
        subcontractor=subcontractor,is_active=False
    ).order_by('name')
    send_data['oldemployees'] = oldemployees
    jobs = Jobs.objects.filter(is_closed=False).order_by('job_number')

    # Build employee list with job assignments
    employee_rows = []

    for emp in employees:

        # Job count
        job_count = Subcontractor_Job_Assignments.objects.filter(employee=emp).count()

        # -----------------------------
        # TOOLBOX CALCULATION
        # -----------------------------
        delegated_jobs = _get_delegated_active_toolbox_jobs_for_sub_employee(emp)

        if not emp.has_access_to_toolbox or not subcontractor.is_toolbox_required:
            toolbox_display = "Not Enrolled"
        elif not delegated_jobs:
            toolbox_display = "0 of 0"
        else:
            assigned_talk_ids = set()

            explicit_assignments = ScheduledToolboxTalkSubEmployees.objects.filter(
                employee=emp,
                employee__subcontractor__is_toolbox_required=True,
                job__in=delegated_jobs
            ).select_related('scheduled')

            assigned_talk_ids.update(
                explicit_assignments.values_list('scheduled_id', flat=True).distinct()
            )

            for job in delegated_jobs:
                subcontract = Subcontracts.objects.filter(
                    subcontractor=emp.subcontractor,
                    job_number=job,
                    is_closed=False,
                    subcontractor__is_toolbox_required=True,
                    job_number__is_closed=False,
                    job_number__is_active=True,
                    job_number__is_labor_done=False
                ).first()

                if not subcontract:
                    continue

                start_date = _sub_employee_assignment_start_date(emp, subcontract)
                if not start_date:
                    continue

                assigned_talk_ids.update(
                    _get_all_employee_toolbox_talks_for_subcontract(
                        subcontract,
                        end_date=date.today(),
                        start_date=start_date
                    ).values_list('id', flat=True).distinct()
                )

            excused_talks = CompletedSubToolboxTalks.objects.filter(
                employee=emp,
                master_id__in=assigned_talk_ids,
                job__in=delegated_jobs,
                is_excused=True
            ).values_list('master_id', flat=True).distinct()

            active_assigned_talk_ids = assigned_talk_ids - set(excused_talks)
            total_assigned = len(active_assigned_talk_ids)

            completed_count = len(
                _get_completed_sub_employee_toolbox_talk_ids(
                    emp,
                    active_assigned_talk_ids,
                    delegated_jobs
                )
            )

            toolbox_display = f"{completed_count} of {total_assigned}" if total_assigned > 0 else "0 of 0"

        employee_rows.append({
            'id': emp.id,
            'name': emp.name,
            'username': emp.username,
            'job_count': job_count,
            'toolbox_display': toolbox_display,
            'has_access_to_TM': emp.has_access_to_TM,
            'is_active': emp.is_active,
        })


    active_jobs = Subcontractor_Job_Assignments.objects.filter(
        employee__subcontractor=subcontractor,
        job__is_closed=False,
        job__subcontracts__subcontractor=subcontractor,
        job__subcontracts__is_closed=False
    ).select_related(
        'employee',
        'job'
    ).order_by(
        'job__job_name',
        'employee__name'
    )

    jobs_seen = {}

    for assignment in active_jobs:
        job = assignment.job
        emp = assignment.employee

        if job.job_number not in jobs_seen:
            subcontract = Subcontracts.objects.filter(
                subcontractor=subcontractor,
                job_number=job,
                is_closed=False
            ).first()
            is_delegated = bool(
                subcontract and
                SubcontractorEmployeeDelegation.objects.filter(
                    subcontractor=subcontractor,
                    subcontract=subcontract
                ).exists()
            )

            jobs_seen[job.job_number] = {
                'job': job,
                'subcontract': subcontract,
                'is_delegated': is_delegated,
                'employees': []
            }

        jobs_seen[job.job_number]['employees'].append(emp)

    job_assignment_rows = list(jobs_seen.values())
    assigned_job_numbers = set(jobs_seen.keys())

    other_subcontract_job_rows = []
    other_subcontracts = Subcontracts.objects.filter(
        subcontractor=subcontractor,
        is_closed=False,
        job_number__is_closed=False,
    ).exclude(
        job_number_id__in=assigned_job_numbers
    ).select_related(
        'job_number'
    ).order_by(
        'job_number__job_name',
        'job_number__job_number'
    )

    for subcontract in other_subcontracts:
        other_subcontract_job_rows.append({
            'job': subcontract.job_number,
            'subcontract': subcontract,
        })

    send_data['job_assignment_rows'] = job_assignment_rows
    send_data['other_subcontract_job_rows'] = other_subcontract_job_rows


    send_data['employees'] = employee_rows
    send_data['jobs'] = jobs

    return render(request, "subcontractor_employee_management.html", send_data)


@require_POST
def toggle_subcontractor_job_delegation(request, sub_id, subcontract_id):
    subcontractor = get_object_or_404(Subcontractors, id=sub_id)
    subcontract = get_object_or_404(
        Subcontracts,
        id=subcontract_id,
        subcontractor=subcontractor,
        is_closed=False
    )

    existing = SubcontractorEmployeeDelegation.objects.filter(
        subcontractor=subcontractor,
        subcontract=subcontract
    )

    if existing.exists():
        closed_count = _close_delegated_job_toolbox_completions_before_undelegate(subcontract)
        existing.delete()
        messages.success(
            request,
            f"Delegation removed for this job. {closed_count} completed toolbox talks were preserved."
        )
    else:
        SubcontractorEmployeeDelegation.objects.get_or_create(
            subcontractor=subcontractor,
            subcontract=subcontract
        )
        backfilled_count = _backfill_delegated_job_toolbox_completions(subcontract)
        messages.success(
            request,
            f"Delegation added for this job. {backfilled_count} existing toolbox completions were applied."
        )

    return redirect('subcontractor_employee_management', sub_id=subcontractor.id)


@transaction.atomic
def assign_subcontractor_employee_job(request):
    if request.method == 'POST':
        employee_id = request.POST.get('employee_id')
        job_id = request.POST.get('job_id')

        employee = Subcontractor_Employees.objects.get(id=employee_id)
        job = Jobs.objects.get(job_number=job_id)

        Subcontractor_Job_Assignments.objects.get_or_create(
            employee=employee,
            job=job
        )

        return JsonResponse({'success': True})

    return JsonResponse({'success': False}, status=400)


def subcontractor_employee_ajax(request):
    employee_id = request.GET.get('employee_id')
    if not employee_id:
        return JsonResponse({'error': 'Missing employee_id'}, status=400)

    emp = Subcontractor_Employees.objects.filter(id=employee_id).first()
    if not emp:
        return JsonResponse({'error': 'Employee not found'}, status=404)

    assignments = Subcontractor_Job_Assignments.objects.filter(
        employee=emp
    ).select_related('job').order_by('job__job_number')

    jobs = []
    for a in assignments:
        jobs.append({
            'id': a.job.job_number,
            'label': f"{a.job.job_number} {a.job.job_name}"
        })

    return JsonResponse({
        'id': emp.id,
        'name': emp.name or "",
        'username': emp.username or "",
        'password1': emp.password1 or "",
        'date_enrolled': emp.date_enrolled.strftime('%m/%d/%Y') if emp.date_enrolled else "",
        'has_access_to_TM': emp.has_access_to_TM,
        'has_access_to_toolbox': emp.has_access_to_toolbox,
        'is_active': emp.is_active,
        'jobs': jobs,
    })




@require_POST
@transaction.atomic
def subcontractor_employee_update(request):
    employee_id = request.POST.get('employee_id')
    emp = Subcontractor_Employees.objects.filter(id=employee_id).first()

    if not emp:
        return JsonResponse({'error': 'Employee not found'}, status=404)

    username = request.POST.get('username', '').strip()

    if username:
        username_exists_in_employees = Subcontractor_Employees.objects.filter(
            username__iexact=username
        ).exclude(id=emp.id).exists()

        username_exists_in_subcontractors = Subcontractors.objects.filter(
            username__iexact=username
        ).exists()

        username_exists_in_django_users = User.objects.filter(
            username__iexact=username
        ).exists()

        if username_exists_in_employees or username_exists_in_subcontractors or username_exists_in_django_users:
            return JsonResponse({'error': 'That username is already in use.'}, status=400)

    emp.name = request.POST.get('name', '').strip()
    emp.username = request.POST.get('username', '').strip()
    emp.password1 = request.POST.get('password1', '').strip()
    emp.has_access_to_toolbox = request.POST.get('has_access_to_toolbox') == 'true'
    emp.has_access_to_TM = request.POST.get('has_access_to_TM') == 'true'
    emp.save()

    return JsonResponse({'success': True})


@require_POST
@transaction.atomic
def subcontractor_employee_remove(request):
    employee_id = request.POST.get('employee_id')
    emp = Subcontractor_Employees.objects.filter(id=employee_id).first()

    if not emp:
        return JsonResponse({'error': 'Employee not found'}, status=404)

    emp.is_active = False
    emp.save()

    return JsonResponse({'success': True})



@require_POST
@transaction.atomic
def subcontractor_employee_create(request):
    subcontractor_id = request.POST.get('subcontractor_id')
    name = request.POST.get('name', '').strip()
    username = request.POST.get('username', '').strip()
    password1 = request.POST.get('password1', '').strip()
    has_access_to_toolbox = request.POST.get('has_access_to_toolbox') == 'true'
    has_access_to_tm = request.POST.get('has_access_to_TM') == 'true'
    job_id = request.POST.get('job_id')

    if not subcontractor_id:
        return JsonResponse({'error': 'Missing subcontractor.'}, status=400)

    if not name:
        return JsonResponse({'error': 'Name is required.'}, status=400)

    subcontractor = Subcontractors.objects.filter(id=subcontractor_id).first()
    if not subcontractor:
        return JsonResponse({'error': 'Subcontractor not found.'}, status=404)

    if username:
        username_exists_in_employees = Subcontractor_Employees.objects.filter(
            username__iexact=username
        ).exists()

        username_exists_in_subcontractors = Subcontractors.objects.filter(
            username__iexact=username
        ).exists()

        username_exists_in_django_users = User.objects.filter(
            username__iexact=username
        ).exists()

        if username_exists_in_employees or username_exists_in_subcontractors or username_exists_in_django_users:
            return JsonResponse({'error': 'That username is already in use.'}, status=400)
    new_emp = Subcontractor_Employees.objects.create(
        subcontractor=subcontractor,
        name=name,
        username=username,
        password1=password1,
        has_access_to_toolbox=has_access_to_toolbox,
        has_access_to_TM=has_access_to_tm,
        is_active=True,
        date_enrolled=date.today()
    )

    if job_id:
        job = Jobs.objects.filter(job_number=job_id).first()
        if job:
            Subcontractor_Job_Assignments.objects.get_or_create(
                employee=new_emp,
                job=job
            )

    return JsonResponse({'success': True, 'employee_id': new_emp.id})


@require_POST
@transaction.atomic
def remove_subcontractor_employee_job(request):
    employee_id = request.POST.get('employee_id')
    job_id = request.POST.get('job_id')

    employee = Subcontractor_Employees.objects.filter(id=employee_id).first()
    if not employee:
        return JsonResponse({'error': 'Employee not found.'}, status=404)

    job = Jobs.objects.filter(job_number=job_id).first()
    if not job:
        return JsonResponse({'error': 'Job not found.'}, status=404)

    Subcontractor_Job_Assignments.objects.filter(
        employee=employee,
        job=job
    ).delete()

    return JsonResponse({'success': True})




@never_cache
def subcontractor_employee_portal(request, employee_id):
    selected_employee = get_object_or_404(Subcontractor_Employees, id=employee_id)

    send_data = {}
    subcontractor = selected_employee.subcontractor

    send_data['selected_employee'] = selected_employee
    send_data['subcontractor'] = subcontractor
    send_data['employee_id'] = employee_id

    # Assigned jobs
    assigned_jobs = Subcontractor_Job_Assignments.objects.filter(
        employee=selected_employee,
        job__is_closed=False
    ).select_related('job').order_by('job__job_name')

    send_data['assigned_jobs'] = assigned_jobs

    # T&M tickets
    outstanding_tm_tickets = 0
    if selected_employee.has_access_to_TM:
        jobs = assigned_jobs.values_list('job', flat=True)

        all_changeorders = ChangeOrders.objects.filter(
            job_number__in=jobs,
            is_closed=False
        ).order_by('cop_number')

        for co in all_changeorders:
            if _subcontractor_portal_tm_ticket_action(co, subcontractor):
                outstanding_tm_tickets += 1

    send_data['outstanding_tm_tickets'] = outstanding_tm_tickets

    # Toolbox talks
    group_toolbox_talks = []
    individual_toolbox_talks = []
    if selected_employee.has_access_to_toolbox and subcontractor.is_toolbox_required:
        send_data['toolbox_allowed'] = True

        individual_toolbox_talks = []
        for item in sub_toolbox.get_missing_individual_talk_items_for_employee(
                selected_employee,
                through_date=date.today()
        ):
            scheduled = item['scheduled']
            english_file = get_uploaded_toolbox_file(scheduled, "English")
            spanish_file = get_uploaded_toolbox_file(scheduled, "Spanish")

            english_view = ViewedSubToolboxTalks.objects.filter(
                employee=selected_employee,
                master=scheduled,
                language="English"
            ).order_by('-date').first()

            spanish_view = ViewedSubToolboxTalks.objects.filter(
                employee=selected_employee,
                master=scheduled,
                language="Spanish"
            ).order_by('-date').first()

            individual_toolbox_talks.append({
                'item': scheduled.id,
                'job': item['job'],
                'job_names': item['job_names'],
                'description': item['title'],
                'date': item['date'],
                'english': english_file['filename'] if english_file else None,
                'spanish': spanish_file['filename'] if spanish_file else None,
                'english_viewed': bool(english_view),
                'english_date': english_view.date if english_view else None,
                'spanish_viewed': bool(spanish_view),
                'spanish_date': spanish_view.date if spanish_view else None,
                'can_complete': bool(english_view or spanish_view),
            })

        group_toolbox_talks = sub_toolbox.get_missing_group_talk_items_for_employee(
            selected_employee,
            through_date=date.today()
        )

        send_data['group_toolbox_talks'] = group_toolbox_talks
        send_data['group_toolbox_talks_count'] = len(group_toolbox_talks)

        send_data['individual_toolbox_talks'] = individual_toolbox_talks
        send_data['individual_toolbox_talks_count'] = len(individual_toolbox_talks)

        toolbox_talks_for_other_employees = []
        other_employees = (
            Subcontractor_Employees.objects
            .filter(
                subcontractor=subcontractor,
                is_active=True,
                has_access_to_toolbox=True,
            )
            .exclude(id=selected_employee.id)
            .order_by('name', 'id')
        )

        for other_employee in other_employees:
            employee_toolbox_talks = []

            for item in sub_toolbox.get_missing_individual_talk_items_for_employee(
                    other_employee,
                    through_date=date.today()
            ):
                scheduled = item['scheduled']
                english_file = get_uploaded_toolbox_file(scheduled, "English")
                spanish_file = get_uploaded_toolbox_file(scheduled, "Spanish")

                english_view = ViewedSubToolboxTalks.objects.filter(
                    employee=other_employee,
                    master=scheduled,
                    language="English"
                ).order_by('-date').first()

                spanish_view = ViewedSubToolboxTalks.objects.filter(
                    employee=other_employee,
                    master=scheduled,
                    language="Spanish"
                ).order_by('-date').first()

                employee_toolbox_talks.append({
                    'item': scheduled.id,
                    'job': item['job'],
                    'job_names': item['job_names'],
                    'description': item['title'],
                    'date': item['date'],
                    'english': english_file['filename'] if english_file else None,
                    'spanish': spanish_file['filename'] if spanish_file else None,
                    'english_viewed': bool(english_view),
                    'english_date': english_view.date if english_view else None,
                    'spanish_viewed': bool(spanish_view),
                    'spanish_date': spanish_view.date if spanish_view else None,
                    'can_complete': bool(english_view or spanish_view),
                })

            if employee_toolbox_talks:
                toolbox_talks_for_other_employees.append({
                    'employee': other_employee,
                    'talks': employee_toolbox_talks,
                    'count': len(employee_toolbox_talks),
                })

        send_data['toolbox_talks_for_other_employees'] = toolbox_talks_for_other_employees
        send_data['toolbox_talks_for_other_employees_count'] = sum(
            row['count'] for row in toolbox_talks_for_other_employees
        )

    else:
        send_data['toolbox_allowed'] = False
        send_data['group_toolbox_talks'] = []
        send_data['group_toolbox_talks_count'] = 0
        send_data['individual_toolbox_talks'] = []
        send_data['individual_toolbox_talks_count'] = 0
        send_data['toolbox_talks_for_other_employees'] = []
        send_data['toolbox_talks_for_other_employees_count'] = 0

    return render(request, "subcontractor_employee_portal.html", send_data)



def subcontractor_toolbox_file(request, scheduled_id, language, employee_id):
    selected_employee = get_object_or_404(Subcontractor_Employees, id=employee_id)
    scheduled = get_object_or_404(ScheduledToolboxTalks, id=scheduled_id)

    ViewedSubToolboxTalks.objects.get_or_create(
        employee=selected_employee,
        master=scheduled,
        language=language,
        defaults={"date": now().date()}
    )

    if scheduled.master:
        folder_path = os.path.join(
            settings.MEDIA_ROOT,
            "toolbox_talks",
            str(scheduled.master.id),
            language
        )
        relative_id = f"{scheduled.master.id}/{language}"
        app_name = "toolbox_talks"
    else:
        folder_path = os.path.join(
            settings.MEDIA_ROOT,
            "custom_toolbox_talks",
            str(scheduled.id),
            language
        )
        relative_id = f"{scheduled.id}/{language}"
        app_name = "custom_toolbox_talks"

    if not os.path.exists(folder_path):
        return HttpResponse("File not found", status=404)

    files = [
        f for f in os.listdir(folder_path)
        if os.path.isfile(os.path.join(folder_path, f))
    ]

    if not files:
        return HttpResponse("File not found", status=404)

    file_name = files[0]

    return MediaUtilities().getDirectoryContents(
        relative_id,
        file_name,
        app_name
    )




def complete_subcontractor_toolbox_talk(request):
    if request.method == "POST":
        employee_id = request.POST.get("employee_id")
        return_employee_id = request.POST.get("return_employee_id") or employee_id
        scheduledtalk_id = request.POST.get("scheduledtalk_id")

        selected_employee = get_object_or_404(Subcontractor_Employees, id=employee_id)
        scheduled_talk = get_object_or_404(ScheduledToolboxTalks, id=scheduledtalk_id)
        return_employee = get_object_or_404(
            Subcontractor_Employees,
            id=return_employee_id,
            subcontractor=selected_employee.subcontractor
        )

        if not selected_employee.subcontractor.is_toolbox_required:
            return redirect('subcontractor_employee_portal', employee_id=return_employee.id)

        assigned_job_ids = Subcontractor_Job_Assignments.objects.filter(
            employee=selected_employee,
            job__is_closed=False,
            job__is_active=True,
            job__is_labor_done=False
        ).values_list('job_id', flat=True)

        delegated_subcontracts = Subcontracts.objects.filter(
            subcontractor=selected_employee.subcontractor,
            is_closed=False,
            subcontractor__is_toolbox_required=True,
            job_number_id__in=assigned_job_ids,
            job_number__is_closed=False,
            job_number__is_active=True,
            job_number__is_labor_done=False,
        )

        for subcontract in delegated_subcontracts:

            if not _subcontractor_employee_delegation_effective(
                    selected_employee.subcontractor,
                    subcontract,
                    scheduled_talk.date
            ):
                continue

            if (
                not selected_employee.date_enrolled or
                selected_employee.date_enrolled > scheduled_talk.date
            ):
                continue

            _complete_subcontractor_toolbox_talk(
                selected_employee,
                scheduled_talk,
                subcontract.job_number
            )

            assigned_employee_ids = Subcontractor_Job_Assignments.objects.filter(
                job=subcontract.job_number,
                employee__subcontractor=selected_employee.subcontractor,
                employee__is_active=True,
                employee__has_access_to_toolbox=True,
                employee__date_enrolled__isnull=False,
                employee__date_enrolled__lte=scheduled_talk.date
            ).values_list('employee_id', flat=True).distinct()

            assigned_employees = Subcontractor_Employees.objects.filter(
                id__in=assigned_employee_ids
            )

            if not assigned_employees.exists():
                continue

            completed_employee_ids = CompletedSubToolboxTalks.objects.filter(
                master=scheduled_talk,
                job=subcontract.job_number,
                employee__in=assigned_employees,
                is_excused=False
            ).values_list('employee_id', flat=True).distinct()
            excused_employee_ids = CompletedSubToolboxTalks.objects.filter(
                master=scheduled_talk,
                job=subcontract.job_number,
                employee__in=assigned_employees,
                is_excused=True
            ).values_list('employee_id', flat=True).distinct()

            required_employee_ids = set(assigned_employee_ids) - set(excused_employee_ids)

            if required_employee_ids and required_employee_ids == set(completed_employee_ids):

                completed_job_talk = _complete_subcontractor_job_toolbox_talk(
                    scheduled_talk,
                    selected_employee.subcontractor,
                    subcontract.job_number
                )

                for emp in assigned_employees:
                    CompletedSubToolboxJobTalkEmployees.objects.get_or_create(
                        completed=completed_job_talk,
                        employee=emp,
                        note="Employee completed themself through the portal"
                    )

        return redirect('subcontractor_employee_portal', employee_id=return_employee.id)

    return redirect('https://wwww.gerloffpainting.com')



def subcontractor_approvers_management(request):

    eligible_employees = Employees.objects.exclude(
        job_title__description="Painter"
    ).order_by("last_name", "first_name")

    active_subcontractors = Subcontractors.objects.filter(
        is_inactive=False
    ).order_by("company")

    selected_employee_id = request.GET.get("employee")
    selected_subcontractor_id = request.GET.get("subcontractor")
    JOB_SUPERINTENDENT_VALUE = "JOB_SUPERINTENDENT"

    def is_job_superintendent(value):
        return value == JOB_SUPERINTENDENT_VALUE
    if request.method == "POST":
        action = request.POST.get("action")

        employee_id = request.POST.get("employee_id")
        subcontractor_id = request.POST.get("subcontractor_id")
        subcontract_id = request.POST.get("subcontract_id")
        approver_id = request.POST.get("approver_id")

        redirect_url = request.POST.get("redirect_url") or "."

        # -------------------------
        # STANDARD APPROVERS
        # -------------------------
        if action == "add_standard_approver":
            if employee_id == JOB_SUPERINTENDENT_VALUE:
                Standard_Approvers.objects.get_or_create(
                    employee=None,
                    job_description="Superintendent"
                )
            else:
                employee = get_object_or_404(Employees, id=employee_id)

                Standard_Approvers.objects.get_or_create(
                    employee=employee,
                    defaults={"job_description": ""}
                )

        elif action == "remove_standard_approver":
            Standard_Approvers.objects.filter(id=approver_id).delete()

        # -------------------------
        # REMOVE SELECTED EMPLOYEE FROM ALL
        # -------------------------
        elif action == "remove_employee_from_all_standard":
            if is_job_superintendent(employee_id):
                Standard_Approvers.objects.filter(
                    employee__isnull=True,
                    job_description="Superintendent"
                ).delete()
            else:
                Standard_Approvers.objects.filter(employee_id=employee_id).delete()

        elif action == "remove_employee_from_all_subcontractors":
            if is_job_superintendent(employee_id):
                Subcontractor_Approvers.objects.filter(
                    employee__isnull=True,
                    job_description="Superintendent",
                    subcontractor__is_inactive=False
                ).delete()
            else:
                Subcontractor_Approvers.objects.filter(
                    employee_id=employee_id,
                    subcontractor__is_inactive=False
                ).delete()

        elif action == "remove_employee_from_all_subcontracts":
            if is_job_superintendent(employee_id):
                Subcontract_Approvers.objects.filter(
                    employee__isnull=True,
                    job_description="Superintendent",
                    subcontract__is_closed=False,
                    subcontract__subcontractor__is_inactive=False
                ).delete()
            else:
                Subcontract_Approvers.objects.filter(
                    employee_id=employee_id,
                    subcontract__is_closed=False,
                    subcontract__subcontractor__is_inactive=False
                ).delete()

        # -------------------------
        # INDIVIDUAL REMOVES
        # -------------------------
        elif action == "remove_subcontractor_approver":
            Subcontractor_Approvers.objects.filter(id=approver_id).delete()

        elif action == "remove_subcontract_approver":
            Subcontract_Approvers.objects.filter(id=approver_id).delete()

        # -------------------------
        # ADD APPROVER TO SUBCONTRACT
        # -------------------------
        elif action == "add_subcontract_approver":
            subcontract = get_object_or_404(Subcontracts, id=subcontract_id)
            if employee_id == JOB_SUPERINTENDENT_VALUE:
                Subcontract_Approvers.objects.get_or_create(
                    employee=None,
                    subcontract=subcontract,
                    job_description="Superintendent"
                )
            else:
                employee = get_object_or_404(Employees, id=employee_id)

                Subcontract_Approvers.objects.get_or_create(
                    employee=employee,
                    subcontract=subcontract,
                    defaults={"job_description": ""}
                )
        elif action == "add_subcontractor_approver":
            subcontractor = get_object_or_404(
                Subcontractors,
                id=subcontractor_id,
                is_inactive=False
            )
            if employee_id == JOB_SUPERINTENDENT_VALUE:
                Subcontractor_Approvers.objects.get_or_create(
                    employee=None,
                    subcontractor=subcontractor,
                    job_description="Superintendent"
                )
            else:
                employee = get_object_or_404(Employees, id=employee_id)


                Subcontractor_Approvers.objects.get_or_create(
                    employee=employee,
                    subcontractor=subcontractor,
                    defaults={"job_description": ""}
                )
        elif action == "add_employee_to_all_subcontractors":
            if employee_id == JOB_SUPERINTENDENT_VALUE:
                for subcontractor in Subcontractors.objects.filter(is_inactive=False):
                    Subcontractor_Approvers.objects.get_or_create(
                        employee=None,
                        subcontractor=subcontractor,
                        job_description="Superintendent"
                    )
            else:
                employee = get_object_or_404(Employees, id=employee_id)
                for subcontractor in Subcontractors.objects.filter(is_inactive=False):
                    Subcontractor_Approvers.objects.get_or_create(
                        employee=employee,
                        subcontractor=subcontractor,
                    )

        elif action == "add_employee_to_all_subcontracts":

            if employee_id == JOB_SUPERINTENDENT_VALUE:
                for subcontract in Subcontracts.objects.filter(
                        is_closed=False,
                        subcontractor__is_inactive=False
                ):
                    Subcontract_Approvers.objects.get_or_create(
                        employee=None,
                        subcontract=subcontract,
                        job_description="Superintendent"
                    )
            else:
                employee = get_object_or_404(Employees, id=employee_id)

                for subcontract in Subcontracts.objects.filter(
                        is_closed=False,
                        subcontractor__is_inactive=False
                ):
                    Subcontract_Approvers.objects.get_or_create(
                        employee=employee,
                        subcontract=subcontract,
                    )
        return redirect(redirect_url)

    # -------------------------
    # TOP STANDARD APPROVERS
    # -------------------------
    standard_approvers = Standard_Approvers.objects.select_related(
        "employee"
    ).order_by("employee__last_name", "employee__first_name")

    # -------------------------
    # SEARCH BY EMPLOYEE DROPDOWN
    # only employees linked to any approver model
    # -------------------------
    employee_ids = set(Standard_Approvers.objects.exclude(employee=None).values_list("employee_id", flat=True))
    employee_ids.update(Subcontractor_Approvers.objects.exclude(employee=None).values_list("employee_id", flat=True))
    employee_ids.update(Subcontract_Approvers.objects.exclude(employee=None).values_list("employee_id", flat=True))

    linked_employees = Employees.objects.filter(
        id__in=employee_ids
    ).order_by("last_name", "first_name")

    selected_employee = None
    employee_standard_approvers = []
    employee_subcontractor_approvers = []
    employee_subcontract_approvers = []

    if selected_employee_id:

        if is_job_superintendent(selected_employee_id):
            selected_employee = "Job Superintendent"

            employee_standard_approvers = Standard_Approvers.objects.filter(
                employee__isnull=True,
                job_description="Superintendent"
            )

            employee_subcontractor_approvers = Subcontractor_Approvers.objects.filter(
                employee__isnull=True,
                job_description="Superintendent",
                subcontractor__is_inactive=False
            ).select_related("subcontractor").order_by("subcontractor__company")

            employee_subcontract_approvers = Subcontract_Approvers.objects.filter(
                employee__isnull=True,
                job_description="Superintendent",
                subcontract__is_closed=False,
                subcontract__subcontractor__is_inactive=False
            ).select_related(
                "subcontract",
                "subcontract__subcontractor",
                "subcontract__job_number",
            ).order_by(
                "subcontract__subcontractor__company",
                "subcontract__job_number__job_name"
            )

        else:
            selected_employee = get_object_or_404(Employees, id=selected_employee_id)

            employee_standard_approvers = Standard_Approvers.objects.filter(
                employee=selected_employee
            ).select_related("employee")

            employee_subcontractor_approvers = Subcontractor_Approvers.objects.filter(
                employee=selected_employee,
                subcontractor__is_inactive=False
            ).select_related("employee", "subcontractor").order_by("subcontractor__company")

            employee_subcontract_approvers = Subcontract_Approvers.objects.filter(
                employee=selected_employee,
                subcontract__is_closed=False,
                subcontract__subcontractor__is_inactive=False
            ).select_related(
                "employee",
                "subcontract",
                "subcontract__subcontractor",
                "subcontract__job_number",
            ).order_by(
                "subcontract__subcontractor__company",
                "subcontract__job_number__job_name"
            )

        # employee_standard_approvers = Standard_Approvers.objects.filter(
        #     employee=selected_employee
        # ).select_related("employee")
        #
        # employee_subcontractor_approvers = Subcontractor_Approvers.objects.filter(
        #     employee=selected_employee,
        #     subcontractor__is_inactive=False
        # ).select_related("employee", "subcontractor").order_by("subcontractor__company")
        #
        # employee_subcontract_approvers = Subcontract_Approvers.objects.filter(
        #     employee=selected_employee,
        #     subcontract__is_closed=False,
        #     subcontract__subcontractor__is_inactive=False
        # ).select_related(
        #     "employee",
        #     "subcontract",
        #     "subcontract__subcontractor",
        #     "subcontract__job_number",
        # ).order_by(
        #     "subcontract__subcontractor__company",
        #     "subcontract__job_number__job_name"
        # )

    # -------------------------
    # SEARCH BY EMPLOYEE DROPDOWN
    # for adding employees
    # -------------------------
    selected_add_employee_id = request.GET.get("add_employee")

    selected_add_employee = None
    add_standard_available = False
    add_subcontractor_rows = []
    add_subcontract_rows = []

    if selected_add_employee_id:

        if is_job_superintendent(selected_add_employee_id):
            selected_add_employee = "Job Superintendent"

            add_standard_available = not Standard_Approvers.objects.filter(
                employee__isnull=True,
                job_description="Superintendent"
            ).exists()

            existing_subcontractor_ids = Subcontractor_Approvers.objects.filter(
                employee__isnull=True,
                job_description="Superintendent"
            ).values_list("subcontractor_id", flat=True)

            add_subcontractor_rows = Subcontractors.objects.filter(
                is_inactive=False
            ).exclude(
                id__in=existing_subcontractor_ids
            ).order_by("company")

            existing_subcontract_ids = Subcontract_Approvers.objects.filter(
                employee__isnull=True,
                job_description="Superintendent"
            ).values_list("subcontract_id", flat=True)

            add_subcontract_rows = Subcontracts.objects.filter(
                is_closed=False,
                subcontractor__is_inactive=False
            ).exclude(
                id__in=existing_subcontract_ids
            ).select_related(
                "subcontractor",
                "job_number"
            ).order_by(
                "subcontractor__company",
                "job_number__job_name"
            )

        else:
            selected_add_employee = get_object_or_404(Employees, id=selected_add_employee_id)

            add_standard_available = not Standard_Approvers.objects.filter(
                employee=selected_add_employee
            ).exists()

            existing_subcontractor_ids = Subcontractor_Approvers.objects.filter(
                employee=selected_add_employee
            ).values_list("subcontractor_id", flat=True)

            add_subcontractor_rows = Subcontractors.objects.filter(
                is_inactive=False
            ).exclude(
                id__in=existing_subcontractor_ids
            ).order_by("company")

            existing_subcontract_ids = Subcontract_Approvers.objects.filter(
                employee=selected_add_employee
            ).values_list("subcontract_id", flat=True)

            add_subcontract_rows = Subcontracts.objects.filter(
                is_closed=False,
                subcontractor__is_inactive=False
            ).exclude(
                id__in=existing_subcontract_ids
            ).select_related(
                "subcontractor",
                "job_number"
            ).order_by(
                "subcontractor__company",
                "job_number__job_name"
            )

        # add_standard_available = not Standard_Approvers.objects.filter(
        #     employee=selected_add_employee
        # ).exists()

        # existing_subcontractor_ids = Subcontractor_Approvers.objects.filter(
        #     employee=selected_add_employee
        # ).values_list("subcontractor_id", flat=True)

        # add_subcontractor_rows = Subcontractors.objects.filter(
        #     is_inactive=False
        # ).exclude(
        #     id__in=existing_subcontractor_ids
        # ).order_by("company")

        # existing_subcontract_ids = Subcontract_Approvers.objects.filter(
        #     employee=selected_add_employee
        # ).values_list("subcontract_id", flat=True)

        # add_subcontract_rows = Subcontracts.objects.filter(
        #     is_closed=False,
        #     subcontractor__is_inactive=False
        # ).exclude(
        #     id__in=existing_subcontract_ids
        # ).select_related(
        #     "subcontractor",
        #     "job_number"
        # ).order_by(
        #     "subcontractor__company",
        #     "job_number__job_name"
        # )

    # -------------------------
    # SEARCH BY SUBCONTRACTOR
    # -------------------------
    selected_subcontractor = None
    subcontractor_approvers = []
    subcontract_rows = []

    if selected_subcontractor_id:
        selected_subcontractor = get_object_or_404(
            Subcontractors,
            id=selected_subcontractor_id,
            is_inactive=False
        )

        subcontractor_approvers = Subcontractor_Approvers.objects.filter(
            subcontractor=selected_subcontractor
        ).select_related("employee").order_by(
            "employee__last_name",
            "employee__first_name"
        )

        open_subcontracts = Subcontracts.objects.filter(
            subcontractor=selected_subcontractor,
            is_closed=False
        ).select_related(
            "subcontractor",
            "job_number"
        ).order_by("job_number__job_name")

        for subcontract in open_subcontracts:
            approvers = Subcontract_Approvers.objects.filter(
                subcontract=subcontract
            ).select_related("employee").order_by(
                "employee__last_name",
                "employee__first_name"
            )

            subcontract_rows.append({
                "subcontract": subcontract,
                "approvers": approvers,
            })

    context = {
        "eligible_employees": eligible_employees,
        "standard_approvers": standard_approvers,

        "linked_employees": linked_employees,
        "selected_employee_id": selected_employee_id,
        "selected_employee": selected_employee,
        "employee_standard_approvers": employee_standard_approvers,
        "employee_subcontractor_approvers": employee_subcontractor_approvers,
        "employee_subcontract_approvers": employee_subcontract_approvers,

        "active_subcontractors": active_subcontractors,
        "selected_subcontractor_id": selected_subcontractor_id,
        "selected_subcontractor": selected_subcontractor,
        "subcontractor_approvers": subcontractor_approvers,
        "subcontract_rows": subcontract_rows,

        "selected_add_employee_id": selected_add_employee_id,
        "selected_add_employee": selected_add_employee,
        "add_standard_available": add_standard_available,
        "add_subcontractor_rows": add_subcontractor_rows,
        "add_subcontract_rows": add_subcontract_rows,
    }

    return render(
        request,
        "subcontractor_approvers_management.html",
        context
    )

def subcontractor_employee_reactivate(request):
    if request.method == "POST":
        employee = get_object_or_404(
            Subcontractor_Employees,
            id=request.POST.get("employee_id")
        )

        employee.is_active = True
        employee.save()

        return JsonResponse({"success": True})

    return JsonResponse({"error": "Invalid request"}, status=400)

@never_cache
def sub_toolbox_complete(request, sub_id, scheduled_id, job_number):
    selected_sub = get_object_or_404(Subcontractors, id=sub_id)
    scheduled = get_object_or_404(ScheduledToolboxTalks, id=scheduled_id)
    job = get_object_or_404(Jobs, job_number=job_number)
    from_employee = request.GET.get('from_employee') or request.POST.get('from_employee')
    preselected_employee_id = request.GET.get('employee') or request.POST.get('employee')
    sub_employees = Subcontractor_Employees.objects.filter(
        subcontractor=selected_sub,
        is_active=True
    ).order_by('name')
    if preselected_employee_id and not sub_employees.filter(id=preselected_employee_id).exists():
        preselected_employee_id = None

    if request.method == 'POST':
        if 'remove_delegation' in request.POST:
            subcontract = Subcontracts.objects.filter(
                subcontractor=selected_sub,
                job_number=job,
                is_closed=False
            ).first()

            if subcontract:
                closed_count = _close_delegated_job_toolbox_completions_before_undelegate(subcontract)
                SubcontractorEmployeeDelegation.objects.filter(
                    subcontractor=selected_sub,
                    subcontract=subcontract
                ).delete()

                messages.success(
                    request,
                    f"Employee self-completion was removed for this job. {closed_count} completed toolbox talks were preserved."
                )

            return redirect('portal', sub_id=selected_sub.id, contract_id='ALL')
        # VIEW ENGLISH / SPANISH FILE
        if 'selected_id' in request.POST:
            folder_id = request.POST.get('selected_id')
            selected_language = request.POST.get('selected_language')
            selected_file = request.POST.get('selected_file')
            base_folder = request.POST.get('base_folder', 'toolbox_talks')

            if not folder_id or not selected_language or not selected_file:
                messages.error(request, "File information was missing.")
                return redirect(
                    'sub_toolbox_complete',
                    sub_id=selected_sub.id,
                    scheduled_id=scheduled.id,
                    job_number=job.job_number
                )

            ViewedSubToolboxJobTalks.objects.get_or_create(
                scheduled=scheduled,
                subcontractor=selected_sub,
                job=job,
                language=selected_language
            )

            return MediaUtilities().getDirectoryContents(
                str(folder_id) + "/" + selected_language,
                selected_file,
                base_folder
            )

        has_viewed = ViewedSubToolboxJobTalks.objects.filter(
            scheduled=scheduled,
            subcontractor=selected_sub,
            job=job
        ).exists()

        if not has_viewed:
            messages.error(request, "You need to view the toolbox talk before marking it complete.")
            return redirect(
                'sub_toolbox_complete',
                sub_id=selected_sub.id,
                scheduled_id=scheduled.id,
                job_number=job.job_number
            )

        employee_selects = request.POST.getlist('employee_select')
        valid_employee_exists = False

        for value in employee_selects:
            if value.strip():
                valid_employee_exists = True
                break

        if not valid_employee_exists:
            messages.error(
                request,
                "Please add at least one employee before completing the toolbox talk."
            )

            return redirect(
                'sub_toolbox_complete',
                sub_id=selected_sub.id,
                scheduled_id=scheduled.id,
                job_number=job.job_number
            )
        add_to_employee_list = request.POST.getlist('add_to_employee_list')

        # COMPLETE TOOLBOX TALK
        completed = _complete_subcontractor_job_toolbox_talk(
            scheduled,
            selected_sub,
            job
        )

        for index, value in enumerate(employee_selects):
            if not value:
                continue

            should_add = str(index) in add_to_employee_list

            if value.startswith("EMPLOYEE_"):
                employee_id = value.replace("EMPLOYEE_", "")

                employee = Subcontractor_Employees.objects.get(
                    id=employee_id,
                    subcontractor=selected_sub
                )

                CompletedSubToolboxJobTalkEmployees.objects.get_or_create(
                    completed=completed,
                    employee=employee
                )

                _complete_subcontractor_toolbox_talk(
                    employee,
                    scheduled,
                    job
                )
                _complete_attendee_delegated_jobs_for_same_talk(
                    employee,
                    scheduled,
                    job
                )

            else:
                custom_name = value.strip()

                new_employee = None

                if should_add:
                    new_employee, created = Subcontractor_Employees.objects.get_or_create(
                        subcontractor=selected_sub,
                        name=custom_name,
                        defaults={
                            'is_active': True,
                            'date_enrolled': date.today(),
                            'has_access_to_toolbox': True,
                        }
                    )

                CompletedSubToolboxJobTalkEmployees.objects.create(
                    completed=completed,
                    employee=new_employee,
                    custom_name=custom_name,
                    added_to_employee_list=should_add
                )

                if new_employee:
                    _complete_subcontractor_toolbox_talk(
                        new_employee,
                        scheduled,
                        job
                    )
                    _complete_attendee_delegated_jobs_for_same_talk(
                        new_employee,
                        scheduled,
                        job
                    )

        messages.success(request, "Toolbox talk completed.")
        if from_employee:
            return redirect('subcontractor_employee_portal', employee_id=from_employee)

        subcontract = Subcontracts.objects.filter(
            subcontractor=selected_sub,
            job_number=job,
            is_closed=False
        ).first()

        delegation_exists = False

        if subcontract:
            delegation_exists = _subcontract_has_delegated_employee_for_date(
                subcontract,
                scheduled.date
            )

        if delegation_exists:
            return redirect(
                f"{reverse('sub_toolbox_complete', args=[selected_sub.id, scheduled.id, job.job_number])}?ask_remove_delegation=1"
            )

        return redirect('portal', sub_id=selected_sub.id, contract_id='ALL')


    english_file = None
    spanish_file = None

    if scheduled.master:
        base_folder = "toolbox_talks"
        folder_id = str(scheduled.master.id)
    else:
        base_folder = "custom_toolbox_talks"
        folder_id = str(scheduled.id)

    english_path = os.path.join(settings.MEDIA_ROOT, base_folder, folder_id, "English")
    spanish_path = os.path.join(settings.MEDIA_ROOT, base_folder, folder_id, "Spanish")

    if os.path.exists(english_path):
        for entry in os.listdir(english_path):
            if os.path.isfile(os.path.join(english_path, entry)):
                english_file = entry
                break

    if os.path.exists(spanish_path):
        for entry in os.listdir(spanish_path):
            if os.path.isfile(os.path.join(spanish_path, entry)):
                spanish_file = entry
                break
    english_viewed = ViewedSubToolboxJobTalks.objects.filter(
        scheduled=scheduled,
        subcontractor=selected_sub,
        job=job,
        language="English"
    ).exists()

    spanish_viewed = ViewedSubToolboxJobTalks.objects.filter(
        scheduled=scheduled,
        subcontractor=selected_sub,
        job=job,
        language="Spanish"
    ).exists()

    can_complete = english_viewed or spanish_viewed
    ask_remove_delegation = request.GET.get('ask_remove_delegation') == '1'
    return render(request, 'sub_toolbox_complete.html', {
        'selected_sub': selected_sub,
        'scheduled': scheduled,
        'job': job,
        'sub_employees': sub_employees,
        'english_file': english_file,
        'spanish_file': spanish_file,
        'english_viewed': english_viewed,
        'spanish_viewed': spanish_viewed,
        'can_complete': can_complete,
        'toolbox_base_folder': base_folder,
        'toolbox_folder_id': folder_id,
        'from_employee': from_employee,
        'preselected_employee_id': str(preselected_employee_id or ''),
        'ask_remove_delegation': ask_remove_delegation,
    })


def sub_toolbox_delegate(request, sub_id, scheduled_id, job_number):
    selected_sub = get_object_or_404(Subcontractors, id=sub_id)
    scheduled = get_object_or_404(ScheduledToolboxTalks, id=scheduled_id)
    job = get_object_or_404(Jobs, job_number=job_number)

    subcontract = get_object_or_404(
        Subcontracts,
        subcontractor=selected_sub,
        job_number=job,
        is_closed=False
    )

    assigned_employee_ids = Subcontractor_Job_Assignments.objects.filter(
        job=job,
        employee__subcontractor=selected_sub,
        employee__is_active=True,
        employee__has_access_to_toolbox=True
    ).values_list('employee_id', flat=True)

    employees = Subcontractor_Employees.objects.filter(
        id__in=assigned_employee_ids
    ).order_by('name')

    if request.method == 'POST':
        SubcontractorEmployeeDelegation.objects.get_or_create(
            subcontractor=selected_sub,
            subcontract=subcontract
        )
        backfilled_count = _backfill_delegated_job_toolbox_completions(subcontract)

        messages.success(
            request,
            f"Employees have been delegated to complete toolbox talks themselves. {backfilled_count} existing toolbox completions were applied."
        )

        return redirect('portal', sub_id=selected_sub.id, contract_id='ALL')

    return render(request, 'sub_toolbox_delegate.html', {
        'selected_sub': selected_sub,
        'scheduled': scheduled,
        'job': job,
        'subcontract': subcontract,
        'employees': employees,
    })


@require_POST
def ajax_check_sub_toolbox_can_complete(request):
    sub_id = request.POST.get("sub_id")
    scheduled_id = request.POST.get("scheduled_id")
    job_number = request.POST.get("job_number")

    if not sub_id or not scheduled_id or not job_number:
        return JsonResponse({
            "can_complete": False,
            "error": "Missing required information."
        })

    try:
        selected_sub = Subcontractors.objects.get(id=sub_id)
        scheduled = ScheduledToolboxTalks.objects.get(id=scheduled_id)
        job = Jobs.objects.get(job_number=job_number)
    except Subcontractors.DoesNotExist:
        return JsonResponse({
            "can_complete": False,
            "error": "Subcontractor not found."
        })
    except ScheduledToolboxTalks.DoesNotExist:
        return JsonResponse({
            "can_complete": False,
            "error": "Toolbox talk not found."
        })
    except Jobs.DoesNotExist:
        return JsonResponse({
            "can_complete": False,
            "error": "Job not found."
        })

    can_complete = ViewedSubToolboxJobTalks.objects.filter(
        scheduled=scheduled,
        subcontractor=selected_sub,
        job=job
    ).exists()

    return JsonResponse({
        "can_complete": can_complete
    })


@require_POST
def ajax_check_subcontractor_employee_toolbox_can_complete(request):
    employee_id = request.POST.get("employee_id")
    scheduled_id = request.POST.get("scheduled_id")

    if not employee_id or not scheduled_id:
        return JsonResponse({
            "can_complete": False,
            "error": "Missing employee or scheduled toolbox talk."
        })

    try:
        selected_employee = Subcontractor_Employees.objects.get(id=employee_id)
    except Subcontractor_Employees.DoesNotExist:
        return JsonResponse({
            "can_complete": False,
            "error": "Subcontractor employee not found."
        })

    try:
        scheduled = ScheduledToolboxTalks.objects.get(id=scheduled_id)
    except ScheduledToolboxTalks.DoesNotExist:
        return JsonResponse({
            "can_complete": False,
            "error": "Toolbox talk not found."
        })

    can_complete = ViewedSubToolboxTalks.objects.filter(
        employee=selected_employee,
        master=scheduled
    ).exists()

    return JsonResponse({
        "can_complete": can_complete
    })
