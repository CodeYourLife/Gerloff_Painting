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

        else:
            self.stdout.write(self.style.ERROR("Unknown action."))
