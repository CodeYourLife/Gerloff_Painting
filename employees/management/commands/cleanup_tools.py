from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from employees.models import *
from subcontractors.models import *
from changeorder.models import (
    ChangeOrders,
    EWTicket,
    EWT,
    TMProposal,
    TMList,
    ChangeOrderNotes,
    TempRecipients,
    Signature,
)
from submittals.models import *
from wallcovering.models import *
from jobs.models import Orders
from accounts.identity_email import normalize_identity_email


# ----------------------------------------
# YOUR FUNCTIONS
# ----------------------------------------

def delete_all_change_orders():
    with transaction.atomic():
        EWTicket.objects.all().delete()
        TMList.objects.all().delete()
        TMProposal.objects.all().delete()
        EWT.objects.all().delete()
        ChangeOrderNotes.objects.all().delete()
        TempRecipients.objects.all().delete()
        Signature.objects.all().delete()
        ChangeOrders.objects.all().delete()

def delete_all_submittals():
    with transaction.atomic():
        SubmittalApprovalNotes.objects.all().delete()
        SubmittalItemNotes.objects.all().delete()
        SubmittalNotes.objects.all().delete()
        SubmittalApprovals.objects.all().delete()
        SubmittalItems.objects.all().delete()
        Submittals.objects.all().delete()


def just_print_hello():
    print("Hello Joe 👋")

def find_duplicate_identity_emails():
    """
    Return every nonblank email used by more than one login-related record.

    Email addresses are compared the same way they are during saving and
    login: surrounding spaces are removed and capitalization is ignored.
    """
    records_by_email = {}

    identity_records = (
        (
            "Employee",
            Employees.objects.exclude(email__isnull=True).exclude(email=""),
            lambda employee: (
                f"{employee.first_name or ''} {employee.last_name or ''}".strip()
                or "Unnamed employee"
            ),
        ),
        (
            "Subcontractor",
            Subcontractors.objects.exclude(email__isnull=True).exclude(email=""),
            lambda subcontractor: subcontractor.company or "Unnamed subcontractor",
        ),
        (
            "Subcontractor employee",
            Subcontractor_Employees.objects.exclude(email__isnull=True).exclude(email=""),
            lambda employee: employee.name or "Unnamed subcontractor employee",
        ),
    )

    for record_type, queryset, display_name in identity_records:
        for record in queryset.iterator():
            normalized_email = normalize_identity_email(record.email)
            if not normalized_email:
                continue

            records_by_email.setdefault(normalized_email, []).append({
                "type": record_type,
                "id": record.pk,
                "name": display_name(record),
                "stored_email": record.email,
            })

    return {
        email: records
        for email, records in records_by_email.items()
        if len(records) > 1
    }


def delete_all_scheduled_toolbox_talks():
    with transaction.atomic():
        CompletedSubToolboxJobTalkEmployees.objects.all().delete()
        CompletedSubToolboxJobTalks.objects.all().delete()

        CompletedSubToolboxTalks.objects.all().delete()
        ViewedSubToolboxTalks.objects.all().delete()
        ViewedSubToolboxJobTalks.objects.all().delete()

        CompletedToolboxTalks.objects.all().delete()
        ViewedToolboxTalks.objects.all().delete()

        ScheduledToolboxTalkEmployees.objects.all().delete()
        ScheduledToolboxTalkSubEmployees.objects.all().delete()
        ScheduledToolboxTalkSubJobs.objects.all().delete()

        SubcontractorEmployeeDelegation.objects.all().delete()

        ScheduledToolboxTalks.objects.all().delete()

