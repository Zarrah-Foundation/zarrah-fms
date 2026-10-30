"""Idempotent Finance Income posting for membership fee payments."""

from django.utils import timezone

from finance.models import Income


def income_key_for_fee_payment(payment):
    return f"membership-fee-payment:{payment.pk}"


def income_key_for_registration_fee(reg_fee):
    return f"membership-registration-fee:{reg_fee.pk}"


def ensure_income_for_fee_payment(payment):
    """Create at most one Income row for a completed MembershipFeePayment."""
    if payment is None or payment.pk is None:
        return None, False
    key = income_key_for_fee_payment(payment)
    member = payment.member
    months = payment.months or []
    period = ", ".join(
        f"{m.get('year')}-{int(m.get('month')):02d}" for m in months
    ) or "membership fees"
    title = f"Membership fees — {member.member_id}"
    description = (
        f"Membership fee payment for {period}. "
        f"Method: {payment.payment_method}. "
        f"Payment id: {payment.pk}."
    )
    txn = getattr(payment, "transaction", None)
    if txn is not None:
        description += f" Transaction: {txn.tran_id}."

    source = f"Member {member.member_id}"
    income, created = Income.objects.get_or_create(
        idempotency_key=key,
        defaults={
            "title": title,
            "description": description,
            "amount": payment.amount,
            "received_date": timezone.now(),
            "source": source[:200],
        },
    )
    return income, created


def ensure_income_for_registration_fee(reg_fee):
    """Create at most one Income row for a completed registration fee."""
    if reg_fee is None or reg_fee.pk is None:
        return None, False
    key = income_key_for_registration_fee(reg_fee)
    member = reg_fee.member
    title = f"Membership registration fee — {member.member_id}"
    description = (
        f"One-time membership registration fee. "
        f"Method: {reg_fee.payment_method}. "
        f"Registration fee id: {reg_fee.pk}."
    )
    txn = getattr(reg_fee, "transaction", None)
    if txn is not None:
        description += f" Transaction: {txn.tran_id}."
    income, created = Income.objects.get_or_create(
        idempotency_key=key,
        defaults={
            "title": title,
            "description": description,
            "amount": reg_fee.amount,
            "received_date": timezone.now(),
            "source": f"Member {member.member_id}"[:200],
        },
    )
    return income, created
