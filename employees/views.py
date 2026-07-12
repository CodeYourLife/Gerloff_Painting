from .forms import EmployeeUploadForm
from collections import defaultdict
from console.misc import createfolder
from console.misc import Email
from datetime import date, timedelta, datetime
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Q, Max, Count
from django.http import JsonResponse, HttpResponse, FileResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.template.loader import get_template
from django.utils.timezone import now
from django.utils import timezone
from django.utils.text import get_valid_filename
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.cache import never_cache

from employees.models import *
from employees.models import Employees, ToolboxTalks, ScheduledToolboxTalks,ScheduledToolboxTalkEmployees
from equipment.models import Inventory
from jobs.models import Jobs, JobNotes, Email_Errors, JobsiteSafetyInspection, ClockSharkTimeEntry
from media.utilities import MediaUtilities
import json
import mimetypes
import openpyxl
import os
import shutil
from subcontractors.models import *
from subcontractors import toolbox_views as sub_toolbox
from xhtml2pdf import pisa
from dateutil.relativedelta import relativedelta


VACATION_APPROVAL_BASE_URL = "http://184.183.68.156"
GROUP_TOOLBOX_VIEW_MINUTES = 30


def _group_toolbox_view_cutoff():
    return timezone.now() - timedelta(minutes=GROUP_TOOLBOX_VIEW_MINUTES)


def _group_toolbox_view_is_current(view):
    if not view:
        return False

    cutoff = _group_toolbox_view_cutoff()
    return (
        (view.viewed_english and view.viewed_english_time and view.viewed_english_time >= cutoff) or
        (view.viewed_spanish and view.viewed_spanish_time and view.viewed_spanish_time >= cutoff)
    )


def _delete_expired_group_toolbox_views():
    cutoff = _group_toolbox_view_cutoff()
    GroupToolboxTalkViews.objects.filter(
        Q(viewed_english_time__isnull=True) | Q(viewed_english_time__lt=cutoff),
        Q(viewed_spanish_time__isnull=True) | Q(viewed_spanish_time__lt=cutoff),
    ).delete()


def _close_previous_employee_respirator_certifications(employee, current_certification, note_user=None):
    previous_certifications = Certifications.objects.filter(
        employee=employee,
        is_closed=False,
        category__description="Respirator Clearance",
    ).exclude(
        id=current_certification.id,
    )

    closed_count = 0
    note_user = note_user or employee

    for certification in previous_certifications:
        certification.is_closed = True
        certification.save(update_fields=["is_closed"])
        CertificationNotes.objects.create(
            certification=certification,
            date=date.today(),
            user=note_user,
            note=f"Closed because new respirator clearance {current_certification.id} was completed.",
        )
        closed_count += 1

    return closed_count


def _certification_files_folder(certification_id):
    return os.path.join(settings.MEDIA_ROOT, "certifications", str(certification_id))


def _certification_file_rows(certification_id):
    folder = _certification_files_folder(certification_id)
    os.makedirs(folder, exist_ok=True)

    files = []
    for filename in sorted(os.listdir(folder)):
        path = os.path.join(folder, filename)
        if os.path.isfile(path):
            files.append({
                "name": filename,
                "url": reverse("certification_file", args=[certification_id, filename]),
            })
    return files


def _certification_upload_filename(uploaded_file, custom_name, index=None):
    original_name = os.path.basename(uploaded_file.name)
    original_root, original_extension = os.path.splitext(original_name)
    file_root = custom_name.strip() if custom_name and custom_name.strip() else original_root

    if index is not None:
        file_root = f"{file_root} {index}"

    safe_root = get_valid_filename(file_root) or "certification_file"
    safe_extension = get_valid_filename(original_extension).lower()
    return f"{safe_root}{safe_extension}"


def _duplicate_certification_sub_employee_name(base_name, subcontractor):
    duplicate_name = f"{base_name} 2"
    suffix = 2

    while Subcontractor_Employees.objects.filter(
        subcontractor=subcontractor,
        name__iexact=duplicate_name,
    ).exists():
        suffix += 1
        duplicate_name = f"{base_name} {suffix}"

    return duplicate_name


@login_required(login_url='/accounts/login')
def certification_file(request, certification_id, filename):
    certification = get_object_or_404(Certifications, id=certification_id)
    safe_name = os.path.basename(filename)
    file_path = os.path.join(_certification_files_folder(certification.id), safe_name)

    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        raise Http404("File not found")

    content_type, _ = mimetypes.guess_type(file_path)
    return FileResponse(
        open(file_path, "rb"),
        as_attachment=False,
        filename=safe_name,
        content_type=content_type,
    )


def get_respirators_in_review():
    respirators_in_review = []
    for x in RespiratorClearance.objects.filter(
        certification__is_closed=False,
    ).select_related('employee', 'certification'):
        if x.approved_for_use:
            continue
        status = "Need Safety Director Approval" if x.date_completed else "Need to Complete Application"
        respirators_in_review.append({
            'employee': x.employee.first_name + " " + x.employee.last_name,
            'date': x.date_completed or x.date_created,
            'status': status,
            'certification_id': x.certification_id,
            'link_to_certification': bool(x.certification_id),
        })

    for x in (
        SubcontractorRespiratorClearance.objects
        .filter(approved_for_use=False, is_closed=False)
        .select_related('subcontractor', 'employee')
    ):
        respirators_in_review.append({
            'employee': f"{x.subcontractor.company} - {x.employee_display_name}",
            'date': x.date_completed or x.date_created,
            'status': "Need Safety Director Approval" if x.date_completed else "Need to Complete Application",
            'link_to_subcontractor_clearance': True,
            'subcontractor_id': x.subcontractor_id,
            'clearance_id': x.id,
        })

    return respirators_in_review


