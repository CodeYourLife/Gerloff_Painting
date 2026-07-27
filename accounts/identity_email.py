from contextlib import contextmanager

from django.core.exceptions import ValidationError
from django.db import connection, models, transaction
from django.db.models.functions import Lower, Trim


EMAIL_IN_USE_MESSAGE = (
    "EMAIL ADDRESS ALREADY IN USE. Please use a different email address."
)


def normalize_identity_email(email):
    return (email or "").strip().lower()


def _identity_models():
    # These imports must stay inside the function to avoid circular model imports.
    from employees.models import Employees
    from subcontractors.models import Subcontractors, Subcontractor_Employees

    return (Employees, Subcontractors, Subcontractor_Employees)


def identity_email_matches(email, exclude_instance=None):
    normalized_email = normalize_identity_email(email)
    if not normalized_email:
        return []

    matches = []
    for model in _identity_models():
        queryset = model.objects.annotate(
            normalized_identity_email=Lower(Trim("email"))
        ).filter(normalized_identity_email=normalized_email)

        if (
            exclude_instance is not None
            and isinstance(exclude_instance, model)
            and exclude_instance.pk is not None
        ):
            queryset = queryset.exclude(pk=exclude_instance.pk)

        matches.extend(queryset)

    return matches


def identity_email_is_available(email, exclude_instance=None):
    return not identity_email_matches(email, exclude_instance=exclude_instance)


def validate_identity_email_unique(email, exclude_instance=None):
    if not identity_email_is_available(email, exclude_instance=exclude_instance):
        raise ValidationError({"email": EMAIL_IN_USE_MESSAGE})


def employee_for_unique_identity_email(email):
    from employees.models import Employees

    matches = identity_email_matches(email)
    if len(matches) == 1 and isinstance(matches[0], Employees):
        return matches[0]
    return None


@contextmanager
def identity_email_save_lock(email):
    """
    Serialize writes for the same normalized email.

    PostgreSQL advisory locks close the race between the cross-table uniqueness
    check and the save. Other supported databases still receive an atomic block.
    """
    normalized_email = normalize_identity_email(email)
    with transaction.atomic():
        if normalized_email and connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT pg_advisory_xact_lock(hashtext(%s))",
                    [f"trinity-identity-email:{normalized_email}"],
                )
        yield


class UniqueIdentityEmailMixin(models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")
        email_is_being_saved = (
            self._state.adding
            or update_fields is None
            or "email" in update_fields
        )
        if not email_is_being_saved:
            return super().save(*args, **kwargs)

        normalized_email = normalize_identity_email(self.email)
        self.email = normalized_email

        previous_email = ""
        if not self._state.adding and self.pk is not None:
            previous_email = normalize_identity_email(
                type(self).objects.filter(pk=self.pk)
                .values_list("email", flat=True)
                .first()
            )

        # Existing duplicate legacy values are allowed to remain during unrelated
        # edits, but every new or changed nonblank email must be globally unique.
        email_changed = self._state.adding or normalized_email != previous_email
        if normalized_email and email_changed:
            with identity_email_save_lock(normalized_email):
                validate_identity_email_unique(
                    normalized_email,
                    exclude_instance=self,
                )
                return super().save(*args, **kwargs)

        return super().save(*args, **kwargs)
