from collections import defaultdict

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from employees.models import Employees


class Command(BaseCommand):
    help = "Audit Django users and employee links."

    def handle(self, *args, **options):
        employees_with_user = Employees.objects.select_related("user").filter(user__isnull=False)
        user_ids_with_employee = set(employees_with_user.values_list("user_id", flat=True))

        users_without_employee = User.objects.exclude(id__in=user_ids_with_employee).order_by("username")
        employees_without_user = Employees.objects.filter(user__isnull=True).order_by("last_name", "first_name")

        employees_by_user_id = defaultdict(list)
        for employee in employees_with_user:
            employees_by_user_id[employee.user_id].append(employee)
        users_with_multiple_employees = {
            user_id: employees
            for user_id, employees in employees_by_user_id.items()
            if len(employees) > 1
        }

        self.stdout.write("DJANGO_USERS={}".format(User.objects.count()))
        self.stdout.write("EMPLOYEES={}".format(Employees.objects.count()))
        self.stdout.write("USERS_WITHOUT_EMPLOYEE={}".format(users_without_employee.count()))
        self.stdout.write("EMPLOYEES_WITHOUT_USER={}".format(employees_without_user.count()))
        self.stdout.write("USERS_LINKED_TO_MULTIPLE_EMPLOYEES={}".format(len(users_with_multiple_employees)))

        has_issue = (
            users_without_employee.exists()
            or employees_without_user.exists()
            or bool(users_with_multiple_employees)
        )

        if users_without_employee.exists():
            self.stdout.write("")
            self.stdout.write(self.style.ERROR("Django users without an employee:"))
            for user in users_without_employee:
                self.stdout.write(
                    "  - User #{} username={!r} name={} {}".format(
                        user.id,
                        user.username,
                        user.first_name or "",
                        user.last_name or "",
                    ).strip()
                )

        if employees_without_user.exists():
            self.stdout.write("")
            self.stdout.write(self.style.ERROR("Employees without a Django user:"))
            for employee in employees_without_user:
                self.stdout.write(
                    "  - Employee #{}: {} {} active={}".format(
                        employee.id,
                        employee.first_name or "",
                        employee.last_name or "",
                        employee.active,
                    ).strip()
                )

        if users_with_multiple_employees:
            self.stdout.write("")
            self.stdout.write(self.style.ERROR("Django users linked to multiple employees:"))
            users_by_id = User.objects.in_bulk(users_with_multiple_employees.keys())
            for user_id in sorted(users_with_multiple_employees):
                user = users_by_id.get(user_id)
                username = user.username if user else "missing user"
                self.stdout.write("  - User #{} username={!r}".format(user_id, username))
                for employee in users_with_multiple_employees[user_id]:
                    self.stdout.write(
                        "      Employee #{}: {} {} active={}".format(
                            employee.id,
                            employee.first_name or "",
                            employee.last_name or "",
                            employee.active,
                        ).strip()
                    )

        if not has_issue:
            self.stdout.write(self.style.SUCCESS("DJANGO_USERS_AND_EMPLOYEES_AUDIT_CLEAN"))
