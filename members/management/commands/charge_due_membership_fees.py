"""Process due membership auto-payments (sandbox/mock only — no gateway HTTP)."""

import logging

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from members.billing import mock_autopay_permitted, mock_charge_due_autopay
from members.models import AutoPayMode, MembershipAutoPay

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Charge due membership auto-pay profiles in MOCK mode only. "
        "Never contacts a real payment gateway. "
        "Refuses to run when DEBUG=False unless ALLOW_MOCK_AUTOPAY_WHEN_DEBUG_FALSE=1."
    )

    def handle(self, *args, **options):
        if not mock_autopay_permitted():
            raise CommandError(
                "MOCK autopay is disabled in this environment "
                "(DEBUG=False and ALLOW_MOCK_AUTOPAY_WHEN_DEBUG_FALSE is not set). "
                "Refusing to mark fees paid without a real gateway."
            )

        today = timezone.localdate()
        due = MembershipAutoPay.objects.filter(
            is_enabled=True,
            mode=AutoPayMode.MOCK,
            next_charge_on__lte=today,
        ).select_related("member")
        charged = 0
        skipped = 0
        for profile in due:
            # GATEWAY mode must never run until officially implemented.
            if profile.mode != AutoPayMode.MOCK:
                skipped += 1
                continue
            result = mock_charge_due_autopay(profile, today=today)
            if result:
                charged += 1
            else:
                skipped += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Mock autopay complete. Charged={charged} skipped={skipped}. "
                "No external HTTP requests were made."
            )
        )
