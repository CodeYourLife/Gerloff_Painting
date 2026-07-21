from django.test import TestCase

from employees.models import (
    CategoryTemplateFields,
    CategoryTemplates,
    CertificationCategories,
    CertificationCustomAttributes,
    Certifications,
    Employees,
)
from employees.views import _create_standard_certification_custom_attributes


class CertificationCustomAttributeTests(TestCase):
    def setUp(self):
        self.employee = Employees.objects.create(
            first_name="Bridgette",
            last_name="Clause",
            employer="Gerloff Painting",
            date_added="2026-01-01",
        )
        self.template = CategoryTemplates.objects.create(name="Base Clearance")
        self.template_field = CategoryTemplateFields.objects.create(
            template=self.template,
            custom_attribute="Date Approved by Sponsor",
        )
        self.original_category = CertificationCategories.objects.create(
            description="Clearance for Langley",
            template=self.template,
        )
        self.new_category = CertificationCategories.objects.create(
            description="Clearance for DEVGRU",
            template=self.template,
        )

    def test_category_change_reuses_existing_custom_attribute(self):
        certification = Certifications.objects.create(
            employee=self.employee,
            category=self.original_category,
            description="Clearance for Langley",
        )
        _create_standard_certification_custom_attributes(certification)
        custom_attribute = CertificationCustomAttributes.objects.get(
            certification=certification,
            custom_attribute="Date Approved by Sponsor",
        )
        custom_attribute.custom_attribute_result = "7/16/26"
        custom_attribute.save(update_fields=["custom_attribute_result"])

        certification.category = self.new_category
        certification.description = self.new_category.description
        certification.save(update_fields=["category", "description"])
        created_count = _create_standard_certification_custom_attributes(certification)

        custom_attributes = CertificationCustomAttributes.objects.filter(
            certification=certification,
            custom_attribute="Date Approved by Sponsor",
        )
        self.assertEqual(created_count, 0)
        self.assertEqual(custom_attributes.count(), 1)
        custom_attribute.refresh_from_db()
        self.assertEqual(custom_attribute.category, self.new_category)
        self.assertEqual(custom_attribute.custom_attribute_result, "7/16/26")
