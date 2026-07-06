from dataclasses import dataclass
from datetime import date, timedelta

from django.db import transaction
from django.utils import timezone

from employees.models import ScheduledToolboxTalks
from jobs.models import Jobs
from subcontractors.models import (
    CompletedSubToolboxJobTalkEmployees,
    CompletedSubToolboxJobTalks,
    CompletedSubToolboxTalks,
    ScheduledToolboxTalkSubEmployees,
    ScheduledToolboxTalkSubJobs,
    SubcontractorEmployeeDelegation,
    SubcontractorInvoice,
    Subcontractor_Employees,
    Subcontractor_Job_Assignments,
    Subcontracts,
)


STATUS_MISSING = "missing"
STATUS_COMPLETED = "completed"
STATUS_EXCUSED = "excused"


@dataclass(frozen=True)
class SubToolboxEmployeeAssignment:
    employee: Subcontractor_Employees
    scheduled: ScheduledToolboxTalks
    job: Jobs
    subcontract: Subcontracts


def get_talk_title(scheduled):
    if scheduled.master and scheduled.master.description:
        return scheduled.master.description
    if scheduled.description:
        return scheduled.description
    return f"Scheduled Toolbox Talk #{scheduled.id}"


def is_active_toolbox_job(job):
    return bool(
        job and
        not job.is_closed and
        job.is_active and
        not job.is_labor_done
    )


def get_first_subcontractor_invoice_date(subcontract):
    return (
        SubcontractorInvoice.objects
        .filter(subcontract=subcontract)
        .order_by("date", "id")
        .values_list("date", flat=True)
        .first()
    )


def get_subcontract_for_job(subcontractor, job):
    return (
        Subcontracts.objects
        .filter(
            subcontractor=subcontractor,
            job_number=job,
            is_closed=False,
            subcontractor__is_toolbox_required=True,
            job_number__is_closed=False,
            job_number__is_active=True,
            job_number__is_labor_done=False,
        )
        .select_related("subcontractor", "job_number")
        .first()
    )


def get_delegation(subcontractor, subcontract):
    return (
        SubcontractorEmployeeDelegation.objects
        .filter(subcontractor=subcontractor, subcontract=subcontract)
        .first()
    )


def is_delegated(subcontract):
    return bool(get_delegation(subcontract.subcontractor, subcontract))


def employee_is_toolbox_eligible(employee):
    return bool(
        employee and
        employee.is_active and
        employee.has_access_to_toolbox and
        employee.date_enrolled and
        employee.subcontractor and
        employee.subcontractor.is_toolbox_required
    )


def _assigned_employee_ids_for_job(subcontract):
    return (
        Subcontractor_Job_Assignments.objects
        .filter(
            job=subcontract.job_number,
            employee__subcontractor=subcontract.subcontractor,
            employee__is_active=True,
            employee__has_access_to_toolbox=True,
            employee__date_enrolled__isnull=False,
        )
        .values_list("employee_id", flat=True)
        .distinct()
    )


def get_assigned_toolbox_employees_for_job(subcontract):
    return (
        Subcontractor_Employees.objects
        .filter(id__in=_assigned_employee_ids_for_job(subcontract))
        .order_by("name", "id")
    )


def get_all_employee_talks_for_subcontract(subcontract, start_date=None, end_date=None):
    first_invoice_date = get_first_subcontractor_invoice_date(subcontract)
    if not first_invoice_date:
        return ScheduledToolboxTalks.objects.none()

    query = ScheduledToolboxTalks.objects.filter(
        is_all_employees=True,
        date__isnull=False,
        date__gt=first_invoice_date,
    )

    if start_date is not None:
        query = query.filter(date__gte=start_date)

    if end_date is not None:
        query = query.filter(date__lte=end_date)

    return query