def delete_all_wallcovering():
    with transaction.atomic():

        # OUTGOING / SENT TO JOB
        OutgoingItem.objects.all().delete()
        OutgoingWallcovering.objects.all().delete()

        # PACKAGES / RECEIVING
        Packages.objects.all().delete()
        ReceivedItems.objects.all().delete()
        WallcoveringDelivery.objects.all().delete()

        # NOTES / PRICING
        WallcoveringNotes.objects.all().delete()
        WallcoveringPricing.objects.all().delete()

        # ORDER ITEMS
        OrderItems.objects.all().delete()

        # ORDERS
        Orders.objects.all().delete()

        # WALLCOVERING
        Wallcovering.objects.all().delete()


def _wallcovering_submittal_description(wallcovering, submittal_type):
    wallcovering_code = wallcovering.code or "Wallcovering"
    return f"{wallcovering_code} {submittal_type}"


def _legacy_wallcovering_submittal_descriptions(wallcovering, submittal_type):
    descriptions = [_wallcovering_submittal_description(wallcovering, submittal_type)]

    vendor_name = wallcovering.vendor.company_name if wallcovering.vendor else ""
    wallcovering_code = wallcovering.code or ""
    pattern = wallcovering.pattern or ""

    legacy_bases = [
        vendor_name,
        f"{wallcovering_code} {vendor_name} {pattern}".strip(),
    ]

    for legacy_base in legacy_bases:
        if legacy_base:
            descriptions.append(f"{legacy_base} {submittal_type}")

    return list(dict.fromkeys(descriptions))


def _wallcovering_approval_notes(wallcovering):
    vendor_name = wallcovering.vendor.company_name if wallcovering.vendor else ""
    return f"{vendor_name} {wallcovering.pattern or ''}".strip()


def backfill_wallcovering_submittal_approvals():
    """
    Bring legacy wallcovering-created submittal items into the current shape.

    Legacy items are identified only by generated wallcovering descriptions.
    Eligible items are renamed to the current form:
    "<wallcovering code> Product Data" or "<wallcovering code> Samples".

    For each matching item, ensure there is an unlinked/future approval and set
    that approval's notes and item_notes to "<vendor company name> <pattern>".
    Items with submitted approvals or multiple approval rows are left untouched.
    """
    matched_items = 0
    renamed_items = 0
    created_approvals = 0
    updated_approvals = 0
    skipped_items = 0
    skipped_duplicate_items = 0

    with transaction.atomic():
        wallcoverings = Wallcovering.objects.select_related(
            "vendor",
            "job_number"
        ).all()

        for wallcovering in wallcoverings:
            approval_notes = _wallcovering_approval_notes(wallcovering)

            for submittal_type in ["Product Data", "Samples"]:
                current_description = _wallcovering_submittal_description(
                    wallcovering,
                    submittal_type
                )
                generated_descriptions = _legacy_wallcovering_submittal_descriptions(
                    wallcovering,
                    submittal_type
                )

                submittal_items = SubmittalItems.objects.filter(
                    wallcovering_id=wallcovering,
                    job_number=wallcovering.job_number,
                    description__in=generated_descriptions,
                )

                eligible_items = []

                for item in submittal_items:
                    matched_items += 1

                    approvals = SubmittalApprovals.objects.filter(
                        submittalitem=item,
                    ).order_by("id")
                    approval_count = approvals.count()
                    approval = approvals.first()

                    if approval_count > 1 or (approval and approval.submittal_id):
                        skipped_items += 1
                        continue

                    eligible_items.append({
                        "item": item,
                        "approvals": approvals,
                        "approval": approval,
                        "has_approval": approval is not None,
                        "has_current_description": item.description == current_description,
                    })

                eligible_items.sort(
                    key=lambda row: (
                        not row["has_approval"],
                        not row["has_current_description"],
                        row["item"].id,
                    )
                )

                if len(eligible_items) > 1:
                    skipped_duplicate_items += len(eligible_items) - 1

                for row in eligible_items[:1]:
                    item = row["item"]
                    approval = row["approval"]

                    if item.description != current_description:
                        item.description = current_description
                        item.save(update_fields=["description"])
                        renamed_items += 1

                    if approval:
                        update_fields = []

                        if approval.notes:
                            approval.notes = ""
                            update_fields.append("notes")

                        if approval.item_notes != approval_notes:
                            approval.item_notes = approval_notes
                            update_fields.append("item_notes")

                        if update_fields:
                            approval.save(update_fields=update_fields)
                            updated_approvals += 1
                    else:
                        SubmittalApprovals.objects.create(
                            submittalitem=item,
                            submittal=None,
                            is_approved=None,
                            notes="",
                            item_notes=approval_notes,
                            quantity=0,
                            date_reviewed=None,
                        )
                        created_approvals += 1

    return {
        "matched_items": matched_items,
        "renamed_items": renamed_items,
        "created_approvals": created_approvals,
        "updated_approvals": updated_approvals,
        "skipped_items": skipped_items,
        "skipped_duplicate_items": skipped_duplicate_items,
    }


