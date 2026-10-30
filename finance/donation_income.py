"""Idempotent Finance Income posting for completed donations."""

from django.utils import timezone

from finance.models import Income


def income_key_for_donation(donation) -> str:
    return f"donation:{donation.pk}"


def ensure_income_for_donation(donation):
    """Create at most one Income row for a completed Donation.

    Policy: any COMPLETED donation (gateway or offline/manual) posts Income once.
    Pending/failed/cancelled donations must not call this (caller responsibility).
    """
    if donation is None or donation.pk is None:
        return None, False
    from core.choices import DonationStatus

    if donation.status != DonationStatus.COMPLETED:
        return None, False

    key = income_key_for_donation(donation)
    category = getattr(donation, "category", None)
    category_name = getattr(category, "name_en", None) or "Donation"
    title = f"Donation — {category_name}"
    description = (
        f"Donation from {donation.display_name}. "
        f"Method: {donation.payment_method}. "
        f"Donation id: {donation.pk}."
    )
    txn = getattr(donation, "transaction", None)
    if txn is not None:
        description += f" Transaction: {txn.tran_id}."
    if donation.receipt_number:
        description += f" Receipt: {donation.receipt_number}."

    source = (donation.display_name or "Donation")[:200]
    income, created = Income.objects.get_or_create(
        idempotency_key=key,
        defaults={
            "title": title[:300],
            "description": description,
            "amount": donation.amount,
            "received_date": timezone.now(),
            "source": source,
        },
    )
    return income, created
