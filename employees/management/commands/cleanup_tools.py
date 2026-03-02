from django.core.management.base import BaseCommand
from django.db import transaction

from changeorder.models import (
    ChangeOrders,
    EWTicket,
    EWT,
    TMProposal,
    TMList,
    ChangeOrderNotes,
    TempRecipients,
    Signature,
)


# ----------------------------------------
# YOUR FUNCTIONS
# ----------------------------------------

def delete_all_change_orders():
    with transaction.atomic():
        EWTicket.objects.all().delete()
        TMList.objects.all().delete()
        TMProposal.objects.all().delete()
        EWT.objects.all().delete()
        ChangeOrderNotes.objects.all().delete()
        TempRecipients.objects.all().delete()
        Signature.objects.all().delete()
        ChangeOrders.objects.all().delete()


def just_print_hello():
    print("Hello Joe 👋")


# ----------------------------------------
# DJANGO ENTRY POINT
# ----------------------------------------

class Command(BaseCommand):
    help = "Utility command for cleanup tasks"

    def add_arguments(self, parser):
        parser.add_argument(
            "action",
            type=str,
            help="Which function to run",
        )

    def handle(self, *args, **options):

        action = options["action"]

        if action == "delete_cos":
            delete_all_change_orders()
            self.stdout.write(self.style.SUCCESS("All change orders deleted."))

        elif action == "hello":
            just_print_hello()

        else:
            self.stdout.write(self.style.ERROR("Unknown action."))