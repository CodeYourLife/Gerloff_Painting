from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from employees.models import Employees
from subcontractors.models import Subcontractors, Subcontractor_Employees


class LoginPageTests(TestCase):
    def test_login_fields_support_password_managers_and_password_toggle(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'autocomplete="username"')
        self.assertContains(response, 'autocomplete="current-password"')
        self.assertContains(response, 'id="toggle-password"')

    def test_failed_login_does_not_render_submitted_password(self):
        submitted_password = "DoNotEchoThisPassword!"

        response = self.client.post(reverse("login"), {
            "username": "unknown-login-test-user",
            "password": submitted_password,
            "login": "Log In",
        })

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, submitted_password)


class IdentityEmailTests(TestCase):
    def create_employee(self, email, username="employee-user"):
        user = User.objects.create_user(
            username=username,
            password="StrongPassword123!",
        )
        employee = Employees.objects.create(
            first_name="Login",
            last_name="Tester",
            employer="Gerloff Painting",
            date_added=date.today(),
            email=email,
            user=user,
        )
        return employee

    def test_email_is_normalized_when_saved(self):
        employee = self.create_employee("  Login.Test@Example.COM  ")

        self.assertEqual(employee.email, "login.test@example.com")

    def test_email_cannot_be_reused_by_another_identity_type(self):
        employee = self.create_employee("shared@example.com")
        subcontractor = Subcontractors(company="Example Subcontractor")
        subcontractor.email = employee.email.upper()

        with self.assertRaises(ValidationError):
            subcontractor.save()

    def test_subcontractor_employee_email_must_also_be_unique(self):
        self.create_employee("field.worker@example.com")
        subcontractor = Subcontractors.objects.create(
            company="Example Subcontractor",
        )

        with self.assertRaises(ValidationError):
            Subcontractor_Employees.objects.create(
                subcontractor=subcontractor,
                name="Field Worker",
                email="FIELD.WORKER@example.com",
            )

    def test_employee_can_log_in_with_unique_email(self):
        employee = self.create_employee("login.employee@example.com")

        response = self.client.post(reverse("login"), {
            "username": "LOGIN.EMPLOYEE@EXAMPLE.COM",
            "password": "StrongPassword123!",
            "login": "Log In",
        })

        self.assertRedirects(response, "/", fetch_redirect_response=False)
        self.assertEqual(
            int(self.client.session["_auth_user_id"]),
            employee.user_id,
        )

    def test_ambiguous_legacy_email_is_not_accepted_for_login(self):
        self.create_employee("legacy.duplicate@example.com")
        subcontractor = Subcontractors.objects.create(
            company="Legacy Duplicate",
            email="temporary@example.com",
        )
        # Simulate duplicate data that predates the model-level guard.
        Subcontractors.objects.filter(pk=subcontractor.pk).update(
            email="legacy.duplicate@example.com",
        )

        response = self.client.post(reverse("login"), {
            "username": "legacy.duplicate@example.com",
            "password": "StrongPassword123!",
            "login": "Log In",
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid credentials")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_registration_keeps_verified_employee_after_validation_error(self):
        employee = self.create_employee(
            "verified.employee@example.com",
            username="existing-registration-user",
        )
        session = self.client.session
        session["registration_employee_id"] = employee.pk
        session.save()

        response = self.client.post(reverse("registration"), {
            "username": "existing-registration-user",
            "password": "StrongPassword123!",
            "reenterpassword": "StrongPassword123!",
            "phonenumber": "555-0100",
            "email": "new.registration@example.com",
            "nickname": "Tester",
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "USERNAME ALREADY IN USE")
        self.assertEqual(response.context["selected_employee"], employee)
        self.assertNotContains(response, 'name="selected_employee"')

    def test_registration_without_verified_employee_returns_to_pin_entry(self):
        response = self.client.post(reverse("registration"), {
            "username": "new-registration-user",
            "password": "StrongPassword123!",
            "email": "new.registration@example.com",
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Please enter your employee PIN again before registering.",
        )

    @patch("accounts.views.Email.sendEmail")
    def test_forgot_password_accepts_unique_employee_email(self, send_email):
        employee = self.create_employee("forgot.employee@example.com")

        response = self.client.post(reverse("login"), {
            "username": "forgot.employee@example.com",
            "password": "",
            "forgot": "Forgot Password",
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Email sent to user")
        send_email.assert_called_once()
        self.assertEqual(send_email.call_args.args[2], [employee.email])