def clear_unlinked_submittal_approval_notes():
    with transaction.atomic():
        approvals = SubmittalApprovals.objects.filter(
            submittal__isnull=True,
        ).exclude(
            notes__isnull=True,
        ).exclude(
            notes="",
        )

        updated_count = approvals.count()
        approvals.update(notes="")

    return updated_count


def _upsert_completed_sub_toolbox_talk(employee, scheduled, job, completed_date=None, is_excused=False, note=""):
    completed_date = completed_date or timezone.localdate()

    record, created = CompletedSubToolboxTalks.objects.get_or_create(
        employee=employee,
        master=scheduled,
        job=job,
        defaults={
            "date": completed_date,
            "is_excused": is_excused,
            "note": note or None,
        },
    )

    if created:
        return True

    update_fields = []

    if is_excused is False and record.is_excused:
        record.is_excused = False
        update_fields.append("is_excused")

    if not record.date and completed_date:
        record.date = completed_date
        update_fields.append("date")

    if note:
        existing_note = record.note or ""
        if note not in existing_note:
            record.note = f"{existing_note} | {note}" if existing_note else note
            update_fields.append("note")

    if update_fields:
        record.save(update_fields=update_fields)

    return False


def backfill_subcontractor_employee_toolbox_records():
    """
    Consolidate existing subcontractor employee-linked toolbox records into
    CompletedSubToolboxTalks, preserving job context when it can be inferred.

    Sources:
    - CompletedSubToolboxJobTalkEmployees -> job comes from CompletedSubToolboxJobTalks
    - ScheduledToolboxTalkSubEmployees + ViewedSubToolboxTalks -> job comes from assignment

    Existing CompletedSubToolboxTalks rows are left in place and only updated
    when a non-excused completion should override an excused row or add a note.
    """
    created_from_group_attendance = 0
    created_from_views = 0

    with transaction.atomic():
        attendance_rows = (
            CompletedSubToolboxJobTalkEmployees.objects
            .filter(
                employee__isnull=False,
                completed__is_excused=False,
            )
            .select_related(
                "employee",
                "completed",
                "completed__scheduled",
                "completed__job",
            )
        )

        for attendance in attendance_rows:
            completed = attendance.completed
            note_parts = ["Backfilled from subcontractor group toolbox attendance"]
            if attendance.note:
                note_parts.append(attendance.note)

            created = _upsert_completed_sub_toolbox_talk(
                employee=attendance.employee,
                scheduled=completed.scheduled,
                job=completed.job,
                completed_date=completed.date,
                is_excused=False,
                note=" - ".join(note_parts),
            )

            if created:
                created_from_group_attendance += 1

        view_rows = (
            ViewedSubToolboxTalks.objects
            .filter(
                employee__isnull=False,
                master__isnull=False,
            )
            .select_related(
                "employee",
                "master",
            )
        )

        for view in view_rows:
            assignments = (
                ScheduledToolboxTalkSubEmployees.objects
                .filter(
                    employee=view.employee,
                    scheduled=view.master,
                    job__isnull=False,
                )
                .select_related("job")
            )

            for assignment in assignments:
                created = _upsert_completed_sub_toolbox_talk(
                    employee=view.employee,
                    scheduled=view.master,
                    job=assignment.job,
                    completed_date=view.date,
                    is_excused=False,
                    note="Backfilled from subcontractor employee viewed toolbox record",
                )

                if created:
                    created_from_views += 1

    return {
        "created_from_group_attendance": created_from_group_attendance,
        "created_from_views": created_from_views,
        "created_total": created_from_group_attendance + created_from_views,
    }