def get_applicable_talks_for_employee_job(employee, subcontract, end_date=None):
    if not employee_is_toolbox_eligible(employee):
        return ScheduledToolboxTalks.objects.none()

    start_date = employee.date_enrolled
    scheduled_ids = set(
        get_all_employee_talks_for_subcontract(
            subcontract,
            start_date=start_date,
            end_date=end_date,
        ).values_list("id", flat=True)
    )

    explicit_job_talks = ScheduledToolboxTalkSubJobs.objects.filter(
        subcontractor=subcontract.subcontractor,
        job=subcontract.job_number,
        scheduled__date__isnull=False,
        scheduled__date__gte=start_date,
    )

    explicit_employee_talks = ScheduledToolboxTalkSubEmployees.objects.filter(
        employee=employee,
        job=subcontract.job_number,
        scheduled__date__isnull=False,
        scheduled__date__gte=start_date,
    )

    if end_date is not None:
        explicit_job_talks = explicit_job_talks.filter(scheduled__date__lte=end_date)
        explicit_employee_talks = explicit_employee_talks.filter(scheduled__date__lte=end_date)

    scheduled_ids.update(explicit_job_talks.values_list("scheduled_id", flat=True))
    scheduled_ids.update(explicit_employee_talks.values_list("scheduled_id", flat=True))

    return ScheduledToolboxTalks.objects.filter(id__in=scheduled_ids)


def talk_applies_to_employee_job(employee, scheduled, subcontract):
    if not employee_is_toolbox_eligible(employee):
        return False

    if scheduled.date and employee.date_enrolled > scheduled.date:
        return False

    return (
        get_applicable_talks_for_employee_job(
            employee,
            subcontract,
            end_date=scheduled.date,
        )
        .filter(id=scheduled.id)
        .exists()
    )


def get_employee_toolbox_record(employee, scheduled, job):
    return (
        CompletedSubToolboxTalks.objects
        .filter(employee=employee, master=scheduled, job=job)
        .first()
    )


def get_employee_toolbox_status(employee, scheduled, job):
    record = get_employee_toolbox_record(employee, scheduled, job)

    if not record:
        return STATUS_MISSING
    if record.is_excused:
        return STATUS_EXCUSED
    return STATUS_COMPLETED


def employee_has_completed_or_attended(employee, scheduled, job=None):
    completed_query = CompletedSubToolboxTalks.objects.filter(
        employee=employee,
        master=scheduled,
        is_excused=False,
    )
    attended_query = CompletedSubToolboxJobTalkEmployees.objects.filter(
        employee=employee,
        completed__scheduled=scheduled,
        completed__is_excused=False,
    )

    if job is not None:
        completed_query = completed_query.filter(job=job)
        attended_query = attended_query.filter(completed__job=job)

    return completed_query.exists() or attended_query.exists()


def _merge_note(existing_note, note):
    if not note:
        return existing_note
    if not existing_note:
        return note
    if note in existing_note:
        return existing_note
    return f"{existing_note} | {note}"


@transaction.atomic
def mark_employee_toolbox_completed(employee, scheduled, job, completed_date=None, note=""):
    completed_date = completed_date or timezone.localdate()
    record, created = CompletedSubToolboxTalks.objects.get_or_create(
        employee=employee,
        master=scheduled,
        job=job,
        defaults={
            "date": completed_date,
            "is_excused": False,
            "note": note or None,
        },
    )

    if created:
        return record

    update_fields = []
    if record.is_excused:
        record.is_excused = False
        update_fields.append("is_excused")
    if record.date != completed_date:
        record.date = completed_date
        update_fields.append("date")
    merged_note = _merge_note(record.note, note)
    if merged_note != record.note:
        record.note = merged_note
        update_fields.append("note")
    if update_fields:
        record.save(update_fields=update_fields)

    return record


