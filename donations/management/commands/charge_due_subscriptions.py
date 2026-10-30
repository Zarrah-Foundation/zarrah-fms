import logging

from django.core.management.base import BaseCommand

from donations.recurring_services import reconcile_due_subscriptions

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Reconcile due recurring donation subscriptions (SSLCommerz gateway-scheduled). "
        "Does not invent merchant-initiated card charges. Settlements arrive via IPN."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=100,
            help="Max ACTIVE subscriptions to claim/reconcile this run.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        claimed = reconcile_due_subscriptions(limit=limit)
        self.stdout.write(
            self.style.SUCCESS(
                f"Reconciled/claimed {claimed} due recurring donation subscription(s). "
                "No merchant-initiated charges were invented."
            )
        )
