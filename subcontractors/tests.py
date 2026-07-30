from django.test import TestCase
from django.urls import reverse


class SubcontractorLoginPageTests(TestCase):
    def test_login_page_has_subcontractor_container_and_actions(self):
        response = self.client.get(reverse("connect"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Gerloff Painting Subcontractor Login")
        self.assertContains(response, 'class="subcontractor-login-panel"')
        self.assertContains(response, 'class="btn btn-primary subcontractor-sign-in-button"')
        self.assertContains(response, 'class="btn btn-secondary btn-sm subcontractor-register-button"')
        self.assertContains(response, "New Subcontractors - Register Here")