@transaction.atomic
def mark_employee_toolbox_excused(employee, scheduled, job, excused_date=None, note=""):
    excused_date = excused_date or timezone.localdate()
    record, created = CompletedSubToolboxTalks.objects.get_or_create(
        employee=employee,
        master=scheduled,
        job=job,
        defaults={
            "date": excused_date,
            "is_excused": True,
            "note": note or None,
        },
    )

    if created:
        return record

    update_fields = []
    if not record.is_excused:
        record.is_excused = True
        update_fields.append("is_excused")
    if record.date != excused_date:
        record.date = excused_date
        update_fields.append("date")
    merged_note = _merge_note(record.note, note)
    if merged_note != record.note:
        record.note = merged_note
        update_fields.append("note")
    if update_fields:
        record.save(update_fields=update_fields)

    return record


def get_delegated_employee_assignments_for_subcontract(subcontract, through_date=None):
    through_date = through_date or date.today()
    assignments = []

    if not is_delegated(subcontract):
        return assignments

    employees = get_assigned_toolbox_employees_for_job(subcontract)
    for employee in employees:
        talks = (
            get_applicable_talks_for_employee_job(
                employee,
                subcontract,
                end_date=through_date,
            )
            .select_related("master")
            .order_by("date", "id")
        )

        for scheduled in talks:
            assignments.append(
                SubToolboxEmployeeAssignment(
                    employee=employee,
                    scheduled=scheduled,
                    job=subcontract.job_number,
                    subcontract=subcontract,
                )
            )

    return assignments


def get_delegated_employee_summary_for_subcontract(subcontract, through_date=None):
    rows = []

    for assignment in get_delegated_employee_assignments_for_subcontract(
        subcontract,
        through_date=through_date,
    ):
        status = get_employee_toolbox_status(
            assignment.employee,
            assignment.scheduled,
            assignment.job,
        )
        rows.append({
            "employee": assignment.employee,
            "scheduled": assignment.scheduled,
            "job": assignment.job,
            "subcontract": assignment.subcontract,
            "title": get_talk_title(assignment.scheduled),
            "date": assignment.scheduled.date,
            "status": status,
            "is_missing": status == STATUS_MISSING,
            "is_completed": status == STATUS_COMPLETED,
            "is_excused": status == STATUS_EXCUSED,
        })

    return rows


def get_missing_delegated_employee_items_for_subcontract(subcontract, through_date=None):
    return [
        row for row in get_delegated_employee_summary_for_subcontract(
            subcontract,
            through_date=through_date,
        )
        if row["is_missing"]
    ]


def get_completed_or_excused_employee_ids_for_talk_job(scheduled, job, employees):
    employee_ids = set(employees.values_list("id", flat=True))
    if not employee_ids:
        return set()

    completed_or_excused_ids = set(
        CompletedSubToolboxTalks.objects
        .filter(
            employee_id__in=employee_ids,
            master=scheduled,
            job=job,
        )
        .values_list("employee_id", flat=True)
        .distinct()
    )

    attended_ids = set(
        CompletedSubToolboxJobTalkEmployees.objects
        .filter(
            employee_id__in=employee_ids,
            completed__scheduled=scheduled,
            completed__job=job,
            completed__is_excused=False,
        )
        .values_list("employee_id", flat=True)
        .distinct()
    )

    return completed_or_excused_ids | attended_ids


def all_delegated_employees_done_for_talk(subcontract, scheduled):
    employees = get_assigned_toolbox_employees_for_job(subcontract).filter(
        date_enrolled__lte=scheduled.date
    )
    employee_ids = set(employees.values_list("id", flat=True))

    if not employee_ids:
        return False

    done_ids = get_completed_or_excused_employee_ids_for_talk_job(
        scheduled,
        subcontract.job_number,
        employees,
    )
    return employee_ids <= done_ids


def get_subcontractor_job_talk_status(subcontract, scheduled):
    job_record = (
        CompletedSubToolboxJobTalks.objects
        .filter(
            scheduled=scheduled,
            subcontractor=subcontract.subcontractor,
            job=subcontract.job_number,
        )
        .first()
    )

    if job_record and job_record.is_excused:
        return STATUS_EXCUSED

    if is_delegated(subcontract):
        if all_delegated_employees_done_for_talk(subcontract, scheduled):
            return STATUS_COMPLETED
        if job_record:
            return STATUS_COMPLETED
        return STATUS_MISSING

    if not job_record:
        return STATUS_MISSING
    return STATUS_COMPLETED


