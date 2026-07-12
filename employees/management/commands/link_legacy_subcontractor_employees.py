from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from employees.models import Certifications
from subcontractors.models import (
    SubcontractorRespiratorClearance,
    Subcontractor_Employees,
)


class Command(BaseCommand):
    help = (
        "Create/link Subcontractor_Employees for legacy subcontractor records "
        "that only have a typed employee name."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--commit",
            action="store_true",
            help="Actually create employees and update records. Without this flag, this is a dry run.",
        )
        parser.add_argument(
            "--backfill-missing-enrollment-dates",
            action="store_true",
            help=(
                "Also set missing subcontractor employee enrollment dates from linked "
                "respirator clearance date_created values."
            ),
        )

    def _legacy_key(self, subcontractor_id, employee_name):
        return subcontractor_id, (employee_name or "").strip().lower()

    def _get_or_create_sub_employee(self, subcontractor, employee_name, cache, commit, enrollment_date=None):
        clean_name = (employee_name or "").strip()
        key = self._legacy_key(subcontractor.id, clean_name)

        if key in cache:
            return cache[key], False

        existing_employee = (
            Subcontractor_Employees.objects
            .filter(
                subcontractor=subcontractor,
                name__iexact=clean_name,
            )
            .order_by("-is_active", "id")
            .first()
        )

        if existing_employee:
            cache[key] = existing_employee
            return existing_employee, False

        if not commit:
            cache[key] = None
            return None, True

        new_employee = Subcontractor_Employees.objects.create(
            subcontractor=subcontractor,
            name=clean_name,
            date_enrolled=enrollment_date,
            is_active=True,
        )
        cache[key] = new_employee
        return new_employee, True

    def _legacy_resp_clearances(self):
        return (
            SubcontractorRespiratorClearance.objects
            .filter(employee__isnull=True)
            .exclude(employee_name__isnull=True)
            .exclude(employee_name__exact="")
            .select_related("subcontractor")
            .order_by("subcontractor__company", "employee_name", "id")
        )

    def _legacy_certifications(self):
        return (
            Certifications.objects
            .filter(
                employee__isnull=True,
                subcontractor__isnull=False,
                subcontractor_employee__isnull=True,
            )
            .exclude(subcontractor_employee_name__isnull=True)
            .exclude(subcontractor_employee_name__exact="")
            .select_related("subcontractor", "category")
            .order_by("subcontractor__company", "subcontractor_employee_name", "id")
        )

    def _backfill_missing_enrollment_dates(self, commit, stats):
        clearances = (
            SubcontractorRespiratorClearance.objects
            .filter(
                employee__isnull=False,
                employee__date_enrolled__isnull=True,
            )
            .select_related("employee", "subcontractor")
            .order_by("employee_id", "date_created", "id")
        )
        employee_dates = {}

        for clearance in clearances:
            enrollment_date = clearance.date_created
            if not enrollment_date:
                continue
            if clearance.employee_id not in employee_dates:
                employee_dates[clearance.employee_id] = {
                    "employee": clearance.employee,
                    "date": enrollment_date,
                    "clearance_id": clearance.id,
                }

        for item in employee_dates.values():
            stats["enrollment_dates_found"] += 1
            employee = item["employee"]
            enrollment_date = item["date"]
            self.stdout.write(
                f"Would set enrollment date for {employee.subcontractor.company} - {employee.name} "
                f"to {enrollment_date} from respirator clearance {item['clearance_id']}."
                if not commit
                else
                f"Set enrollment date for {employee.subcontractor.company} - {employee.name} "
                f"to {enrollment_date} from respirator clearance {item['clearance_id']}."
            )
            if commit:
                employee.date_enrolled = enrollment_date
                employee.save(update_fields=["date_enrolled"])
                stats["enrollment_dates_backfilled"] += 1

    @transaction.atomic
    def handle(self, *args, **options):
        commit = options["commit"]
        cache = {}
        stats = defaultdict(int)

        self.stdout.write(
            self.style.WARNING("DRY RUN - no records will be changed.")
            if not commit
            else self.style.SUCCESS("COMMIT MODE - records will be changed.")
        )

        for clearance in self._legacy_resp_clearances():
            employee_name = (clearance.employee_name or "").strip()
            enrollment_date = clearance.date_created
            sub_employee, would_create = self._get_or_create_sub_employee(
                clearance.subcontractor,
                employee_name,
                cache,
                commit,
                enrollment_date=enrollment_date,
            )

            if would_create:
                stats["employees_created"] += 1
                self.stdout.write(
                    f"Would create subcontractor employee: "
                    f"{clearance.subcontractor.company} - {employee_name} "
                    f"(date enrolled {enrollment_date or 'None'})"
                    if not commit
                    else f"Created subcontractor employee: "
                    f"{clearance.subcontractor.company} - {employee_name} "
                    f"(date enrolled {enrollment_date or 'None'})"
                )

            stats["resp_clearances_found"] += 1
            if commit and sub_employee:
                clearance.employee = sub_employee
                clearance.employee_name = sub_employee.name
                clearance.save(update_fields=["employee", "employee_name"])
                stats["resp_clearances_linked"] += 1
            else:
                self.stdout.write(
                    f"Would link respirator clearance {clearance.id} to "
                    f"{clearance.subcontractor.company} - {employee_name}."
                )

        for certification in self._legacy_certifications():
            employee_name = (certification.subcontractor_employee_name or "").strip()
            sub_employee, would_create = self._get_or_create_sub_employee(
                certification.subcontractor,
                employee_name,
                cache,
                commit,
            )

            if would_create:
                stats["employees_created"] += 1
                self.stdout.write(
                    f"Would create subcontractor employee: "
                    f"{certification.subcontractor.company} - {employee_name}"
                    if not commit
                    else f"Created subcontractor employee: "
                    f"{certification.subcontractor.company} - {employee_name}"
                )

            stats["certifications_found"] += 1
            if commit and sub_employee:
                certification.subcontractor_employee = sub_employee
                certification.subcontractor_employee_name = ""
                certification.save(update_fields=["subcontractor_employee", "subcontractor_employee_name"])
                stats["certifications_linked"] += 1
            else:
                self.stdout.write(
                    f"Would link certification {certification.id} to "
                    f"{certification.subcontractor.company} - {employee_name}."
                )

        if options["backfill_missing_enrollment_dates"]:
            self._backfill_missing_enrollment_dates(commit, stats)

        self.stdout.write("")
        self.stdout.write("Summary:")
        self.stdout.write(f"  Employees to create/created: {stats['employees_created']}")
        self.stdout.write(f"  Legacy respirator clearances found: {stats['resp_clearances_found']}")
        self.stdout.write(f"  Respirator clearances linked: {stats['resp_clearances_linked']}")
        self.stdout.write(f"  Legacy certifications found: {stats['certifications_found']}")
        self.stdout.write(f"  Certifications linked: {stats['certifications_linked']}")
        self.stdout.write(f"  Missing enrollment dates found: {stats['enrollment_dates_found']}")
        self.stdout.write(f"  Enrollment dates backfilled: {stats['enrollment_dates_backfilled']}")

        if not commit:
            self.stdout.write("")
            self.stdout.write("Run again with --commit to apply these changes.")
