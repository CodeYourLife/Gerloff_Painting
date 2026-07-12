from django.core.management.base import BaseCommand

from employees.models import Certifications


class Command(BaseCommand):
    help = "Copy category descriptions into Certifications.description for existing certifications."

    def add_arguments(self, parser):
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Overwrite existing certification descriptions with the category description.",
        )

    def handle(self, *args, **options):
        overwrite = options["overwrite"]
        certifications = Certifications.objects.filter(
            category__isnull=False,
        ).select_related(
            "category",
        )

        updated_count = 0
        skipped_count = 0

        for certification in certifications:
            category_description = (certification.category.description or "").strip()

            if not category_description:
                skipped_count += 1
                continue

            current_description = (certification.description or "").strip()
            if current_description and not overwrite:
                skipped_count += 1
                continue

            if certification.description == category_description:
                skipped_count += 1
                continue

            certification.description = category_description
            certification.save(update_fields=["description"])
            updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Backfill complete. "
                f"Updated: {updated_count}. "
                f"Skipped: {skipped_count}."
            )
        )