# ----------------------------------------
# DJANGO ENTRY POINT
# ----------------------------------------

class Command(BaseCommand):
    help = "Utility command for cleanup tasks"

    def add_arguments(self, parser):
        parser.add_argument(
            "action",
            type=str,
            help="Which function to run",
        )

    def handle(self, *args, **options):

        action = options["action"]

        if action == "delete_cos":
            delete_all_change_orders()
            self.stdout.write(self.style.SUCCESS("All change orders deleted."))


        elif action == "delete_submittals":
            delete_all_submittals()
            self.stdout.write(self.style.SUCCESS("All submittals deleted."))

        elif action == "hello":
            just_print_hello()

        elif action == "duplicate_emails":
            duplicates = find_duplicate_identity_emails()

            if not duplicates:
                self.stdout.write(
                    self.style.SUCCESS(
                        "No duplicate employee, subcontractor, or "
                        "subcontractor employee email addresses found."
                    )
                )
                return

            duplicate_record_count = sum(
                len(records) for records in duplicates.values()
            )
            self.stdout.write(
                self.style.WARNING(
                    f"Found {len(duplicates)} duplicated email address(es) "
                    f"across {duplicate_record_count} records:"
                )
            )

            for email, records in sorted(duplicates.items()):
                self.stdout.write("")
                self.stdout.write(self.style.WARNING(email))
                for record in records:
                    stored_email_note = ""
                    if record["stored_email"] != email:
                        stored_email_note = (
                            f" (stored as: {record['stored_email']})"
                        )
                    self.stdout.write(
                        f"  - {record['type']} #{record['id']}: "
                        f"{record['name']}{stored_email_note}"
                    )

        elif action == "delete_toolbox":
            delete_all_scheduled_toolbox_talks()
            self.stdout.write(self.style.SUCCESS("All scheduled toolbox talks deleted."))

        elif action == "delete_wallcovering":
            delete_all_wallcovering()
            self.stdout.write(self.style.SUCCESS("All wallcovering data deleted."))

        elif action == "backfill_sub_toolbox":
            result = backfill_subcontractor_employee_toolbox_records()
            self.stdout.write(
                self.style.SUCCESS(
                    "Subcontractor employee toolbox records backfilled. "
                    f"Created from group attendance: {result['created_from_group_attendance']}. "
                    f"Created from viewed records: {result['created_from_views']}. "
                    f"Created total: {result['created_total']}."
                )
            )

        elif action == "backfill_wallcovering_submittals":
            result = backfill_wallcovering_submittal_approvals()
            self.stdout.write(
                self.style.SUCCESS(
                    "Wallcovering submittal approvals backfilled. "
                    f"Matched generated item(s): {result['matched_items']}. "
                    f"Renamed item(s): {result['renamed_items']}. "
                    f"Created approval(s): {result['created_approvals']}. "
                    f"Updated approval(s): {result['updated_approvals']}. "
                    f"Skipped item(s): {result['skipped_items']}. "
                    f"Skipped duplicate generated item(s): {result['skipped_duplicate_items']}."
                )
            )

        elif action == "clear_unlinked_submittal_approval_notes":
            updated_count = clear_unlinked_submittal_approval_notes()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Cleared notes on {updated_count} unlinked submittal approval(s)."
                )
            )

        else:
            self.stdout.write(self.style.ERROR("Unknown action."))
