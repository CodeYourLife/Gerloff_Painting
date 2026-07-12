from django.core.management.base import BaseCommand

from employees.models import Certifications, EmployeePendingActions


class Command(BaseCommand):
    help = "Transfer action-required certifications into EmployeePendingActions."

    def handle(self, *args, **options):
        certifications = Certifications.objects.filter(
            action_required=True
        ).select_related(
            "employee"
        )

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for certification in certifications:
            description = (certification.action or "").strip()

            if not description:
                skipped_count += 1
                continue

            _, created = EmployeePendingActions.objects.update_or_create(
                certification=certification,
                defaults={
                    "employee": certification.employee,
                    "date": certification.date_received,
                    "description": description,
                    "notes": certification.note,
                    "is_complete": False,
                    "confirmed_is_complete": False,
                },
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Transfer complete. "
                f"Created: {created_count}. "
                f"Updated: {updated_count}. "
                f"Skipped without action text: {skipped_count}."
            )
        )