def _complete_employee_toolbox_talk(employee, scheduled_talk):
    completed_talk, created = CompletedToolboxTalks.objects.get_or_create(
        employee=employee,
        master=scheduled_talk,
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


def _excuse_employee_toolbox_talk(employee, scheduled_talk):
    completed_talk, created = CompletedToolboxTalks.objects.get_or_create(
        employee=employee,
        master=scheduled_talk,
        defaults={
            'date': date.today(),
            'is_excused': True,
        }
    )

    if not created and not completed_talk.is_excused:
        return False

    return created


def _excuse_subcontractor_toolbox_talk(employee, scheduled_talk, job):
    completed_talk, created = CompletedSubToolboxTalks.objects.get_or_create(
        employee=employee,
        master=scheduled_talk,
        job=job,
        defaults={
            'date': date.today(),
            'is_excused': True,
        }
    )

    if not created and not completed_talk.is_excused:
        return False

    return created


def _excuse_subcontractor_job_toolbox_talk(scheduled_talk, subcontractor, job):
    completed_talk, created = CompletedSubToolboxJobTalks.objects.get_or_create(
        scheduled=scheduled_talk,
        subcontractor=subcontractor,
        job=job,
        defaults={
            'is_excused': True,
        }
    )

    if not created and not completed_talk.is_excused:
        return False

    return created


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


def _has_excused_employee_toolbox_talk(employee, scheduled_talk):
    return CompletedToolboxTalks.objects.filter(
        master=scheduled_talk,
        employee=employee,
        is_excused=True
    ).exists()


def _has_excused_subcontractor_toolbox_talk(employee, scheduled_talk, job=None):
    query = CompletedSubToolboxTalks.objects.filter(
        master=scheduled_talk,
        employee=employee,
        is_excused=True
    )

    if job is not None:
        query = query.filter(job=job)

    return query.exists()


def _has_excused_subcontractor_job_toolbox_talk(scheduled_talk, subcontractor, job):
    return CompletedSubToolboxJobTalks.objects.filter(
        scheduled=scheduled_talk,
        subcontractor=subcontractor,
        job=job,
        is_excused=True
    ).exists()


def _get_first_subcontractor_invoice_date(subcontract):
    return (
        SubcontractorInvoice.objects
        .filter(subcontract=subcontract)
        .order_by('date', 'id')
        .values_list('date', flat=True)
        .first()
    )


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


def _get_all_employee_toolbox_talks_for_subcontract(subcontract, end_date=None, start_date=None, **filters):
    first_invoice_date = _get_first_subcontractor_invoice_date(subcontract)
    if not first_invoice_date:
        return ScheduledToolboxTalks.objects.none()

    query = ScheduledToolboxTalks.objects.filter(
        is_all_employees=True,
        date__isnull=False,
        date__gt=first_invoice_date,
        **filters
    )

    if end_date is not None:
        query = query.filter(date__lte=end_date)

    if start_date is not None:
        query = query.filter(date__gte=start_date)

    return query


def _is_active_toolbox_job(job):
    return bool(
        job and
        not job.is_closed and
        job.is_active and
        not job.is_labor_done
    )


def _sub_employee_has_active_toolbox_job(sub_employee, job=None):
    query = Subcontractor_Job_Assignments.objects.filter(
        employee=sub_employee,
        job__is_closed=False,
        job__is_active=True,
        job__is_labor_done=False
    )

    if job is not None:
        query = query.filter(job=job)

    return query.exists()


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


def _sub_employee_has_delegated_active_toolbox_job(sub_employee, job=None, effective_date=None):
    return bool(_get_delegated_active_toolbox_jobs_for_sub_employee(sub_employee, job, effective_date))


def _has_sub_employee_toolbox_record_for_any_job(sub_employee, scheduled_talk, jobs):
    if CompletedSubToolboxTalks.objects.filter(
        employee=sub_employee,
        master=scheduled_talk,
        job__in=jobs
    ).exists():
        return True

    return CompletedSubToolboxJobTalkEmployees.objects.filter(
        employee=sub_employee,
        completed__scheduled=scheduled_talk,
        completed__job__in=jobs,
        completed__is_excused=False
    ).exists()


def _sub_employee_has_completed_scheduled_talk_anywhere(sub_employee, scheduled_talk):
    if CompletedSubToolboxTalks.objects.filter(
        employee=sub_employee,
        master=scheduled_talk,
        is_excused=False
    ).exists():
        return True

    return CompletedSubToolboxJobTalkEmployees.objects.filter(
        employee=sub_employee,
        completed__scheduled=scheduled_talk,
        completed__is_excused=False
    ).exists()


def _get_toolbox_talks_for_delegated_subcontract(subcontract, sub_employee, end_date=None):
    start_date = _sub_employee_assignment_start_date(sub_employee, subcontract)
    if not start_date:
        return ScheduledToolboxTalks.objects.none()

    scheduled_ids = set(
        _get_all_employee_toolbox_talks_for_subcontract(
            subcontract,
            end_date=end_date,
            start_date=start_date
        ).values_list('id', flat=True)
    )

    explicit_job_talks = ScheduledToolboxTalkSubJobs.objects.filter(
        subcontractor=subcontract.subcontractor,
        job=subcontract.job_number,
        subcontractor__is_toolbox_required=True,
        scheduled__date__isnull=False,
        scheduled__date__gte=start_date,
    )

    explicit_employee_talks = ScheduledToolboxTalkSubEmployees.objects.filter(
        employee=sub_employee,
        job=subcontract.job_number,
        employee__subcontractor__is_toolbox_required=True,
        scheduled__date__isnull=False,
        scheduled__date__gte=start_date,
    )

    if end_date is not None:
        explicit_job_talks = explicit_job_talks.filter(scheduled__date__lte=end_date)
        explicit_employee_talks = explicit_employee_talks.filter(scheduled__date__lte=end_date)

    scheduled_ids.update(explicit_job_talks.values_list('scheduled_id', flat=True))
    scheduled_ids.update(explicit_employee_talks.values_list('scheduled_id', flat=True))

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
    today = timezone.localdate()

    for sub_employee in assigned_employees:
        scheduled_talks = _get_toolbox_talks_for_delegated_subcontract(
            subcontract,
            sub_employee,
            end_date=today
        )

        for scheduled_talk in scheduled_talks:
            if scheduled_talk.date and sub_employee.date_enrolled > scheduled_talk.date:
                continue

            if CompletedSubToolboxTalks.objects.filter(
                employee=sub_employee,
                master=scheduled_talk,
                job=subcontract.job_number
            ).exists():
                continue

            if not _sub_employee_has_completed_scheduled_talk_anywhere(
                sub_employee,
                scheduled_talk
            ):
                continue

            _complete_subcontractor_toolbox_talk(
                sub_employee,
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
    today = timezone.localdate()

    for sub_employee in assigned_employees:
        scheduled_ids.update(
            _get_toolbox_talks_for_delegated_subcontract(
                subcontract,
                sub_employee,
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


def _get_completed_sub_employee_toolbox_talk_ids(sub_employee, assigned_ids, jobs):
    individual_ids = set(
        CompletedSubToolboxTalks.objects
        .filter(
            employee=sub_employee,
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
            employee=sub_employee,
            completed__scheduled_id__in=assigned_ids,
            completed__job__in=jobs,
            completed__is_excused=False
        )
        .values_list('completed__scheduled_id', flat=True)
        .distinct()
    )

    return individual_ids | attended_group_ids


def _get_assigned_sub_employee_toolbox_pairs(sub_employee):
    if (
        not sub_employee.has_access_to_toolbox or
        not sub_employee.subcontractor or
        not sub_employee.subcontractor.is_toolbox_required
    ):
        return set()

    delegated_jobs = _get_delegated_active_toolbox_jobs_for_sub_employee(sub_employee)
    if not delegated_jobs:
        return set()

    assigned_pairs = set()

    explicit_assignments = (
        ScheduledToolboxTalkSubEmployees.objects
        .filter(
            employee=sub_employee,
            employee__subcontractor__is_toolbox_required=True
        )
        .select_related('scheduled', 'job')
        .distinct()
    )

    for assignment in explicit_assignments:
        if not assignment.job:
            continue
        if not _is_active_toolbox_job(assignment.job):
            continue
        if not _sub_employee_has_delegated_active_toolbox_job(
            sub_employee,
            assignment.job,
            assignment.scheduled.date
        ):
            continue
        assigned_pairs.add((assignment.scheduled_id, assignment.job_id))

    if sub_employee.date_enrolled:
        today = timezone.localdate()
        for job in delegated_jobs:
            subcontract = Subcontracts.objects.filter(
                subcontractor=sub_employee.subcontractor,
                job_number=job,
                is_closed=False,
                subcontractor__is_toolbox_required=True,
                job_number__is_closed=False,
                job_number__is_active=True,
                job_number__is_labor_done=False
            ).first()

            if not subcontract:
                continue

            start_date = _sub_employee_assignment_start_date(sub_employee, subcontract)
            if not start_date:
                continue

            scheduled_ids = (
                _get_all_employee_toolbox_talks_for_subcontract(
                    subcontract,
                    end_date=today,
                    start_date=start_date
                )
                .values_list('id', flat=True)
                .distinct()
            )

            for scheduled_id in scheduled_ids:
                assigned_pairs.add((scheduled_id, job.pk))

    return assigned_pairs


def _get_completed_sub_employee_toolbox_pairs(sub_employee, assigned_pairs):
    if not assigned_pairs:
        return set()

    scheduled_ids = {scheduled_id for scheduled_id, job_id in assigned_pairs}
    job_ids = {job_id for scheduled_id, job_id in assigned_pairs}

    individual_pairs = set(
        CompletedSubToolboxTalks.objects
        .filter(
            employee=sub_employee,
            master_id__in=scheduled_ids,
            job_id__in=job_ids,
            is_excused=False
        )
        .values_list('master_id', 'job_id')
        .distinct()
    )

    attended_group_pairs = set(
        CompletedSubToolboxJobTalkEmployees.objects
        .filter(
            employee=sub_employee,
            completed__scheduled_id__in=scheduled_ids,
            completed__job_id__in=job_ids,
            completed__is_excused=False
        )
        .values_list('completed__scheduled_id', 'completed__job_id')
        .distinct()
    )

    return (individual_pairs | attended_group_pairs) & assigned_pairs


def _get_excused_sub_employee_toolbox_pairs(sub_employee, assigned_pairs):
    if not assigned_pairs:
        return set()

    scheduled_ids = {scheduled_id for scheduled_id, job_id in assigned_pairs}
    job_ids = {job_id for scheduled_id, job_id in assigned_pairs}

    return set(
        CompletedSubToolboxTalks.objects
        .filter(
            employee=sub_employee,
            master_id__in=scheduled_ids,
            job_id__in=job_ids,
            is_excused=True
        )
        .values_list('master_id', 'job_id')
        .distinct()
    ) & assigned_pairs


def _get_sub_employee_toolbox_completion_date(sub_employee, scheduled_talk, job):
    completed = (
        CompletedSubToolboxTalks.objects
        .filter(
            employee=sub_employee,
            master=scheduled_talk,
            job=job,
            is_excused=False
        )
        .order_by('-date')
        .first()
    )

    if completed:
        return completed.date

    attended = (
        CompletedSubToolboxJobTalkEmployees.objects
        .filter(
            employee=sub_employee,
            completed__scheduled=scheduled_talk,
            completed__job=job,
            completed__is_excused=False
        )
        .select_related('completed')
        .order_by('-completed__date')
        .first()
    )

    if attended and attended.completed:
        return attended.completed.date

    return None


def _is_painter(employee):
    return bool(employee.job_title and employee.job_title.description == "Painter")


def _vacation_weekday_count(first_day, last_day):
    if not first_day or not last_day or last_day < first_day:
        return 0

    vacation_days = 0
    current_day = first_day

    while current_day <= last_day:
        if current_day.weekday() < 5:
            vacation_days += 1

        current_day += timedelta(days=1)

    return vacation_days


def _vacation_allowed_days_for(employee):
    if employee.vacation_days_per_year is not None:
        return employee.vacation_days_per_year

    vacation_defaults, created = VacationDefaults.objects.get_or_create(id=1)

    if (
        employee.job_title and
        employee.job_title.description == "Painter"
    ):
        if (
            employee.employment_company and
            employee.employment_company.company_name == "Gerloff Painting"
        ):
            return vacation_defaults.painter_days_per_year

        return 0

    return vacation_defaults.non_painter_days_per_year


def _vacation_history_by_year(employee):
    vacation_history_by_year = []
    vacation_history = Vacation.objects.filter(
        employee=employee,
    ).order_by("-first_day", "-id")
    vacation_history_years = {}

    for vacation_item in vacation_history:
        vacation_year = vacation_item.first_day.year

        if vacation_year not in vacation_history_years:
            vacation_history_years[vacation_year] = {
                "year": vacation_year,
                "total_days": 0,
                "vacations": [],
            }

        vacation_item.display_duration = _vacation_weekday_count(
            vacation_item.first_day,
            vacation_item.last_day,
        )
        vacation_item.approver_statuses = ApprovedVacations.objects.filter(
            request=vacation_item,
        ).select_related(
            "approver",
        ).order_by("approver__last_name", "approver__first_name")

        if vacation_item.is_approved:
            vacation_history_years[vacation_year]["total_days"] += vacation_item.display_duration

        vacation_history_years[vacation_year]["vacations"].append(vacation_item)

    for vacation_year in sorted(vacation_history_years.keys(), reverse=True):
        vacation_history_by_year.append(vacation_history_years[vacation_year])

    return vacation_history_by_year


def _vacation_approvers_for(employee):
    if _is_painter(employee):
        group_names = [
            "Painter Vacation Approvals",
            "Painter Vacation Approvers",
        ]
    else:
        group_names = [
            "Office Vacation Approvers",
        ]

    approvers = {}

    group_approvers = Employees.objects.filter(
        active=True,
        user__groups__name__in=group_names,
    ).distinct()

    for approver in group_approvers:
        approvers[approver.id] = approver

    if _is_painter(employee):
        superintendents = Employees.objects.filter(
            active=True,
            job_title__description__in=["Superintendent", "Superintendant"],
        )

        for approver in superintendents:
            approvers[approver.id] = approver

    return list(approvers.values())


def _send_vacation_request_emails(vacation, approvers):
    vacation_link = VACATION_APPROVAL_BASE_URL + reverse("my_page")
    requester = vacation.employee
    requester_name = str(requester)
    sender = requester.email or "operations@gerloffpainting.com"
    note = vacation.employee_note or "No note provided."
    vacation_duration = _vacation_weekday_count(vacation.first_day, vacation.last_day)

    body = (
        f"{requester_name} submitted a vacation request.\n\n"
        f"First Day Off: {vacation.first_day.strftime('%m/%d/%Y')}\n"
        f"Last Day Off: {vacation.last_day.strftime('%m/%d/%Y')}\n"
        f"Duration: {vacation_duration} day{'s' if vacation_duration != 1 else ''}\n"
        f"Note: {note}\n\n"
        f"Review the request here:\n{vacation_link}"
    )

    for approver in approvers:
        if not approver.email:
            continue

        Email.sendEmail(
            "Vacation Request Submitted",
            body,
            [approver.email],
            False,
            sender,
        )


def _send_vacation_final_status_email(vacation):
    employee = vacation.employee

    if not employee.email:
        Email.sendEmail(
            "Employee Vacation Approved - Missing Email",
            "Employee vacation approved, however no email is on file",
            ["bridgette@gerloffpainting.com"],
            False,
            "operations@gerloffpainting.com",
        )
        return

    rejected_approvals = ApprovedVacations.objects.filter(
        request=vacation,
        is_rejected=True,
    ).select_related(
        "approver",
    ).order_by("approver__last_name", "approver__first_name")

    sender = "operations@gerloffpainting.com"
    vacation_duration = _vacation_weekday_count(vacation.first_day, vacation.last_day)

    if rejected_approvals.exists():
        rejection_notes = []

        for approval in rejected_approvals:
            if approval.approver_notes:
                rejection_notes.append(f"{approval.approver}: {approval.approver_notes}")
            else:
                rejection_notes.append(f"{approval.approver}: No note provided.")

        body = (
            "Your vacation request was rejected.\n\n"
            f"First Day Off: {vacation.first_day.strftime('%m/%d/%Y')}\n"
            f"Last Day Off: {vacation.last_day.strftime('%m/%d/%Y')}\n"
            f"Duration: {vacation_duration} day{'s' if vacation_duration != 1 else ''}\n\n"
            "Rejection Notes:\n"
            + "\n".join(rejection_notes)
        )

        Email.sendEmail(
            "Vacation Request Rejected",
            body,
            [employee.email],
            False,
            sender,
        )
        return

    body = (
        "Your vacation request was approved.\n\n"
        f"First Day Off: {vacation.first_day.strftime('%m/%d/%Y')}\n"
        f"Last Day Off: {vacation.last_day.strftime('%m/%d/%Y')}\n"
        f"Duration: {vacation_duration} day{'s' if vacation_duration != 1 else ''}"
    )

    Email.sendEmail(
        "Vacation Request Approved",
        body,
        [employee.email, "joe@gerloffpainting.com"],
        False,
        sender,
    )


@login_required(login_url='/accounts/login')
def employee_notes(request, employee):
    send_data = {}
    special = False
    if employee == 'AUTO':
        selected_superid = Employees.objects.get(user=request.user).id
    else:
        selected_superid = employee  # selected_superid = either 'ALL' or the ID of super
    if request.method == 'GET':
        if 'search2' in request.GET:
            send_data['search2_exists'] = request.GET['search2']  # super name
            if request.GET['search2'] == 'ALL':
                selected_superid = 'ALL'
            else:
                selected_superid = request.GET['search2']
    if selected_superid == 'ALL':
        send_data['filter_status'] = 'ALL'
        send_data['notes'] = JobNotes.objects.all()
    else:
        selected_employee = Employees.objects.get(id=selected_superid)
        send_data['selected_super'] = selected_employee
        send_data['notes'] = JobNotes.objects.filter(user=selected_employee)
    send_data['supers'] = Employees.objects.filter(active=True)
    # notes = []
    # for x in notes_list:
    #     notes.append({'job_name': jobs.objects.get(job_number=x.job_number)})
    # invoice_items.append({'description': "Release Retainage", 'billed': selected_invoice.release_retainage,
    #                       'notes': selected_invoice.retainage_note, 'sov_item': 0, 'quantity': 0})
    return render(request, "employee_notes.html", send_data)
@login_required(login_url='/accounts/login')
def new_production_report(request, jobnumber):
    send_data = {}
    if jobnumber == 'ALL':
        send_data['jobs'] = Jobs.objects.filter(is_closed=False)
    else:
        send_data['jobs'] = Jobs.objects.get(job_number=jobnumber)
        send_data['selected_job'] = Jobs.objects.get(job_number=jobnumber)

    send_data['category1'] = json.dumps(
        list(ProductionCategory.objects.all().order_by('item1').values().distinct('item1')), cls=DjangoJSONEncoder)
    send_data['category2'] = json.dumps(
        list(ProductionCategory.objects.all().order_by('item1', 'item2', 'item3', 'task').values()),
        cls=DjangoJSONEncoder)
    send_data['employees_json'] = json.dumps(list(Employees.objects.filter(active=True).values()),
                                             cls=DjangoJSONEncoder)
    send_data['employees'] = Employees.objects.filter(active=True)
    send_data['current_employee'] = Employees.objects.get(user=request.user)

    if request.method == 'POST':
        if 'job_select' in request.POST:
            jobnumber = request.POST['select_job']
            send_data['jobs'] = Jobs.objects.get(job_number=jobnumber)
            send_data['selected_job'] = Jobs.objects.get(job_number=jobnumber)
            return render(request, "new_production_report.html", send_data)
        send_data['selected_reviewer'] = Employees.objects.get(id=request.POST['select_reviewer'])
        if 'report_complete' in request.POST:
            daily_report = DailyReports.objects.create(
                foreman=Employees.objects.get(id=request.POST['select_reviewer']), date=date.today(),
                note=request.POST['report_note'], job=Jobs.objects.get(job_number=request.POST['selected_job']))
            for x in request.POST:
                if x[0:20] == 'select_teamcategory1':
                    team_members = 0
                    team = x[20:len(x)]
                    team_note = ""
                    for y in request.POST:  # count team members
                        if y[0:26 + len(team)] == 'select_team' + team + 'select_employee':
                            team_members = team_members + 1
                            employee_number = y[26 + int(len(team)):len(y)]
                            employee = Employees.objects.get(
                                id=request.POST['select_team' + team + 'select_employee' + employee_number]).first_name
                            if 'taskteam_' + team + '_employee_' + employee_number in request.POST:
                                task = ProductionCategory.objects.get(
                                    id=request.POST['taskteam_' + team + '_employee_' + employee_number]).task
                            if 'custom_taskteam_' + team + '_employee_' + employee_number in request.POST:
                                task = request.POST['custom_taskteam_' + team + '_employee_' + employee_number]
                            team_note = team_note + employee + " " + task + ". "
                    team_note = request.POST['teamnotes_' + team] + ". " + team_note
                    for y in request.POST:
                        if y[0:26 + len(team)] == 'select_team' + team + 'select_employee':
                            employee_number = y[26 + len(team):len(y)]
                            employee = Employees.objects.get(id=request.POST[y])
                            note = request.POST['team_' + team + "_employeenote_" + employee_number]
                            if 'taskteam_' + team + '_employee_' + employee_number in request.POST:
                                task = ProductionCategory.objects.get(
                                    id=request.POST['taskteam_' + team + '_employee_' + employee_number])
                                description = task.item1 + " - " + task.item2 + " - " + task.item3 + " - " + task.task
                            else:
                                description = request.POST['custom_category1' + team] + "- " + request.POST[
                                    'custom_taskteam_' + team + '_employee_' + employee_number]
                            new_entry = ProductionItems.objects.create(team_number=team, note=note, is_team=True,
                                                                       team_note=team_note, daily_report=daily_report,
                                                                       employee=employee, date=date.today(),
                                                                       team_members=team_members,
                                                                       description=description)
                            if 'taskteam_' + team + '_employee_' + employee_number in request.POST:
                                new_entry.task = ProductionCategory.objects.get(
                                    id=request.POST['taskteam_' + team + '_employee_' + employee_number])
                            if request.POST['hoursteam_' + team] != "":
                                new_entry.hours = float(request.POST['hoursteam_' + team])
                            if 'unit1team_' + team in request.POST:
                                if request.POST['unit1team_' + team] != "":
                                    new_entry.value1 = float(request.POST['unit1team_' + team])
                                    new_entry.unit = task.unit1
                            if 'unit2team_' + team in request.POST:
                                if request.POST['unit2team_' + team] != "":
                                    new_entry.value2 = float(request.POST['unit2team_' + team])
                                    new_entry.unit2 = task.unit2
                            if 'unit3team_' + team in request.POST:
                                if request.POST['unit3team_' + team] != "":
                                    new_entry.value3 = float(request.POST['unit3team_' + team])
                                    new_entry.unit3 = task.unit3
                            if 'custom_category1' + team in request.POST:
                                new_entry.value1 = float(request.POST['custom_value' + team])
                                new_entry.unit = request.POST['custom_unit' + team]
                            new_entry.save()
                if x[0:15] == 'select_employee':
                    employee_number = x[15:len(x)]
                    if 'select_task' + employee_number in request.POST:
                        task = ProductionCategory.objects.get(id=request.POST['select_task' + employee_number])
                        description = task.item1 + " - " + task.item2 + " - " + task.item3 + " - " + task.task
                    else:
                        description = request.POST['custom_description' + employee_number]
                    employee = Employees.objects.get(id=request.POST[x])
                    note = request.POST['note' + employee_number]
                    new_entry = ProductionItems.objects.create(note=note, is_team=False, daily_report=daily_report,
                                                               employee=employee, date=date.today(),
                                                               description=description)
                    if 'select_task' + employee_number in request.POST:
                        new_entry.task = ProductionCategory.objects.get(
                            id=request.POST['select_task' + employee_number])
                    else:
                        new_entry.value1 = request.POST['custom_value1' + employee_number]
                        new_entry.unit = request.POST['custom_unit' + employee_number]
                    if request.POST['hours' + employee_number] != "":
                        new_entry.hours = float(request.POST['hours' + employee_number])
                    if 'value1' + employee_number in request.POST:
                        if request.POST['value1' + employee_number] != "":
                            new_entry.value1 = float(request.POST['value1' + employee_number])
                            new_entry.unit = task.unit1
                    if 'value2' + employee_number in request.POST:
                        if request.POST['value2' + employee_number] != "":
                            new_entry.value2 = float(request.POST['value2' + employee_number])
                            new_entry.unit2 = task.unit2
                    if 'value3' + employee_number in request.POST:
                        if request.POST['value3' + employee_number] != "":
                            new_entry.value3 = float(request.POST['value3' + employee_number])
                            new_entry.unit3 = task.unit3
                    new_entry.save()
            return render(request, "new_production_report.html", send_data)
    return render(request, "new_production_report.html", send_data)


@login_required(login_url='/accounts/login')
def new_assessment(request, id):
    send_data = {}
    if request.method == 'POST':
        if 'new_assessment' in request.POST:
            assessment = MetricAssessment.objects.create(reviewer=Employees.objects.get(id=request.POST['reviewer']),
                                                         note=request.POST['note_main'], date=date.today())
            review = EmployeeReview.objects.create(assessment=assessment,
                                                   employee=Employees.objects.get(id=request.POST['employee']))
            for x in request.POST:
                if request.POST[x] == 'on':
                    # if x[0:4] != 'note':
                    category = MetricCategories.objects.get(id=x)
                    MetricAssessmentItem.objects.create(assessment=review,
                                                        note=request.POST['note' + str(category.metric.id)],
                                                        category=category,
                                                        employee=Employees.objects.get(id=request.POST['employee']))
        if 'select_employees' in request.POST:
            send_data['reviewer'] = Employees.objects.get(id=request.POST['select_reviewer'])
            employee = Employees.objects.get(id=request.POST['select_employee'])
            send_data['employee'] = employee
            categories = MetricCategories.objects.order_by('metric', 'number').values('id', 'metric__id',
                                                                                      'metric__description', 'number',
                                                                                      'description')
            allcategories_json = json.dumps(list(categories), cls=DjangoJSONEncoder)
            send_data['allcategories'] = allcategories_json
            categories = []
            for x in MetricLevels.objects.filter(level=employee.level):
                for y in MetricCategories.objects.order_by('metric', 'number'):
                    if x.metric == y.metric:
                        categories.append(
                            {'id': y.id, 'metric__id': y.metric.id, 'metric__description': y.metric.description,
                             'number': y.number, 'description': y.description})

            categories_json = json.dumps(list(categories), cls=DjangoJSONEncoder)
            send_data['categories'] = categories_json
            send_data['metrics'] = json.dumps(list(Metrics.objects.values('id', 'description')), cls=DjangoJSONEncoder)
    else:
        send_data['current_user'] = Employees.objects.get(user=request.user)
        send_data['employees'] = Employees.objects.filter(active=True)
        # send_data['current_user']=json.dumps(list(Employees.objects.filter(user=request.user).values('id','last_name','first_name')), cls=DjangoJSONEncoder)
        # send_data['employees'] = json.dumps(list(Employees.objects.filter(active=True).values('id','last_name','first_name')), cls=DjangoJSONEncoder)
    return render(request, "new_assessment.html", send_data)


@login_required(login_url='/accounts/login')
def classes(request, id):
    send_data = {}
    send_data['classoccurrences'] = ClassOccurrence.objects.all()
    if id != 'ALL':
        send_data['selected_item'] = ClassOccurrence.objects.get(id=id)
        send_data['attendees'] = ClassAttendees.objects.filter(class_event__id=id)
    return render(request, "classes.html", send_data)


@login_required(login_url='/accounts/login')
def new_class(request):
    send_data = {}
    send_data['employees'] = Employees.objects.filter(active=True)
    send_data['topics'] = TrainingTopic.objects.all()
    send_data['jobs'] = Jobs.objects.filter(is_closed=False)
    send_data['topics_json'] = json.dumps(list(TrainingTopic.objects.values()), cls=DjangoJSONEncoder)
    send_data['employees_json'] = json.dumps(list(Employees.objects.filter(active=True).values()),
                                             cls=DjangoJSONEncoder)
    if request.method == 'POST':
        new_class = ClassOccurrence.objects.create(date=date.today(), note=request.POST['class_note'],
                                                   location=request.POST['location'])
        if request.POST['select_job'] != 'please_select':
            new_class.job = Jobs.objects.get(job_number=request.POST['select_job'])
        if request.POST['select_topic'] != 'custom_topic':
            topic = TrainingTopic.objects.get(id=request.POST['select_topic'])
            description = topic.description
            new_class.topic = topic
            new_class.description = description
        else:
            description = request.POST['custom_topic']
            new_class.description = description
        if request.POST['select_teacher'] != 'custom_teacher':
            teacher = Employees.objects.get(id=request.POST['select_teacher'])
            new_class.teacher = teacher
        else:
            teacher2 = request.POST['custom_teacher']
            new_class.teacher2 = teacher2
        new_class.save()
        for x in request.POST:
            if x[0:15] == 'select_employee':
                employee_number = x[15:int(len(x))]
                if request.POST[x] == 'custom_student':
                    ClassAttendees.objects.create(class_event=new_class,
                                                  student2=request.POST['custom_student' + employee_number],
                                                  note=request.POST['note_' + employee_number])
                else:
                    ClassAttendees.objects.create(class_event=new_class,
                                                  student=Employees.objects.get(id=request.POST[x]),
                                                  note=request.POST['note_' + employee_number])
        return redirect('classes', id='ALL')
    return render(request, "new_class.html", send_data)


@login_required(login_url='/accounts/login')
def exams(request, id):
    send_data = {}
    send_data['employees'] = Employees.objects.filter(active=True)
    send_data['exam_scores'] = ExamScore.objects.all()
    if id != 'ALL':
        send_data['selected_item'] = ExamScore.objects.get(id=id)
        send_data['attendees'] = ClassAttendees.objects.filter(class_event__id=id)
    return render(request, "exams.html", send_data)


@login_required(login_url='/accounts/login')
def new_exam(request):
    send_data = {}
    send_data['employees'] = Employees.objects.filter(active=True)
    send_data['exams'] = Exam.objects.all()
    send_data['exams_json'] = json.dumps(list(Exam.objects.all().values()), cls=DjangoJSONEncoder)
    if request.method == 'POST':
        new_exam = ExamScore.objects.create(score=request.POST['score'], note=request.POST['exam_note'],
                                            date=date.today())
        if 'custom_student' in request.POST:
            new_exam.student2 = request.POST['custom_student']
        else:
            new_exam.student = Employees.objects.get(id=request.POST['select_student'])
        if 'custom_teacher' in request.POST:
            new_exam.teacher2 = request.POST['custom_teacher']
        else:
            new_exam.teacher = Employees.objects.get(id=request.POST['select_teacher'])
        if 'custom_exam' in request.POST:
            new_exam.exam2 = request.POST['custom_exam']
            new_exam.custom_score_max = request.POST['custom_score_max']
        else:
            new_exam.exam = Exam.objects.get(id=request.POST['select_exam'])
        new_exam.save()
    return render(request, "new_exam.html", send_data)


@login_required(login_url='/accounts/login')
def mentorships(request, id):
    send_data = {}
    send_data['mentorships'] = Mentorship.objects.all()
    if request.method == 'POST':
        if 'new_note' in request.POST:
            MentorshipNotes.objects.create(mentorship=Mentorship.objects.get(id=id), date=date.today(),
                                           user=Employees.objects.get(user=request.user),
                                           note=request.POST['note'])
        else:
            if 'closed' in request.POST:
                selected_item = Mentorship.objects.get(id=id)
                selected_item.is_closed = True
                selected_item.end_date = date.today()
                MentorshipNotes.objects.create(mentorship=selected_item, date=date.today(),
                                               user=Employees.objects.get(user=request.user),
                                               note="Mentorship Ended." + request.POST['note'])
            else:
                selected_item = Mentorship.objects.get(id=id)
                selected_item.is_closed = False
                selected_item.end_date = ""
                MentorshipNotes.objects.create(mentorship=selected_item, date=date.today(),
                                               user=Employees.objects.get(user=request.user),
                                               note="Mentorship Activated Again." + request.POST['note'])
            selected_item.save()
    if id != 'ALL':
        send_data['selected_notes'] = MentorshipNotes.objects.filter(mentorship__id=id)
        send_data['selected_item'] = Mentorship.objects.get(id=id)
    return render(request, "mentorships.html", send_data)


@login_required(login_url='/accounts/login')
def new_mentorship(request):
    send_data = {}
    send_data['employees'] = Employees.objects.filter(active=True)
    if request.method == 'POST':
        new_item = Mentorship.objects.create(apprentice=Employees.objects.get(id=request.POST['select_apprentice']),
                                             mentor=Employees.objects.get(id=request.POST['select_mentor']),
                                             start_date=date.today(), note=request.POST['note'])
        MentorshipNotes.objects.create(mentorship=new_item, date=date.today(),
                                       user=Employees.objects.get(user=request.user),
                                       note="New mentorship added")
        return redirect('mentorships', id=new_item.id)
    return render(request, "new_mentorship.html", send_data)


@login_required(login_url='/accounts/login')
def assessments(request, id):
    send_data = {}
    send_data['employeereviews'] = EmployeeReview.objects.filter(employee__active=True)
    if id != 'ALL':
        send_data['selected_item'] = EmployeeReview.objects.get(id=id)
        selected_assessment = []
        for x in MetricAssessmentItem.objects.filter(assessment__id=id):
            if MetricCategories.objects.filter(metric=x.category.metric, number=x.category.number + 1).exists():
                selected_assessment.append(
                    {'category': x.category, 'total': x.category.metric.total_numbers, 'note': x.note,
                     'description': x.category.description,
                     'next': MetricCategories.objects.get(metric=x.category.metric,
                                                          number=x.category.number + 1).description})
            else:
                selected_assessment.append(
                    {'category': x.category, 'total': x.category.metric.total_numbers, 'note': x.note,
                     'description': x.category.description, 'next': "None"})
        send_data['selected_assessment'] = selected_assessment
    return render(request, "assessments.html", send_data)


@login_required(login_url='/accounts/login')
def production_reports(request, id):
    send_data = {}
    if id != 'ALL':
        send_data['production_reports'] = ProductionItems.objects.filter(id=id).order_by('employee', 'date')
        send_data['selected_item'] = ProductionItems.objects.get(id=id)
    else:
        send_data['production_reports'] = ProductionItems.objects.all().order_by('employee', 'date')
    return render(request, "production_reports.html", send_data)

def reinstate_employee(request, id):
    employee = get_object_or_404(Employees, id=id)

    employee.active = True
    employee.save()

    return redirect("employees_home")

def reinstate_subcontractor_employee(request, id):
    employee = get_object_or_404(Subcontractor_Employees, id=id)

    employee.is_active = True
    employee.save()

    return redirect("employees_home")


def _sub_employee_toolbox_summary(sub_employee):
    assigned_pairs = _get_assigned_sub_employee_toolbox_pairs(sub_employee)
    completed_pairs = _get_completed_sub_employee_toolbox_pairs(sub_employee, assigned_pairs)
    excused_pairs = _get_excused_sub_employee_toolbox_pairs(sub_employee, assigned_pairs)
    incomplete_pairs = assigned_pairs - completed_pairs - excused_pairs
    scheduled_ids = {scheduled_id for scheduled_id, job_id in assigned_pairs}
    job_ids = {job_id for scheduled_id, job_id in assigned_pairs}
    scheduled_by_id = {
        item.id: item
        for item in ScheduledToolboxTalks.objects.filter(
            id__in=scheduled_ids,
        ).select_related("master")
    }
    jobs_by_id = {
        item.pk: item
        for item in Jobs.objects.filter(pk__in=job_ids)
    }

    def talk_description(scheduled):
        if scheduled.description:
            return scheduled.description
        if scheduled.master:
            return scheduled.master.description
        return ""

    def pair_rows(pairs, include_completed_date=False):
        rows = []
        for scheduled_id, job_id in sorted(
            pairs,
            key=lambda pair: (
                scheduled_by_id.get(pair[0]).date if scheduled_by_id.get(pair[0]) else date.min,
                str(jobs_by_id.get(pair[1]) or ""),
            ),
        ):
            scheduled = scheduled_by_id.get(scheduled_id)
            job = jobs_by_id.get(job_id)
            row = {
                "scheduled_date": scheduled.date if scheduled else None,
                "description": talk_description(scheduled) if scheduled else "",
                "job": job,
            }
            if include_completed_date and scheduled and job:
                row["completed_date"] = _get_sub_employee_toolbox_completion_date(
                    sub_employee,
                    scheduled,
                    job,
                )
            rows.append(row)
        return rows

    return {
        "completed_count": len(completed_pairs),
        "incomplete_count": len(incomplete_pairs),
        "completed_talks": pair_rows(completed_pairs, include_completed_date=True),
        "incomplete_talks": pair_rows(incomplete_pairs),
    }


def subcontractor_employee_page(request, id):
    sub_employee = get_object_or_404(
        Subcontractor_Employees.objects.select_related("subcontractor"),
        id=id,
    )
    if request.method == "POST" and "update_employee_details" in request.POST:
        sub_employee.name = (request.POST.get("name") or "").strip()
        sub_employee.nickname = (request.POST.get("nickname") or "").strip()
        sub_employee.phone = (request.POST.get("phone") or "").strip()
        sub_employee.email = (request.POST.get("email") or "").strip()
        sub_employee.birth_date = request.POST.get("birth_date") or None
        sub_employee.save(update_fields=[
            "name",
            "nickname",
            "phone",
            "email",
            "birth_date",
        ])
        messages.success(request, "Employee details updated.")
        return redirect("subcontractor_employee_page", id=sub_employee.id)

    if request.method == "POST" and "update_trinity_registration" in request.POST:
        username = (request.POST.get("username") or "").strip()
        if username:
            username_exists = (
                Subcontractor_Employees.objects
                .filter(username__iexact=username)
                .exclude(id=sub_employee.id)
                .exists()
            )
            username_exists = username_exists or Subcontractors.objects.filter(
                username__iexact=username
            ).exists()
            username_exists = username_exists or User.objects.filter(
                username__iexact=username
            ).exists()
            if username_exists:
                messages.error(request, "USERNAME ALREADY IN USE. Please choose a different username.")
                return redirect("subcontractor_employee_page", id=sub_employee.id)

        sub_employee.username = username
        sub_employee.password1 = (request.POST.get("password1") or "").strip()
        sub_employee.has_access_to_toolbox = request.POST.get("has_access_to_toolbox") == "on"
        sub_employee.has_access_to_TM = request.POST.get("has_access_to_TM") == "on"
        sub_employee.save(update_fields=[
            "username",
            "password1",
            "has_access_to_toolbox",
            "has_access_to_TM",
        ])
        messages.success(request, "Trinity registration updated.")
        return redirect("subcontractor_employee_page", id=sub_employee.id)

    if request.method == "POST" and "add_assigned_job" in request.POST:
        selected_job = get_object_or_404(
            Jobs,
            job_number=request.POST.get("assigned_job"),
            is_closed=False,
        )
        Subcontractor_Job_Assignments.objects.get_or_create(
            employee=sub_employee,
            job=selected_job,
        )
        messages.success(request, "Job assigned.")
        return redirect("subcontractor_employee_page", id=sub_employee.id)

    if request.method == "POST" and "remove_assigned_job" in request.POST:
        Subcontractor_Job_Assignments.objects.filter(
            employee=sub_employee,
            job_id=request.POST.get("remove_assigned_job"),
        ).delete()
        messages.success(request, "Job removed.")
        return redirect("subcontractor_employee_page", id=sub_employee.id)

    if request.method == "POST" and "add_pending_action" in request.POST:
        description = (request.POST.get("pending_action_description") or "").strip()
        note_text = (request.POST.get("pending_action_notes") or "").strip()

        if not description:
            messages.error(request, "Please enter a task description.")
            return redirect("subcontractor_employee_page", id=sub_employee.id)

        current_employee = None
        if request.user.is_authenticated:
            current_employee = Employees.objects.filter(user=request.user).first()
        added_by = current_employee.first_name if current_employee else "Unknown"
        notes = f"{date.today().strftime('%m/%d/%Y')} - Added by {added_by}."
        if note_text:
            notes += f" {note_text}"

        pending_action = EmployeePendingActions.objects.create(
            subcontractor_employee=sub_employee,
            description=description,
            notes=notes,
            date=date.today(),
            is_complete=False,
            confirmed_is_complete=False,
        )

        if sub_employee.email:
            sender = (
                current_employee.email
                if current_employee and current_employee.email
                else "bridgette@gerloffpainting.com"
            )
            email_body = (
                "A new required task has been added for you.\n\n"
                f"Task: {pending_action.description}\n"
                f"Date Added: {pending_action.date.strftime('%m/%d/%Y')}\n"
            )
            if note_text:
                email_body += f"\nNotes:\n{note_text}"

            try:
                Email.sendEmail(
                    "New Required Task",
                    email_body,
                    [sub_employee.email],
                    False,
                    sender,
                )
                messages.success(request, "Required task added and employee notified.")
            except Exception:
                messages.warning(request, "Required task added, but the employee email could not be sent.")
        else:
            messages.warning(request, "Required task added, but this employee does not have an email on file.")

        return redirect("subcontractor_employee_page", id=sub_employee.id)

    if request.method == "POST" and "complete_pending_action" in request.POST:
        pending_action = get_object_or_404(
            EmployeePendingActions,
            id=request.POST.get("pending_action_id"),
            subcontractor_employee=sub_employee,
            is_complete=False,
        )
        completion_note = (request.POST.get("completion_note") or "").strip()
        current_employee = None
        if request.user.is_authenticated:
            current_employee = Employees.objects.filter(user=request.user).first()

        completed_by = current_employee.first_name if current_employee else sub_employee.name
        note_prefix = f"{date.today().strftime('%m/%d/%Y')} - {completed_by}: Completed task."
        if completion_note:
            note_prefix += f" {completion_note}"

        existing_notes = pending_action.notes or ""
        if existing_notes:
            pending_action.notes = existing_notes + "\n" + note_prefix
        else:
            pending_action.notes = note_prefix
        pending_action.is_complete = True
        pending_action.save(update_fields=["notes", "is_complete"])

        email_body = (
            f"{sub_employee.name} completed a required task.\n\n"
            f"Subcontractor: {sub_employee.subcontractor.company}\n"
            f"Task: {pending_action.description}\n"
            f"Date: {date.today().strftime('%m/%d/%Y')}\n"
        )
        if pending_action.certification:
            email_body += f"Certification: {pending_action.certification}\n"
        if completion_note:
            email_body += f"\nNotes:\n{completion_note}"

        sender = sub_employee.email or "bridgette@gerloffpainting.com"
        try:
            Email.sendEmail(
                "Required Task Completed",
                email_body,
                ["bridgette@gerloffpainting.com"],
                False,
                sender,
            )
            messages.success(request, "Task marked complete.")
        except Exception:
            messages.warning(request, "Task marked complete, but the email could not be sent.")
        return redirect("subcontractor_employee_page", id=sub_employee.id)

    toolbox_summary = _sub_employee_toolbox_summary(sub_employee)
    assigned_jobs = list(
        Subcontractor_Job_Assignments.objects
        .filter(employee=sub_employee)
        .select_related("job")
        .order_by("job__job_name", "job__job_number")
    )
    delegated_job_numbers = set(
        SubcontractorEmployeeDelegation.objects.filter(
            subcontractor=sub_employee.subcontractor,
            subcontract__job_number_id__in=[
                assignment.job_id
                for assignment in assigned_jobs
            ],
        ).values_list("subcontract__job_number_id", flat=True)
    )
    for assignment in assigned_jobs:
        assignment.is_toolbox_delegated = assignment.job_id in delegated_job_numbers
    assigned_job_numbers = [assignment.job_id for assignment in assigned_jobs]
    available_jobs = (
        Jobs.objects
        .filter(
            subcontracts__subcontractor=sub_employee.subcontractor,
            subcontracts__is_closed=False,
            is_closed=False,
        )
        .exclude(job_number__in=assigned_job_numbers)
        .order_by("job_name", "job_number")
        .distinct()
    )
    certifications = (
        Certifications.objects
        .filter(subcontractor_employee=sub_employee)
        .select_related("category", "subcontractor", "subcontractor_employee")
        .order_by("is_closed", "date_expires", "description")
    )
    open_certifications = certifications.filter(is_closed=False)
    pending_tasks = (
        EmployeePendingActions.objects
        .filter(
            subcontractor_employee=sub_employee,
            is_complete=False,
        )
        .select_related("certification")
        .order_by("date", "id")
    )
    respirator_clearances = (
        SubcontractorRespiratorClearance.objects
        .filter(employee=sub_employee)
        .select_related("subcontractor", "employee")
        .order_by("is_closed", "-date_created", "-id")
    )

    return render(request, "subcontractor_employee_page.html", {
        "sub_employee": sub_employee,
        "selected_sub": sub_employee.subcontractor,
        "assigned_jobs": assigned_jobs,
        "assigned_jobs_count": len(assigned_jobs),
        "available_jobs": available_jobs,
        "toolbox_summary": toolbox_summary,
        "toolbox_completed_count": toolbox_summary["completed_count"],
        "toolbox_incomplete_count": toolbox_summary["incomplete_count"],
        "open_certifications": open_certifications,
        "certification_count": open_certifications.count(),
        "pending_tasks": pending_tasks,
        "pending_task_count": pending_tasks.count(),
        "respirator_clearances": respirator_clearances,
        "respirator_clearance_count": respirator_clearances.count(),
    })


@login_required(login_url='/accounts/login')
def employees_home(request):
    send_data = {}
    show_inactive = request.GET.get("inactive") == "1"
    send_data["show_inactive"] = show_inactive

    if show_inactive:
        employees = Employees.objects.filter(
            active=False
        ).order_by("last_name", "first_name")
    else:
        employees = Employees.objects.filter(
            active=True
        ).order_by("last_name", "first_name")

    subcontractor_groups = []

    for sub in Subcontractors.objects.filter(is_inactive=False).order_by("company"):

        if show_inactive:
            sub_employees = Subcontractor_Employees.objects.filter(
                subcontractor=sub,
                is_active=False
            ).order_by("name")
        else:
            sub_employees = Subcontractor_Employees.objects.filter(
                subcontractor=sub,
                is_active=True
            ).order_by("name")


        sub_employees = list(sub_employees)
        sub_employee_ids = [sub_employee.id for sub_employee in sub_employees]

        task_counts = {
            row["certification__subcontractor_employee_id"]: row["count"]
            for row in (
                EmployeePendingActions.objects
                .filter(
                    certification__subcontractor_employee_id__in=sub_employee_ids,
                    is_complete=False,
                )
                .values("certification__subcontractor_employee_id")
                .annotate(count=Count("id"))
            )
        }
        certification_counts = {
            row["subcontractor_employee_id"]: row["count"]
            for row in (
                Certifications.objects
                .filter(
                    subcontractor_employee_id__in=sub_employee_ids,
                    is_closed=False,
                )
                .values("subcontractor_employee_id")
                .annotate(count=Count("id"))
            )
        }
        respirator_counts = {
            row["employee_id"]: row["count"]
            for row in (
                SubcontractorRespiratorClearance.objects
                .filter(
                    employee_id__in=sub_employee_ids,
                    is_closed=False,
                )
                .values("employee_id")
                .annotate(count=Count("id"))
            )
        }
        job_counts = {
            row["employee_id"]: row["count"]
            for row in (
                Subcontractor_Job_Assignments.objects
                .filter(employee_id__in=sub_employee_ids)
                .values("employee_id")
                .annotate(count=Count("id"))
            )
        }

        for sub_employee in sub_employees:
            sub_employee.task_count = task_counts.get(sub_employee.id, 0)
            sub_employee.certification_count = (
                certification_counts.get(sub_employee.id, 0) +
                respirator_counts.get(sub_employee.id, 0)
            )
            sub_employee.job_count = job_counts.get(sub_employee.id, 0)
            sub_employee.toolbox_completed_count = 0
            sub_employee.toolbox_incomplete_count = 0
            if sub_employee.has_access_to_toolbox and sub_employee.subcontractor.is_toolbox_required:
                toolbox_summary = _sub_employee_toolbox_summary(sub_employee)
                sub_employee.toolbox_completed_count = toolbox_summary["completed_count"]
                sub_employee.toolbox_incomplete_count = toolbox_summary["incomplete_count"]

        subcontractor_groups.append({
            "subcontractor": sub,
            "employees": sub_employees,
            "count": len(sub_employees),
        })


    send_data["subcontractor_groups"] = subcontractor_groups
    send_data['employees'] = employees
    return render(request, "employees_home.html", send_data)

def toggle_subcontractor_delegation(request, sub_id):

    selected_sub = get_object_or_404(Subcontractors, id=sub_id)

    existing = SubcontractorEmployeeDelegation.objects.filter(
        subcontractor=selected_sub
    )

    if existing.exists():
        closed_count = 0
        delegated_subcontracts = Subcontracts.objects.filter(
            id__in=existing.values_list('subcontract_id', flat=True)
        )
        for subcontract in delegated_subcontracts:
            closed_count += _close_delegated_job_toolbox_completions_before_undelegate(subcontract)

        existing.delete()
        messages.success(
            request,
            f"Delegation removed. {closed_count} completed toolbox talks were preserved."
        )
    else:
        active_subcontracts = Subcontracts.objects.filter(
            subcontractor=selected_sub,
            is_closed=False,
            job_number__is_active=True,
            job_number__is_closed=False,
            job_number__is_labor_done=False,
        )

        backfilled_count = 0
        for subcontract in active_subcontracts:
            SubcontractorEmployeeDelegation.objects.get_or_create(
                subcontractor=selected_sub,
                subcontract=subcontract
            )
            backfilled_count += _backfill_delegated_job_toolbox_completions(subcontract)

        messages.success(
            request,
            f"Delegation added. {backfilled_count} existing toolbox completions were applied."
        )

    return redirect('employees_home')

def employees_page(request, id):
    employee = get_object_or_404(Employees, id=id)
    current_user_employee = Employees.objects.filter(user=request.user).first() if request.user.is_authenticated else None

    if request.method == 'POST' and 'add_pending_action' in request.POST:
        description = (request.POST.get("pending_action_description") or "").strip()
        note_text = (request.POST.get("pending_action_notes") or "").strip()

        if not description:
            messages.error(request, "Please enter a task description.")
            return redirect("employees_page", id=employee.id)

        added_by = current_user_employee.first_name if current_user_employee else "Unknown"
        notes = f"{date.today().strftime('%m/%d/%Y')} - Added by {added_by}."
        if note_text:
            notes += f" {note_text}"

        pending_action = EmployeePendingActions.objects.create(
            employee=employee,
            description=description,
            notes=notes,
            date=date.today(),
            is_complete=False,
            confirmed_is_complete=False,
        )

        if employee.email:
            sender = current_user_employee.email if current_user_employee and current_user_employee.email else "bridgette@gerloffpainting.com"
            email_body = (
                "A new required task has been added for you.\n\n"
                f"Task: {pending_action.description}\n"
                f"Date Added: {pending_action.date.strftime('%m/%d/%Y')}\n"
            )
            if note_text:
                email_body += f"\nNotes:\n{note_text}"

            try:
                Email.sendEmail(
                    "New Required Task",
                    email_body,
                    [employee.email],
                    False,
                    sender,
                )
                messages.success(request, "Required task added and employee notified.")
            except Exception:
                messages.warning(request, "Required task added, but the employee email could not be sent.")
        else:
            messages.warning(request, "Required task added, but this employee does not have an email on file.")

        return redirect("employees_page", id=employee.id)

    if request.method == 'POST' and 'add_pending_action_note' in request.POST:
        pending_action = get_object_or_404(
            EmployeePendingActions,
            id=request.POST.get("add_pending_action_note"),
            employee=employee,
            certification__isnull=True,
            is_complete=False,
        )
        note_text = (request.POST.get(f"pending_action_note_{pending_action.id}") or "").strip()

        if not note_text:
            messages.error(request, "Please enter a note before adding it.")
            return redirect("employees_page", id=employee.id)

        note_prefix = date.today().strftime('%m/%d/%Y')
        if current_user_employee:
            note_prefix += f" - {current_user_employee.first_name}"

        pending_action.notes = (
            (pending_action.notes + "\n") if pending_action.notes else ""
        ) + f"{note_prefix}: {note_text}"
        pending_action.save(update_fields=["notes"])
        messages.success(request, "Task note added.")
        return redirect("employees_page", id=employee.id)

    if request.method == 'POST' and 'delete_pending_action' in request.POST:
        pending_action = get_object_or_404(
            EmployeePendingActions,
            id=request.POST.get("delete_pending_action"),
            employee=employee,
            certification__isnull=True,
        )
        pending_action.delete()
        messages.success(request, "Pending employee task deleted.")
        return redirect("employees_page", id=employee.id)

    if request.method == 'POST' and ('approve_vacation' in request.POST or 'reject_vacation' in request.POST):
        if not current_user_employee:
            messages.error(request, "Vacation approval could not be found.")
            return redirect("employees_page", id=employee.id)

        vacation_approval_id = request.POST.get("vacation_approval_id")

        if not vacation_approval_id or not vacation_approval_id.isdigit():
            messages.error(request, "Vacation approval could not be found.")
            return redirect("employees_page", id=employee.id)

        approval = get_object_or_404(
            ApprovedVacations,
            id=vacation_approval_id,
            approver=current_user_employee,
        )
        vacation = approval.request
        had_pending_approvals_before_review = ApprovedVacations.objects.filter(
            request=vacation,
            is_approved=False,
            is_rejected=False,
        ).exists()

        approval.approver_notes = request.POST.get("approver_notes") or ""
        approval.is_approved = 'approve_vacation' in request.POST
        approval.is_rejected = 'reject_vacation' in request.POST
        approval.save()

        has_pending_approvals = ApprovedVacations.objects.filter(
            request=vacation,
            is_approved=False,
            is_rejected=False,
        ).exists()
        has_rejected_approvals = ApprovedVacations.objects.filter(
            request=vacation,
            is_rejected=True,
        ).exists()
        has_approval_rows = ApprovedVacations.objects.filter(request=vacation).exists()

        if has_approval_rows and not has_pending_approvals and not has_rejected_approvals:
            vacation.is_approved = True
            vacation.is_rejected = False
            vacation.save()
        elif has_approval_rows and not has_pending_approvals and has_rejected_approvals:
            vacation.is_approved = False
            vacation.is_rejected = True
            vacation.save()
        else:
            vacation.is_approved = False
            vacation.is_rejected = False
            vacation.save()

        if had_pending_approvals_before_review and not has_pending_approvals:
            try:
                _send_vacation_final_status_email(vacation)
            except Exception:
                messages.warning(
                    request,
                    "Vacation review saved, but the final status email could not be sent.",
                )

        if approval.is_approved:
            messages.success(request, "Vacation request approved.")
        else:
            messages.success(request, "Vacation request rejected.")

        return redirect("employees_page", id=employee.id)

    if request.method == 'POST' and 'manual_vacation_entry' in request.POST:
        if not current_user_employee:
            messages.error(request, "Manual vacation entry could not be saved.")
            return redirect("employees_page", id=employee.id)

        if employee.job_title and employee.job_title.description == "Painter":
            vacation_viewer_group_name = "Painter Vacation Viewers"
        else:
            vacation_viewer_group_name = "Office Vacation Viewers"

        can_make_manual_vacation_entry = request.user.groups.filter(
            name=vacation_viewer_group_name
        ).exists()

        if not can_make_manual_vacation_entry:
            messages.error(request, "You are not allowed to add vacation for this employee.")
            return redirect("employees_page", id=employee.id)

        first_day_raw = request.POST.get("first_day")
        last_day_raw = request.POST.get("last_day")
        manual_note = request.POST.get("employee_note") or ""

        try:
            first_day = date.fromisoformat(first_day_raw)
            last_day = date.fromisoformat(last_day_raw)
        except (TypeError, ValueError):
            messages.error(request, "Please enter valid vacation dates.")
            return redirect("employees_page", id=employee.id)

        if last_day < first_day:
            messages.error(request, "Last day cannot be before first day.")
            return redirect("employees_page", id=employee.id)

        Vacation.objects.create(
            employee=employee,
            vacation_date=first_day,
            first_day=first_day,
            last_day=last_day,
            duration=_vacation_weekday_count(first_day, last_day),
            employee_note=f"Added by {current_user_employee.first_name}- {manual_note}",
            is_approved=True,
            is_rejected=False,
            request_date=date.today(),
        )

        messages.success(request, "Manual vacation entry added.")
        return redirect("employees_page", id=employee.id)

    if request.method == 'POST' and 'adjust_vacation_days' in request.POST:
        if employee.job_title and employee.job_title.description == "Painter":
            vacation_viewer_group_name = "Painter Vacation Viewers"
        else:
            vacation_viewer_group_name = "Office Vacation Viewers"

        can_adjust_vacation_days = (
            request.user.is_authenticated and
            request.user.groups.filter(name=vacation_viewer_group_name).exists()
        )

        if not can_adjust_vacation_days:
            messages.error(request, "You are not allowed to adjust vacation days for this employee.")
            return redirect("employees_page", id=employee.id)

        previous_vacation_days = employee.vacation_days_per_year
        vacation_days_value = request.POST.get("vacation_days_per_year")

        if vacation_days_value in [None, ""]:
            employee.vacation_days_per_year = None
        elif vacation_days_value.isdigit():
            employee.vacation_days_per_year = int(vacation_days_value)
        else:
            messages.error(request, "Please enter a valid vacation day amount.")
            return redirect("employees_page", id=employee.id)

        employee.save()
        adjustment_note = request.POST.get("vacation_adjustment_note") or ""
        note = (
            f"Allowed vacation days changed from "
            f"{previous_vacation_days if previous_vacation_days is not None else 'Default'} "
            f"to "
            f"{employee.vacation_days_per_year if employee.vacation_days_per_year is not None else 'Default'}."
        )

        if adjustment_note:
            note += f" {adjustment_note}"

        VacationNotes.objects.create(
            employee=employee,
            user=current_user_employee,
            date=date.today(),
            note=note,
        )
        messages.success(request, "Allowed vacation days updated.")
        return redirect("employees_page", id=employee.id)

    toolbox_summary = employee.toolbox_talk_summary()
    toolbox_completed_count = toolbox_summary["completed_count"]
    toolbox_incomplete_count = toolbox_summary["incomplete_count"]
    pending_actions = list(
        EmployeePendingActions.objects.filter(
            employee=employee,
            is_complete=False,
        ).select_related(
            "certification",
            "certification__category",
        ).order_by(
            "date",
            "id",
        )
    )
    pending_actions_count = len(pending_actions)
    certification_summary = employee.certification_summary()
    certification_count = certification_summary["count"]
    open_pending_action_cert_ids = set(
        EmployeePendingActions.objects.filter(
            employee=employee,
            certification__isnull=False,
            is_complete=False,
        ).values_list("certification_id", flat=True)
    )
    certification_summary["open_certifications"] = list(certification_summary["open_certifications"])

    for cert in certification_summary["open_certifications"]:
        cert.has_open_pending_action = cert.id in open_pending_action_cert_ids

    inventory_summary = employee.inventory_summary()
    assigned_equipment_count = inventory_summary["count"]
    if employee.job_title and employee.job_title.description == "Painter":
        vacation_viewer_group_name = "Painter Vacation Viewers"
    else:
        vacation_viewer_group_name = "Office Vacation Viewers"

    can_view_employee_vacation_history = (
        request.user.is_authenticated and
        request.user.groups.filter(name=vacation_viewer_group_name).exists()
    )
    current_year = date.today().year
    pending_vacation_requests = []
    vacation_days_allowed = 0
    vacation_days_used_current_year = 0
    vacation_history_by_year = []

    if can_view_employee_vacation_history:
        pending_vacation_requests = list(Vacation.objects.filter(
            employee=employee,
            is_approved=False,
            is_rejected=False,
        ).order_by("first_day", "id"))

        for vacation_request in pending_vacation_requests:
            vacation_request.display_duration = _vacation_weekday_count(
                vacation_request.first_day,
                vacation_request.last_day,
            )
            vacation_request.current_user_approval = None

            if current_user_employee:
                vacation_request.current_user_approval = ApprovedVacations.objects.filter(
                    request=vacation_request,
                    approver=current_user_employee,
                ).first()

            vacation_request.approver_statuses = ApprovedVacations.objects.filter(
                request=vacation_request,
            ).select_related(
                "approver",
            ).order_by("approver__last_name", "approver__first_name")

            if date.today() < date(2027, 1, 1):
                vacation_request.days_used_prior = "Annual Calculation will Start on 1/1/27"
            else:
                vacation_year_start = date(vacation_request.first_day.year, 1, 1)
                prior_vacations = Vacation.objects.filter(
                    employee=employee,
                    is_approved=True,
                    first_day__gte=vacation_year_start,
                    first_day__lt=vacation_request.first_day,
                ).exclude(
                    id=vacation_request.id,
                )
                vacation_request.days_used_prior = sum(
                    _vacation_weekday_count(vacation.first_day, vacation.last_day)
                    for vacation in prior_vacations
                )

        vacation_days_allowed = _vacation_allowed_days_for(employee)
        current_year_start = date(current_year, 1, 1)
        current_year_end = date(current_year, 12, 31)
        vacation_days_used_current_year = sum(
            _vacation_weekday_count(
                max(vacation.first_day, current_year_start),
                min(vacation.last_day, current_year_end),
            )
            for vacation in Vacation.objects.filter(
                employee=employee,
                is_approved=True,
                first_day__lte=current_year_end,
                last_day__gte=current_year_start,
            )
        )
        vacation_history_by_year = _vacation_history_by_year(employee)

    send_data = {
        "employee": employee,
        "toolbox_completed_count": toolbox_completed_count,
        "toolbox_incomplete_count": toolbox_incomplete_count,
        "toolbox_summary": toolbox_summary,
        "pending_actions": pending_actions,
        "pending_actions_count": pending_actions_count,
        "certification_count": certification_count,
        "assigned_equipment_count": assigned_equipment_count,
        "can_view_employee_vacation_history": can_view_employee_vacation_history,
        "current_year": current_year,
        "pending_vacation_requests": pending_vacation_requests,
        "vacation_days_allowed": vacation_days_allowed,
        "vacation_days_used_current_year": vacation_days_used_current_year,
        "vacation_history_by_year": vacation_history_by_year,
        "vacation_notes": VacationNotes.objects.filter(employee=employee).select_related("user").order_by("-date", "-id"),
        "certification_summary": certification_summary,
        "inventory_summary": inventory_summary,
    }

    return render(request, "employees_page.html", send_data)


@login_required(login_url='/accounts/login')
def employee_edit(request, id):
    employee = get_object_or_404(Employees, id=id)

    if request.method == "POST":
        employee.first_name = request.POST.get("first_name")
        employee.middle_name = request.POST.get("middle_name")
        employee.last_name = request.POST.get("last_name")
        employee.phone = request.POST.get("phone")
        employee.email = request.POST.get("email")
        employee.nickname = request.POST.get("nickname")

        employee.birth_date = request.POST.get("birth_date") or None
        employee.date_added = request.POST.get("date_added") or None

        job_title_id = request.POST.get("job_title")
        employment_company_value = request.POST.get("employment_company")

        if employment_company_value:
            if employment_company_value.isdigit():
                employee.employment_company = Employers.objects.get(id=employment_company_value)
            else:
                new_company, created = Employers.objects.get_or_create(
                    company_name=employment_company_value.strip()
                )
                employee.employment_company = new_company
        else:
            employee.employment_company = None

        employee.job_title = EmployeeTitles.objects.get(id=job_title_id) if job_title_id else None


        employee.save()

        return redirect("employees_page", id=employee.id)

    send_data = {
        "employee": employee,
        "job_titles": EmployeeTitles.objects.all().order_by("description"),
        "employment_companies": Employers.objects.all().order_by("company_name"),
    }

    return render(request, "employee_edit.html", send_data)


@login_required(login_url='/accounts/login')
def training(request):
    send_data = {}
    return render(request, "training.html", send_data)

def _serve_toolbox_file(scheduled, language):
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


def _open_toolbox_file_for_employee(employee, scheduled_id, language):
    scheduled = ScheduledToolboxTalks.objects.get(id=scheduled_id)

    ViewedToolboxTalks.objects.get_or_create(
        employee=employee,
        master=scheduled,
        language=language,
        defaults={"date": now().date()}
    )

    return _serve_toolbox_file(scheduled, language)


def toolbox_file(request, scheduled_id, language):
    employee = Employees.objects.get(user=request.user)
    return _open_toolbox_file_for_employee(employee, scheduled_id, language)


@login_required(login_url='/accounts/login')
def group_toolbox_file(request, scheduled_id, language):
    employee = Employees.objects.get(user=request.user)
    scheduled = ScheduledToolboxTalks.objects.get(id=scheduled_id)
    group_view, created = GroupToolboxTalkViews.objects.get_or_create(
        employee=employee,
        scheduled_toolbox_talk=scheduled
    )

    if language == "English":
        group_view.viewed_english = True
        group_view.viewed_english_time = timezone.now()
    elif language == "Spanish":
        group_view.viewed_spanish = True
        group_view.viewed_spanish_time = timezone.now()

    group_view.save()
    return _serve_toolbox_file(scheduled, language)


@login_required(login_url='/accounts/login')
def toolbox_file_for_employee(request, employee_id, scheduled_id, language):
    employee = get_object_or_404(Employees, id=employee_id)
    return _open_toolbox_file_for_employee(employee, scheduled_id, language)


def _missing_regular_employees_for_toolbox(scheduled_talk):
    if scheduled_talk.is_all_employees:
        employees_qs = Employees.objects.filter(
            active=True,
            job_title__description__in=["Painter", "Superintendent", "Warehouse"]
        )

        if scheduled_talk.date:
            employees_qs = employees_qs.filter(
                Q(date_added__isnull=True) |
                Q(date_added__lte=scheduled_talk.date)
            )
    else:
        employees_qs = Employees.objects.filter(
            scheduledtoolboxtalkemployees__scheduled=scheduled_talk,
            active=True
        )

    resolved_employee_ids = CompletedToolboxTalks.objects.filter(
        master=scheduled_talk
    ).values_list(
        "employee_id",
        flat=True
    )

    return employees_qs.exclude(
        id__in=resolved_employee_ids
    ).distinct().order_by(
        "last_name",
        "first_name"
    )


@login_required(login_url='/accounts/login')
@never_cache
def my_page(request):
    employee = Employees.objects.get(user=request.user)
    send_data = {}
    has_worked_more_than_one_year = (
        employee.date_added and
        employee.date_added < date.today() - relativedelta(years=1)
    )
    vacation_eligible_date = employee.date_added + relativedelta(years=1) if employee.date_added else None
    is_vacation_request_employee = not (
        employee.job_title and
        employee.job_title.description == "Painter" and
        (
            not employee.employment_company or
            employee.employment_company.company_name != "Gerloff Painting"
        )
    )
    show_vacation_requests = is_vacation_request_employee
    can_request_vacation = has_worked_more_than_one_year and is_vacation_request_employee

    def task_review_scope_filter():
        if request.user.groups.filter(name="Employee Task Reviewers").exists():
            return (
                Q(employee__active=True) |
                Q(
                    subcontractor_employee__is_active=True,
                    subcontractor_employee__subcontractor__is_inactive=False,
                )
            )
        if employee.job_title and employee.job_title.description == "Superintendent":
            return (
                Q(
                    employee__active=True,
                    employee__job_title__description__in=["Painter", "Warehouse"],
                ) |
                Q(
                    subcontractor_employee__is_active=True,
                    subcontractor_employee__subcontractor__is_inactive=False,
                )
            )
        return Q(pk__in=[])

    if request.method == 'POST':
        if 'complete_pending_action' in request.POST:
            pending_action = get_object_or_404(
                EmployeePendingActions,
                id=request.POST.get("pending_action_id"),
                employee=employee,
                is_complete=False,
            )
            completion_note = (request.POST.get("completion_note") or "").strip()
            note_prefix = f"{date.today().strftime('%m/%d/%Y')} - {employee.first_name}: Completed task."
            if completion_note:
                note_prefix += f" {completion_note}"

            existing_notes = pending_action.notes or ""
            if existing_notes:
                pending_action.notes = existing_notes + "\n" + note_prefix
            else:
                pending_action.notes = note_prefix

            pending_action.is_complete = True
            pending_action.save()

            email_body = (
                f"{employee} completed a required task.\n\n"
                f"Task: {pending_action.description}\n"
                f"Date: {date.today().strftime('%m/%d/%Y')}\n"
            )
            if pending_action.certification:
                email_body += f"Certification: {pending_action.certification}\n"
            if completion_note:
                email_body += f"\nNotes:\n{completion_note}"

            sender = employee.email if employee.email else "bridgette@gerloffpainting.com"
            try:
                Email.sendEmail(
                    "Required Task Completed",
                    email_body,
                    ["bridgette@gerloffpainting.com"],
                    False,
                    sender,
                )
                messages.success(request, "Task marked complete.")
            except Exception:
                messages.warning(request, "Task marked complete, but the email could not be sent.")

            return redirect('my_page')

        if 'add_review_pending_action_note' in request.POST:
            pending_action = get_object_or_404(
                EmployeePendingActions.objects.filter(
                    task_review_scope_filter(),
                    certification__isnull=True,
                    is_complete=False,
                ),
                id=request.POST.get("add_review_pending_action_note"),
            )
            note_text = (request.POST.get(f"review_pending_action_note_{pending_action.id}") or "").strip()

            if not note_text:
                messages.error(request, "Please enter a note before adding it.")
                return redirect('my_page')

            note_prefix = date.today().strftime('%m/%d/%Y')
            if employee:
                note_prefix += f" - {employee.first_name}"

            pending_action.notes = (
                (pending_action.notes + "\n") if pending_action.notes else ""
            ) + f"{note_prefix}: {note_text}"
            pending_action.save(update_fields=["notes"])
            messages.success(request, "Task note added.")
            return redirect('my_page')

        if 'delete_review_pending_action' in request.POST:
            pending_action = get_object_or_404(
                EmployeePendingActions.objects.filter(
                    task_review_scope_filter(),
                    certification__isnull=True,
                    is_complete=False,
                ),
                id=request.POST.get("delete_review_pending_action"),
            )
            pending_action.delete()
            messages.success(request, "Pending employee task deleted.")
            return redirect('my_page')

        if 'confirm_review_completed_action' in request.POST:
            completed_action = get_object_or_404(
                EmployeePendingActions.objects.filter(
                    task_review_scope_filter(),
                    is_complete=True,
                    confirmed_is_complete=False,
                ),
                id=request.POST.get("confirm_review_completed_action"),
            )
            completed_action.confirmed_is_complete = True
            completed_action.save(update_fields=["confirmed_is_complete"])
            if completed_action.certification:
                CertificationNotes.objects.create(
                    certification=completed_action.certification,
                    date=date.today(),
                    user=employee,
                    note=(
                        f"Completed employee task confirmed for {completed_action.assignee_display}: "
                        f"{completed_action.description}"
                    ),
                )
            messages.success(request, "Completed task confirmed.")
            return redirect('my_page')

        if 'deny_review_completed_action' in request.POST:
            completed_action = get_object_or_404(
                EmployeePendingActions.objects.filter(
                    task_review_scope_filter(),
                    is_complete=True,
                    confirmed_is_complete=False,
                ),
                id=request.POST.get("deny_review_completed_action"),
            )
            denial_note = (request.POST.get(f"deny_review_completed_action_note_{completed_action.id}") or "").strip()
            if not denial_note:
                messages.error(request, "Please enter a note explaining why the completed task was denied.")
                return redirect('my_page')

            completed_action.is_complete = False
            completed_action.confirmed_is_complete = False
            completed_action.notes = (
                (completed_action.notes + "\n") if completed_action.notes else ""
            ) + f"{date.today().strftime('%m/%d/%Y')} - {employee.first_name}: Denied completion. {denial_note}"
            completed_action.save(update_fields=["is_complete", "confirmed_is_complete", "notes"])
            if completed_action.certification:
                CertificationNotes.objects.create(
                    certification=completed_action.certification,
                    date=date.today(),
                    user=employee,
                    note=(
                        f"Completed employee task denied and reopened for {completed_action.assignee_display}: "
                        f"{completed_action.description}. Reason: {denial_note}"
                    ),
                )
            messages.success(request, "Completed task denied and reopened.")
            return redirect('my_page')

        if 'approve_vacation' in request.POST or 'reject_vacation' in request.POST:
            vacation_approval_id = request.POST.get("vacation_approval_id")

            if not vacation_approval_id or not vacation_approval_id.isdigit():
                messages.error(request, "Vacation approval could not be found.")
                return redirect('my_page')

            approval = get_object_or_404(
                ApprovedVacations,
                id=vacation_approval_id,
                approver=employee,
            )
            vacation = approval.request
            had_pending_approvals_before_review = ApprovedVacations.objects.filter(
                request=vacation,
                is_approved=False,
                is_rejected=False,
            ).exists()

            approval.approver_notes = request.POST.get("approver_notes") or ""
            approval.is_approved = 'approve_vacation' in request.POST
            approval.is_rejected = 'reject_vacation' in request.POST
            approval.save()

            has_pending_approvals = ApprovedVacations.objects.filter(
                request=vacation,
                is_approved=False,
                is_rejected=False,
            ).exists()
            has_rejected_approvals = ApprovedVacations.objects.filter(
                request=vacation,
                is_rejected=True,
            ).exists()
            has_approval_rows = ApprovedVacations.objects.filter(request=vacation).exists()

            if has_approval_rows and not has_pending_approvals and not has_rejected_approvals:
                vacation.is_approved = True
                vacation.is_rejected = False
                vacation.save()
            elif has_approval_rows and not has_pending_approvals and has_rejected_approvals:
                vacation.is_approved = False
                vacation.is_rejected = True
                vacation.save()
            else:
                vacation.is_approved = False
                vacation.is_rejected = False
                vacation.save()

            if had_pending_approvals_before_review and not has_pending_approvals:
                try:
                    _send_vacation_final_status_email(vacation)
                except Exception:
                    messages.warning(
                        request,
                        "Vacation review saved, but the final status email could not be sent.",
                    )

            if approval.is_approved:
                messages.success(request, "Vacation request approved.")
            else:
                messages.success(request, "Vacation request rejected.")
            return redirect('my_page')

        if 'request_vacation' in request.POST:
            if not can_request_vacation:
                messages.error(request, "You are not allowed to request vacation.")
                return redirect('my_page')

            first_day_raw = request.POST.get("first_day")
            last_day_raw = request.POST.get("last_day")
            employee_note = request.POST.get("employee_note") or ""

            try:
                first_day = date.fromisoformat(first_day_raw)
                last_day = date.fromisoformat(last_day_raw)
            except (TypeError, ValueError):
                messages.error(request, "Please enter valid vacation dates.")
                return redirect('my_page')

            if last_day < first_day:
                messages.error(request, "Last day cannot be before first day.")
                return redirect('my_page')

            vacation = Vacation.objects.create(
                employee=employee,
                vacation_date=first_day,
                first_day=first_day,
                last_day=last_day,
                duration=_vacation_weekday_count(first_day, last_day),
                employee_note=employee_note,
                request_date=date.today(),
            )

            approvers = _vacation_approvers_for(employee)

            for approver in approvers:
                ApprovedVacations.objects.get_or_create(
                    request=vacation,
                    approver=approver,
                    defaults={
                        "approver_notes": "",
                    },
                )

            try:
                _send_vacation_request_emails(vacation, approvers)
            except Exception:
                messages.warning(
                    request,
                    "Vacation request submitted, but the approval email could not be sent.",
                )

            messages.success(request, "Vacation request submitted.")
            return redirect('my_page')

        if 'nickname' in request.POST:
            employee.nickname = request.POST['nickname']
            employee.phone = request.POST['phone']
            employee.email = request.POST['email']
            employee.save()

        if request.POST.get('selected_file') == "pumpkin":
            selected_talk = ScheduledToolboxTalks.objects.get(
                id=request.POST['scheduledtalk_id']
            )

            has_viewed = ViewedToolboxTalks.objects.filter(
                employee=employee,
                master=selected_talk
            ).exists()

            if has_viewed:
                _complete_employee_toolbox_talk(employee, selected_talk)

            return redirect('my_page')

        if request.POST.get('selected_file') == "other_employee_toolbox":
            selected_employee = get_object_or_404(
                Employees,
                id=request.POST.get('toolbox_employee_id')
            )
            selected_talk = get_object_or_404(
                ScheduledToolboxTalks,
                id=request.POST.get('scheduledtalk_id')
            )

            has_viewed = ViewedToolboxTalks.objects.filter(
                employee=selected_employee,
                master=selected_talk
            ).exists()

            if has_viewed:
                _complete_employee_toolbox_talk(selected_employee, selected_talk)

            return redirect('my_page')

        if request.POST.get('selected_file') == "group_toolbox":
            selected_talk = get_object_or_404(
                ScheduledToolboxTalks,
                id=request.POST.get('group_scheduledtalk_id')
            )

            group_view = GroupToolboxTalkViews.objects.filter(
                employee=employee,
                scheduled_toolbox_talk=selected_talk
            ).first()

            if not _group_toolbox_view_is_current(group_view):
                messages.error(request, "You need to read the toolbox talk first before completing it.")
                return redirect('my_page')

            selected_employee_ids = request.POST.getlist("group_employee_ids")

            if not selected_employee_ids:
                messages.error(request, "Please select at least one employee who completed the toolbox talk.")
                return redirect('my_page')

            job_number = request.POST.get("group_job_number")
            selected_job = None

            if job_number:
                selected_job = Jobs.objects.filter(
                    job_number=job_number,
                    is_closed=False
                ).first()

            selected_employees = Employees.objects.filter(
                id__in=selected_employee_ids,
                active=True
            ).order_by(
                "last_name",
                "first_name"
            )

            with transaction.atomic():
                group_toolbox_talk = GroupToolboxTalks.objects.create(
                    job=selected_job,
                    Foreman=employee,
                    date_completed=date.today()
                )

                for selected_employee in selected_employees:
                    completed_talk = _complete_employee_toolbox_talk(
                        selected_employee,
                        selected_talk
                    )

                    GroupToolboxTalkCompletedToolboxTalks.objects.get_or_create(
                        group_toolbox_talk=group_toolbox_talk,
                        completed_toolbox_talk=completed_talk
                    )

            messages.success(request, "Group toolbox talk completed.")
            return redirect('my_page')
    # Everything else is just data preparation
    if employee.job_title and employee.job_title.description == "Painter":
        base_template = "painter_base.html"
    else:
        base_template = "base.html"
    send_data['base_template'] = base_template

    today = date.today()

    # External respirator certification:
    # category is Respirator Clearance,
    # no attached RespiratorClearance record,
    # and expiration date is still valid.
    external_resp_cert = Certifications.objects.filter(
        employee=employee,
        is_closed=False,
        category__description="Respirator Clearance",
        date_expires__gte=today
    ).exclude(
        respiratorclearance__isnull=False
    ).order_by("-date_expires").first()

    # Trinity respirator clearance:
    # completed through the Trinity questionnaire,
    # approved for use,
    # and the attached Certification is not expired.
    trinity_resp_clearance = RespiratorClearance.objects.filter(
        employee=employee,
        date_completed__isnull=False,
        approved_for_use=True,
        certification__is_closed=False,
        certification__date_expires__gte=today
    ).order_by("-certification__date_expires", "-date_completed", "-id").first()

    pending_trinity_resp_clearance = RespiratorClearance.objects.filter(
        employee=employee,
        date_completed__isnull=False,
        approved_for_use=False,
        certification__is_closed=False
    ).order_by("-date_completed", "-id").first()

    # Expired Trinity clearance, for display purposes only.
    expired_trinity_resp_clearance = RespiratorClearance.objects.filter(
        employee=employee,
        date_completed__isnull=False,
        approved_for_use=True,
        certification__is_closed=False,
        certification__date_expires__lt=today
    ).order_by("-certification__date_expires", "-date_completed", "-id").first()

    # Expired external cert, for display purposes only.
    expired_external_resp_cert = Certifications.objects.filter(
        employee=employee,
        is_closed=False,
        category__description="Respirator Clearance",
        date_expires__lt=today
    ).exclude(
        respiratorclearance__isnull=False
    ).order_by("-date_expires").first()

    if external_resp_cert:
        send_data["respirator_clearance_required"] = False
        send_data["external_respirator_cert"] = external_resp_cert

    elif trinity_resp_clearance:
        send_data["respirator_clearance_required"] = False
        send_data["respirator_clearance_id"] = trinity_resp_clearance.id

    elif pending_trinity_resp_clearance:
        send_data["respirator_clearance_required"] = False
        send_data["respirator_not_approved"] = "Yes"
        send_data["respirator_clearance_id"] = pending_trinity_resp_clearance.id

    else:
        send_data["respirator_clearance_required"] = "Yes"

        if expired_trinity_resp_clearance:
            send_data["expired_respirator_cert"] = expired_trinity_resp_clearance.certification

        elif expired_external_resp_cert:
            send_data["expired_respirator_cert"] = expired_external_resp_cert
    send_data['employeeJobs'] = EmployeeJob.objects.filter(employee=employee.id,job__is_closed=False)
    send_data['employeeJobs_count'] = EmployeeJob.objects.filter(employee=employee.id,job__is_closed=False).count()
    send_data['employee'] = employee
    send_data['show_vacation_requests'] = show_vacation_requests
    send_data['can_request_vacation'] = can_request_vacation
    send_data['vacation_eligible_date'] = vacation_eligible_date
    send_data['inventory'] = Inventory.objects.filter(assigned_to=employee,is_closed=False)
    send_data['inventory_count'] = Inventory.objects.filter(assigned_to=employee, is_closed=False).count()
    send_data['assessments_performed'] = EmployeeReview.objects.filter(assessment__reviewer=employee)
    send_data['assessments_received'] = EmployeeReview.objects.filter(employee=employee)
    send_data['writeups_written'] = WriteUp.objects.filter(supervisor=employee)
    send_data['writeups_received'] = WriteUp.objects.filter(employee=employee)
    send_data['writeups_received_count'] = WriteUp.objects.filter(employee=employee).count()
    vacation_requests = list(Vacation.objects.filter(employee=employee))
    for vacation_request in vacation_requests:
        vacation_request.display_duration = _vacation_weekday_count(
            vacation_request.first_day,
            vacation_request.last_day,
        )
    send_data['vacation_requests'] = vacation_requests
    send_data['my_vacation_history_by_year'] = _vacation_history_by_year(employee)
    my_vacation_days_allowed = _vacation_allowed_days_for(employee)
    current_year = date.today().year
    current_year_start = date(current_year, 1, 1)
    current_year_end = date(current_year, 12, 31)
    my_vacation_days_used_current_year = sum(
        _vacation_weekday_count(
            max(vacation.first_day, current_year_start),
            min(vacation.last_day, current_year_end),
        )
        for vacation in Vacation.objects.filter(
            employee=employee,
            is_approved=True,
            first_day__lte=current_year_end,
            last_day__gte=current_year_start,
        )
    )
    send_data['my_vacation_days_allowed'] = my_vacation_days_allowed
    send_data['my_vacation_days_used_current_year'] = my_vacation_days_used_current_year
    vacation_requests_with_pending_reviews = ApprovedVacations.objects.filter(
        is_approved=False,
        is_rejected=False,
    ).values_list("request_id", flat=True)

    vacation_approvals_requiring_my_approval = list(ApprovedVacations.objects.filter(
        approver=employee,
        request_id__in=vacation_requests_with_pending_reviews,
        is_approved=False,
        is_rejected=False,
    ).select_related(
        "request",
        "request__employee",
    ).order_by("request__first_day", "request__employee__last_name", "request__employee__first_name"))

    vacation_approvals_waiting_on_others = list(ApprovedVacations.objects.filter(
        approver=employee,
        request_id__in=vacation_requests_with_pending_reviews,
    ).filter(
        Q(is_approved=True) | Q(is_rejected=True)
    ).select_related(
        "request",
        "request__employee",
    ).order_by("request__first_day", "request__employee__last_name", "request__employee__first_name"))

    vacation_approval_modal_requests = (
        vacation_approvals_requiring_my_approval +
        vacation_approvals_waiting_on_others
    )

    for approval in vacation_approval_modal_requests:
        approval.approver_statuses = ApprovedVacations.objects.filter(
            request=approval.request,
        ).select_related(
            "approver",
        ).order_by("approver__last_name", "approver__first_name")
        approval.display_duration = _vacation_weekday_count(
            approval.request.first_day,
            approval.request.last_day,
        )
        if date.today() < date(2027, 1, 1):
            approval.days_used_prior = "Annual Calculation will Start on 1/1/27"
        else:
            vacation_year_start = date(approval.request.first_day.year, 1, 1)
            prior_vacations = Vacation.objects.filter(
                employee=approval.request.employee,
                is_approved=True,
                first_day__gte=vacation_year_start,
                first_day__lt=approval.request.first_day,
            ).exclude(
                id=approval.request.id,
            )
            approval.days_used_prior = sum(
                _vacation_weekday_count(vacation.first_day, vacation.last_day)
                for vacation in prior_vacations
            )
        vacation_history_by_year = []
        vacation_history = Vacation.objects.filter(
            employee=approval.request.employee,
        ).order_by("-first_day", "-id")
        vacation_history_years = {}

        for vacation_item in vacation_history:
            vacation_year = vacation_item.first_day.year

            if vacation_year not in vacation_history_years:
                vacation_history_years[vacation_year] = {
                    "year": vacation_year,
                    "total_days": 0,
                    "vacations": [],
                }

            vacation_item.display_duration = _vacation_weekday_count(
                vacation_item.first_day,
                vacation_item.last_day,
            )
            vacation_item.approver_statuses = ApprovedVacations.objects.filter(
                request=vacation_item,
            ).select_related(
                "approver",
            ).order_by("approver__last_name", "approver__first_name")

            if vacation_item.is_approved:
                vacation_history_years[vacation_year]["total_days"] += vacation_item.display_duration

            vacation_history_years[vacation_year]["vacations"].append(vacation_item)

        for vacation_year in sorted(vacation_history_years.keys(), reverse=True):
            vacation_history_by_year.append(vacation_history_years[vacation_year])

        approval.vacation_history_by_year = vacation_history_by_year

    send_data['vacation_approvals_requiring_my_approval'] = vacation_approvals_requiring_my_approval
    send_data['vacation_approvals_requiring_my_approval_count'] = len(vacation_approvals_requiring_my_approval)
    send_data['vacation_approvals_waiting_on_others'] = vacation_approvals_waiting_on_others
    send_data['vacation_approvals_waiting_on_others_count'] = len(vacation_approvals_waiting_on_others)
    send_data['vacation_approval_modal_requests'] = vacation_approval_modal_requests
    send_data['vacation_approval_requests_exist'] = bool(vacation_approval_modal_requests)
    send_data['production_reports_written'] = DailyReports.objects.filter(foreman=employee)
    send_data['production_reports_received'] = ProductionItems.objects.filter(employee=employee)
    send_data['classes_taught'] = ClassOccurrence.objects.filter(teacher=employee)
    send_data['classes_attended'] = ClassAttendees.objects.filter(student=employee)
    send_data['exams'] = ExamScore.objects.filter(student=employee)
    send_data['mentorship_mentor'] = Mentorship.objects.filter(mentor=employee)
    send_data['mentorship_apprentice'] = Mentorship.objects.filter(apprentice=employee)
    certifications = list(
        Certifications.objects.filter(
            employee=employee,
            is_closed=False,
        ).select_related(
            "category",
        )
    )
    pending_actions = list(
        EmployeePendingActions.objects.filter(
            employee=employee,
            is_complete=False,
        ).select_related(
            "certification",
            "certification__category",
        ).order_by(
            "date",
            "id",
        )
    )

    pending_actions_by_certification = {}
    for pending_action in pending_actions:
        if pending_action.certification_id:
            pending_actions_by_certification.setdefault(
                pending_action.certification_id,
                [],
            ).append(pending_action)

    for certification in certifications:
        certification.pending_actions = pending_actions_by_certification.get(
            certification.id,
            [],
        )

    send_data['certifications'] = certifications
    send_data['certifications_count'] = len(certifications)
    send_data['pending_actions'] = pending_actions
    send_data['pending_actions_count'] = len(pending_actions)
    task_review_employee_filter = task_review_scope_filter()

    task_review_select_related = (
        "employee",
        "employee__job_title",
        "subcontractor_employee",
        "subcontractor_employee__subcontractor",
        "certification",
        "certification__category",
    )
    task_reviewer_pending_actions = list(
        EmployeePendingActions.objects.filter(
            task_review_employee_filter,
            is_complete=False,
        ).select_related(
            *task_review_select_related,
        ).order_by(
            "employee__last_name",
            "employee__first_name",
            "subcontractor_employee__subcontractor__company",
            "subcontractor_employee__name",
            "date",
            "id",
        )
    )
    task_reviewer_completed_actions = list(
        EmployeePendingActions.objects.filter(
            task_review_employee_filter,
            is_complete=True,
            confirmed_is_complete=False,
        ).select_related(
            *task_review_select_related,
        ).order_by(
            "employee__last_name",
            "employee__first_name",
            "subcontractor_employee__subcontractor__company",
            "subcontractor_employee__name",
            "date",
            "id",
        )
    )
    send_data['task_reviewer_pending_actions'] = task_reviewer_pending_actions
    send_data['task_reviewer_pending_actions_count'] = len(task_reviewer_pending_actions)
    send_data['task_reviewer_completed_actions'] = task_reviewer_completed_actions
    send_data['task_reviewer_completed_actions_count'] = len(task_reviewer_completed_actions)
    from django.utils.timezone import now

    if employee.job_title and employee.job_title.description in ["Painter", "Superintendent", "Warehouse"]:

        toolbox_talks_required = []

        scheduled_qs = ScheduledToolboxTalks.objects.filter(
            date__lte=date.today(),
            date__gte=employee.date_added
        ).filter(
            Q(is_all_employees=True) |
            Q(scheduledtoolboxtalkemployees__employee=employee)
        ).distinct().order_by('date')

        for x in scheduled_qs:

            if CompletedToolboxTalks.objects.filter(employee=employee, master=x).exists():
                continue

            if x.master:
                talk_description = x.master.description
                talk_display_id = x.master.id
            else:
                talk_description = x.description or "Custom Toolbox Talk"
                talk_display_id = x.id

            english_file = get_uploaded_toolbox_file(x, "English")
            spanish_file = get_uploaded_toolbox_file(x, "Spanish")

            english = english_file['filename'] if english_file else None
            spanish = spanish_file['filename'] if spanish_file else None

            spanish_view = ViewedToolboxTalks.objects.filter(
                employee=employee,
                master=x,
                language="Spanish"
            ).order_by('-date').first()

            english_view = ViewedToolboxTalks.objects.filter(
                employee=employee,
                master=x,
                language="English"
            ).order_by('-date').first()

            toolbox_talks_required.append({
                'id': talk_display_id,
                'item': x.id,
                'description': talk_description,
                'date': x.date,
                'english': english,
                'spanish': spanish,
                'spanish_viewed': bool(spanish_view),
                'spanish_date': spanish_view.date if spanish_view else None,
                'english_viewed': bool(english_view),
                'english_date': english_view.date if english_view else None,
                'can_complete': bool(spanish_view or english_view),
                'notes': x.notes or "",
                'is_all_employees': x.is_all_employees,
            })

        send_data['toolbox_talks_required'] = toolbox_talks_required
        send_data['toolbox_talks_required_count'] = len(toolbox_talks_required)

    group_toolbox_talks = []
    _delete_expired_group_toolbox_views()

    for scheduled_talk in ScheduledToolboxTalks.objects.filter(
        date__lte=date.today()
    ).order_by(
        "date",
        "id"
    ):
        missing_employees = list(_missing_regular_employees_for_toolbox(scheduled_talk))

        if not missing_employees:
            continue

        if scheduled_talk.master:
            talk_description = scheduled_talk.master.description
        else:
            talk_description = scheduled_talk.description or "Custom Toolbox Talk"

        english_file = get_uploaded_toolbox_file(scheduled_talk, "English")
        spanish_file = get_uploaded_toolbox_file(scheduled_talk, "Spanish")

        group_view = GroupToolboxTalkViews.objects.filter(
            employee=employee,
            scheduled_toolbox_talk=scheduled_talk
        ).first()
        cutoff = _group_toolbox_view_cutoff()
        spanish_viewed = bool(
            group_view and
            group_view.viewed_spanish and
            group_view.viewed_spanish_time and
            group_view.viewed_spanish_time >= cutoff
        )
        english_viewed = bool(
            group_view and
            group_view.viewed_english and
            group_view.viewed_english_time and
            group_view.viewed_english_time >= cutoff
        )

        group_toolbox_talks.append({
            "id": scheduled_talk.id,
            "description": talk_description,
            "date": scheduled_talk.date,
            "option_label": f"{scheduled_talk.date} - {talk_description}",
            "english": english_file['filename'] if english_file else None,
            "spanish": spanish_file['filename'] if spanish_file else None,
            "spanish_viewed": spanish_viewed,
            "spanish_date": group_view.viewed_spanish_time if spanish_viewed else None,
            "english_viewed": english_viewed,
            "english_date": group_view.viewed_english_time if english_viewed else None,
            "can_complete": bool(spanish_viewed or english_viewed),
            "missing_employees": missing_employees,
            "missing_count": len(missing_employees),
        })

    send_data["group_toolbox_talks"] = group_toolbox_talks
    send_data["group_toolbox_talks_count"] = len(group_toolbox_talks)
    send_data["open_jobs"] = Jobs.objects.filter(
        is_closed=False
    ).order_by(
        "job_number"
    )

    toolbox_talks_for_other_employees = []
    other_employees = Employees.objects.filter(
        active=True,
        job_title__description__in=["Painter", "Superintendent", "Warehouse"]
    ).exclude(
        id=employee.id
    ).select_related(
        "job_title"
    ).order_by(
        "last_name",
        "first_name"
    )

    for other_employee in other_employees:
        scheduled_qs = ScheduledToolboxTalks.objects.filter(
            date__lte=date.today()
        )

        if other_employee.date_added:
            scheduled_qs = scheduled_qs.filter(
                date__gte=other_employee.date_added
            )

        scheduled_qs = scheduled_qs.filter(
            Q(is_all_employees=True) |
            Q(scheduledtoolboxtalkemployees__employee=other_employee)
        ).distinct().order_by("date")

        employee_toolbox_talks = []

        for scheduled_talk in scheduled_qs:
            if CompletedToolboxTalks.objects.filter(
                employee=other_employee,
                master=scheduled_talk
            ).exists():
                continue

            if scheduled_talk.master:
                talk_description = scheduled_talk.master.description
            else:
                talk_description = scheduled_talk.description or "Custom Toolbox Talk"

            english_file = get_uploaded_toolbox_file(scheduled_talk, "English")
            spanish_file = get_uploaded_toolbox_file(scheduled_talk, "Spanish")

            english = english_file['filename'] if english_file else None
            spanish = spanish_file['filename'] if spanish_file else None

            spanish_view = ViewedToolboxTalks.objects.filter(
                employee=other_employee,
                master=scheduled_talk,
                language="Spanish"
            ).order_by('-date').first()

            english_view = ViewedToolboxTalks.objects.filter(
                employee=other_employee,
                master=scheduled_talk,
                language="English"
            ).order_by('-date').first()

            employee_toolbox_talks.append({
                "id": scheduled_talk.id,
                "item": scheduled_talk.id,
                "description": talk_description,
                "date": scheduled_talk.date,
                "english": english,
                "spanish": spanish,
                "spanish_viewed": bool(spanish_view),
                "spanish_date": spanish_view.date if spanish_view else None,
                "english_viewed": bool(english_view),
                "english_date": english_view.date if english_view else None,
                "can_complete": bool(spanish_view or english_view),
                "notes": scheduled_talk.notes or "",
                "is_all_employees": scheduled_talk.is_all_employees,
            })

        if employee_toolbox_talks:
            toolbox_talks_for_other_employees.append({
                "employee": other_employee,
                "talks": employee_toolbox_talks,
                "count": len(employee_toolbox_talks),
            })

    send_data["toolbox_talks_for_other_employees"] = toolbox_talks_for_other_employees
    send_data["toolbox_talks_for_other_employees_count"] = sum(
        row["count"] for row in toolbox_talks_for_other_employees
    )
    return render(request, "my_page.html", send_data)


@login_required(login_url='/accounts/login')
def certifications(request, id):
    send_data = {}
    show_closed_certifications = request.GET.get("show_closed") == "1"
    if id != 'ALL':
        selected_cert = Certifications.objects.get(id=id)
        send_data['selected_item'] = selected_cert
        send_data['notes2'] = CertificationNotes.objects.filter(certification__id=id)
        pending_employee_tasks = EmployeePendingActions.objects.filter(
            certification=selected_cert,
            is_complete=False,
        ).order_by(
            "date",
            "id",
        )
        completed_tasks_requiring_review = EmployeePendingActions.objects.filter(
            certification=selected_cert,
            is_complete=True,
            confirmed_is_complete=False,
        ).order_by(
            "date",
            "id",
        )
        send_data['pending_employee_tasks'] = pending_employee_tasks
        send_data['pending_employee_tasks_count'] = pending_employee_tasks.count()
        send_data['completed_tasks_requiring_review'] = completed_tasks_requiring_review
        send_data['completed_tasks_requiring_review_count'] = completed_tasks_requiring_review.count()
        send_data['certification_files'] = _certification_file_rows(selected_cert.id)
        send_data['certification_files_count'] = len(send_data['certification_files'])
        send_data['certification_folder_path'] = rf"\\gp-webserver\trinity\certifications\{selected_cert.id}"
        send_data['active_employees'] = Employees.objects.filter(
            active=True,
        ).order_by(
            "first_name",
            "last_name",
        )
        pending_task_assignee_options = [
            {
                "value": f"employee:{employee.id}",
                "label": str(employee),
                "selected": bool(selected_cert.employee_id == employee.id),
            }
            for employee in send_data['active_employees']
        ]
        if selected_cert.subcontractor_id:
            for sub_employee in (
                Subcontractor_Employees.objects
                .filter(
                    subcontractor=selected_cert.subcontractor,
                    is_active=True,
                )
                .order_by("name")
            ):
                pending_task_assignee_options.append({
                    "value": f"sub:{sub_employee.id}",
                    "label": f"[SUB] {sub_employee.name}",
                    "selected": bool(selected_cert.subcontractor_employee_id == sub_employee.id),
                })
        send_data['pending_task_assignee_options'] = pending_task_assignee_options
        if selected_cert.subcontractor_employee_id:
            send_data['pending_task_selected_assignee'] = f"sub:{selected_cert.subcontractor_employee_id}"
        elif selected_cert.employee_id:
            send_data['pending_task_selected_assignee'] = f"employee:{selected_cert.employee_id}"
        else:
            send_data['pending_task_selected_assignee'] = ""
        if selected_cert.category:
            if selected_cert.category.description=="Respirator Clearance" and RespiratorClearance.objects.filter(certification=selected_cert).exists():
                return redirect('view_respirator_certification',id=id)

    if request.method == 'POST':
        cert = Certifications.objects.get(id=id)
        if 'upload_certification_files' in request.POST:
            uploaded_files = request.FILES.getlist('certification_files')
            custom_name = request.POST.get('certification_file_name') or ""

            if not uploaded_files:
                messages.error(request, "Please choose at least one file to upload.")
                return redirect('certifications', id=cert.id)

            folder = _certification_files_folder(cert.id)
            os.makedirs(folder, exist_ok=True)

            for index, uploaded_file in enumerate(uploaded_files, start=1):
                filename = _certification_upload_filename(
                    uploaded_file,
                    custom_name,
                    index if len(uploaded_files) > 1 else None,
                )
                file_path = os.path.join(folder, filename)
                with open(file_path, "wb+") as destination:
                    for chunk in uploaded_file.chunks():
                        destination.write(chunk)

            CertificationNotes.objects.create(
                certification=cert,
                date=date.today(),
                user=Employees.objects.get(user=request.user),
                note=f"Uploaded {len(uploaded_files)} certification file(s).",
            )
            messages.success(request, "Certification file uploaded.")
            return redirect('certifications', id=cert.id)
        if 'add_pending_task' in request.POST:
            task_assignee = request.POST.get('pending_task_employee') or ""
            task_employee = None
            task_subcontractor_employee = None
            if task_assignee.startswith("sub:"):
                task_subcontractor_employee = get_object_or_404(
                    Subcontractor_Employees,
                    id=task_assignee.replace("sub:", "", 1),
                    is_active=True,
                    subcontractor=cert.subcontractor,
                )
            elif task_assignee.startswith("employee:"):
                task_employee = get_object_or_404(
                    Employees,
                    id=task_assignee.replace("employee:", "", 1),
                    active=True,
                )
            else:
                messages.error(request, "Please select an employee.")
                return redirect('certifications', id=cert.id)

            task_assignee_display = (
                f"[SUB] {task_subcontractor_employee}"
                if task_subcontractor_employee
                else str(task_employee)
            )
            recipient_email = (
                task_subcontractor_employee.email
                if task_subcontractor_employee
                else task_employee.email
            )
            task_description = (request.POST.get('pending_task_description') or "").strip()
            task_note = (request.POST.get('pending_task_note') or "").strip()

            if not task_description:
                messages.error(request, "Please enter a task description.")
                return redirect('certifications', id=cert.id)

            current_employee = Employees.objects.filter(user=request.user).first()
            notes = ""
            if task_note:
                note_prefix = date.today().strftime('%m/%d/%Y')
                if current_employee:
                    note_prefix += f" - {current_employee.first_name}"
                notes = f"{note_prefix}: {task_note}"

            pending_action = EmployeePendingActions.objects.create(
                employee=task_employee,
                subcontractor_employee=task_subcontractor_employee,
                certification=cert,
                date=date.today(),
                description=task_description,
                notes=notes,
                is_complete=False,
                confirmed_is_complete=False,
            )
            certification_note = f"Pending employee task assigned to {task_assignee_display}: {task_description}"
            if task_note:
                certification_note += f". Note: {task_note}"
            note_user = (
                current_employee or
                task_employee or
                Employees.objects.filter(user__is_superuser=True).first() or
                Employees.objects.first()
            )
            CertificationNotes.objects.create(
                certification=cert,
                date=date.today(),
                user=note_user,
                note=certification_note,
            )
            if recipient_email:
                sender = (
                    current_employee.email
                    if current_employee and current_employee.email
                    else "bridgette@gerloffpainting.com"
                )
                email_body = (
                    "A new required task has been added for you.\n\n"
                    f"Task: {pending_action.description}\n"
                    f"Certification: {cert}\n"
                    f"Date Added: {pending_action.date.strftime('%m/%d/%Y')}\n"
                )
                if task_note:
                    email_body += f"\nNotes:\n{task_note}"

                try:
                    Email.sendEmail(
                        "New Required Task",
                        email_body,
                        [recipient_email],
                        False,
                        sender,
                    )
                    messages.success(request, "Pending employee task added and employee notified.")
                except Exception:
                    messages.warning(request, "Pending employee task added, but the employee email could not be sent.")
            else:
                messages.warning(request, "Pending employee task added, but this employee does not have an email on file.")
            return redirect('certifications', id=cert.id)
        if 'add_pending_task_note' in request.POST:
            pending_task = get_object_or_404(
                EmployeePendingActions,
                id=request.POST.get('add_pending_task_note'),
                certification=cert,
                is_complete=False,
            )
            task_note = (request.POST.get(f"pending_task_note_{pending_task.id}") or "").strip()
            if task_note:
                current_employee = Employees.objects.filter(user=request.user).first()
                note_prefix = date.today().strftime('%m/%d/%Y')
                if current_employee:
                    note_prefix += f" - {current_employee.first_name}"
                pending_task.notes = (
                    (pending_task.notes + "\n") if pending_task.notes else ""
                ) + f"{note_prefix}: {task_note}"
                pending_task.save(update_fields=["notes"])
                messages.success(request, "Task note added.")
            else:
                messages.error(request, "Please enter a note before adding it.")
            return redirect('certifications', id=cert.id)
        if 'delete_pending_task' in request.POST:
            pending_task = get_object_or_404(
                EmployeePendingActions,
                id=request.POST.get('delete_pending_task'),
                certification=cert,
            )
            current_employee = Employees.objects.filter(user=request.user).first()
            certification_note = (
                f"Pending employee task deleted for {pending_task.assignee_display}: "
                f"{pending_task.description}"
            )
            if pending_task.notes:
                certification_note += f". Notes: {pending_task.notes}"
            CertificationNotes.objects.create(
                certification=cert,
                date=date.today(),
                user=current_employee or pending_task.employee or Employees.objects.filter(user__is_superuser=True).first() or Employees.objects.first(),
                note=certification_note,
            )
            pending_task.delete()
            messages.success(request, "Pending employee task deleted.")
            return redirect('certifications', id=cert.id)
        if 'confirm_completed_task' in request.POST:
            completed_task = get_object_or_404(
                EmployeePendingActions,
                id=request.POST.get('confirm_completed_task'),
                certification=cert,
                is_complete=True,
                confirmed_is_complete=False,
            )
            current_employee = Employees.objects.filter(user=request.user).first()
            completed_task.confirmed_is_complete = True
            completed_task.save(update_fields=["confirmed_is_complete"])
            CertificationNotes.objects.create(
                certification=cert,
                date=date.today(),
                user=current_employee or completed_task.employee or Employees.objects.filter(user__is_superuser=True).first() or Employees.objects.first(),
                note=(
                    f"Completed employee task confirmed for {completed_task.assignee_display}: "
                    f"{completed_task.description}"
                ),
            )
            messages.success(request, "Completed task confirmed.")
            return redirect('certifications', id=cert.id)
        if 'deny_completed_task' in request.POST:
            completed_task = get_object_or_404(
                EmployeePendingActions,
                id=request.POST.get('deny_completed_task'),
                certification=cert,
                is_complete=True,
                confirmed_is_complete=False,
            )
            current_employee = Employees.objects.filter(user=request.user).first()
            denial_note = (request.POST.get(f"deny_completed_task_note_{completed_task.id}") or "").strip()
            if not denial_note:
                messages.error(request, "Please enter a note explaining why the completed task was denied.")
                return redirect('certifications', id=cert.id)

            completed_task.is_complete = False
            completed_task.confirmed_is_complete = False
            completed_task.notes = (
                (completed_task.notes + "\n") if completed_task.notes else ""
            ) + f"{date.today().strftime('%m/%d/%Y')} - {current_employee.first_name if current_employee else 'Unknown'}: Denied completion. {denial_note}"
            completed_task.save(update_fields=["is_complete", "confirmed_is_complete", "notes"])
            CertificationNotes.objects.create(
                certification=cert,
                date=date.today(),
                user=current_employee or completed_task.employee or Employees.objects.filter(user__is_superuser=True).first() or Employees.objects.first(),
                note=(
                    f"Completed employee task denied and reopened for {completed_task.assignee_display}: "
                    f"{completed_task.description}. Reason: {denial_note}"
                ),
            )
            messages.success(request, "Completed task denied and reopened.")
            return redirect('certifications', id=cert.id)
        if 'new_note' in request.POST:
            CertificationNotes.objects.create(certification=cert, date=date.today(),
                                              user=Employees.objects.get(user=request.user),
                                              note=request.POST['note'])
            return redirect('certifications', id=cert.id)
        if 'closed_item' in request.POST:
            cert.is_closed = True
            deleted_pending_actions_count, _ = EmployeePendingActions.objects.filter(
                certification=cert,
                confirmed_is_complete=False,
            ).delete()
            CertificationNotes.objects.create(certification=cert, date=date.today(),
                                              user=Employees.objects.get(user=request.user),
                                              note=(
                                                  "Cert closed."
                                                  + request.POST['closed_note']
                                                  + f" Deleted {deleted_pending_actions_count} unconfirmed pending employee task(s)."
                                              ))
            cert.save()
            return redirect('certifications', id='ALL')
        if 'change_start_date' in request.POST:
            cert.date_received = request.POST['start_date']
            CertificationNotes.objects.create(certification=cert, date=date.today(),
                                              user=Employees.objects.get(user=request.user),
                                              note="Start Date Changed to: " + cert.date_received + "- " + request.POST[
                                                  'start_date_note'])
            cert.save()
            messages.success(request, "Date received updated.")
            return redirect('certifications', id=cert.id)
        if 'change_end_date' in request.POST:
            cert.date_expires = request.POST['end_date']
            CertificationNotes.objects.create(certification=cert, date=date.today(),
                                              user=Employees.objects.get(user=request.user),
                                              note="Expiration Date Changed to: " + cert.date_expires + "- " +
                                                   request.POST['end_date_note'])
            cert.save()
            messages.success(request, "Expiration date updated.")
            return redirect('certifications', id=cert.id)
        cert.save()
    certifications_list = Certifications.objects.filter(
        is_closed=show_closed_certifications,
    ).filter(
        Q(employee__active=True) | Q(employee__isnull=True, subcontractor__is_inactive=False),
    ).select_related(
        "employee",
        "category",
        "subcontractor",
        "subcontractor_employee",
    )
    certification_ids = list(certifications_list.values_list("id", flat=True))
    trinity_respirators_by_certification = {
        clearance.certification_id: clearance
        for clearance in RespiratorClearance.objects.filter(
            certification_id__in=certification_ids,
        ).select_related("certification")
    }
    pending_tasks_by_certification = {}
    for task in EmployeePendingActions.objects.filter(
        certification__isnull=False,
        is_complete=False,
    ).order_by(
        "date",
        "id",
    ):
        pending_tasks_by_certification.setdefault(task.certification_id, []).append(task)

    certification_rows = []
    certification_filter_descriptions = set()
    for cert in certifications_list:
        cert.pending_employee_tasks = pending_tasks_by_certification.get(cert.id, [])
        if cert.category and cert.category.description == "Respirator Clearance":
            respirator_clearance = trinity_respirators_by_certification.get(cert.id)
            if respirator_clearance:
                cert.display_description = "Respirator Certification [Trinity]"
            else:
                cert.display_description = "Respirator Certification [External]"
        else:
            if cert.category:
                cert.display_description = cert.category
            else:
                cert.display_description = cert.description
        if cert.display_description:
            certification_filter_descriptions.add(str(cert.display_description))
        action_required = []
        if cert.category and cert.category.description == "Respirator Clearance":
            respirator_clearance = trinity_respirators_by_certification.get(cert.id)
            if respirator_clearance:
                if not respirator_clearance.date_completed:
                    action_required.append("Form Incomplete")
                elif not respirator_clearance.approved_for_use:
                    action_required.append("Awaiting Approval")
        if not action_required:
            action_required = [task.description for task in cert.pending_employee_tasks]
        employee_url = None
        if cert.employee_id:
            employee_url = reverse("employees_page", args=[cert.employee_id])
        elif cert.subcontractor_employee_id:
            employee_url = reverse("subcontractor_employee_page", args=[cert.subcontractor_employee_id])
        certification_rows.append({
            "employee": cert.owner_display,
            "employee_url": employee_url,
            "display_description": cert.display_description,
            "view_url": reverse("certifications", args=[cert.id]),
            "date_received": cert.date_received,
            "date_expires": cert.date_expires,
            "action_required": action_required,
        })

    subcontractor_clearances = (
        SubcontractorRespiratorClearance.objects
        .filter(is_closed=show_closed_certifications)
        .select_related("subcontractor", "employee")
        .order_by("subcontractor__company", "employee_name", "-date_created", "-id")
    )
    subcontractor_description = "Respirator Certification [Subcontractor]"
    for clearance in subcontractor_clearances:
        action_required = []
        if not clearance.date_completed:
            action_required.append("Form Incomplete")
        elif not clearance.approved_for_use:
            action_required.append("Awaiting Approval")

        certification_filter_descriptions.add(subcontractor_description)
        employee_url = None
        if clearance.employee_id:
            employee_url = reverse("subcontractor_employee_page", args=[clearance.employee_id])
        certification_rows.append({
            "employee": f"{clearance.subcontractor.company} - {clearance.employee_display_name}",
            "employee_url": employee_url,
            "display_description": subcontractor_description,
            "view_url": reverse(
                "subcontractor_resp_clearance_review",
                args=[clearance.subcontractor_id, clearance.id],
            ),
            "date_received": clearance.date_completed or clearance.date_created,
            "date_expires": clearance.date_expires,
            "action_required": action_required,
        })

    send_data['certifications'] = sorted(
        certification_rows,
        key=lambda row: (
            row["employee"].lower(),
            str(row["display_description"]).lower(),
        ),
    )
    send_data['certification_filter_descriptions'] = sorted(
        certification_filter_descriptions,
        key=str.casefold,
    )
    send_data['show_closed_certifications'] = show_closed_certifications
    return render(request, "certifications.html", send_data)


@login_required(login_url='/accounts/login')
def subcontractor_certifications(request):
    return redirect("certifications", id="ALL")


@login_required(login_url='/accounts/login')
def new_certification(request):
    subcontractor_employees_by_subcontractor = defaultdict(list)
    for subcontractor_employee in (
        Subcontractor_Employees.objects
        .filter(is_active=True, subcontractor__is_inactive=False)
        .select_related('subcontractor')
        .order_by('name')
    ):
        subcontractor_employees_by_subcontractor[str(subcontractor_employee.subcontractor_id)].append({
            'id': subcontractor_employee.id,
            'name': subcontractor_employee.name,
        })

    send_data = {
        'employees': Employees.objects.filter(
            active=True,
        ).order_by('first_name', 'last_name'),
        'subcontractors': Subcontractors.objects.filter(
            is_inactive=False,
        ).order_by('company'),
        'subcontractor_employees_json': json.dumps(
            subcontractor_employees_by_subcontractor,
            cls=DjangoJSONEncoder,
        ),
        'jobs': Jobs.objects.filter(is_closed=False).order_by('job_name'),
        'categories': CertificationCategories.objects.all().order_by('description'),
    }

    if request.method == 'POST':
        selected_category = request.POST.get('select_category')
        save_new_type = request.POST.get('save_new_certification_type') == 'YES'
        cert_description = ""
        category = None

        if selected_category and selected_category.startswith('NEW__'):
            new_type_description = selected_category.replace('NEW__', '').strip()

            if save_new_type:
                category, created = CertificationCategories.objects.get_or_create(
                    description=new_type_description
                )
                cert_description = category.description
            else:
                cert_description = new_type_description

        elif selected_category and selected_category != 'please_select':
            category = CertificationCategories.objects.get(id=selected_category)
            cert_description = category.description

        else:
            return redirect('new_certification')

        certification_note = request.POST.get('note', '')
        selected_employee_id = request.POST.get('select_employee')
        selected_subcontractor_id = request.POST.get('select_subcontractor')
        selected_subcontractor_employee_id = request.POST.get('select_subcontractor_employee')
        duplicate_choice = request.POST.get('duplicate_choice')
        duplicate_employee_id = request.POST.get('duplicate_employee_id')
        custom_subcontractor_employee_name = (
            request.POST.get('subcontractor_employee_name') or ""
        ).strip()

        selected_employee_id = None if selected_employee_id in [None, '', 'please_select'] else selected_employee_id
        selected_subcontractor_id = None if selected_subcontractor_id in [None, '', 'please_select'] else selected_subcontractor_id
        selected_subcontractor_employee_id = (
            None
            if selected_subcontractor_employee_id in [None, '', 'please_select']
            else selected_subcontractor_employee_id
        )

        if selected_employee_id and (
            selected_subcontractor_id or selected_subcontractor_employee_id or custom_subcontractor_employee_name
        ):
            messages.error(request, "Select either a regular employee or a subcontractor employee, not both.")
            return redirect('new_certification')

        if not selected_employee_id and not selected_subcontractor_id:
            messages.error(request, "Select a regular employee or a subcontractor.")
            return redirect('new_certification')

        employee = None
        subcontractor = None
        subcontractor_employee = None
        if selected_employee_id:
            employee = get_object_or_404(Employees, id=selected_employee_id, active=True)
        else:
            subcontractor = get_object_or_404(
                Subcontractors,
                id=selected_subcontractor_id,
                is_inactive=False,
            )
            if selected_subcontractor_employee_id:
                subcontractor_employee = get_object_or_404(
                    Subcontractor_Employees,
                    id=selected_subcontractor_employee_id,
                    subcontractor=subcontractor,
                    is_active=True,
                )
                custom_subcontractor_employee_name = ""
            elif not custom_subcontractor_employee_name:
                messages.error(request, "Select a subcontractor employee or enter a subcontractor employee name.")
                return redirect('new_certification')
            else:
                matching_subcontractor_employees = (
                    Subcontractor_Employees.objects
                    .filter(
                        subcontractor=subcontractor,
                        name__iexact=custom_subcontractor_employee_name,
                    )
                )
                active_duplicate_count = matching_subcontractor_employees.filter(is_active=True).count()
                inactive_duplicate_count = matching_subcontractor_employees.filter(is_active=False).count()

                if (active_duplicate_count or inactive_duplicate_count) and duplicate_choice != "new":
                    duplicate_post_items = []
                    for key in request.POST:
                        if key in [
                            "csrfmiddlewaretoken",
                            "duplicate_choice",
                            "duplicate_employee_id",
                        ]:
                            continue
                        for value in request.POST.getlist(key):
                            duplicate_post_items.append({
                                "key": key,
                                "value": value,
                            })

                    send_data.update({
                        "duplicate_subcontractor_employee_name": custom_subcontractor_employee_name,
                        "duplicate_subcontractor": subcontractor,
                        "duplicate_active_count": active_duplicate_count,
                        "duplicate_inactive_count": inactive_duplicate_count,
                        "duplicate_certification_post_items": duplicate_post_items,
                    })
                    return render(request, "new_certification.html", send_data)

                new_subcontractor_employee_name = custom_subcontractor_employee_name
                if active_duplicate_count or inactive_duplicate_count:
                    new_subcontractor_employee_name = _duplicate_certification_sub_employee_name(
                        custom_subcontractor_employee_name,
                        subcontractor,
                    )

                subcontractor_employee = Subcontractor_Employees.objects.create(
                    subcontractor=subcontractor,
                    name=new_subcontractor_employee_name,
                    date_enrolled=date.today(),
                    is_active=True,
                )
                custom_subcontractor_employee_name = ""

        new_cert = Certifications.objects.create(
            category=category,
            employee=employee,
            subcontractor=subcontractor,
            subcontractor_employee=subcontractor_employee,
            subcontractor_employee_name=custom_subcontractor_employee_name,
            description=cert_description,
            note=certification_note
        )

        if 'dont_know_start' not in request.POST and request.POST.get('start_date'):
            new_cert.date_received = request.POST.get('start_date')

        if 'dont_know_end' not in request.POST and request.POST.get('end_date'):
            new_cert.date_expires = request.POST.get('end_date')

        selected_job = request.POST.get('select_job')
        if selected_job and selected_job != 'please_select':
            new_cert.job = Jobs.objects.get(job_number=selected_job)

        new_cert.save()

        if certification_note:
            CertificationNotes.objects.create(
                certification=new_cert,
                date=date.today(),
                user=Employees.objects.get(user=request.user),
                note=certification_note,
            )

        os.makedirs(_certification_files_folder(new_cert.id), exist_ok=True)

        return redirect('certifications', id=new_cert.id)

    return render(request, "new_certification.html", send_data)


@login_required(login_url='/accounts/login')
def add_new_employee(request):
    send_data = {}
    job_titles = EmployeeTitles.objects.all()
    employers = Employers.objects.all()
    vacation_defaults, created = VacationDefaults.objects.get_or_create(id=1)
    painter_default_days = vacation_defaults.painter_days_per_year if vacation_defaults else 0
    non_painter_default_days = vacation_defaults.non_painter_days_per_year if vacation_defaults else 0
    send_data['jobtitles'] = job_titles
    send_data['employers'] = employers
    send_data['painter_default_days'] = painter_default_days
    send_data['non_painter_default_days'] = non_painter_default_days
    send_data['job_titles_json'] = json.dumps(
        list(job_titles.values("id", "description")),
        cls=DjangoJSONEncoder,
    )
    send_data['employers_json'] = json.dumps(
        list(employers.values("id", "company_name")),
        cls=DjangoJSONEncoder,
    )
    if request.method == 'POST':
        job_title = EmployeeTitles.objects.get(id=request.POST['jobTitle'])
        employer = Employers.objects.get(id=request.POST['employer'])
        vacation_days_per_year = None

        if (
            job_title.description == "Painter" and
            employer.company_name == "Gerloff Painting"
        ) or job_title.description != "Painter":
            vacation_days_value = request.POST.get("vacation_days_per_year")

            if vacation_days_value not in [None, ""]:
                vacation_days_per_year = int(vacation_days_value)

        employee = Employees.objects.create(first_name=request.POST['first_name'],
                                            middle_name=request.POST['middle_name'],
                                            last_name=request.POST['last_name'],
                                            job_title=job_title,
                                            employer=employer.company_name,
                                            employment_company=employer,
                                            vacation_days_per_year=vacation_days_per_year,
                                            date_added=date.today())
        try:
            # check if employees directory exists
            employeesFolderPath = os.path.join(settings.MEDIA_ROOT, "employees")
            if not os.path.isdir(employeesFolderPath):
                # create employees directory
                os.mkdir(employeesFolderPath)
            # create employee folder
            employeeFolderPath = os.path.join(settings.MEDIA_ROOT, "employees", str(employee.id))
            os.mkdir(employeeFolderPath)
        except Exception as e:
            print('unable to create employee folder', e)

        return redirect('employees_home')
    return render(request, "add_new_employee.html", send_data)


@login_required(login_url='/accounts/login')
def write_ups(request, id):
    send_data = {}
    send_data['employees'] = Employees.objects.filter(active=True)
    send_data['me'] = Employees.objects.get(user=request.user)
    send_data['jobs'] = Jobs.objects.filter(is_closed=False)
    send_data['write_ups'] = WriteUp.objects.filter(employee__active=True)
    if id != 'ALL':
        send_data['selected_item'] = WriteUp.objects.get(id=id)
    return render(request, "write_ups.html", send_data)


@login_required(login_url='/accounts/login')
def write_ups_new(request):
    send_data = {}
    send_data['employees'] = Employees.objects.filter(active=True)
    send_data['me'] = Employees.objects.get(user=request.user)
    send_data['jobs'] = Jobs.objects.filter(is_closed=False)
    send_data['write_ups'] = WriteUp.objects.filter(employee__active=True)
    send_data['defaults'] = WriteUpDefaults.objects.all()
    if request.method == 'POST':
        if 'custom_topic' in request.POST:
            new_writeup = WriteUp.objects.create(supervisor=Employees.objects.get(id=request.POST['select_supervisor']),
                                                 employee=Employees.objects.get(id=request.POST['select_employee']),
                                                 date=date.today(), description=request.POST['custom_topic'],
                                                 note=request.POST['note'])
        else:
            new_writeup = WriteUp.objects.create(supervisor=Employees.objects.get(id=request.POST['select_supervisor']),
                                                 employee=Employees.objects.get(id=request.POST['select_employee']),
                                                 date=date.today(),
                                                 description=request.POST['select_topic'], note=request.POST['note'])
        if request.POST['select_job'] != "please_select":
            new_writeup.job = Jobs.objects.get(job_number=request.POST['select_job'])
            new_writeup.save()
        return redirect('write_ups', id=new_writeup.id)
    return render(request, "write_ups_new.html", send_data)


@login_required(login_url='/accounts/login')
def daily_reports(request, id):
    send_data = {}
    send_data['dailyreports'] = DailyReports.objects.all()
    if id != 'ALL':
        teamnumbers = []
        numbercheck = []
        a = 0
        for x in ProductionItems.objects.filter(daily_report__id=id):
            if x.team_number != None:
                a = 1
                if x.team_number not in numbercheck:
                    numbercheck.append(x.team_number)
                    if x.task != None:
                        teamnumbers.append(
                            {'number': x.team_number, 'value1': x.value1, 'value2': x.value2, 'value3': x.value3,
                             'unit1': x.unit, 'unit2': x.unit2, 'unit3': x.unit3, 'hours': x.hours,
                             'description': x.task.item1 + ' ' + x.task.item2 + ' ' + x.task.item3})
                    else:
                        teamnumbers.append(
                            {'number': x.team_number, 'value1': x.value1, 'value2': x.value2, 'value3': x.value3,
                             'unit1': x.unit, 'unit2': x.unit2, 'unit3': x.unit3, 'hours': x.hours,
                             'description': x.description})
        if a == 1:
            send_data['teamnumbers'] = teamnumbers
        send_data['selected_item'] = DailyReports.objects.get(id=id)
        send_data['items'] = ProductionItems.objects.filter(daily_report__id=id)
    return render(request, "daily_reports.html", send_data)

def safety_home(request):
    send_data = {}
    painters_needing_respirator = []
    today = date.today()
    expiration_warning_date = today + timedelta(days=14)
    for x in Employees.objects.filter(active=True, job_title__description="Painter"):
        external_resp_cert = Certifications.objects.filter(
            employee=x,
            is_closed=False,
            category__description="Respirator Clearance",
            date_expires__gte=today
        ).exclude(
            respiratorclearance__isnull=False
        ).order_by("date_expires").first()

        trinity_resp_clearance = RespiratorClearance.objects.filter(
            employee=x,
            date_completed__isnull=False,
            approved_for_use=True,
            certification__is_closed=False,
            certification__date_expires__gte=today
        ).select_related("certification").order_by("certification__date_expires").first()

        pending_trinity_resp_clearance = RespiratorClearance.objects.filter(
            employee=x,
            date_completed__isnull=False,
            approved_for_use=False,
            certification__is_closed=False
        ).exists()

        expired_trinity_resp_clearance = RespiratorClearance.objects.filter(
            employee=x,
            date_completed__isnull=False,
            approved_for_use=True,
            certification__is_closed=False,
            certification__date_expires__lt=today
        ).exists()

        expired_external_resp_cert = Certifications.objects.filter(
            employee=x,
            is_closed=False,
            category__description="Respirator Clearance",
            date_expires__lt=today
        ).exclude(
            respiratorclearance__isnull=False
        ).exists()

        if external_resp_cert or trinity_resp_clearance or pending_trinity_resp_clearance:
            current_expiration = None
            if external_resp_cert:
                current_expiration = external_resp_cert.date_expires
            if trinity_resp_clearance and (
                current_expiration is None or trinity_resp_clearance.certification.date_expires < current_expiration
            ):
                current_expiration = trinity_resp_clearance.certification.date_expires

            if current_expiration and today <= current_expiration <= expiration_warning_date:
                painters_needing_respirator.append({
                    'employee': x.first_name + " " + x.last_name,
                    'status': f"Pending Expiration {current_expiration.strftime('%m/%d/%Y')}",
                })
            continue

        status = "Expired" if expired_trinity_resp_clearance or expired_external_resp_cert else "Not Completed"
        painters_needing_respirator.append({
            'employee': x.first_name + " " + x.last_name,
            'status': status,
        })

    for x in (
        SubcontractorRespiratorClearance.objects
        .filter(
            approved_for_use=True,
            is_closed=False,
            date_expires__gte=today,
            date_expires__lte=expiration_warning_date,
        )
        .select_related('subcontractor', 'employee')
    ):
        painters_needing_respirator.append({
            'employee': f"{x.subcontractor.company} - {x.employee_display_name}",
            'status': f"Pending Expiration {x.date_expires.strftime('%m/%d/%Y')}",
        })

    send_data['pending_respirators'] = painters_needing_respirator
    send_data['pending_respirators_count'] = len(painters_needing_respirator)
    respirators_in_review = get_respirators_in_review()
    send_data['respirators_in_review'] = respirators_in_review
    send_data['respirators_in_review_count'] = len(respirators_in_review)
    send_data['safety_inspections'] = (
        JobsiteSafetyInspection.objects
        .select_related('job', 'inspector')
        .order_by('-inspection_date')[:50]
    )
    return render(request, 'safety_home.html', send_data)

def toolbox_talks_master(request):
    send_data = {}

    if request.method == 'POST':
        if 'replace_next_toolbox_id' in request.POST:

            selected_master = ToolboxTalks.objects.get(
                id=request.POST['replace_next_toolbox_id']
            )

            url = reverse('toolbox_talk_assign') + f"?master_id={request.POST['replace_next_toolbox_id']}" + '&existing=1'
            return redirect(url)
            # next_scheduled = ScheduledToolboxTalks.objects.filter(
            #     date__gte=date.today(),
            #     is_all_employees=True,
            # ).order_by('date', 'id').first()
            #
            # if next_scheduled:
            #
            #     next_date = next_scheduled.date
            #
            #     future_talks = ScheduledToolboxTalks.objects.filter(
            #         date__gte=next_date,
            #         is_all_employees=True,
            #     ).order_by('-date', '-id')
            #
            #     for talk in future_talks:
            #         talk.date = talk.date + timedelta(days=7)
            #         talk.save()
            #
            #     ScheduledToolboxTalks.objects.create(
            #         master=selected_master,
            #         description=None,
            #         date=next_date,
            #         is_all_employees=True,
            #         notes="All Employees"
            #     )

            # return redirect('toolbox_talks_master')
        if 'description' in request.POST:
            newitem = ToolboxTalks.objects.create(
                description=request.POST['description']
            )
            createfolder("toolbox_talks/" + str(newitem.id))
            createfolder("toolbox_talks/" + str(newitem.id) + "/English")
            createfolder("toolbox_talks/" + str(newitem.id) + "/Spanish")
            return redirect('toolbox_talks_master')

        if 'selected_id' in request.POST:
            id = str(request.POST['selected_id'] + "/" + request.POST['selected_language'])
            return MediaUtilities().getDirectoryContents(
                id,
                request.POST['selected_file'],
                'toolbox_talks'
            )

    toolboxtalks = []
    folder_name = settings.MEDIA_ROOT

    for x in ToolboxTalks.objects.all().order_by('id'):

        spanish = None
        english = None

        spanish_path = os.path.join(
            folder_name,
            "toolbox_talks",
            str(x.id),
            "Spanish"
        )

        english_path = os.path.join(
            folder_name,
            "toolbox_talks",
            str(x.id),
            "English"
        )

        if os.path.exists(spanish_path):
            for entry in os.listdir(spanish_path):
                full_path = os.path.join(spanish_path, entry)
                if os.path.isfile(full_path):
                    spanish = entry
                    break

        if os.path.exists(english_path):
            for entry in os.listdir(english_path):
                full_path = os.path.join(english_path, entry)
                if os.path.isfile(full_path):
                    english = entry
                    break

        scheduled_instances = ScheduledToolboxTalks.objects.filter(
            master=x,date__lte=date.today(),
        ).order_by('-date')

        scheduled_count = scheduled_instances.count()
        last_issued = None

        if scheduled_instances.exists():
            last_issued = scheduled_instances.first().date

        if not english or not spanish:
            status = "NEED TO UPLOAD"
        elif scheduled_count > 0:
            status = f"{scheduled_count} Times. Last Issued {last_issued.strftime('%m/%d/%y')}"
        else:
            status = "Files Uploaded. Never Issued"

        instance_rows = []

        for scheduled in scheduled_instances:
            employee_count = ScheduledToolboxTalkEmployees.objects.filter(
                scheduled=scheduled
            ).count()

            sub_employee_count = ScheduledToolboxTalkSubEmployees.objects.filter(
                scheduled=scheduled
            ).count()

            sub_job_count = ScheduledToolboxTalkSubJobs.objects.filter(
                scheduled=scheduled
            ).count()

            instance_rows.append({
                'id': scheduled.id,
                'date': scheduled.date,
                'description': scheduled.description,
                'is_all_employees': scheduled.is_all_employees,
                'notes': scheduled.notes,
                'employee_count': employee_count,
                'sub_employee_count': sub_employee_count,
                'sub_job_count': sub_job_count,
            })

        future_scheduled_instances = ScheduledToolboxTalks.objects.filter(
            master=x,
            date__gte=date.today(),
        ).order_by('date')

        future_instance_rows = []

        for scheduled in future_scheduled_instances:
            future_instance_rows.append({
                'id': scheduled.id,
                'date': scheduled.date,
                'description': scheduled.description,
                'notes': scheduled.notes,
            })

        toolboxtalks.append({
            'id': x.id,
            'description': x.description,
            'english': english,
            'spanish': spanish,
            'status': status,
            'scheduled_count': scheduled_count,
            'last_issued': last_issued,
            'instances': instance_rows,
            'future_instances': future_instance_rows,
        })

    send_data['toolboxtalks'] = toolboxtalks
    return render(request, 'toolbox_talks_master.html', send_data)

def _get_subcontractor_scheduled_talk_counts(scheduled):
    counts = sub_toolbox.get_scheduled_talk_subcontractor_counts(scheduled)
    return counts["total"], counts["completed"]


def scheduled_toolbox_talks(request):
    today = date.today()
    days_until_monday = (0 - today.weekday() + 7) % 7
    if days_until_monday == 0:
        days_until_monday = 7

    next_monday_date = today + timedelta(days=days_until_monday)
    next_date = next_monday_date - timedelta(days=7)

    if request.method == 'POST':
        if ScheduledToolboxTalks.objects.filter(is_all_employees=True).exists():
            latest_object = ScheduledToolboxTalks.objects.filter(is_all_employees=True).order_by('-date').first()
            if latest_object.date < today - timedelta(days=7):
                next_date = today
            else:
                next_date = latest_object.date + timedelta(days=7)

        for x in ToolboxTalks.objects.all():
            ScheduledToolboxTalks.objects.create(
                master=x,
                date=next_date,
                is_all_employees=True,
                notes="All Employees"
            )
            next_date = next_date + timedelta(days=7)

        return redirect('scheduled_toolbox_talks')

    send_data = {}
    toolboxtalks = []

    scheduled_rows = ScheduledToolboxTalks.objects.all().order_by('date')

    for x in scheduled_rows:
        if x.master:
            description = f"{x.master.description}"
        else:
            description = x.description or "Custom Toolbox Talk"

        english_file = get_uploaded_toolbox_file(x, "English")
        spanish_file = get_uploaded_toolbox_file(x, "Spanish")
        files_uploaded = bool(english_file) and bool(spanish_file)
        if not files_uploaded:
            ratio = "FILES NOT UPLOADED"
        else:

            ratio = "Not Issued Yet"
            ratio_done_count = None
            ratio_missing_count = None

            employee_assignments = ScheduledToolboxTalkEmployees.objects.filter(
                scheduled=x
            ).select_related('employee')

            sub_assignments = ScheduledToolboxTalkSubEmployees.objects.filter(
                scheduled=x,
                employee__subcontractor__is_toolbox_required=True
            ).select_related('employee', 'job', 'employee__subcontractor')
            sub_job_assignments = ScheduledToolboxTalkSubJobs.objects.filter(
                scheduled=x,
                subcontractor__is_toolbox_required=True
            ).select_related('subcontractor', 'job')
            if x.date <= date.today():
                total_count = 0
                completed_count = 0

                # regular employee assignments
                for row in employee_assignments:
                    if _has_excused_employee_toolbox_talk(row.employee, x):
                        continue

                    total_count += 1

                    if CompletedToolboxTalks.objects.filter(
                            master=x,
                            employee=row.employee,
                            is_excused=False
                    ).exists():
                        completed_count += 1

                if x.is_all_employees:
                    target_employees = Employees.objects.filter(
                        active=True,
                        date_added__lte=x.date,
                        job_title__description__in=[
                            "Painter",
                            "Warehouse",
                            "Superintendent"
                        ]
                    )

                    for emp in target_employees:
                        if _has_excused_employee_toolbox_talk(emp, x):
                            continue

                        total_count += 1

                        if CompletedToolboxTalks.objects.filter(
                                master=x,
                                employee=emp,
                                is_excused=False
                        ).exists():
                            completed_count += 1

                sub_total_count, sub_completed_count = _get_subcontractor_scheduled_talk_counts(x)
                total_count += sub_total_count
                completed_count += sub_completed_count

                if total_count > 0:
                    ratio_done_count = completed_count
                    ratio_missing_count = total_count - completed_count
                    ratio = ""
                else:
                    ratio_done_count = 0
                    ratio_missing_count = 0
                    ratio = ""

        toolboxtalks.append({
            'Item': x.id,
            'description': description,
            'date': x.date,
            'ratio': ratio,
            'ratio_done_count': ratio_done_count if files_uploaded else None,
            'ratio_missing_count': ratio_missing_count if files_uploaded else None,
            'notes': x.notes or "",
        })

    send_data['toolboxtalks'] = toolboxtalks
    return render(request, 'scheduled_toolbox_talks.html', send_data)


def delete_old_incomplete_toolbox_talks(request):
    send_data = {}
    mode = request.GET.get('mode')
    selected_subcontractor = None

    if request.method == 'POST' and request.POST.get('action') in ['excuse_all', 'excuse_before_date']:
        action = request.POST.get('action')
        today = timezone.localdate()
        selected_date = None

        if action == 'excuse_before_date':
            selected_date_value = request.POST.get('before_date')
            try:
                selected_date = date.fromisoformat(selected_date_value)
            except (TypeError, ValueError):
                messages.error(request, "Please select a valid date.")
                return render(request, 'delete_old_incomplete_toolbox_talks.html', send_data)

            scheduled_date_filter = {'date__lt': selected_date}
            prefixed_scheduled_date_filter = {'scheduled__date__lt': selected_date}
            success_scope = f"before {selected_date.strftime('%m/%d/%Y')}"
        else:
            scheduled_date_filter = {'date__lte': today}
            prefixed_scheduled_date_filter = {'scheduled__date__lte': today}
            success_scope = "through today"

        excused_employee_count = 0
        excused_sub_employee_count = 0
        excused_sub_job_count = 0
        closed_all_employee_count = 0

        with transaction.atomic():
            regular_employees = Employees.objects.filter(
                active=True,
                job_title__description__in=[
                    "Painter",
                    "Warehouse",
                    "Superintendent"
                ]
            )

            for employee in regular_employees:
                assigned_ids = _get_assigned_talk_ids_for_employee(employee)
                if not assigned_ids:
                    continue

                completed_ids = set(
                    CompletedToolboxTalks.objects.filter(
                        employee=employee,
                        master_id__in=assigned_ids
                    ).values_list('master_id', flat=True)
                )

                outstanding_talks = ScheduledToolboxTalks.objects.filter(
                    id__in=assigned_ids - completed_ids,
                    **scheduled_date_filter
                )

                for scheduled_talk in outstanding_talks:
                    if _excuse_employee_toolbox_talk(employee, scheduled_talk):
                        excused_employee_count += 1

            sub_cutoff_date = selected_date if action == 'excuse_before_date' else today + timedelta(days=1)
            sub_items = sub_toolbox.get_missing_subcontractor_items_before(
                sub_cutoff_date
            )

            for item in sub_items:
                if item["type"] == "subcontractor_employee":
                    item_excused = False
                    for job in item["jobs"]:
                        if _excuse_subcontractor_toolbox_talk(
                            item["employee"],
                            item["scheduled"],
                            job
                        ):
                            item_excused = True
                    if item_excused:
                        excused_sub_employee_count += 1
                elif item["type"] == "subcontractor_job":
                    if _excuse_subcontractor_job_toolbox_talk(
                        item["scheduled"],
                        item["subcontractor"],
                        item["job"]
                    ):
                        excused_sub_job_count += 1

            closed_all_employee_count = _close_all_employee_assignment_for_excused_talks(
                scheduled_date_filter,
                today
            )

        messages.success(
            request,
            f"Excused {excused_employee_count} employee toolbox talks, {excused_sub_employee_count} subcontractor employee toolbox talks, and {excused_sub_job_count} subcontractor job toolbox talks {success_scope}."
        )
        send_data['excused_employee_count'] = excused_employee_count
        send_data['excused_sub_employee_count'] = excused_sub_employee_count
        send_data['excused_sub_job_count'] = excused_sub_job_count
        send_data['closed_all_employee_count'] = closed_all_employee_count

    if request.method == 'POST' and request.POST.get('action') in ['excuse_selected_sub_all', 'excuse_selected_sub_selected']:
        selected_subcontractor = get_object_or_404(
            Subcontractors,
            id=request.POST.get('subcontractor_id')
        )
        outstanding_items = _get_outstanding_toolbox_items_for_subcontractor(selected_subcontractor)

        if request.POST.get('action') == 'excuse_selected_sub_selected':
            selected_values = set(request.POST.getlist('selected_talks'))
            outstanding_items = [
                item for item in outstanding_items
                if item['value'] in selected_values
            ]

            if not outstanding_items:
                messages.error(request, "Please select at least one toolbox talk to excuse.")
                return redirect(
                    reverse('delete_old_incomplete_toolbox_talks') +
                    f"?mode=subs&subcontractor_id={selected_subcontractor.id}"
                )

        excused_sub_employee_count = 0
        excused_sub_job_count = 0

        with transaction.atomic():
            for item in outstanding_items:
                if item['kind'] == 'sub_employee':
                    item_excused = False
                    for job in item.get('jobs') or [item['job']]:
                        if _excuse_subcontractor_toolbox_talk(
                            item['employee'],
                            item['scheduled'],
                            job
                        ):
                            item_excused = True
                    if item_excused:
                        excused_sub_employee_count += 1
                elif item['kind'] == 'sub_job':
                    if _excuse_subcontractor_job_toolbox_talk(
                        item['scheduled'],
                        selected_subcontractor,
                        item['job']
                    ):
                        excused_sub_job_count += 1

        messages.success(
            request,
            f"Excused {excused_sub_employee_count} subcontractor employee toolbox talks and {excused_sub_job_count} subcontractor job toolbox talks for {selected_subcontractor.company}."
        )
        if request.POST.get('action') in ['excuse_selected_sub_all', 'excuse_selected_sub_selected']:
            return redirect('delete_old_incomplete_toolbox_talks')

        return redirect(
            reverse('delete_old_incomplete_toolbox_talks') +
            f"?mode=subs&subcontractor_id={selected_subcontractor.id}"
        )

    if request.method == 'POST' and request.POST.get('action') in ['excuse_selected_employee_all', 'excuse_selected_employee_selected']:
        selected_employee = get_object_or_404(
            Employees,
            id=request.POST.get('employee_id'),
            active=True,
            job_title__description__in=[
                "Painter",
                "Warehouse",
                "Superintendent"
            ]
        )
        outstanding_items = _get_outstanding_toolbox_items_for_employee(selected_employee)

        if request.POST.get('action') == 'excuse_selected_employee_selected':
            selected_values = set(request.POST.getlist('selected_talks'))
            outstanding_items = [
                item for item in outstanding_items
                if item['value'] in selected_values
            ]

            if not outstanding_items:
                messages.error(request, "Please select at least one toolbox talk to excuse.")
                return redirect(
                    reverse('delete_old_incomplete_toolbox_talks') +
                    f"?mode=employees&employee_id={selected_employee.id}"
                )

        excused_employee_count = 0

        with transaction.atomic():
            for item in outstanding_items:
                if _excuse_employee_toolbox_talk(
                    selected_employee,
                    item['scheduled']
                ):
                    excused_employee_count += 1

        messages.success(
            request,
            f"Excused {excused_employee_count} toolbox talks for {selected_employee.first_name} {selected_employee.last_name}."
        )
        if request.POST.get('action') in ['excuse_selected_employee_all', 'excuse_selected_employee_selected']:
            return redirect('delete_old_incomplete_toolbox_talks')

        return redirect(
            reverse('delete_old_incomplete_toolbox_talks') +
            f"?mode=employees&employee_id={selected_employee.id}"
        )

    if request.method == 'POST' and request.POST.get('action') == 'excuse_selected_talk_people':
        selected_talk = get_object_or_404(
            ScheduledToolboxTalks,
            id=request.POST.get('scheduled_talk_id')
        )
        selected_values = set(request.POST.getlist('selected_people'))
        outstanding_items = [
            item for item in _get_outstanding_toolbox_items_for_talk(selected_talk)
            if item['value'] in selected_values
        ]

        if not outstanding_items:
            messages.error(request, "Please select at least one person to excuse.")
            return redirect(
                reverse('delete_old_incomplete_toolbox_talks') +
                f"?mode=talks&scheduled_talk_id={selected_talk.id}"
            )

        excused_employee_count = 0
        excused_sub_employee_count = 0
        excused_sub_job_count = 0

        with transaction.atomic():
            for item in outstanding_items:
                if item['kind'] == 'employee':
                    if _excuse_employee_toolbox_talk(
                        item['employee'],
                        selected_talk
                    ):
                        excused_employee_count += 1
                elif item['kind'] == 'sub_employee':
                    item_excused = False
                    for job in item.get('jobs') or [item['job']]:
                        if _excuse_subcontractor_toolbox_talk(
                            item['employee'],
                            selected_talk,
                            job
                        ):
                            item_excused = True
                    if item_excused:
                        excused_sub_employee_count += 1
                elif item['kind'] == 'sub_job':
                    if _excuse_subcontractor_job_toolbox_talk(
                        selected_talk,
                        item['subcontractor'],
                        item['job']
                    ):
                        excused_sub_job_count += 1

        messages.success(
            request,
            f"Excused {excused_employee_count} employee toolbox talks, {excused_sub_employee_count} subcontractor employee toolbox talks, and {excused_sub_job_count} subcontractor job toolbox talks for {_get_talk_title(selected_talk)}."
        )
        return redirect('delete_old_incomplete_toolbox_talks')

    if mode == 'subs':
        selected_subcontractor_id = request.GET.get('subcontractor_id')
        subcontractor_rows = []

        for subcontractor in Subcontractors.objects.filter(
            is_inactive=False,
            is_toolbox_required=True
        ).order_by(
            'company'
        ):
            outstanding_count = len(_get_outstanding_toolbox_items_for_subcontractor(subcontractor))
            if not subcontractor.is_toolbox_required and outstanding_count == 0:
                continue

            subcontractor_rows.append({
                'id': subcontractor.id,
                'company': subcontractor.company,
                'label': f"{subcontractor.company} ({outstanding_count} outstanding)",
                'outstanding_count': outstanding_count,
            })

        send_data['mode'] = mode
        send_data['subcontractor_rows'] = subcontractor_rows

        if selected_subcontractor_id:
            selected_subcontractor = get_object_or_404(
                Subcontractors,
                id=selected_subcontractor_id
            )
            send_data['selected_subcontractor'] = selected_subcontractor
            send_data['selected_subcontractor_label'] = next(
                (
                    row['label'] for row in subcontractor_rows
                    if row['id'] == selected_subcontractor.id
                ),
                str(selected_subcontractor)
            )
            send_data['selected_subcontractor_outstanding_items'] = _get_outstanding_toolbox_items_for_subcontractor(
                selected_subcontractor
            )

    if mode == 'employees':
        selected_employee_id = request.GET.get('employee_id')
        employee_rows = []

        for employee in Employees.objects.filter(
            active=True,
            job_title__description__in=[
                "Painter",
                "Warehouse",
                "Superintendent"
            ]
        ).order_by(
            'last_name',
            'first_name'
        ):
            outstanding_count = len(_get_outstanding_toolbox_items_for_employee(employee))
            employee_name = f"{employee.first_name} {employee.last_name}"
            employee_rows.append({
                'id': employee.id,
                'name': employee_name,
                'label': f"{employee_name} ({outstanding_count} outstanding)",
                'outstanding_count': outstanding_count,
            })

        send_data['mode'] = mode
        send_data['employee_rows'] = employee_rows

        if selected_employee_id:
            selected_employee = get_object_or_404(
                Employees,
                id=selected_employee_id,
                active=True,
                job_title__description__in=[
                    "Painter",
                    "Warehouse",
                    "Superintendent"
                ]
            )
            send_data['selected_employee'] = selected_employee
            send_data['selected_employee_label'] = next(
                (
                    row['label'] for row in employee_rows
                    if row['id'] == selected_employee.id
                ),
                f"{selected_employee.first_name} {selected_employee.last_name}"
            )
            send_data['selected_employee_outstanding_items'] = _get_outstanding_toolbox_items_for_employee(
                selected_employee
            )

    if mode == 'talks':
        selected_talk_id = request.GET.get('scheduled_talk_id')
        talk_rows = _get_incomplete_toolbox_talk_rows()

        send_data['mode'] = mode
        send_data['talk_rows'] = talk_rows

        if selected_talk_id:
            selected_talk = get_object_or_404(
                ScheduledToolboxTalks,
                id=selected_talk_id
            )
            send_data['selected_talk'] = selected_talk
            send_data['selected_talk_label'] = next(
                (
                    row['label'] for row in talk_rows
                    if row['id'] == selected_talk.id
                ),
                _format_outstanding_employee_toolbox_item(selected_talk)
            )
            send_data['selected_talk_outstanding_items'] = _get_outstanding_toolbox_items_for_talk(
                selected_talk
            )

    return render(request, 'delete_old_incomplete_toolbox_talks.html', send_data)


def _get_incomplete_toolbox_talk_rows():
    rows = []
    today = timezone.localdate()

    scheduled_talks = (
        ScheduledToolboxTalks.objects
        .filter(date__lte=today)
        .select_related('master')
        .order_by('date', 'id')
    )

    for scheduled_talk in scheduled_talks:
        outstanding_count = len(_get_outstanding_toolbox_items_for_talk(scheduled_talk))
        if not outstanding_count:
            continue

        item_date = scheduled_talk.date.strftime('%m/%d/%Y') if scheduled_talk.date else 'No Date'
        rows.append({
            'id': scheduled_talk.id,
            'label': f"{item_date} - {_get_talk_title(scheduled_talk)} ({outstanding_count} incomplete)",
            'outstanding_count': outstanding_count,
        })

    return rows


def _get_outstanding_toolbox_items_for_talk(scheduled_talk):
    outstanding_items = []

    regular_employees = Employees.objects.filter(
        active=True,
        job_title__description__in=[
            "Painter",
            "Warehouse",
            "Superintendent"
        ]
    ).order_by(
        'last_name',
        'first_name'
    )

    for employee in regular_employees:
        if scheduled_talk.id not in _get_assigned_talk_ids_for_employee(employee):
            continue

        if CompletedToolboxTalks.objects.filter(
            employee=employee,
            master=scheduled_talk
        ).exists():
            continue

        employee_name = f"{employee.first_name} {employee.last_name}"
        outstanding_items.append({
            'kind': 'employee',
            'value': f"employee|{scheduled_talk.id}|{employee.id}",
            'employee': employee,
            'display': f"Employee - {employee_name}",
            'sort_name': employee_name,
            'jobs': [],
            'job': None,
            'subcontractor': None,
        })

    subcontractor_items = sub_toolbox.get_scheduled_talk_subcontractor_items(scheduled_talk)["missing"]

    for item in subcontractor_items:
        if item["type"] == "subcontractor_employee":
            jobs = item.get("jobs") or []
            if not jobs:
                continue

            employee = item["employee"]
            job_text = "Jobs " + ", ".join(f"{job.job_number} {job.job_name}" for job in jobs)
            outstanding_items.append({
                'kind': 'sub_employee',
                'value': f"sub_employee|{scheduled_talk.id}|{employee.id}",
                'employee': employee,
                'subcontractor': item["subcontractor"],
                'job': jobs[0],
                'jobs': jobs,
                'display': f"Subcontractor Employee - {employee.name} - {item['subcontractor'].company} - {job_text}",
                'sort_name': employee.name,
            })
        elif item["type"] == "subcontractor_job":
            job = item["job"]
            subcontractor = item["subcontractor"]
            outstanding_items.append({
                'kind': 'sub_job',
                'value': f"sub_job|{scheduled_talk.id}|{subcontractor.id}|{job.pk}",
                'employee': None,
                'subcontractor': subcontractor,
                'job': job,
                'jobs': [job],
                'display': f"Subcontractor Job - {subcontractor.company} - Job {job.job_number} {job.job_name}",
                'sort_name': subcontractor.company,
            })

    return sorted(
        outstanding_items,
        key=lambda item: (
            item['kind'],
            item['sort_name'] or '',
            item['display'] or ''
        )
    )


def _get_outstanding_toolbox_items_for_employee(employee):
    today = timezone.localdate()
    assigned_ids = _get_assigned_talk_ids_for_employee(employee)

    if not assigned_ids:
        return []

    completed_ids = set(
        CompletedToolboxTalks.objects.filter(
            employee=employee,
            master_id__in=assigned_ids
        ).values_list('master_id', flat=True)
    )

    outstanding_talks = ScheduledToolboxTalks.objects.filter(
        id__in=assigned_ids - completed_ids,
        date__lte=today
    ).order_by(
        'date',
        'id'
    )

    return [
        {
            'scheduled': scheduled_talk,
            'value': str(scheduled_talk.id),
            'date': scheduled_talk.date,
            'description': _get_talk_title(scheduled_talk),
            'display': _format_outstanding_employee_toolbox_item(scheduled_talk),
        }
        for scheduled_talk in outstanding_talks
    ]


def _format_outstanding_employee_toolbox_item(scheduled_talk):
    item_date = scheduled_talk.date.strftime('%m/%d/%Y') if scheduled_talk.date else 'No Date'
    description = _get_talk_title(scheduled_talk)
    return f"{item_date} - {description}"


def _close_all_employee_assignment_for_excused_talks(scheduled_date_filter, note_date):
    note_text = f"All Excused {note_date.strftime('%m/%d/%y')}"
    closed_count = 0

    scheduled_talks = ScheduledToolboxTalks.objects.filter(
        is_all_employees=True,
        **scheduled_date_filter
    )

    for scheduled_talk in scheduled_talks:
        current_notes = scheduled_talk.notes or ""
        if note_text not in current_notes:
            separator = " | " if current_notes else ""
            max_existing_length = 2000 - len(separator) - len(note_text)
            current_notes = current_notes[:max_existing_length]
            scheduled_talk.notes = f"{current_notes}{separator}{note_text}"

        scheduled_talk.is_all_employees = False
        scheduled_talk.save(update_fields=['is_all_employees', 'notes'])
        closed_count += 1

    return closed_count


def _get_outstanding_toolbox_items_for_subcontractor(subcontractor):
    if not subcontractor.is_toolbox_required:
        return []

    outstanding_items = []

    for item in sub_toolbox.get_missing_subcontractor_items_for_subcontractor(
        subcontractor,
        timezone.localdate() + timedelta(days=1)
    ):
        if item["type"] == "subcontractor_employee":
            jobs = item.get("jobs") or []
            if not jobs:
                continue

            job = jobs[0]
            employee = item["employee"]
            kind = "sub_employee"
            value = f"{kind}|{item['scheduled'].id}|{job.job_number}|{employee.id}"
            display = _format_outstanding_subcontractor_toolbox_item(
                kind,
                item["scheduled"],
                job,
                employee,
                jobs=jobs
            )
        else:
            job = item["job"]
            employee = None
            kind = "sub_job"
            value = f"{kind}|{item['scheduled'].id}|{job.job_number}|"
            display = _format_outstanding_subcontractor_toolbox_item(
                kind,
                item["scheduled"],
                job
            )

        outstanding_items.append({
            'kind': kind,
            'value': value,
            'scheduled': item["scheduled"],
            'job': job,
            'jobs': item.get("jobs") or [job],
            'employee': employee,
            'date': item["date"],
            'description': item["title"],
            'display': display,
        })

    return sorted(
        outstanding_items,
        key=lambda item: (
            item['date'] or date.min,
            item['description'],
            str(item['job'] or ''),
            str(item['employee'] or '')
        )
    )


def _format_outstanding_subcontractor_toolbox_item(kind, scheduled, job, employee=None, jobs=None):
    item_date = scheduled.date.strftime('%m/%d/%Y') if scheduled.date else 'No Date'
    description = _get_talk_title(scheduled)
    if jobs:
        job_text = "Jobs " + ", ".join(f"{job.job_number} {job.job_name}" for job in jobs)
    else:
        job_text = f"Job {job.job_number} {job.job_name}" if job else "No Job"

    if kind == 'sub_employee' and employee:
        return f"{item_date} - {description} - {job_text} - {employee.name}"

    return f"{item_date} - {description} - {job_text}"


def respirator_clearance_base(request):
    send_data = {}
    employee = Employees.objects.get(user=request.user)
    send_data['employee'] = employee

    main = get_current_resp_clearance(employee)

    if main:
        send_data['started_at_base'] = True
        send_data['respirator_clearance0'] = True

        if RespiratorClearance1.objects.filter(main=main).exists():
            send_data['respirator_clearance1'] = True
        if RespiratorClearance2.objects.filter(main=main).exists():
            send_data['respirator_clearance2'] = True
        if RespiratorClearance3.objects.filter(main=main).exists():
            send_data['respirator_clearance3'] = True
        if RespiratorClearance4.objects.filter(main=main).exists():
            send_data['respirator_clearance4'] = True
        if RespiratorClearance5.objects.filter(main=main).exists():
            send_data['respirator_clearance5'] = True
        if RespiratorClearance6.objects.filter(main=main).exists():
            send_data['respirator_clearance6'] = True

    return render(request, 'respirator_clearance_base.html', send_data)

def respirator_clearance_section0(request):
    send_data = {}
    employee = Employees.objects.get(user=request.user)
    send_data['employee'] = employee

    if request.method == 'POST':
        rc = get_current_resp_clearance(employee)

        if not rc:
            new_cert = Certifications.objects.create(
                employee=employee,
                category=CertificationCategories.objects.get(description="Respirator Clearance"),
                description="Respirator Clearance"
            )

            rc = RespiratorClearance.objects.create(
                employee=employee,
                date_created=date.today(),
                certification=new_cert
            )

            RespiratorNotes.objects.create(
                employee=employee,
                date=date.today(),
                main=rc,
                note="Respirator Clearance Form Started"
            )

            CertificationNotes.objects.create(
                certification=new_cert,
                date=date.today(),
                user=employee,
                note="Respirator Clearance Form Started"
            )

        employee.gender = request.POST.get('gender')
        employee.height = request.POST.get('height')
        employee.weight = request.POST.get('weight')
        employee.phone = request.POST.get('phone')
        employee.birth_date = request.POST.get('birth_date')
        employee.save()

        if request.POST['next_page'] == 'back_to_base':
            return redirect('respirator_clearance_base')

        if request.POST['next_page'] == 'next_page':
            return redirect('respirator_clearance_section1')

    return render(request, 'respirator_clearance_section0.html', send_data)



@csrf_exempt
def respirator_clearance_section1(request):
    send_data = {}
    employee = Employees.objects.get(user=request.user)
    send_data['employee'] = employee
    main = get_current_resp_clearance(employee)

    if not main:
        return redirect('respirator_clearance_section0')
    if not RespiratorClearance1.objects.filter(main=main).exists():
        RespiratorClearance1.objects.create(main=main)
    part1 = RespiratorClearance1.objects.get(main=main)
    send_data['part1'] = part1
    if request.method == 'POST':
        for field in part1._meta.fields:
            name = field.name
            if name == 'id' or name == 'main':
                continue
            if name in request.POST:
                value = request.POST[name]
                setattr(part1, name, value)
                part1.save()

        return redirect('respirator_clearance_section2')
    return render(request, 'respirator_clearance_section1.html', send_data)

@csrf_exempt
def respirator_clearance_section2(request):
    send_data = {}
    employee = Employees.objects.get(user=request.user)
    send_data['employee'] = employee
    main = get_current_resp_clearance(employee)

    if not main:
        return redirect('respirator_clearance_section0')
    if not RespiratorClearance2.objects.filter(main=main).exists():
        RespiratorClearance2.objects.create(main=main)
    part1 = RespiratorClearance2.objects.get(main=main)
    send_data['part1'] = part1
    if request.method == 'POST':
        for field in part1._meta.fields:
            name = field.name
            if name == 'id' or name == 'main':
                continue
            if name in request.POST:
                value = request.POST[name]
                setattr(part1, name, value)
                part1.save()
        return redirect('respirator_clearance_section3')
    return render(request, 'respirator_clearance_section2.html', send_data)

def respirator_clearance_section3(request):
    send_data = {}
    employee = Employees.objects.get(user=request.user)
    send_data['employee'] = employee
    main = get_current_resp_clearance(employee)

    if not main:
        return redirect('respirator_clearance_section0')
    if not RespiratorClearance3.objects.filter(main=main).exists():
        RespiratorClearance3.objects.create(main=main)
    part1 = RespiratorClearance3.objects.get(main=main)
    send_data['part1'] = part1
    if request.method == 'POST':
        for field in part1._meta.fields:
            name = field.name
            if name == 'id' or name == 'main':
                continue
            if name in request.POST:
                value = request.POST[name]
                setattr(part1, name, value)
                part1.save()
        return redirect('respirator_clearance_section4')
    return render(request, 'respirator_clearance_section3.html', send_data)


def respirator_clearance_section4(request):
    send_data = {}
    employee = Employees.objects.get(user=request.user)
    send_data['employee'] = employee
    main = get_current_resp_clearance(employee)

    if not main:
        return redirect('respirator_clearance_section0')
    if not RespiratorClearance4.objects.filter(main=main).exists():
        RespiratorClearance4.objects.create(main=main)
    part1 = RespiratorClearance4.objects.get(main=main)
    send_data['part1'] = part1
    if request.method == 'POST':
        for field in part1._meta.fields:
            name = field.name
            if name == 'id' or name == 'main':
                continue
            if name in request.POST:
                value = request.POST[name]
                setattr(part1, name, value)
                part1.save()
        return redirect('respirator_clearance_section5')
    return render(request, 'respirator_clearance_section4.html', send_data)

def respirator_clearance_section5(request):
    send_data = {}
    employee = Employees.objects.get(user=request.user)
    send_data['employee'] = employee
    main = get_current_resp_clearance(employee)

    if not main:
        return redirect('respirator_clearance_section0')
    if not RespiratorClearance5.objects.filter(main=main).exists():
        RespiratorClearance5.objects.create(main=main)
    part1 = RespiratorClearance5.objects.get(main=main)
    send_data['part1'] = part1
    if request.method == 'POST':
        for field in part1._meta.fields:
            name = field.name
            if name == 'id' or name == 'main':
                continue
            if name in request.POST:
                value = request.POST[name]
                setattr(part1, name, value)
                part1.save()
        return redirect('respirator_clearance_section6')
    return render(request, 'respirator_clearance_section5.html', send_data)

def respirator_clearance_section6(request):
    send_data = {}
    employee = Employees.objects.get(user=request.user)
    send_data['employee'] = employee
    main = get_current_resp_clearance(employee)

    if not main:
        return redirect('respirator_clearance_section0')
    if not RespiratorClearance6.objects.filter(main=main).exists():
        RespiratorClearance6.objects.create(main=main)
    part1 = RespiratorClearance6.objects.get(main=main)
    send_data['part1'] = part1
    if request.method == 'POST':
        for field in part1._meta.fields:
            name = field.name
            if name == 'id' or name == 'main':
                continue
            if name in request.POST:
                value = request.POST[name]
                setattr(part1, name, value)
                part1.save()
        main.date_completed = date.today()
        main.save()
        message = "Respirator Clearance Completed. \n Employee: " + employee.first_name + employee.last_name
        recipients = ["skip@gerloffpainting.com","bridgette@gerloffpainting.com"]
        Email_Errors.objects.filter(user=request.user.first_name + " " + request.user.last_name).delete()
        check_sender = Employees.objects.filter(user=request.user).first() if request.user.is_authenticated else None
        sender = check_sender.email if check_sender else "operations@gerloffpainting.com"
        try:
            Email.sendEmail("Respirator Clearance Completed", message,
                            recipients, False,sender)
            message = "Your email about the respirator clearance was sent successfully"
        except:
            message = "Error! Your email about the respirator clearance failed to send. Please call them and let them know it was completed."
        Email_Errors.objects.create(user=request.user.first_name + " " + request.user.last_name, error=message,
                                    date=date.today())
        RespiratorNotes.objects.create(employee=employee,date=date.today(),main=main, note="Respirator Clearance Form Completed")
        new_cert = main.certification
        CertificationNotes.objects.create(certification=new_cert,date=date.today(),user=employee,note="Respirator Clearance Form Completed")
        _close_previous_employee_respirator_certifications(employee, new_cert, employee)
        if request.POST['physician'] == 'Yes':
            main.is_physician_required = True
            main.is_physician_actually_required = True
            main.save()
            CertificationNotes.objects.create(certification=new_cert, date=date.today(), user=employee,
                                              note="Employee Requested Physician Review")
        return redirect('my_page')
    return render(request, 'respirator_clearance_section6.html', send_data)

def respirator_clearance_completed(request,respirator_id):
    send_data = {}
    main = RespiratorClearance.objects.get(id=respirator_id)
    employee = main.employee
    send_data['employee'] = employee
    send_data['main'] = main
    send_data['part1'] = RespiratorClearance1.objects.get(main=main)
    send_data['part2'] = RespiratorClearance2.objects.get(main=main)
    send_data['part3'] = RespiratorClearance3.objects.get(main=main)
    send_data['part4'] = RespiratorClearance4.objects.get(main=main)
    send_data['part5'] = RespiratorClearance5.objects.get(main=main)
    send_data['part6'] = RespiratorClearance6.objects.get(main=main)
    return render(request, 'respirator_clearance_completed.html', send_data)


def _get_talk_title(talk):
    if talk.master and talk.master.description:
        return talk.master.description
    if talk.description:
        return talk.description
    return f"Scheduled Toolbox Talk #{talk.id}"


def _get_assigned_talk_ids_for_employee(employee):
    """
    Assigned talks for regular employees:
    1. Explicitly assigned via ScheduledToolboxTalkEmployees
    2. OR talk.is_all_employees=True AND:
       - talk.date is not null
       - talk.date <= today
       - employee.date_added <= talk.date
    """
    assigned_ids = set()

    explicit_ids = set(
        ScheduledToolboxTalkEmployees.objects
        .filter(employee=employee)
        .values_list('scheduled_id', flat=True)
        .distinct()
    )
    assigned_ids.update(explicit_ids)

    if employee.date_added:
        today = timezone.localdate()
        global_ids = set(
            ScheduledToolboxTalks.objects
            .filter(
                is_all_employees=True,
                date__isnull=False,
                date__lte=today,
                date__gte=employee.date_added,
            )
            .values_list('id', flat=True)
            .distinct()
        )
        assigned_ids.update(global_ids)

    return assigned_ids


def _get_assigned_talk_ids_for_sub_employee(sub_employee):
    """
    Assigned talks for subcontractor employees:
    1. If has_access_to_toolbox=False -> none
    2. Explicitly assigned via ScheduledToolboxTalkSubEmployees
    3. OR talk.is_all_employees=True AND:
       - talk.date is not null
       - talk.date <= today
       - sub_employee.date_enrolled <= talk.date
       - the talk date is after the first invoice date for a delegated subcontract/job
       - sub_employee.has_access_to_toolbox=True
    """
    if (
        not sub_employee.has_access_to_toolbox or
        not sub_employee.subcontractor or
        not sub_employee.subcontractor.is_toolbox_required
    ):
        return set()

    delegated_jobs = _get_delegated_active_toolbox_jobs_for_sub_employee(sub_employee)
    if not delegated_jobs:
        return set()

    assigned_ids = set()

    explicit_assignments = (
        ScheduledToolboxTalkSubEmployees.objects
        .filter(
            employee=sub_employee,
            employee__subcontractor__is_toolbox_required=True
        )
        .select_related('job')
        .distinct()
    )

    for assignment in explicit_assignments:
        if not assignment.job:
            continue
        if not _is_active_toolbox_job(assignment.job):
            continue
        if not _sub_employee_has_delegated_active_toolbox_job(
            sub_employee,
            assignment.job,
            assignment.scheduled.date
        ):
            continue
        assigned_ids.add(assignment.scheduled_id)

    if sub_employee.date_enrolled:
        today = timezone.localdate()
        for job in delegated_jobs:
            subcontract = Subcontracts.objects.filter(
                subcontractor=sub_employee.subcontractor,
                job_number=job,
                is_closed=False,
                subcontractor__is_toolbox_required=True,
                job_number__is_closed=False,
                job_number__is_active=True,
                job_number__is_labor_done=False
            ).first()

            if not subcontract:
                continue

            start_date = _sub_employee_assignment_start_date(sub_employee, subcontract)
            if not start_date:
                continue

            global_ids = set(
                _get_all_employee_toolbox_talks_for_subcontract(
                    subcontract,
                    end_date=today,
                    start_date=start_date
                )
                .values_list('id', flat=True)
                .distinct()
            )
            assigned_ids.update(global_ids)

    return assigned_ids


def toolbox_talks_by_employee(request):
    rows = []

    employees = (
        Employees.objects
        .filter(active=True,
        job_title__description__in=[
            "Painter",
            "Warehouse",
            "Superintendent"
        ])
        .select_related('employment_company')
        .order_by('first_name', 'last_name')
    )

    for emp in employees:
        assigned_ids = _get_assigned_talk_ids_for_employee(emp)

        completed_ids = set(
            CompletedToolboxTalks.objects
            .filter(employee=emp, master_id__in=assigned_ids, is_excused=False)
            .values_list('master_id', flat=True)
            .distinct()
        )
        excused_ids = set(
            CompletedToolboxTalks.objects
            .filter(employee=emp, master_id__in=assigned_ids, is_excused=True)
            .values_list('master_id', flat=True)
            .distinct()
        )

        active_assigned_ids = assigned_ids - excused_ids
        total_assigned = len(active_assigned_ids)
        total_completed = len(completed_ids & active_assigned_ids)

        full_name = f"{emp.first_name or ''} {emp.last_name or ''}".strip()
        if not full_name:
            full_name = f"Employee #{emp.id}"

        employer_name = str(emp.employment_company) if emp.employment_company else ""

        rows.append({
            'person_type': 'employee',
            'person_id': emp.id,
            'name': full_name,
            'employer': employer_name,
            'ratio_sort_completed': total_completed,
            'ratio_sort_total': total_assigned,
            'ratio_display': f"{total_completed} Done, {total_assigned - total_completed} Missing",
            'done_count': total_completed,
            'missing_count': total_assigned - total_completed,
        })

    sub_toolbox_items = sub_toolbox.get_subcontractor_items_before(
        timezone.localdate() + timedelta(days=1)
    )
    missing_sub_toolbox_items_by_employee = defaultdict(list)
    completed_sub_toolbox_items_by_employee = defaultdict(list)
    missing_sub_toolbox_items_by_subcontractor = defaultdict(list)
    completed_sub_toolbox_items_by_subcontractor = defaultdict(list)

    for item in sub_toolbox_items["missing"]:
        if item["type"] == "subcontractor_employee":
            missing_sub_toolbox_items_by_employee[item["employee"].id].append(item)
        elif item["type"] == "subcontractor_job":
            missing_sub_toolbox_items_by_subcontractor[item["subcontractor"].id].append(item)

    for item in sub_toolbox_items["completed"]:
        if item["type"] == "subcontractor_employee":
            completed_sub_toolbox_items_by_employee[item["employee"].id].append(item)
        elif item["type"] == "subcontractor_job":
            completed_sub_toolbox_items_by_subcontractor[item["subcontractor"].id].append(item)

    sub_employees = (
        Subcontractor_Employees.objects
        .filter(
            is_active=True,
            subcontractor__is_toolbox_required=True
        )
        .select_related('subcontractor')
        .order_by('name')
    )

    for sub_emp in sub_employees:
        employer_name = sub_emp.subcontractor.company if sub_emp.subcontractor else ""

        if not sub_emp.has_access_to_toolbox:
            rows.append({
                'person_type': 'sub',
                'person_id': sub_emp.id,
                'management_sub_id': sub_emp.subcontractor_id,
                'name': sub_emp.name or f"Sub Employee #{sub_emp.id}",
                'employer': employer_name,
                'ratio_sort_completed': -1,
                'ratio_sort_total': -1,
                'ratio_display': "Not Signed Up",
                'done_count': None,
                'missing_count': None,
            })
            continue

        missing_items = missing_sub_toolbox_items_by_employee.get(sub_emp.id, [])
        completed_items = completed_sub_toolbox_items_by_employee.get(sub_emp.id, [])
        total_assigned = len(missing_items) + len(completed_items)
        total_completed = len(completed_items)

        rows.append({
            'person_type': 'sub',
            'person_id': sub_emp.id,
            'management_sub_id': sub_emp.subcontractor_id,
            'name': sub_emp.name or f"Sub Employee #{sub_emp.id}",
            'employer': employer_name,
            'ratio_sort_completed': total_completed,
            'ratio_sort_total': total_assigned,
            'ratio_display': f"{total_completed} Done, {total_assigned - total_completed} Missing",
            'done_count': total_completed,
            'missing_count': total_assigned - total_completed,
        })

    subcontractors = (
        Subcontractors.objects
        .filter(subcontract__is_closed=False,is_toolbox_required=True)
        .distinct()
        .order_by('company')
    )

    for sub in subcontractors:
        missing_items = missing_sub_toolbox_items_by_subcontractor.get(sub.id, [])
        completed_items = completed_sub_toolbox_items_by_subcontractor.get(sub.id, [])
        assigned_count = len(missing_items) + len(completed_items)
        completed_count = len(completed_items)

        rows.append({
            'person_type': 'subcontractor',
            'person_id': sub.id,
            'management_sub_id': sub.id,
            'name': 'Subcontractor',
            'employer': sub.company,
            'ratio_sort_completed': completed_count,
            'ratio_sort_total': assigned_count,
            'ratio_display': f"{completed_count} Done, {assigned_count - completed_count} Missing",
            'done_count': completed_count,
            'missing_count': assigned_count - completed_count,
        })



    rows = sorted(
        rows,
        key=lambda x: (
            (x['employer'] or '').lower(),
            (x['name'] or '').lower()
        )
    )

    return render(request, 'toolbox_talks_by_employee.html', {
        'rows': rows
    })


def toolbox_talks_by_employee_modal(request, person_type, person_id):
    management_sub_id = None

    if person_type == 'employee':
        person = get_object_or_404(
            Employees.objects.select_related('employment_company'),
            id=person_id,
            active=True
        )

        person_name = f"{person.first_name or ''} {person.last_name or ''}".strip()
        if not person_name:
            person_name = f"Employee #{person.id}"

        employer_name = str(person.employment_company) if person.employment_company else ""
        has_access_to_toolbox = True

        assigned_ids = _get_assigned_talk_ids_for_employee(person)

        completed_ids = set(
            CompletedToolboxTalks.objects
            .filter(employee=person, master_id__in=assigned_ids, is_excused=False)
            .values_list('master_id', flat=True)
            .distinct()
        )
        excused_ids = set(
            CompletedToolboxTalks.objects
            .filter(employee=person, master_id__in=assigned_ids, is_excused=True)
            .values_list('master_id', flat=True)
            .distinct()
        )

    elif person_type == 'sub':
        person = get_object_or_404(
            Subcontractor_Employees.objects.select_related('subcontractor'),
            id=person_id,
            is_active=True,
            subcontractor__is_toolbox_required=True
        )

        person_name = person.name or f"Sub Employee #{person.id}"
        employer_name = person.subcontractor.company if person.subcontractor else ""
        has_access_to_toolbox = person.has_access_to_toolbox
        management_sub_id = person.subcontractor_id

        if not has_access_to_toolbox:
            return JsonResponse({
                'success': True,
                'person_name': person_name,
                'employer_name': employer_name,
                'management_sub_id': management_sub_id,
                'has_access_to_toolbox': False,
                'completed_talks': [],
                'incomplete_talks': [],
            })

        sub_items = sub_toolbox.get_subcontractor_items_before(
            timezone.localdate() + timedelta(days=1)
        )

        def item_to_talk_dict(item):
            jobs = item.get("jobs") or []
            job_names = ", ".join(job.job_name for job in jobs)
            return {
                'id': item["scheduled"].id,
                'title': item["title"],
                'date': item["date"].strftime('%m/%d/%Y') if item["date"] else '',
                'notes': f"Job: {job_names}" if job_names else '',
                '_sort_date': item["date"] or date.min,
                '_sort_id': item["scheduled"].id,
            }

        completed_talks = [
            item_to_talk_dict(item)
            for item in sub_items["completed"]
            if (
                item["type"] == "subcontractor_employee" and
                item["employee"].id == person.id
            )
        ]
        incomplete_talks = [
            item_to_talk_dict(item)
            for item in sub_items["missing"]
            if (
                item["type"] == "subcontractor_employee" and
                item["employee"].id == person.id
            )
        ]

        completed_talks = sorted(
            completed_talks,
            key=lambda item: (item['_sort_date'], item['_sort_id']),
            reverse=True
        )
        incomplete_talks = sorted(
            incomplete_talks,
            key=lambda item: (item['_sort_date'], item['_sort_id']),
            reverse=True
        )

        for item in completed_talks + incomplete_talks:
            item.pop('_sort_date', None)
            item.pop('_sort_id', None)

        return JsonResponse({
            'success': True,
            'person_name': person_name,
            'employer_name': employer_name,
            'management_sub_id': management_sub_id,
            'has_access_to_toolbox': has_access_to_toolbox,
            'completed_talks': completed_talks,
            'incomplete_talks': incomplete_talks,
        })
    elif person_type == 'subcontractor':
        subcontractor = get_object_or_404(
            Subcontractors,
            id=person_id,
            is_toolbox_required=True
        )

        person_name = "Subcontractor"
        employer_name = subcontractor.company
        has_access_to_toolbox = True
        management_sub_id = subcontractor.id

        sub_items = sub_toolbox.get_subcontractor_items_before(
            timezone.localdate() + timedelta(days=1)
        )

        def job_item_to_talk_dict(item):
            return {
                'id': item["scheduled"].id,
                'title': item["title"],
                'date': item["date"].strftime('%m/%d/%Y') if item["date"] else '',
                'notes': f"Job: {item['job'].job_name}" if item.get("job") else '',
                '_sort_date': item["date"] or date.min,
                '_sort_id': item["scheduled"].id,
            }

        completed_talks = [
            job_item_to_talk_dict(item)
            for item in sub_items["completed"]
            if (
                item["type"] == "subcontractor_job" and
                item["subcontractor"].id == subcontractor.id
            )
        ]
        incomplete_talks = [
            job_item_to_talk_dict(item)
            for item in sub_items["missing"]
            if (
                item["type"] == "subcontractor_job" and
                item["subcontractor"].id == subcontractor.id
            )
        ]

        completed_talks = sorted(
            completed_talks,
            key=lambda item: (item['_sort_date'], item['_sort_id']),
            reverse=True
        )
        incomplete_talks = sorted(
            incomplete_talks,
            key=lambda item: (item['_sort_date'], item['_sort_id']),
            reverse=True
        )

        for item in completed_talks + incomplete_talks:
            item.pop('_sort_date', None)
            item.pop('_sort_id', None)

        return JsonResponse({
            'success': True,
            'person_name': person_name,
            'employer_name': employer_name,
            'management_sub_id': management_sub_id,
            'has_access_to_toolbox': has_access_to_toolbox,
            'completed_talks': completed_talks,
            'incomplete_talks': incomplete_talks,
        })


    else:
        return JsonResponse({
            'success': False,
            'error': 'Invalid person type.'
        }, status=400)

    assigned_talks = list(
        ScheduledToolboxTalks.objects
        .filter(id__in=assigned_ids - excused_ids)
        .select_related('master')
        .order_by('-date', '-id')
    )

    completed_talks = []
    incomplete_talks = []

    for talk in assigned_talks:
        talk_dict = {
            'id': talk.id,
            'title': _get_talk_title(talk),
            'date': talk.date.strftime('%m/%d/%Y') if talk.date else '',
            'notes': talk.notes or '',
        }

        if talk.id in completed_ids:
            completed_talks.append(talk_dict)
        else:
            incomplete_talks.append(talk_dict)

    return JsonResponse({
        'success': True,
        'person_name': person_name,
        'employer_name': employer_name,
        'management_sub_id': management_sub_id,
        'has_access_to_toolbox': has_access_to_toolbox,
        'completed_talks': completed_talks,
        'incomplete_talks': incomplete_talks,
    })

def view_respirator_certification(request,id):
    send_data = {}
    selected_cert = Certifications.objects.get(id=id)
    selected_respirator_cert = RespiratorClearance.objects.get(certification=selected_cert)
    if request.method == 'POST':
        if 'delete_clearance' in request.POST:
            if selected_respirator_cert.date_completed:
                messages.error(request, "Completed respirator clearances cannot be deleted.")
                return redirect('view_respirator_certification', id=selected_cert.id)

            with transaction.atomic():
                CertificationNotes.objects.filter(certification=selected_cert).delete()
                CertificationActionRequired.objects.filter(main=selected_cert).delete()
                EmployeePendingActions.objects.filter(certification=selected_cert).delete()
                selected_respirator_cert.delete()
                selected_cert.delete()
            messages.success(request, "Respirator clearance deleted.")
            return redirect('safety_home')

        if 'note' in request.POST:
            CertificationNotes.objects.create(certification=selected_cert,date=date.today(), user=Employees.objects.get(user=request.user), note=request.POST['note'])
        elif 'change_expiration_date' in request.POST:
            old_expiration_date = selected_cert.date_expires
            new_expiration_date = request.POST.get('expiration_date')

            selected_cert.date_expires = new_expiration_date
            selected_cert.save()

            CertificationNotes.objects.create(
                certification=selected_cert,
                date=date.today(),
                user=Employees.objects.get(user=request.user),
                note=(
                        "Expiration date changed from "
                        + (old_expiration_date.strftime("%m/%d/%Y") if old_expiration_date else "None")
                        + " to "
                        + new_expiration_date
                )
            )

            return redirect('view_respirator_certification', id=selected_cert.id)
        else:
            if request.POST['submit_status'] == 'Approved':
                selected_cert.date_received = date.today()
                selected_cert.date_expires = date.today() + relativedelta(years=1)
                selected_cert.save()
                CertificationActionRequired.objects.filter(main=selected_cert,action="Waiting for Safety Director").delete()
                selected_respirator_cert.approved_for_use = True
                selected_respirator_cert.date_approved = date.today()
                current_user_employee = Employees.objects.get(user=request.user)
                _close_previous_employee_respirator_certifications(
                    selected_cert.employee,
                    selected_cert,
                    current_user_employee,
                )
                if request.POST['is_physician_required'] == 'Yes':
                    selected_respirator_cert.is_physician_actually_required = True
                    selected_respirator_cert.physician_approved = True
                else:
                    selected_respirator_cert.is_physician_actually_required = False
                    selected_respirator_cert.physician_approved = False
                CertificationNotes.objects.create(certification=selected_cert, date=date.today(),
                                                  user=current_user_employee,
                                                  note="Approved for Respirator Use")
            else:
                if request.POST['is_physician_required'] == 'No':
                    selected_respirator_cert.is_physician_actually_required = False
                if request.POST['is_physician_required'] == 'Yes':
                    selected_respirator_cert.is_physician_actually_required = True
                CertificationNotes.objects.create(certification=selected_cert, date=date.today(),
                                                  user=Employees.objects.get(user=request.user),
                                                  note="Not Approved Yet. Physician Required? - " + request.POST['is_physician_required'] + ". Physician Approved? - " + request.POST['physician_approved'])
            selected_respirator_cert.save()
            return redirect('certifications', id='ALL')
    if selected_respirator_cert.approved_for_use:
        send_data['approved_for_use'] = 'True'
    send_data['certification'] = selected_respirator_cert
    send_data['selected_cert'] = selected_cert
    send_data['certification_id'] = selected_cert.id
    send_data['notes'] = CertificationNotes.objects.filter(certification=selected_cert)

    respirator_sections = [
        ("Section 1", RespiratorClearance1.objects.filter(main=selected_respirator_cert).exists()),
        ("Section 2", RespiratorClearance2.objects.filter(main=selected_respirator_cert).exists()),
        ("Section 3", RespiratorClearance3.objects.filter(main=selected_respirator_cert).exists()),
        ("Section 4", RespiratorClearance4.objects.filter(main=selected_respirator_cert).exists()),
        ("Section 5", RespiratorClearance5.objects.filter(main=selected_respirator_cert).exists()),
        ("Section 6", RespiratorClearance6.objects.filter(main=selected_respirator_cert).exists()),
    ]

    sections_completed = sum(1 for section_name, is_complete in respirator_sections if is_complete)
    total_sections = len(respirator_sections)

    send_data["respirator_sections"] = respirator_sections
    send_data["sections_completed"] = sections_completed
    send_data["total_sections"] = total_sections

    if not selected_respirator_cert.date_completed:
        send_data['not_completed_yet']=True
        #return redirect('certifications', id='ALL')
    return render(request, 'view_respirator_certification.html', send_data)

def delete_employee(request,id):
    deleted_employee = Employees.objects.get(id=id)
    if deleted_employee.active:
        deleted_employee.active=False
    else:
        deleted_employee.active = True
        deleted_employee.date_added = date.today()
    deleted_employee.save()
    return redirect('employees_home')

def upload_employees(request):
    if request.method == "POST":
        form = EmployeeUploadForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES["excel_file"]

            wb = openpyxl.load_workbook(excel_file)
            sheet = wb.active

            created = 0
            skipped = 0

            with transaction.atomic():
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    (
                        employee_number,
                        active,
                        first_name,
                        middle_name,
                        last_name,
                        phone,
                        email,
                        level_name,
                        nickname,
                        job_title,
                        employer,
                        pin,
                        date_added,
                        birth_date,
                        gender,
                        height,
                        weight,
                    ) = row

                    # REQUIRED FIELDS CHECK
                    if not first_name or not last_name or not employer:
                        skipped += 1
                        continue

                    # Resolve Foreign Keys safely
                    level = None
                    if level_name:
                        level = EmployeeLevels.objects.filter(name=level_name).first()

                    # job_title = None
                    # if job_title_name:
                    #     job_title = EmployeeTitles.objects.filter(description=job_title_name).first()

                    Employees.objects.create(
                        employee_number=employee_number or 0,
                        active=bool(active) if active is not None else True,
                        first_name=first_name,
                        middle_name=middle_name,
                        last_name=last_name,
                        phone=phone,
                        email=email,
                        level=level,
                        nickname=nickname,
                        job_title=EmployeeTitles.objects.get(id=job_title),
                        employment_company=Employers.objects.get(id=employer),
                        pin=pin,
                        date_added=date_added if isinstance(date_added, datetime) else datetime.today(),
                        birth_date=birth_date if isinstance(birth_date, datetime) else None,
                        gender=gender if gender in ["Male", "Female", "Unassigned"] else "Select",
                        height=height,
                        weight=weight,
                    )

                    created += 1

            messages.success(
                request,
                f"Employees imported: {created}. Rows skipped: {skipped}."
            )
            return redirect("employees_home")

    else:
        form = EmployeeUploadForm()

    return render(request, "upload_employees.html", {"form": form})



@login_required
@transaction.atomic
def toolbox_talk_assign(request):
    toolbox_talks = ToolboxTalks.objects.all().order_by('description')

    painters = Employees.objects.filter(
        active=True,
        job_title__description__in=[
            "Painter",
            "Warehouse",
            "Superintendent"
        ]
    ).order_by('last_name', 'first_name')

    subcontractors = Subcontractors.objects.filter(
        is_inactive=False,
        is_toolbox_required=True
    ).order_by('company')

    jobs = Jobs.objects.filter(
        is_closed=False,
        is_active=True,
        is_labor_done=False
    ).order_by('job_number')

    context = {
        'toolbox_talks': toolbox_talks,
        'painters': painters,
        'subcontractors': subcontractors,
        'jobs': jobs,
        'today': date.today(),
        'selected_master_id':request.GET.get('master_id'),
    }

    def create_custom_toolbox_folders(scheduled_obj):
        base_path = f"custom_toolbox_talks/{scheduled_obj.id}"
        createfolder(base_path)
        createfolder(f"{base_path}/English")
        createfolder(f"{base_path}/Spanish")

    if request.method == 'POST':
        talk_source = request.POST.get('talk_source')
        schedule_mode = request.POST.get('schedule_mode')
        assignment_type = request.POST.get('assignment_type')

        existing_talk_id = request.POST.get('existing_talk_id')
        custom_description = request.POST.get('custom_description', '').strip()
        custom_date_raw = request.POST.get('custom_date')

        employee_ids = request.POST.getlist('employee_ids')
        sub_employee_ids = request.POST.getlist('sub_employee_ids')
        sub_job_id = request.POST.get('sub_job_ids')

        job_number = request.POST.get('job_number')
        subcontractor_employee_id = request.POST.get('subcontractor_employee_id')
        subcontractor_job_id = request.POST.get('subcontractor_job_id')

        job_subcontractor_ids = request.POST.getlist('job_subcontractor_ids')

        selected_master = None
        selected_description = None

        # -----------------------------
        # Validate talk selection
        # -----------------------------
        if talk_source == 'existing':
            if not existing_talk_id:
                messages.error(request, 'Please select an existing Toolbox Talk.')
                return render(request, 'toolbox_talk_assign.html', context)

            try:
                selected_master = ToolboxTalks.objects.get(id=existing_talk_id)
            except ToolboxTalks.DoesNotExist:
                messages.error(request, 'Selected Toolbox Talk could not be found.')
                return render(request, 'toolbox_talk_assign.html', context)

        elif talk_source == 'custom':
            if not custom_description:
                messages.error(request, 'Please enter a custom Toolbox Talk description.')
                return render(request, 'toolbox_talk_assign.html', context)
            selected_description = custom_description

        else:
            messages.error(request, 'Please choose an existing Toolbox Talk or enter a custom one.')
            return render(request, 'toolbox_talk_assign.html', context)

        # -----------------------------
        # Scheduling method: Replace next scheduled talk for all employees
        # -----------------------------
        if schedule_mode == 'replace_next':
            next_scheduled = ScheduledToolboxTalks.objects.filter(
                date__gte=date.today(),
                is_all_employees=True,
            ).order_by('date', 'id').first()

            if next_scheduled:
                next_date = next_scheduled.date

                future_talks = ScheduledToolboxTalks.objects.filter(
                    date__gte=next_date,
                    is_all_employees=True,
                ).order_by('-date', '-id')

                for talk in future_talks:
                    talk.date = talk.date + timedelta(days=7)
                    talk.save()

                new_scheduled = ScheduledToolboxTalks.objects.create(
                    master=selected_master,
                    description=selected_description if selected_master is None else None,
                    date=next_date,
                    is_all_employees=True,
                    notes="All Employees"
                )

            else:
                fallback_date = date.today()
                new_scheduled = ScheduledToolboxTalks.objects.create(
                    master=selected_master,
                    description=selected_description if selected_master is None else None,
                    date=fallback_date,
                    is_all_employees=True,
                    notes="All Employees"
                )


            if selected_master is None:
                create_custom_toolbox_folders(new_scheduled)

            messages.success(request, 'Toolbox Talk created successfully.')
            return redirect('safety_home')

        # -----------------------------
        # Scheduling method: Add to end of schedule for all employees
        # -----------------------------
        if schedule_mode == 'add_to_end_all':
            latest_scheduled = ScheduledToolboxTalks.objects.filter(is_all_employees=True,date__gte=date.today()).order_by('-date', '-id').first()

            if latest_scheduled and latest_scheduled.date:
                scheduled_date = latest_scheduled.date + timedelta(days=7)
            else:
                scheduled_date = date.today()

            new_scheduled = ScheduledToolboxTalks.objects.create(
                master=selected_master,
                description=selected_description if selected_master is None else None,
                date=scheduled_date,
                is_all_employees=True,
                notes="All Employees"
            )

            if selected_master is None:
                create_custom_toolbox_folders(new_scheduled)

            messages.success(request, 'Toolbox Talk added to the end of the schedule for all employees.')
            return redirect('safety_home')

        # -----------------------------
        # All other options require custom date
        # -----------------------------
        if schedule_mode != 'custom_date':
            messages.error(request, 'Please choose a scheduling option.')
            return render(request, 'toolbox_talk_assign.html', context)

        if not custom_date_raw:
            messages.error(request, 'Please choose a date.')
            return render(request, 'toolbox_talk_assign.html', context)

        try:
            scheduled_date = date.fromisoformat(custom_date_raw)
        except ValueError:
            messages.error(request, 'Invalid date.')
            return render(request, 'toolbox_talk_assign.html', context)

        is_all_employees = assignment_type == 'all_employees'

        scheduled = ScheduledToolboxTalks.objects.create(
            master=selected_master,
            description=selected_description if selected_master is None else None,
            date=scheduled_date,
            is_all_employees=is_all_employees
        )

        if selected_master is None:
            create_custom_toolbox_folders(scheduled)

        # -----------------------------
        # Assignment type: All Employees
        # -----------------------------
        if assignment_type == 'all_employees':
            scheduled.notes = (
                "All Employees"
                if selected_master else
                "Custom -All Employees"
            )
            scheduled.save()

            messages.success(request, 'Toolbox Talk assigned to all employees.')
            return redirect('safety_home')

        # -----------------------------
        # Assignment type: Employees
        # -----------------------------
        elif assignment_type == 'employees':
            if not employee_ids:
                scheduled.delete()
                messages.error(request, 'Please select at least one employee.')
                return render(request, 'toolbox_talk_assign.html', context)

            valid_employees = Employees.objects.filter(
                id__in=employee_ids,
                active=True,
                job_title__description__in=[
                    "Painter",
                    "Warehouse",
                    "Superintendent"
                ]
            )

            ScheduledToolboxTalkEmployees.objects.bulk_create([
                ScheduledToolboxTalkEmployees(
                    scheduled=scheduled,
                    employee=emp
                )
                for emp in valid_employees
            ])

            scheduled.notes = (
                "Certain Employees"
                if selected_master else
                "Custom-Certain Employees"
            )
            scheduled.save()

            messages.success(request, 'Toolbox Talk assigned to selected employees.')
            return redirect('safety_home')

        # -----------------------------
        # Assignment type: Job
        # -----------------------------
        elif assignment_type == 'job':
            if not job_number:
                scheduled.delete()
                messages.error(request, 'Please select a job.')
                return render(request, 'toolbox_talk_assign.html', context)

            selected_employees = Employees.objects.filter(
                id__in=employee_ids,
                active=True,
                job_title__description__in=[
                    "Painter",
                    "Warehouse",
                    "Superintendent"
                ]
            )

            selected_subcontracts = Subcontracts.objects.filter(
                job_number_id=job_number,
                subcontractor_id__in=job_subcontractor_ids,
                is_closed=False,
                subcontractor__is_toolbox_required=True,
                job_number__is_closed=False,
                job_number__is_active=True,
                job_number__is_labor_done=False,
                subcontractor__is_inactive=False
            ).select_related('subcontractor', 'job_number')

            if not selected_employees.exists() and not selected_subcontracts.exists():
                scheduled.delete()
                messages.error(request, 'Please select at least one employee or subcontractor.')
                return render(request, 'toolbox_talk_assign.html', context)

            ScheduledToolboxTalkEmployees.objects.bulk_create([
                ScheduledToolboxTalkEmployees(
                    scheduled=scheduled,
                    employee=emp,
                    job_id=job_number
                )
                for emp in selected_employees
            ])

            ScheduledToolboxTalkSubJobs.objects.bulk_create([
                ScheduledToolboxTalkSubJobs(
                    scheduled=scheduled,
                    job=subcontract.job_number,
                    subcontractor=subcontract.subcontractor
                )
                for subcontract in selected_subcontracts
            ])

            job_obj = Jobs.objects.filter(job_number=job_number).first()
            job_label = f"{job_obj.job_number}" if job_obj else str(job_number)

            scheduled.notes = (
                f"For Job {job_label}"
                if selected_master else
                f"Custom-For Job {job_label}"
            )
            scheduled.save()

            messages.success(request, 'Toolbox Talk assigned to selected job employees/subcontractors.')
            return redirect('safety_home')

        # -----------------------------
        # Assignment type: Subcontractor Employees
        # -----------------------------
        elif assignment_type == 'sub_employees':
            if not subcontractor_employee_id:
                scheduled.delete()
                messages.error(request, 'Please choose a subcontractor.')
                return render(request, 'toolbox_talk_assign.html', context)

            if not sub_employee_ids:
                scheduled.delete()
                messages.error(request, 'Please select at least one subcontractor employee.')
                return render(request, 'toolbox_talk_assign.html', context)

            valid_sub_employees = Subcontractor_Employees.objects.filter(
                id__in=sub_employee_ids,
                subcontractor_id=subcontractor_employee_id,
                is_active=True,
                has_access_to_toolbox=True,
                subcontractor__is_toolbox_required=True
            )

            ScheduledToolboxTalkSubEmployees.objects.bulk_create([
                ScheduledToolboxTalkSubEmployees(
                    scheduled=scheduled,
                    employee=emp,
                    job=None
                )
                for emp in valid_sub_employees
            ])

            sub = Subcontractors.objects.filter(id=subcontractor_employee_id).first()
            company = sub.company if sub else "Unknown Subcontractor"

            scheduled.notes = (
                f"Assigned to {company}"
                if selected_master else
                f"Custom-Assigned to {company}"
            )
            scheduled.save()

            messages.success(request, 'Toolbox Talk assigned to selected subcontractor employees.')
            return redirect('safety_home')

        # -----------------------------
        # Assignment type: Subcontractor Jobs
        # -----------------------------
        elif assignment_type == 'sub_jobs':
            if not subcontractor_job_id:
                scheduled.delete()
                messages.error(request, 'Please choose a subcontractor.')
                return render(request, 'toolbox_talk_assign.html', context)

            if not sub_job_id:
                scheduled.delete()
                messages.error(request, 'Please select at least one subcontractor job.')
                return render(request, 'toolbox_talk_assign.html', context)

            valid_job_ids = Subcontracts.objects.filter(
                    subcontractor_id=subcontractor_job_id,
                    is_closed=False,
                    subcontractor__is_toolbox_required=True,
                    job_number__is_closed=False,
                    job_number__is_active=True,
                    job_number__is_labor_done=False,
                    job_number=sub_job_id
                ).values_list('job_number', flat=True).distinct()


            if not valid_job_ids:
                scheduled.delete()
                messages.error(request, 'No valid open jobs were found for that subcontractor.')
                return render(request, 'toolbox_talk_assign.html', context)

            assignments = Subcontractor_Job_Assignments.objects.filter(
                job_id__in=valid_job_ids,
                employee__subcontractor_id=subcontractor_job_id,
                employee__is_active=True,
                employee__has_access_to_toolbox=True
            ).select_related('employee', 'job')

            create_rows = []
            seen = set()

            for assignment in assignments:
                key = (scheduled.id, assignment.employee.id, assignment.job.pk)
                if key in seen:
                    continue
                seen.add(key)

                create_rows.append(
                    ScheduledToolboxTalkSubEmployees(
                        scheduled=scheduled,
                        employee=assignment.employee,
                        job=assignment.job
                    )
                )

            if not create_rows:
                scheduled.delete()
                messages.error(request, 'No active subcontractor employees were assigned to the selected job(s).')
                return render(request, 'toolbox_talk_assign.html', context)

            ScheduledToolboxTalkSubEmployees.objects.bulk_create(create_rows)

            sub = Subcontractors.objects.filter(id=subcontractor_job_id).first()
            company = sub.company if sub else "Unknown Subcontractor"

            job_list = ", ".join(str(x) for x in valid_job_ids[:5])
            if len(valid_job_ids) > 5:
                job_list += "..."

            scheduled.notes = (
                f"For job {job_list}"
                if selected_master else
                f"Custom-for job {job_list}"
            )
            scheduled.save()

            messages.success(request, 'Toolbox Talk assigned to subcontractor employees on the selected job(s).')
            return redirect('safety_home')

        else:
            scheduled.delete()
            messages.error(request, 'Please select an assignment type.')
            return render(request, 'toolbox_talk_assign.html', context)

    return render(request, 'toolbox_talk_assign.html', context)


@login_required
@require_GET
def ajax_subcontractor_employees(request):
    subcontractor_id = request.GET.get('subcontractor_id')

    results = []
    if subcontractor_id:
        employees = Subcontractor_Employees.objects.filter(
            subcontractor_id=subcontractor_id,
            is_active=True,
            has_access_to_toolbox=True,
            subcontractor__is_toolbox_required=True
        ).order_by('name')

        results = [
            {
                'id': x.id,
                'name': x.name or f'Employee #{x.id}'
            }
            for x in employees
        ]

    return JsonResponse({'results': results})


@require_GET
def ajax_subcontractor_jobs(request):
    subcontractor_id = request.GET.get('subcontractor_id')

    results = []
    if subcontractor_id:
        rows = Subcontracts.objects.filter(
            subcontractor_id=subcontractor_id,
            is_closed=False,
            subcontractor__is_toolbox_required=True,
            job_number__is_closed=False,
            job_number__is_active=True,
            job_number__is_labor_done=False
        ).select_related('job_number').order_by(
            'job_number__job_number'
        ).distinct()

        seen = set()
        for row in rows:
            job = row.job_number
            if job.pk in seen:
                continue
            seen.add(job.pk)

            results.append({
                'id': job.job_number,
                'label': f'{job.job_number} - {job.job_name}'
            })

    return JsonResponse({'results': results})


def participation_ajax(request):
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        if 'scheduled_toolbox_talk_id' not in request.GET:
            return HttpResponse(
                json.dumps({'error': 'Missing scheduled_toolbox_talk_id'}),
                content_type='application/json',
                status=400
            )

        send_data = {}

        x = ScheduledToolboxTalks.objects.get(id=request.GET['scheduled_toolbox_talk_id'])

        incomplete_people = []
        completed_people = []
        people = []
        assignment_type = ""
        job_info = ""

        description = x.master.description if x.master else (x.description or "Custom Toolbox Talk")

        def group_toolbox_held_by_text(completed_toolbox_talk):
            group_link = GroupToolboxTalkCompletedToolboxTalks.objects.filter(
                completed_toolbox_talk=completed_toolbox_talk
            ).select_related(
                'group_toolbox_talk__Foreman',
                'group_toolbox_talk__job'
            ).order_by(
                '-group_toolbox_talk__date_completed',
                '-group_toolbox_talk_id'
            ).first()

            if not group_link:
                return ""

            group_talk = group_link.group_toolbox_talk
            foreman = group_talk.Foreman
            held_by = f"Held by {foreman.first_name} {foreman.last_name}"

            if group_talk.job:
                held_by += f" Job {group_talk.job.job_number}"

            return held_by

        employee_assignments = ScheduledToolboxTalkEmployees.objects.filter(
            scheduled=x
        ).select_related('employee', 'job')

        sub_assignments = ScheduledToolboxTalkSubEmployees.objects.filter(
            scheduled=x,
            employee__subcontractor__is_toolbox_required=True
        ).select_related('employee', 'employee__subcontractor', 'job')

        sub_job_assignments = ScheduledToolboxTalkSubJobs.objects.filter(
            scheduled=x,
            subcontractor__is_toolbox_required=True
        ).select_related('subcontractor', 'job')

        # Build job info for header
        sub_job = sub_assignments.exclude(job__isnull=True).first()
        emp_job = employee_assignments.exclude(job__isnull=True).first()

        if sub_job and sub_job.job:
            job_info = f"{sub_job.job.job_number} {sub_job.job.job_name}"
        elif emp_job and emp_job.job:
            job_info = f"{emp_job.job.job_number} {emp_job.job.job_name}"
        has_assignment = False
        # Certain regular employees
        if employee_assignments.exists():
            has_assignment = True
            jobs_used = employee_assignments.exclude(job__isnull=True)

            if jobs_used.exists():
                assignment_type = "Assigned by Job"
            else:
                assignment_type = "Certain Employees"

            for row in employee_assignments:
                y = row.employee

                if _has_excused_employee_toolbox_talk(y, x):
                    continue

                completed = CompletedToolboxTalks.objects.filter(
                    master=x,
                    employee=y,
                    is_excused=False
                ).order_by('-date').first()

                label = f"{y.first_name} {y.last_name}"

                if completed:
                    completed_people.append({
                        'name': label,
                        'held_by': group_toolbox_held_by_text(completed),
                        'completed_date': completed.date.strftime('%m/%d/%y') if completed.date else ""
                    })
                else:
                    incomplete_people.append({
                        'name': label
                    })

        # Subcontractor employees / jobs
        if sub_assignments.exists():
            has_assignment = True
            jobs_used = sub_assignments.exclude(job__isnull=True)

            if jobs_used.exists():
                assignment_type = "Subcontractor Job Assignment"
            else:
                assignment_type = "Subcontractor Employees"

            for row in sub_assignments:
                y = row.employee
                if not y.has_access_to_toolbox:
                    continue

                if not row.job:
                    continue

                if not _is_active_toolbox_job(row.job):
                    continue

                if not _sub_employee_has_active_toolbox_job(y, row.job):
                    continue

                if _has_excused_subcontractor_toolbox_talk(y, x, row.job):
                    continue

                completed_date = _get_sub_employee_toolbox_completion_date(
                    y,
                    x,
                    row.job
                )

                label = y.name or f"Employee #{y.id}"

                if completed_date:
                    completed_people.append({
                        'company': y.subcontractor.company if y.subcontractor else '',
                        'job': row.job.job_name,
                        'name': label,
                        'completed_date': completed_date.strftime('%m/%d/%y')
                    })
                else:
                    incomplete_people.append({
                        'company': y.subcontractor.company if y.subcontractor else '',
                        'job': row.job.job_name,
                        'name': label
                    })

        if sub_job_assignments.exists():
            has_assignment = True
            assignment_type = "Subcontractor Job Assignment"

            for row in sub_job_assignments:
                if not _is_active_toolbox_job(row.job):
                    continue

                subcontract = Subcontracts.objects.filter(
                    subcontractor=row.subcontractor,
                    job_number=row.job,
                    is_closed=False,
                    subcontractor__is_toolbox_required=True,
                    job_number__is_closed=False,
                    job_number__is_active=True,
                    job_number__is_labor_done=False
                ).first()

                if not subcontract:
                    continue

                delegation_exists = _subcontract_has_delegated_employee_for_date(
                    subcontract,
                    x.date
                )

                if delegation_exists:
                    assigned_employee_ids = Subcontractor_Job_Assignments.objects.filter(
                        job=row.job,
                        employee__subcontractor=row.subcontractor,
                        employee__is_active=True,
                        employee__has_access_to_toolbox=True
                    ).values_list('employee_id', flat=True).distinct()

                    delegated_employees = Subcontractor_Employees.objects.filter(
                        id__in=assigned_employee_ids
                    ).order_by('name')

                    for sub_emp in delegated_employees:
                        if not sub_emp.date_enrolled or sub_emp.date_enrolled > x.date:
                            continue

                        if _has_excused_subcontractor_toolbox_talk(sub_emp, x, row.job):
                            continue

                        completed_date = _get_sub_employee_toolbox_completion_date(
                            sub_emp,
                            x,
                            row.job
                        )

                        if completed_date:
                            completed_people.append({
                                'company': row.subcontractor.company,
                                'job': row.job.job_name,
                                'name': sub_emp.name,
                                'completed_date': completed_date.strftime('%m/%d/%Y')
                            })
                        else:
                            people.append({
                                'company': row.subcontractor.company,
                                'job': row.job.job_name,
                                'name': sub_emp.name,
                            })

                else:
                    if _has_excused_subcontractor_job_toolbox_talk(x, row.subcontractor, row.job):
                        continue

                    completed = CompletedSubToolboxJobTalks.objects.filter(
                        scheduled=x,
                        subcontractor=row.subcontractor,
                        job=row.job,
                        is_excused=False
                    ).order_by('-date').first()

                    if completed:
                        completed_people.append({
                            'company': row.subcontractor.company,
                            'job': row.job.job_name,
                            'completed_date': completed.date.strftime('%m/%d/%Y') if completed.date else ''
                        })
                    else:
                        people.append({
                            'company': row.subcontractor.company,
                            'job': row.job.job_name,
                        })

        # All employees
        if x.is_all_employees:
            has_assignment = True
            assignment_type = "All Employees"

            # 1. Gerloff employees
            target_employees = Employees.objects.filter(
                active=True,
                date_added__lte=x.date,
                job_title__description__in=[
                    "Painter",
                    "Warehouse",
                    "Superintendent"
                ]
            ).order_by('last_name', 'first_name')

            for emp in target_employees:
                if _has_excused_employee_toolbox_talk(emp, x):
                    continue

                completed = CompletedToolboxTalks.objects.filter(
                    master=x,
                    employee=emp,
                    is_excused=False
                ).order_by('-date').first()

                label = f"{emp.first_name} {emp.last_name}"

                if completed:
                    completed_people.append({
                        'name': label,
                        'held_by': group_toolbox_held_by_text(completed),
                        'completed_date': completed.date.strftime('%m/%d/%y') if completed.date else ""
                    })
                else:
                    people.append({
                        'name': label
                    })

            # 2. Required subcontractors
            required_subcontracts = Subcontracts.objects.filter(
                is_closed=False,
                subcontractor__is_toolbox_required=True,
                job_number__is_closed=False,
                job_number__is_active=True,
                job_number__is_labor_done=False,
            ).select_related(
                'subcontractor',
                'job_number'
            )

            for subcontract in required_subcontracts:
                first_invoice_date = _get_first_subcontractor_invoice_date(subcontract)
                if not first_invoice_date or x.date <= first_invoice_date:
                    continue

                delegation_exists = _subcontract_has_delegated_employee_for_date(
                    subcontract,
                    x.date
                )

                if delegation_exists:
                    assigned_employee_ids = Subcontractor_Job_Assignments.objects.filter(
                        job=subcontract.job_number,
                        employee__subcontractor=subcontract.subcontractor,
                        employee__is_active=True,
                        employee__has_access_to_toolbox=True
                    ).values_list('employee_id', flat=True).distinct()

                    delegated_employees = Subcontractor_Employees.objects.filter(
                        id__in=assigned_employee_ids
                    ).order_by('name')

                    for sub_emp in delegated_employees:
                        if not sub_emp.date_enrolled or sub_emp.date_enrolled > x.date:
                            continue

                        if _has_excused_subcontractor_toolbox_talk(sub_emp, x, subcontract.job_number):
                            continue

                        completed_date = _get_sub_employee_toolbox_completion_date(
                            sub_emp,
                            x,
                            subcontract.job_number
                        )

                        if completed_date:
                            completed_people.append({
                                'company': subcontract.subcontractor.company,
                                'job': subcontract.job_number.job_name,
                                'name': sub_emp.name,
                                'completed_date': completed_date.strftime('%m/%d/%Y')
                            })
                        else:
                            people.append({
                                'company': subcontract.subcontractor.company,
                                'job': subcontract.job_number.job_name,
                                'name': sub_emp.name,
                            })

                else:
                    if _has_excused_subcontractor_job_toolbox_talk(
                        x,
                        subcontract.subcontractor,
                        subcontract.job_number
                    ):
                        continue

                    completed = CompletedSubToolboxJobTalks.objects.filter(
                        scheduled=x,
                        subcontractor=subcontract.subcontractor,
                        job=subcontract.job_number,
                        is_excused=False
                    ).order_by('-date').first()

                    if completed:
                        completed_people.append({
                            'company': subcontract.subcontractor.company,
                            'job': subcontract.job_number.job_name,
                            'completed_date': completed.date.strftime('%m/%d/%Y') if completed.date else ''
                        })
                    else:
                        people.append({
                            'company': subcontract.subcontractor.company,
                            'job': subcontract.job_number.job_name,
                        })
        if not has_assignment:
            assignment_type = "Unassigned"

        subcontractor_items = sub_toolbox.get_scheduled_talk_subcontractor_items(x)

        incomplete_people = [
            row for row in incomplete_people
            if not row.get('company')
        ]
        people = [
            row for row in people
            if not row.get('company')
        ]
        completed_people = [
            row for row in completed_people
            if not row.get('company')
        ]

        for item in subcontractor_items["missing"]:
            if item["type"] == "subcontractor_employee":
                people.append({
                    'company': item["subcontractor"].company,
                    'name': item["employee"].name,
                })
            else:
                people.append({
                    'company': item["subcontractor"].company,
                    'job': item["job"].job_name,
                })

        for item in subcontractor_items["completed"]:
            if item["type"] == "subcontractor_employee":
                completed_people.append({
                    'company': item["subcontractor"].company,
                    'name': item["employee"].name,
                })
            else:
                completed_people.append({
                    'company': item["subcontractor"].company,
                    'job': item["job"].job_name,
                })

        def dedupe_subcontractor_employee_rows(missing_rows, completed_rows):
            missing_keys = set()
            deduped_missing = []
            seen_missing = set()

            for row in missing_rows:
                if row.get('company') and row.get('name'):
                    key = (row.get('company'), row.get('name'))
                    missing_keys.add(key)
                    if key in seen_missing:
                        continue
                    seen_missing.add(key)
                    deduped_missing.append({
                        'company': row.get('company'),
                        'name': row.get('name'),
                    })
                else:
                    deduped_missing.append(row)

            deduped_completed = []
            seen_completed = set()

            for row in completed_rows:
                if row.get('company') and row.get('name'):
                    key = (row.get('company'), row.get('name'))
                    if key in missing_keys or key in seen_completed:
                        continue
                    seen_completed.add(key)
                    deduped_completed.append({
                        'company': row.get('company'),
                        'name': row.get('name'),
                        'completed_date': row.get('completed_date', ''),
                    })
                else:
                    deduped_completed.append(row)

            return deduped_missing, deduped_completed

        people, completed_people = dedupe_subcontractor_employee_rows(
            incomplete_people + people,
            completed_people
        )
        incomplete_people = []

        def sort_toolbox_person(row):
            company = row.get('company', '')
            job = row.get('job', '')
            name = row.get('name', '')
            return f"{company} {job} {name}".lower()

        incomplete_people = sorted(
            incomplete_people,
            key=sort_toolbox_person
        )

        people = sorted(
            people,
            key=sort_toolbox_person
        )

        completed_people = sorted(
            completed_people,
            key=sort_toolbox_person
        )

        send_data['assignment_type'] = assignment_type
        send_data['description'] = description
        send_data['date'] = x.date.strftime('%Y-%m-%d') if x.date else ""
        send_data['job_info'] = job_info
        send_data['people'] = people
        send_data['completed_people'] = completed_people
        send_data['english_file'] = get_uploaded_toolbox_file(x, "English")
        send_data['spanish_file'] = get_uploaded_toolbox_file(x, "Spanish")

        return HttpResponse(json.dumps(send_data), content_type='application/json')

@login_required(login_url='/accounts/login')
def upload_master_toolbox_file(request):
    if request.method == 'POST':
        fileitem = request.FILES.get('upload_file')
        language = request.POST.get('language')
        toolbox_id = request.POST.get('toolbox_id')

        if not toolbox_id:
            messages.error(request, 'No toolbox talk was selected.')
            return redirect('toolbox_talks_master')

        if not fileitem:
            messages.error(request, 'Please choose a file to upload.')
            return redirect('toolbox_talks_master')

        toolbox = ToolboxTalks.objects.get(id=toolbox_id)

        folder_name = "English" if language == "English" else "Spanish"

        abs_path = os.path.join(
            settings.MEDIA_ROOT,
            "toolbox_talks",
            str(toolbox.id),
            folder_name
        )

        os.makedirs(abs_path, exist_ok=True)

        for f in os.listdir(abs_path):
            os.remove(os.path.join(abs_path, f))

        fn = os.path.basename(fileitem.name)
        filepath = os.path.join(abs_path, fn)

        with open(filepath, 'wb') as f:
            f.write(fileitem.read())

        messages.success(request, f'{language} file uploaded.')

        return redirect('toolbox_talks_master')

    return redirect('toolbox_talks_master')


def upload_toolbox_file(request):
    if request.method == 'POST':
        fileitem = request.FILES.get('upload_file')
        language = request.POST.get('language')
        scheduled_id = request.POST.get('scheduled_id')

        if not scheduled_id:
            messages.error(request, 'No scheduled toolbox talk was selected.')
            return redirect('scheduled_toolbox_talks')

        if not fileitem:
            messages.error(request, 'Please choose a file to upload.')
            return redirect('scheduled_toolbox_talks')

        scheduled = ScheduledToolboxTalks.objects.get(id=scheduled_id)

        rel_path, abs_path = get_scheduled_toolbox_folder(scheduled, language)

        os.makedirs(abs_path, exist_ok=True)

        # delete existing file
        for f in os.listdir(abs_path):
            os.remove(os.path.join(abs_path, f))

        fn = os.path.basename(fileitem.name)
        filepath = os.path.join(abs_path, fn)

        with open(filepath, 'wb') as f:
            f.write(fileitem.read())

        return redirect('scheduled_toolbox_talks')

def get_scheduled_toolbox_folder(scheduled, language):
    if scheduled.master:
        rel_path = os.path.join("toolbox_talks", str(scheduled.master.id), language)
    else:
        rel_path = os.path.join("custom_toolbox_talks", str(scheduled.id), language)

    abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)
    return rel_path, abs_path

def get_uploaded_toolbox_file(scheduled, language):

    if scheduled.master:
        base_folder = "toolbox_talks"
        folder_id = str(scheduled.master.id)
    else:
        base_folder = "custom_toolbox_talks"
        folder_id = str(scheduled.id)

    path = os.path.join(
        settings.MEDIA_ROOT,
        base_folder,
        folder_id,
        language
    )

    if not os.path.exists(path):
        return None

    for entry in os.listdir(path):
        full_path = os.path.join(path, entry)

        if os.path.isfile(full_path):
            return {
                'filename': entry,
                'path': full_path,
                'url': (
                    settings.MEDIA_URL +
                    f"{base_folder}/{folder_id}/{language}/{entry}"
                )
            }

    return None



def scheduled_toolbox_report(request, scheduled_id):
    scheduled = ScheduledToolboxTalks.objects.get(id=scheduled_id)

    if scheduled.master:
        topic = scheduled.master.description
    else:
        topic = scheduled.description or "Custom Toolbox Talk"

    job = None

    sub_row = ScheduledToolboxTalkSubEmployees.objects.filter(
        scheduled=scheduled,
        job__isnull=False
    ).select_related('job').first()

    emp_row = ScheduledToolboxTalkEmployees.objects.filter(
        scheduled=scheduled,
        job__isnull=False
    ).select_related('job').first()

    if sub_row:
        job = sub_row.job
    elif emp_row:
        job = emp_row.job

    job_info = f"{job.job_number} {job.job_name}" if job else ""
    # # Job info for header only
    # job_info = ""
    # job_numbers = list(
    #     ScheduledToolboxTalkSubEmployees.objects.filter(
    #         scheduled=scheduled,
    #         job__isnull=False
    #     ).values_list('job__job_number', flat=True).distinct()
    # )
    # if job_numbers:
    #     job_info = ", ".join(str(x) for x in job_numbers if x)

    rows = []

    employee_assignments = ScheduledToolboxTalkEmployees.objects.filter(
        scheduled=scheduled
    ).select_related('employee')

    sub_assignments = ScheduledToolboxTalkSubEmployees.objects.filter(
        scheduled=scheduled
    ).select_related('employee', 'job', 'employee__subcontractor')

    # Certain regular employees
    if employee_assignments.exists():
        for row in employee_assignments:
            emp = row.employee

            completed = CompletedToolboxTalks.objects.filter(
                master=scheduled,
                employee=emp,
                is_excused=False
            ).order_by('-date').first()

            if not completed:
                continue

            rows.append({
                'employee_name': f"{emp.first_name} {emp.last_name}",
                'completed_date': completed.date,
            })

    # Subcontractor employees / subcontractor job assignments
    elif sub_assignments.exists():
        seen = set()

        for row in sub_assignments:
            emp = row.employee

            if emp.id in seen:
                continue

            completed_date = None
            if row.job:
                completed_date = _get_sub_employee_toolbox_completion_date(
                    emp,
                    scheduled,
                    row.job
                )
            else:
                completed = CompletedSubToolboxTalks.objects.filter(
                    master=scheduled,
                    employee=emp,
                    is_excused=False
                ).order_by('-date').first()
                if completed:
                    completed_date = completed.date

            if not completed_date:
                continue

            seen.add(emp.id)
            rows.append({
                'employee_name': emp.name or f"Employee #{emp.id}",
                'completed_date': completed_date,
            })

    # All employees
    elif scheduled.is_all_employees:
        target_employees = Employees.objects.filter(
            active=True,
            date_added__lte=scheduled.date,
            job_title__description__in=[
                "Painter",
                "Warehouse",
                "Superintendent"
            ]
        ).order_by('last_name', 'first_name')

        for emp in target_employees:
            completed = CompletedToolboxTalks.objects.filter(
                master=scheduled,
                employee=emp,
                is_excused=False
            ).order_by('-date').first()

            if not completed:
                continue

            rows.append({
                'employee_name': f"{emp.first_name} {emp.last_name}",
                'completed_date': completed.date,
            })

    # Optional: sort by completed date, newest first
    rows = sorted(rows, key=lambda x: x['completed_date'], reverse=True)

    context = {
        'topic': topic,
        'scheduled_date': scheduled.date,
        'job_info': job_info,
        'rows': rows,
    }

    template = get_template('print_scheduled_toolbox_report.html')
    html = template.render(context)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="scheduled_toolbox_report_{scheduled.id}.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse("Error generating PDF", status=500)

    return response



@login_required
@require_GET
def ajax_job_sorted_employees(request):
    job_number = request.GET.get('job_number')

    results = []

    active_painters = Employees.objects.filter(
        active=True,
        job_title__description__in=[
            "Painter",
            "Warehouse",
            "Superintendent"
        ]
    ).order_by('last_name', 'first_name')

    if not job_number:
        results = [
            {
                'id': emp.id,
                'label': f'{emp.first_name} {emp.last_name}'
            }
            for emp in active_painters
        ]
        return JsonResponse({'results': results})

    # Pull ClockShark entries for this job and get latest clock-in per name
    clock_rows = (
        ClockSharkTimeEntry.objects.filter(
            job_id=job_number
        )
        .exclude(employee_first_name__isnull=True)
        .exclude(employee_last_name__isnull=True)
        .values('employee_first_name', 'employee_last_name')
        .annotate(last_clock_in=Max('clock_in'))
        .order_by('-last_clock_in', 'employee_last_name', 'employee_first_name')
    )

    used_employee_ids = set()

    # 1. Employees who clocked into the selected job, most recent first
    for row in clock_rows:
        match = Employees.objects.filter(
            active=True,
            job_title__description="Painter",
            first_name__iexact=row['employee_first_name'],
            last_name__iexact=row['employee_last_name']
        ).order_by('last_name', 'first_name').first()

        if not match:
            continue

        if match.id in used_employee_ids:
            continue

        used_employee_ids.add(match.id)

        last_clock_in = row['last_clock_in']
        label = f"{match.first_name} {match.last_name}"
        if last_clock_in:
            label += f" - last clocked in {last_clock_in.strftime('%m/%d/%y')}"

        results.append({
            'id': match.id,
            'label': label
        })

    # 2. Remaining active painters who have not clocked into that job
    remaining_employees = active_painters.exclude(id__in=used_employee_ids)

    for emp in remaining_employees:
        results.append({
            'id': emp.id,
            'label': f'{emp.first_name} {emp.last_name}'
        })

    return JsonResponse({'results': results})

@login_required
@transaction.atomic
def delete_scheduled_toolbox_talk(request):
    if request.method != 'POST':
        return redirect('scheduled_toolbox_talks')

    scheduled_id = request.POST.get('scheduled_id')
    if not scheduled_id:
        messages.error(request, 'No scheduled toolbox talk was selected.')
        return redirect('scheduled_toolbox_talks')

    scheduled = ScheduledToolboxTalks.objects.filter(id=scheduled_id).first()
    if not scheduled:
        messages.error(request, 'Scheduled toolbox talk not found.')
        return redirect('scheduled_toolbox_talks')

    # Delete related records first
    CompletedSubToolboxTalks.objects.filter(master=scheduled).delete()
    ViewedSubToolboxTalks.objects.filter(master=scheduled).delete()

    CompletedToolboxTalks.objects.filter(master=scheduled).delete()
    ViewedToolboxTalks.objects.filter(master=scheduled).delete()

    ScheduledToolboxTalkEmployees.objects.filter(scheduled=scheduled).delete()
    ScheduledToolboxTalkSubEmployees.objects.filter(scheduled=scheduled).delete()

    # If it is a custom scheduled talk, remove its folder too
    if not scheduled.master:
        folder_path = os.path.join(settings.MEDIA_ROOT, "custom_toolbox_talks", str(scheduled.id))
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path, ignore_errors=True)

    scheduled.delete()

    messages.success(request, 'Scheduled toolbox talk deleted.')
    return redirect('scheduled_toolbox_talks')

def ajax_job_subcontractors(request):
    job_number = request.GET.get('job_number')

    results = []

    if job_number:
        subcontracts = Subcontracts.objects.filter(
            job_number_id=job_number,
            is_closed=False,
            subcontractor__is_toolbox_required=True,
            job_number__is_closed=False,
            job_number__is_active=True,
            job_number__is_labor_done=False,
            subcontractor__is_inactive=False
        ).select_related('subcontractor').order_by('subcontractor__company')

        seen = set()

        for subcontract in subcontracts:
            sub = subcontract.subcontractor

            if sub.id in seen:
                continue

            seen.add(sub.id)

            results.append({
                'id': sub.id,
                'label': sub.company
            })

    return JsonResponse({'results': results})

def scheduled_toolbox_talk_edit(request, scheduled_id):
    scheduled = get_object_or_404(ScheduledToolboxTalks, id=scheduled_id)

    toolbox_talks = ToolboxTalks.objects.all().order_by('description')
    jobs = Jobs.objects.filter(
        is_closed=False,
        is_active=True,
        is_labor_done=False
    ).order_by('job_number')

    has_any_completion = (
            CompletedToolboxTalks.objects.filter(master=scheduled, is_excused=False).exists()
            or CompletedSubToolboxTalks.objects.filter(master=scheduled, is_excused=False).exists()
            or CompletedSubToolboxJobTalks.objects.filter(scheduled=scheduled, is_excused=False).exists()
    )

    selected_employee_ids = list(
        ScheduledToolboxTalkEmployees.objects.filter(
            scheduled=scheduled
        ).values_list('employee_id', flat=True)
    )

    selected_subcontractor_ids = list(
        ScheduledToolboxTalkSubJobs.objects.filter(
            scheduled=scheduled
        ).values_list('subcontractor_id', flat=True)
    )

    assigned_job = None

    employee_job = ScheduledToolboxTalkEmployees.objects.filter(
        scheduled=scheduled,
        job__isnull=False
    ).select_related('job').first()

    sub_job = ScheduledToolboxTalkSubJobs.objects.filter(
        scheduled=scheduled
    ).select_related('job').first()

    if employee_job:
        assigned_job = employee_job.job
    elif sub_job:
        assigned_job = sub_job.job

    if request.method == 'POST':
        master_id = request.POST.get('master_id')
        scheduled_date = request.POST.get('scheduled_date')
        job_number = request.POST.get('job_number')
        employee_ids = request.POST.getlist('employee_ids')
        subcontractor_ids = request.POST.getlist('subcontractor_ids')

        if master_id:
            if has_any_completion and scheduled.master and str(scheduled.master.id) != str(master_id):
                messages.error(
                    request,
                    "You cannot change the toolbox talk topic because someone has already completed it."
                )
                return redirect('scheduled_toolbox_talk_edit', scheduled_id=scheduled.id)

            scheduled.master = ToolboxTalks.objects.get(id=master_id)
            scheduled.description = None

        if scheduled_date:
            scheduled.date = scheduled_date

        scheduled.save()

        if scheduled.is_all_employees:
            messages.success(request, "Scheduled toolbox talk updated.")
            return redirect('scheduled_toolbox_talks')

        if job_number:
            job = get_object_or_404(
                Jobs,
                job_number=job_number,
                is_closed=False,
                is_active=True,
                is_labor_done=False
            )

            existing_employee_ids = set(
                ScheduledToolboxTalkEmployees.objects.filter(
                    scheduled=scheduled
                ).values_list('employee_id', flat=True)
            )

            new_employee_ids = set(int(x) for x in employee_ids if x)

            removed_employee_ids = existing_employee_ids - new_employee_ids

            completed_removed_employees = CompletedToolboxTalks.objects.filter(
                master=scheduled,
                employee_id__in=removed_employee_ids,
                is_excused=False
            )

            if completed_removed_employees.exists():
                messages.error(
                    request,
                    "You cannot remove an employee who has already completed this toolbox talk."
                )
                return redirect('scheduled_toolbox_talk_edit', scheduled_id=scheduled.id)

            ScheduledToolboxTalkEmployees.objects.filter(
                scheduled=scheduled
            ).delete()

            existing_subcontractor_ids = set(
                ScheduledToolboxTalkSubJobs.objects.filter(
                    scheduled=scheduled
                ).values_list('subcontractor_id', flat=True)
            )

            new_subcontractor_ids = set(int(x) for x in subcontractor_ids if x)

            removed_subcontractor_ids = existing_subcontractor_ids - new_subcontractor_ids

            completed_removed_subs = CompletedSubToolboxJobTalks.objects.filter(
                scheduled=scheduled,
                subcontractor_id__in=removed_subcontractor_ids,
                is_excused=False
            )

            if completed_removed_subs.exists():
                messages.error(
                    request,
                    "You cannot remove a subcontractor who has already completed this toolbox talk."
                )
                return redirect('scheduled_toolbox_talk_edit', scheduled_id=scheduled.id)

            completed_removed_sub_employees = CompletedSubToolboxTalks.objects.filter(
                master=scheduled,
                employee__subcontractor_id__in=removed_subcontractor_ids,
                is_excused=False
            )

            if completed_removed_sub_employees.exists():
                messages.error(
                    request,
                    "You cannot remove a subcontractor because one of their employees has already completed this toolbox talk."
                )
                return redirect('scheduled_toolbox_talk_edit', scheduled_id=scheduled.id)

            ScheduledToolboxTalkSubJobs.objects.filter(
                scheduled=scheduled
            ).delete()

            valid_employees = Employees.objects.filter(
                id__in=employee_ids,
                active=True,
                job_title__description__in=[
                    "Painter",
                    "Warehouse",
                    "Superintendent"
                ]
            )

            ScheduledToolboxTalkEmployees.objects.bulk_create([
                ScheduledToolboxTalkEmployees(
                    scheduled=scheduled,
                    employee=emp,
                    job=job
                )
                for emp in valid_employees
            ])

            valid_subcontracts = Subcontracts.objects.filter(
                job_number=job,
                subcontractor_id__in=subcontractor_ids,
                is_closed=False,
                subcontractor__is_toolbox_required=True,
                job_number__is_closed=False,
                job_number__is_active=True,
                job_number__is_labor_done=False,
                subcontractor__is_inactive=False
            ).select_related('subcontractor', 'job_number')

            ScheduledToolboxTalkSubJobs.objects.bulk_create([
                ScheduledToolboxTalkSubJobs(
                    scheduled=scheduled,
                    job=subcontract.job_number,
                    subcontractor=subcontract.subcontractor
                )
                for subcontract in valid_subcontracts
            ])

            scheduled.is_all_employees = False
            scheduled.notes = f"For Job {job.job_number}"
            scheduled.save()

        messages.success(request, "Scheduled toolbox talk updated.")
        return redirect('scheduled_toolbox_talks')

    context = {
        'scheduled': scheduled,
        'toolbox_talks': toolbox_talks,
        'jobs': jobs,
        'assigned_job': assigned_job,
        'selected_employee_ids': selected_employee_ids,
        'selected_subcontractor_ids': selected_subcontractor_ids,
        'has_any_completion': has_any_completion,
    }

    return render(request, 'scheduled_toolbox_talk_edit.html', context)


@login_required
@require_POST
def ajax_check_toolbox_can_complete(request):
    scheduled_id = request.POST.get("scheduled_id")
    employee_id = request.POST.get("employee_id")
    is_group_toolbox = request.POST.get("group_toolbox") == "1"

    if not scheduled_id:
        return JsonResponse({
            "can_complete": False,
            "error": "Missing scheduled toolbox talk ID."
        })

    if employee_id:
        employee = get_object_or_404(Employees, id=employee_id)
    else:
        try:
            employee = Employees.objects.get(user=request.user)
        except Employees.DoesNotExist:
            return JsonResponse({
                "can_complete": False,
                "error": "Employee not found."
            })

    try:
        scheduled_talk = ScheduledToolboxTalks.objects.get(id=scheduled_id)
    except ScheduledToolboxTalks.DoesNotExist:
        return JsonResponse({
            "can_complete": False,
            "error": "Toolbox talk not found."
        })

    if is_group_toolbox:
        group_view = GroupToolboxTalkViews.objects.filter(
            employee=employee,
            scheduled_toolbox_talk=scheduled_talk
        ).first()
        can_complete = _group_toolbox_view_is_current(group_view)
    else:
        can_complete = scheduled_talk.link_has_been_viewed(employee)

    return JsonResponse({
        "can_complete": can_complete
    })


def get_current_resp_clearance(employee):
    return (
        RespiratorClearance.objects
        .filter(
            employee=employee,
            date_completed__isnull=True,
        )
        .order_by("-date_created", "-id")
        .first()
    )