def get_scheduled_talk_subcontractor_items(scheduled):
    missing_employee_items = {}
    completed_employee_items = {}
    missing_job_items = {}
    completed_job_items = {}
    processed_job_keys = set()

    def employee_item_key(employee):
        return (employee.subcontractor_id, employee.id)

    def job_item_key(subcontract):
        return (subcontract.subcontractor_id, subcontract.job_number_id)

    def add_employee_status(employee, subcontract):
        if not talk_applies_to_employee_job(employee, scheduled, subcontract):
            return False

        key = employee_item_key(employee)
        status = get_employee_toolbox_status(
            employee,
            scheduled,
            subcontract.job_number,
        )

        if status == STATUS_MISSING:
            item = missing_employee_items.setdefault(
                key,
                {
                    "type": "subcontractor_employee",
                    "subcontractor": employee.subcontractor,
                    "employee": employee,
                    "scheduled": scheduled,
                    "jobs": [],
                    "title": get_talk_title(scheduled),
                    "date": scheduled.date,
                    "status": STATUS_MISSING,
                }
            )
            item["jobs"].append(subcontract.job_number)
            completed_employee_items.pop(key, None)
            return True

        if status == STATUS_COMPLETED and key in missing_employee_items:
            return True

        if status == STATUS_COMPLETED:
            item = completed_employee_items.setdefault(
                key,
                {
                    "type": "subcontractor_employee",
                    "subcontractor": employee.subcontractor,
                    "employee": employee,
                    "scheduled": scheduled,
                    "jobs": [],
                    "title": get_talk_title(scheduled),
                    "date": scheduled.date,
                    "status": STATUS_COMPLETED,
                }
            )
            item["jobs"].append(subcontract.job_number)
            return True

        return status == STATUS_EXCUSED

    def add_delegated_subcontract(subcontract):
        added_employee_item = False
        for employee in get_assigned_toolbox_employees_for_job(subcontract):
            if add_employee_status(employee, subcontract):
                added_employee_item = True

        if not added_employee_item:
            add_non_delegated_subcontract(subcontract)

    def add_non_delegated_subcontract(subcontract):
        key = job_item_key(subcontract)
        if key in processed_job_keys:
            return
        processed_job_keys.add(key)

        status = get_subcontractor_job_talk_status(subcontract, scheduled)
        if status == STATUS_EXCUSED:
            return

        item = {
            "type": "subcontractor_job",
            "subcontractor": subcontract.subcontractor,
            "scheduled": scheduled,
            "job": subcontract.job_number,
            "title": get_talk_title(scheduled),
            "date": scheduled.date,
            "status": status,
        }

        if status == STATUS_COMPLETED:
            completed_job_items[key] = item
        else:
            missing_job_items[key] = item

    def add_subcontract(subcontract):
        if is_delegated(subcontract):
            add_delegated_subcontract(subcontract)
        else:
            add_non_delegated_subcontract(subcontract)

    explicit_job_assignments = (
        ScheduledToolboxTalkSubJobs.objects
        .filter(
            scheduled=scheduled,
            subcontractor__is_toolbox_required=True,
            job__is_closed=False,
            job__is_active=True,
            job__is_labor_done=False,
        )
        .select_related("subcontractor", "job")
    )

    for assignment in explicit_job_assignments:
        subcontract = get_subcontract_for_job(
            assignment.subcontractor,
            assignment.job,
        )
        if subcontract:
            add_subcontract(subcontract)

    explicit_employee_assignments = (
        ScheduledToolboxTalkSubEmployees.objects
        .filter(
            scheduled=scheduled,
            employee__subcontractor__is_toolbox_required=True,
            employee__is_active=True,
            employee__has_access_to_toolbox=True,
            job__isnull=False,
            job__is_closed=False,
            job__is_active=True,
            job__is_labor_done=False,
        )
        .select_related("employee", "employee__subcontractor", "job")
    )

    for assignment in explicit_employee_assignments:
        subcontract = get_subcontract_for_job(
            assignment.employee.subcontractor,
            assignment.job,
        )
        if not subcontract or not is_delegated(subcontract):
            continue
        add_employee_status(assignment.employee, subcontract)

    if scheduled.is_all_employees:
        required_subcontracts = (
            Subcontracts.objects
            .filter(
                is_closed=False,
                subcontractor__is_toolbox_required=True,
                job_number__is_closed=False,
                job_number__is_active=True,
                job_number__is_labor_done=False,
            )
            .select_related("subcontractor", "job_number")
        )

        for subcontract in required_subcontracts:
            if scheduled.date:
                first_invoice_date = get_first_subcontractor_invoice_date(subcontract)
                if not first_invoice_date or scheduled.date <= first_invoice_date:
                    continue
            add_subcontract(subcontract)

    missing_items = list(missing_employee_items.values()) + list(missing_job_items.values())
    completed_items = list(completed_employee_items.values()) + list(completed_job_items.values())

    return {
        "missing": missing_items,
        "completed": completed_items,
    }


