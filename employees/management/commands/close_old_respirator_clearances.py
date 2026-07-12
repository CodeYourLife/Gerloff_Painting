from django.core.management.base import BaseCommand
from django.db.models import Q

from employees.models import Certifications, CertificationNotes, Employees
from subcontractors.models import (
    SubcontractorRespiratorClearance,
    SubcontractorRespiratorNotes,
)


class Command(BaseCommand):
    help = "Close older open respirator clearances for employees and subcontractor employees."

    def add_arguments(self, parser):
        parser.add_argument(
            "--commit",
            action="store_true",
            help="Actually close records. Without this flag, the command only reports what would change.",
        )

    def _employee_cert_sort_key(self, certification):
        return (
            certification.date_expires is not None,
            certification.date_expires,
            certification.date_received is not None,
            certification.date_received,
            certification.id,
        )

    def _sub_clearance_sort_key(self, clearance):
        return (
            clearance.date_expires is not None,
            clearance.date_expires,
            clearance.date_completed is not None,
            clearance.date_completed,
            clearance.date_created is not None,
            clearance.date_created,
            clearance.id,
        )

    def _close_employee_certifications(self, commit):
        system_user = Employees.objects.filter(user__is_superuser=True).first()
        closed_count = 0

        employee_ids = (
            Certifications.objects.filter(
                is_closed=False,
                category__description="Respirator Clearance",
            )
            .values_list("employee_id", flat=True)
            .distinct()
        )

        for employee_id in employee_ids:
            certifications = list(
                Certifications.objects.filter(
                    employee_id=employee_id,
                    is_closed=False,
                    category__description="Respirator Clearance",
                ).select_related(
                    "employee",
                    "category",
                )
            )

            if len(certifications) <= 1:
                continue

            keep_certification = max(certifications, key=self._employee_cert_sort_key)
            close_certifications = [
                certification
                for certification in certifications
                if certification.id != keep_certification.id
            ]

            self.stdout.write(
                f"Employee {keep_certification.employee}: keeping certification "
                f"{keep_certification.id}; closing {[cert.id for cert in close_certifications]}."
            )

            for certification in close_certifications:
                if commit:
                    certification.is_closed = True
                    certification.save(update_fields=["is_closed"])
                    if system_user:
                        CertificationNotes.objects.create(
                            certification=certification,
                            date=keep_certification.date_received or keep_certification.date_expires or certification.date_received,
                            user=system_user,
                            note=f"Closed by cleanup because respirator clearance {keep_certification.id} is newer.",
                        )
                closed_count += 1

        return closed_count

    def _subcontractor_identity_filter(self, clearance):
        if clearance.employee_id:
            return Q(employee_id=clearance.employee_id)

        return Q(
            employee__isnull=True,
            employee_name__iexact=clearance.employee_name,
        )

    def _close_subcontractor_clearances(self, commit):
        closed_count = 0
        processed_keys = set()

        open_clearances = (
            SubcontractorRespiratorClearance.objects.filter(
                is_closed=False,
            )
            .select_related(
                "subcontractor",
                "employee",
            )
            .order_by(
                "subcontractor_id",
                "employee_id",
                "employee_name",
                "id",
            )
        )

        for clearance in open_clearances:
            if clearance.employee_id:
                identity_key = ("employee", clearance.subcontractor_id, clearance.employee_id)
            else:
                identity_key = (
                    "name",
                    clearance.subcontractor_id,
                    (clearance.employee_name or "").strip().lower(),
                )

            if identity_key in processed_keys:
                continue

            processed_keys.add(identity_key)

            clearances = list(
                SubcontractorRespiratorClearance.objects.filter(
                    Q(subcontractor_id=clearance.subcontractor_id),
                    self._subcontractor_identity_filter(clearance),
                    is_closed=False,
                ).select_related(
                    "subcontractor",
                    "employee",
                )
            )

            if len(clearances) <= 1:
                continue

            keep_clearance = max(clearances, key=self._sub_clearance_sort_key)
            close_clearances = [
                item
                for item in clearances
                if item.id != keep_clearance.id
            ]

            self.stdout.write(
                f"Subcontractor {keep_clearance.subcontractor} - "
                f"{keep_clearance.employee_display_name}: keeping clearance "
                f"{keep_clearance.id}; closing {[item.id for item in close_clearances]}."
            )

            for close_clearance in close_clearances:
                if commit:
                    close_clearance.is_closed = True
                    close_clearance.save(update_fields=["is_closed"])
                    SubcontractorRespiratorNotes.objects.create(
                        main=close_clearance,
                        date=keep_clearance.date_completed or keep_clearance.date_created or close_clearance.date_created,
                        note=f"Closed by cleanup because respirator clearance {keep_clearance.id} is newer.",
                    )
                closed_count += 1

        return closed_count

    def handle(self, *args, **options):
        commit = options["commit"]

        employee_closed_count = self._close_employee_certifications(commit)
        subcontractor_closed_count = self._close_subcontractor_clearances(commit)

        mode = "Closed" if commit else "Would close"
        self.stdout.write(
            self.style.SUCCESS(
                f"{mode} {employee_closed_count} employee respirator certification(s) "
                f"and {subcontractor_closed_count} subcontractor respirator clearance(s)."
            )
        )

        if not commit:
            self.stdout.write("Dry run only. Re-run with --commit to apply these changes.")
