from collections import defaultdict

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from employees.models import Employees
from subcontractors.models import Subcontractor_Employees, Subcontractors


class Command(BaseCommand):
    help = "Audit username collisions if logins become case-insensitive."

    def handle(self, *args, **options):
        employee_by_user = {
            employee.user_id: employee
            for employee in Employees.objects.select_related("user").filter(user__isnull=False)
        }

        rows = []

        for user in User.objects.exclude(username__isnull=True).exclude(username__exact=""):
            username = (user.username or "").strip()
            if not username:
                continue
            employee = employee_by_user.get(user.id)
            if employee:
                label = "Django User #{} / Employee #{}: {} {}".format(
                    user.id,
                    employee.id,
                    employee.first_name or "",
                    employee.last_name or "",
                ).strip()
            else:
                label = "Django User #{}: {} {}".format(
                    user.id,
                    user.first_name or "",
                    user.last_name or "",
                ).strip()
            rows.append((username.lower(), "django_user", username, label))

        for sub in Subcontractors.objects.exclude(username__isnull=True).exclude(username__exact=""):
            username = (sub.username or "").strip()
            if username:
                rows.append(
                    (
                        username.lower(),
                        "subcontractor",
                        username,
                        "Subcontractor #{}: {}".format(sub.id, sub.company or "").strip(),
                    )
                )

        sub_employees = (
            Subcontractor_Employees.objects.select_related("subcontractor")
            .exclude(username__isnull=True)
            .exclude(username__exact="")
        )
        for emp in sub_employees:
            username = (emp.username or "").strip()
            if username:
                company = emp.subcontractor.company if emp.subcontractor_id and emp.subcontractor else ""
                rows.append(
                    (
                        username.lower(),
                        "subcontractor_employee",
                        username,
                        "Subcontractor Employee #{}: {} ({})".format(
                            emp.id,
                            emp.name or "",
                            company,
                        ).strip(),
                    )
                )

        groups = defaultdict(list)
        for key, source, username, label in rows:
            groups[key].append((source, username, label))

        dupes = {key: values for key, values in groups.items() if len(values) > 1}

        self.stdout.write("AUDITED_USERNAMES={}".format(len(rows)))
        self.stdout.write("CASE_INSENSITIVE_DUPLICATE_GROUPS={}".format(len(dupes)))

        if not dupes:
            self.stdout.write(self.style.SUCCESS("NO_CASE_INSENSITIVE_DUPLICATES_FOUND"))
            return

        for key in sorted(dupes):
            self.stdout.write("")
            self.stdout.write(self.style.ERROR("DUPLICATE_KEY={}".format(key)))
            for source, username, label in dupes[key]:
                self.stdout.write("  - [{}] {!r} :: {}".format(source, username, label))