def get_scheduled_talk_subcontractor_counts(scheduled):
    items = get_scheduled_talk_subcontractor_items(scheduled)
    return {
        "total": len(items["missing"]) + len(items["completed"]),
        "completed": len(items["completed"]),
        "missing": len(items["missing"]),
    }


def get_missing_subcontractor_items_before(cutoff_date):
    return get_subcontractor_items_before(cutoff_date)["missing"]


def get_missing_subcontractor_items_for_subcontractor(subcontractor, cutoff_date):
    return [
        item for item in get_missing_subcontractor_items_before(cutoff_date)
        if item["subcontractor"].id == subcontractor.id
    ]


def get_subcontractor_portal_required_talks(subcontractor, through_date=None):
    through_date = through_date or timezone.localdate()
    cutoff_date = through_date + timedelta(days=1)
    required_talks = []
    delegated_groups = {}

    def build_delegated_group(item, job):
        key = (item["scheduled"].id, job.pk)
        group = delegated_groups.setdefault(
            key,
            {
                "scheduled": item["scheduled"],
                "job": job,
                "jobs": [job],
                "job_names": job.job_name,
                "description": item["title"],
                "date": item["date"],
                "delegated": True,
                "employee_id": None,
                "employee_name": "",
                "employee_names": "",
                "completed_count": 0,
                "employee_count": 0,
                "_missing_employee_names": {},
            }
        )
        group["_missing_employee_names"][item["employee"].id] = item["employee"].name
        return group

    def set_delegated_group_progress(group):
        subcontract = get_subcontract_for_job(subcontractor, group["job"])
        if not subcontract:
            return

        completed_count = 0
        employee_count = 0
        for employee in get_assigned_toolbox_employees_for_job(subcontract):
            if not talk_applies_to_employee_job(employee, group["scheduled"], subcontract):
                continue

            status = get_employee_toolbox_status(
                employee,
                group["scheduled"],
                group["job"],
            )
            if status == STATUS_EXCUSED:
                continue

            employee_count += 1
            if status == STATUS_COMPLETED:
                completed_count += 1

        group["completed_count"] = completed_count
        group["employee_count"] = employee_count
        missing_names = sorted(group["_missing_employee_names"].values())
        group["employee_names"] = ", ".join(missing_names)
        group["employee_name"] = group["employee_names"]

    for item in get_missing_subcontractor_items_for_subcontractor(subcontractor, cutoff_date):
        if item["type"] == "subcontractor_employee":
            jobs = sorted(item["jobs"], key=lambda job: (job.job_name or "", job.pk))
            if not jobs:
                continue

            for job in jobs:
                build_delegated_group(item, job)
            continue

        required_talks.append({
            "scheduled": item["scheduled"],
            "job": item["job"],
            "jobs": [item["job"]],
            "job_names": item["job"].job_name,
            "description": item["title"],
            "date": item["date"],
            "delegated": False,
            "employee_id": None,
            "employee_name": "",
            "completed_count": 0,
            "employee_count": 0,
        })

    for group in delegated_groups.values():
        set_delegated_group_progress(group)
        group.pop("_missing_employee_names", None)
        required_talks.append(group)

    return sorted(
        required_talks,
        key=lambda talk: (
            talk["date"] or date.min,
            talk["description"] or "",
            talk["job_names"] or "",
            talk["employee_name"] or "",
        )
    )


def get_missing_individual_talk_items_for_employee(employee, through_date=None):
    through_date = through_date or timezone.localdate()
    cutoff_date = through_date + timedelta(days=1)
    rows_by_scheduled = {}

    if not employee_is_toolbox_eligible(employee):
        return []

    items = get_subcontractor_items_before(cutoff_date)["missing"]
    for item in items:
        if item["type"] != "subcontractor_employee":
            continue
        if item["employee"].id != employee.id:
            continue

        scheduled = item["scheduled"]
        row = rows_by_scheduled.setdefault(
            scheduled.id,
            {
                "scheduled": scheduled,
                "jobs": [],
                "title": item["title"],
                "date": item["date"],
            }
        )
        row["jobs"].extend(item["jobs"])

    rows = []
    for row in rows_by_scheduled.values():
        seen_jobs = {}
        for job in row["jobs"]:
            seen_jobs[job.pk] = job
        jobs = sorted(seen_jobs.values(), key=lambda job: (job.job_name or "", job.pk))
        if not jobs:
            continue
        row["jobs"] = jobs
        row["job"] = jobs[0]
        row["job_names"] = ", ".join(job.job_name for job in jobs)
        rows.append(row)

    return sorted(
        rows,
        key=lambda row: (
            row["date"] or date.min,
            row["title"] or "",
            row["job_names"] or "",
        )
    )


def get_missing_group_talk_items_for_employee(employee, through_date=None):
    through_date = through_date or timezone.localdate()
    cutoff_date = through_date + timedelta(days=1)

    if not employee_is_toolbox_eligible(employee):
        return []

    assigned_job_ids = set(
        Subcontractor_Job_Assignments.objects
        .filter(
            employee=employee,
            job__is_closed=False,
            job__is_active=True,
            job__is_labor_done=False,
        )
        .values_list("job_id", flat=True)
    )
    if not assigned_job_ids:
        return []

    rows = []
    for item in get_subcontractor_items_before(cutoff_date)["missing"]:
        if item["type"] != "subcontractor_job":
            continue
        if item["subcontractor"].id != employee.subcontractor_id:
            continue
        if item["job"].pk not in assigned_job_ids:
            continue

        rows.append({
            "scheduled": item["scheduled"],
            "job": item["job"],
            "description": item["title"],
            "date": item["date"],
        })

    return sorted(
        rows,
        key=lambda row: (
            row["date"] or date.min,
            row["description"] or "",
            row["job"].job_name or "",
        )
    )


def get_subcontractor_items_before(cutoff_date):
    missing_items = []
    completed_items = []

    scheduled_talks = (
        ScheduledToolboxTalks.objects
        .filter(date__lt=cutoff_date)
        .select_related("master")
        .order_by("date", "id")
    )

    for scheduled in scheduled_talks:
        items = get_scheduled_talk_subcontractor_items(scheduled)
        missing_items.extend(items["missing"])
        completed_items.extend(items["completed"])

    return {
        "missing": missing_items,
        "completed": completed_items,
    }


def get_missing_subcontractor_count_before(cutoff_date):
    return len(get_missing_subcontractor_items_before(cutoff_date))
