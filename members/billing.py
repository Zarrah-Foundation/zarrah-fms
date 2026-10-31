"""Membership monthly fee ledger, payments, and auto-pay rules."""

from __future__ import annotations

import logging
from datetime import date

from django.db import transaction
from django.utils import timezone

from core.choices import DonationStatus, PaymentMethod
from members.fee_settings import (
    DEFAULT_MONTHLY_FEE_BDT,
    get_monthly_fee_amount,
    member_fee_start_period,
)
from members.models import (
    AutoPayMode,
    FeePaymentSource,
    Member,
    MembershipAutoPay,
    MembershipBillingEvent,
    MembershipFee,
    MembershipFeePayment,
    MembershipRegistrationFee,
)

logger = logging.getLogger(__name__)

# Backward-compatible documented default; runtime amount comes from settings.
MEMBERSHIP_MONTHLY_FEE_BDT = float(DEFAULT_MONTHLY_FEE_BDT)


def current_year_month(today=None):
    today = today or timezone.localdate()
    return today.year, today.month


def period_tuple(year, month):
    return int(year), int(month)


def period_key(year, month):
    return (int(year), int(month))


def add_months(year, month, n):
    idx = year * 12 + (month - 1) + n
    return idx // 12, (idx % 12) + 1


def months_inclusive(start_year, start_month, end_year, end_month):
    """Yield (year, month) from start through end inclusive."""
    y, m = int(start_year), int(start_month)
    ey, em = int(end_year), int(end_month)
    if (y, m) > (ey, em):
        return
    while (y, m) <= (ey, em):
        yield y, m
        y, m = add_months(y, m, 1)


def normalize_month_list(months):
    """Return sorted unique list of {"year","month"} dicts."""
    seen = set()
    out = []
    for item in months:
        if isinstance(item, (list, tuple)):
            y, m = item[0], item[1]
        else:
            y, m = item["year"], item["month"]
        y, m = int(y), int(m)
        if m < 1 or m > 12:
            raise ValueError(f"Invalid month: {m}")
        key = (y, m)
        if key in seen:
            continue
        seen.add(key)
        out.append({"year": y, "month": m})
    out.sort(key=lambda d: (d["year"], d["month"]))
    return out


def record_billing_event(member, action, *, actor=None, message="", metadata=None):
    return MembershipBillingEvent.objects.create(
        member=member,
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        message=message or "",
        metadata=metadata,
    )


def member_join_period(member):
    """First liability month for monthly fees (configured start ∩ approval month)."""
    return member_fee_start_period(member)


@transaction.atomic
def ensure_ledger_months(member, through_year=None, through_month=None, *, actor=None):
    """Create missing PENDING rows from fee-start month through target month."""
    cy, cm = current_year_month()
    through_year = through_year or cy
    through_month = through_month or cm
    start_y, start_m = member_fee_start_period(member)
    # Never invent unpaid months before the applicable start month.
    if (through_year, through_month) < (start_y, start_m):
        return []
    amount = get_monthly_fee_amount()
    created = []
    for y, m in months_inclusive(start_y, start_m, through_year, through_month):
        fee, was_created = MembershipFee.objects.get_or_create(
            member=member,
            year=y,
            month=m,
            defaults={"amount": amount, "status": DonationStatus.PENDING},
        )
        if was_created:
            created.append(fee)
        # Idempotent FEE_DUE for unpaid months at/before current (no storms for far future).
        if fee.status == DonationStatus.PENDING and (y, m) <= (cy, cm):
            try:
                from members.fee_notifications import notify_fee_due

                notify_fee_due(fee)
            except Exception:
                logger.exception("FEE_DUE notification failed for %s", fee.pk)
    if created:
        record_billing_event(
            member,
            MembershipBillingEvent.Action.LEDGER_ENSURED,
            actor=actor,
            message=f"Ensured ledger through {through_year}-{through_month:02d}",
            metadata={"created": len(created)},
        )
    return created


def paid_through(member):
    """Latest CONTIGUOUS paid month from join month forward (gaps stop the chain).

    Example: Jan paid, Feb pending, March paid → paid_through is January, not March.
    Contiguous prepaid future months (Jan–Mar all paid) → March.
    """
    paid = set(
        MembershipFee.objects.filter(member=member, status=DonationStatus.COMPLETED)
        .values_list("year", "month")
    )
    if not paid:
        return None
    start_y, start_m = member_fee_start_period(member)
    max_paid = max(paid)
    y, m = start_y, start_m
    last = None
    while (y, m) <= max_paid:
        if (y, m) not in paid:
            break
        last = (y, m)
        y, m = add_months(y, m, 1)
    return period_tuple(*last) if last else None


def is_prepaid_beyond_current(member, today=None):
    """True when paid-through is strictly after the current calendar month."""
    pt = paid_through(member)
    if not pt:
        return False
    cy, cm = current_year_month(today)
    return pt > (cy, cm)


def is_due_for_current_month(member, today=None):
    """True when current month is not yet paid (member may activate auto-pay)."""
    cy, cm = current_year_month(today)
    ensure_ledger_months(member, cy, cm)
    return not MembershipFee.objects.filter(
        member=member, year=cy, month=cm, status=DonationStatus.COMPLETED
    ).exists()


@transaction.atomic
def mark_fee_months_paid(
    member,
    months,
    *,
    payment_method,
    source,
    fee_payment=None,
    transaction_id=None,
    actor=None,
    notes="",
):
    """Idempotently mark the given months COMPLETED. Never deletes paid rows."""
    months = normalize_month_list(months)
    if not months:
        raise ValueError("No months selected.")
    last = months[-1]
    ensure_ledger_months(member, last["year"], last["month"], actor=actor)

    updated = []
    for item in months:
        fee = (
            MembershipFee.objects.select_for_update()
            .filter(member=member, year=item["year"], month=item["month"])
            .first()
        )
        if fee is None:
            fee = MembershipFee.objects.create(
                member=member,
                year=item["year"],
                month=item["month"],
                amount=get_monthly_fee_amount(),
                status=DonationStatus.PENDING,
            )
        if fee.status == DonationStatus.COMPLETED:
            continue
        # Preserve historical row amounts — configuration changes do not rewrite them.
        fee.status = DonationStatus.COMPLETED
        fee.paid_at = timezone.now()
        fee.payment_method = payment_method
        fee.source = source
        fee.transaction_id = transaction_id or fee.transaction_id
        fee.fee_payment = fee_payment
        fee.save()
        updated.append(fee)

    # Prepaid future months keep auto-payment OFF until the member is due again.
    if is_prepaid_beyond_current(member):
        deactivate_autopay(
            member,
            actor=actor,
            reason="prepaid future coverage",
            forced=True,
        )

    return updated


def get_or_create_autopay(member):
    profile, _ = MembershipAutoPay.objects.get_or_create(member=member)
    return profile


@transaction.atomic
def activate_autopay(member, *, actor=None):
    """Member-explicit activation only. Refuses when not due or gateway recurring required."""
    from donations.gateway_capabilities import autopay_activation_allowed

    if not is_due_for_current_month(member):
        raise ValueError(
            "Auto-payment can only be activated when the current month is unpaid. "
            "Prepaid coverage keeps auto-payment off."
        )
    allowed, reason, mode = autopay_activation_allowed()
    if not allowed:
        raise ValueError(reason)

    profile = get_or_create_autopay(member)
    # Never enable GATEWAY recurring unless capability is verified.
    profile.mode = mode
    profile.is_enabled = True
    profile.activated_at = timezone.now()
    profile.deactivated_at = None
    profile.deactivated_by = None
    cy, cm = current_year_month()
    # Next charge: first day of next month (mock).
    ny, nm = add_months(cy, cm, 1)
    profile.next_charge_on = date(ny, nm, 1)
    # Tokens remain unused/null.
    profile.gateway_subscription_ref = None
    profile.payment_token = None
    profile.save()
    record_billing_event(
        member,
        MembershipBillingEvent.Action.AUTOPAY_ACTIVATED,
        actor=actor,
        message=f"Auto-pay activated (mode={mode})",
        metadata={"mode": mode},
    )
    return profile


@transaction.atomic
def deactivate_autopay(member, *, actor=None, reason="", forced=False):
    profile = MembershipAutoPay.objects.filter(member=member).first()
    if not profile:
        return None
    if not profile.is_enabled and not forced:
        return profile
    was_enabled = profile.is_enabled
    profile.is_enabled = False
    profile.deactivated_at = timezone.now()
    profile.deactivated_by = actor if getattr(actor, "is_authenticated", False) else None
    profile.next_charge_on = None
    profile.save()
    if was_enabled:
        action = (
            MembershipBillingEvent.Action.AUTOPAY_FORCED_OFF
            if forced
            else MembershipBillingEvent.Action.AUTOPAY_DEACTIVATED
        )
        record_billing_event(
            member,
            action,
            actor=actor,
            message=reason or "Auto-pay deactivated",
            metadata={"forced": forced},
        )
    return profile


@transaction.atomic
def initiate_fee_checkout(member, months, *, request, actor=None, method=None):
    """Create PENDING fee payment + Transaction and return the provider redirect URL."""
    from donations.gateway_capabilities import online_checkout_allowed
    from donations.models import Transaction, TransactionPurpose
    from donations.services import generate_tran_id
    from donations.gateways import get_gateway

    method = method or PaymentMethod.SSLCOMMERZ
    ok, err = online_checkout_allowed(method, purpose=TransactionPurpose.MEMBERSHIP_FEE)
    if not ok:
        raise ValueError(err)

    months = normalize_month_list(months)
    if not months:
        raise ValueError("Select at least one month.")
    cy, cm = current_year_month()
    for item in months:
        if (item["year"], item["month"]) < (cy, cm):
            # Past unpaid months are allowed.
            pass
        # Future and current allowed; no upper bound beyond ensure.
    last = months[-1]
    ensure_ledger_months(member, last["year"], last["month"], actor=actor)

    # Reject months already completed (prevent double-pay selection).
    for item in months:
        if MembershipFee.objects.filter(
            member=member,
            year=item["year"],
            month=item["month"],
            status=DonationStatus.COMPLETED,
        ).exists():
            raise ValueError(
                f"Month {item['year']}-{item['month']:02d} is already paid."
            )

    # Sum ledger amounts for selected months (supports rate changes without rewriting paid rows).
    amount = 0.0
    for item in months:
        fee = MembershipFee.objects.filter(
            member=member, year=item["year"], month=item["month"]
        ).first()
        amount += float(fee.amount) if fee else get_monthly_fee_amount()
    import uuid

    txn = Transaction.objects.create(
        session_id=str(uuid.uuid4()),
        tran_id=generate_tran_id(),
        amount=amount,
        currency="BDT",
        status=DonationStatus.PENDING,
        gateway=method,
        purpose=TransactionPurpose.MEMBERSHIP_FEE,
        cus_name=f"{member.first_name} {member.last_name}".strip() or member.member_id,
        cus_email=getattr(member.user, "email", None),
        cus_phone=member.phone,
    )
    payment = MembershipFeePayment.objects.create(
        member=member,
        transaction=txn,
        amount=amount,
        currency="BDT",
        status=DonationStatus.PENDING,
        payment_method=method,
        months=months,
        source=FeePaymentSource.GATEWAY,
    )
    record_billing_event(
        member,
        MembershipBillingEvent.Action.PAYMENT_INITIATED,
        actor=actor,
        message=f"Checkout for {len(months)} month(s), ৳{amount:g}",
        metadata={"payment_id": str(payment.pk), "months": months, "tran_id": txn.tran_id},
    )
    gateway = get_gateway(method)
    url = gateway.init_payment(payment, request)
    return payment, url


@transaction.atomic
def complete_fee_payment(payment, *, val_id=None, validation_data=None):
    """Idempotent completion after verified gateway validation."""
    # Lock payment row only — nullable transaction FK cannot use FOR UPDATE with OUTER JOIN.
    payment = MembershipFeePayment.objects.select_for_update(of=("self",)).select_related(
        "transaction", "member"
    ).get(pk=payment.pk)
    if payment.status == DonationStatus.COMPLETED:
        # Re-run idempotent side effects so duplicate callbacks never leave gaps.
        _post_fee_payment_side_effects(payment)
        return payment

    txn = payment.transaction
    # Gateway SSLCommerz completions require validated payload (same invariant as donations).
    if payment.payment_method in (PaymentMethod.SSLCOMMERZ, PaymentMethod.BKASH) or (
        txn and txn.gateway in (PaymentMethod.SSLCOMMERZ, PaymentMethod.BKASH)
    ):
        if not validation_data or not isinstance(validation_data, dict):
            raise ValueError(
                "Gateway validation data is required to complete this fee payment."
            )
        if (validation_data.get("status") or "").upper() not in ("VALID", "VALIDATED"):
            raise ValueError("Gateway validation status is not VALID.")
        if txn and str(validation_data.get("tran_id") or "") != str(txn.tran_id):
            raise ValueError("Validated tran_id does not match fee payment.")
        from donations.money import amounts_equal, normalize_currency

        if not amounts_equal(validation_data.get("amount"), payment.amount):
            raise ValueError("Validated amount does not match fee payment.")
        if txn and not amounts_equal(validation_data.get("amount"), txn.amount):
            raise ValueError("Validated amount does not match transaction.")
        expected_currency = normalize_currency(
            getattr(txn, "currency", None) or "BDT"
        )
        if validation_data.get("currency") and normalize_currency(
            validation_data.get("currency")
        ) != expected_currency:
            raise ValueError("Validated currency does not match fee payment.")

    if txn:
        if validation_data:
            txn.val_id = val_id
            txn.bank_tran_id = validation_data.get("bank_tran_id")
            # Store truncated card metadata from gateway only (never PIN/CVV).
            txn.card_type = validation_data.get("card_type")
            card_no = validation_data.get("card_no") or ""
            # SSLCommerz returns masked card; store as-is if masked, else blank.
            txn.card_no = card_no if ("*" in str(card_no) or len(str(card_no)) <= 4) else ""
            txn.card_issuer = validation_data.get("card_issuer")
            txn.risk_level = validation_data.get("risk_level")
            txn.validated_on = timezone.now()
        txn.status = DonationStatus.COMPLETED
        txn.save()

    mark_fee_months_paid(
        payment.member,
        payment.months,
        payment_method=payment.payment_method,
        source=payment.source or FeePaymentSource.GATEWAY,
        fee_payment=payment,
        transaction_id=txn.tran_id if txn else None,
        actor=None,
    )
    payment.status = DonationStatus.COMPLETED
    payment.save(update_fields=["status", "updated_at"])
    record_billing_event(
        payment.member,
        MembershipBillingEvent.Action.PAYMENT_COMPLETED,
        message=f"Payment {txn.tran_id if txn else payment.pk} completed",
        metadata={"payment_id": str(payment.pk), "months": payment.months},
    )
    _post_fee_payment_side_effects(payment)
    return payment


@transaction.atomic
def mark_fee_payment_failed(payment):
    payment = MembershipFeePayment.objects.select_for_update().get(pk=payment.pk)
    if payment.status == DonationStatus.COMPLETED:
        return payment
    payment.status = DonationStatus.FAILED
    payment.save(update_fields=["status", "updated_at"])
    if payment.transaction_id:
        payment.transaction.status = DonationStatus.FAILED
        payment.transaction.save(update_fields=["status", "updated_at"])
    record_billing_event(
        payment.member,
        MembershipBillingEvent.Action.PAYMENT_FAILED,
        message="Fee payment failed",
        metadata={"payment_id": str(payment.pk)},
    )
    return payment


@transaction.atomic
def record_admin_fee_payment(
    member,
    months,
    *,
    payment_method,
    actor,
    notes="",
    transaction_id="",
):
    """Admin/Finance offline recording (cash/bank/other). Never enables auto-pay."""
    months = normalize_month_list(months)
    ensure_ledger_months(
        member,
        months[-1]["year"],
        months[-1]["month"],
        actor=actor,
    )
    amount = 0.0
    for item in months:
        fee = MembershipFee.objects.filter(
            member=member, year=item["year"], month=item["month"]
        ).first()
        amount += float(fee.amount) if fee else get_monthly_fee_amount()
    payment = MembershipFeePayment.objects.create(
        member=member,
        transaction=None,
        amount=amount,
        status=DonationStatus.COMPLETED,
        payment_method=payment_method,
        months=months,
        source=FeePaymentSource.ADMIN,
        notes=notes or "",
        recorded_by=actor,
    )
    mark_fee_months_paid(
        member,
        months,
        payment_method=payment_method,
        source=FeePaymentSource.ADMIN,
        fee_payment=payment,
        transaction_id=transaction_id or f"ADMIN-{payment.pk}",
        actor=actor,
        notes=notes,
    )
    record_billing_event(
        member,
        MembershipBillingEvent.Action.ADMIN_RECORDED,
        actor=actor,
        message=f"Admin recorded {len(months)} month(s) via {payment_method}",
        metadata={"payment_id": str(payment.pk), "months": months},
    )
    _post_fee_payment_side_effects(payment)
    return payment


def mock_autopay_permitted() -> bool:
    """MOCK fee completion is allowed only in DEBUG, or with explicit override.

    Never silently mark fees paid when DEBUG=False unless
    ``ALLOW_MOCK_AUTOPAY_WHEN_DEBUG_FALSE`` is set deliberately.
    """
    from django.conf import settings

    if settings.DEBUG:
        return True
    return bool(getattr(settings, "ALLOW_MOCK_AUTOPAY_WHEN_DEBUG_FALSE", False))


@transaction.atomic
def mock_charge_due_autopay(profile, *, today=None):
    """Sandbox/mock auto-charge for one due month. Never contacts a gateway."""
    if not mock_autopay_permitted():
        logger.error(
            "Refusing MOCK autopay: DEBUG=False and "
            "ALLOW_MOCK_AUTOPAY_WHEN_DEBUG_FALSE is not enabled."
        )
        return None
    if not profile.is_enabled:
        return None
    if profile.mode != AutoPayMode.MOCK:
        logger.info("Skipping non-mock autopay profile %s", profile.pk)
        return None

    today = today or timezone.localdate()
    member = profile.member
    if not is_due_for_current_month(member, today):
        # Coverage exists — keep OFF.
        deactivate_autopay(member, reason="coverage present", forced=True)
        return None

    cy, cm = current_year_month(today)
    ensure_ledger_months(member, cy, cm)
    fee = MembershipFee.objects.filter(member=member, year=cy, month=cm).first()
    charge_amount = float(fee.amount) if fee else get_monthly_fee_amount()
    payment = MembershipFeePayment.objects.create(
        member=member,
        transaction=None,
        amount=charge_amount,
        status=DonationStatus.COMPLETED,
        payment_method=PaymentMethod.OTHER,
        months=[{"year": cy, "month": cm}],
        source=FeePaymentSource.AUTO,
        notes="Mock auto-payment (sandbox) — no gateway contact",
    )
    mark_fee_months_paid(
        member,
        [{"year": cy, "month": cm}],
        payment_method=PaymentMethod.OTHER,
        source=FeePaymentSource.AUTO,
        fee_payment=payment,
        transaction_id=f"MOCK-AUTO-{payment.pk}",
        actor=None,
    )
    ny, nm = add_months(cy, cm, 1)
    profile.refresh_from_db()
    if profile.is_enabled:
        profile.next_charge_on = date(ny, nm, 1)
        profile.save(update_fields=["next_charge_on", "updated_at"])
    record_billing_event(
        member,
        MembershipBillingEvent.Action.AUTOPAY_MOCK_CHARGE,
        message=f"Mock charged {cy}-{cm:02d}",
        metadata={"payment_id": str(payment.pk)},
    )
    _post_fee_payment_side_effects(payment)
    return payment


def _post_fee_payment_side_effects(payment):
    """Finance Income + FEE_PAID notification (each idempotent). Never raises."""
    try:
        from finance.membership_income import ensure_income_for_fee_payment

        ensure_income_for_fee_payment(payment)
    except Exception:
        logger.exception("Finance income posting failed for payment %s", payment.pk)
    try:
        from members.fee_notifications import notify_fee_paid

        notify_fee_paid(payment)
    except Exception:
        logger.exception("FEE_PAID notification failed for payment %s", payment.pk)


def ensure_registration_fee(member, *, actor=None):
    """Create the one-time registration fee row if missing (idempotent)."""
    from members.fee_settings import get_registration_fee_amount

    amount = get_registration_fee_amount()
    obj, created = MembershipRegistrationFee.objects.get_or_create(
        member=member,
        defaults={
            "amount": amount,
            "status": DonationStatus.PENDING,
            "currency": "BDT",
        },
    )
    if created:
        record_billing_event(
            member,
            MembershipBillingEvent.Action.LEDGER_ENSURED,
            actor=actor,
            message="Registration fee created",
            metadata={"registration_fee_id": str(obj.pk), "amount": amount},
        )
    return obj


@transaction.atomic
def initiate_registration_fee_checkout(member, *, request, actor=None, method=None):
    """Create PENDING registration fee + Transaction and return the provider URL."""
    from donations.gateway_capabilities import online_checkout_allowed
    from donations.gateways import get_gateway
    from donations.models import Transaction, TransactionPurpose
    from donations.services import generate_tran_id
    import uuid

    method = method or PaymentMethod.SSLCOMMERZ
    ok, err = online_checkout_allowed(
        method, purpose=TransactionPurpose.MEMBERSHIP_REGISTRATION
    )
    if not ok and method == PaymentMethod.SSLCOMMERZ:
        # Fall back to membership-fee toggle if registration-specific gate is unused.
        ok, err = online_checkout_allowed(
            method, purpose=TransactionPurpose.MEMBERSHIP_FEE
        )
    if not ok:
        raise ValueError(err)

    reg = ensure_registration_fee(member, actor=actor)
    if reg.status == DonationStatus.COMPLETED:
        raise ValueError("Registration fee is already paid.")

    txn = Transaction.objects.create(
        session_id=str(uuid.uuid4()),
        tran_id=generate_tran_id(),
        amount=reg.amount,
        currency=reg.currency or "BDT",
        status=DonationStatus.PENDING,
        gateway=method,
        purpose=TransactionPurpose.MEMBERSHIP_REGISTRATION,
        cus_name=f"{member.first_name} {member.last_name}".strip() or member.member_id,
        cus_email=getattr(member.user, "email", None),
        cus_phone=member.phone,
    )
    reg.transaction = txn
    reg.payment_method = method
    reg.source = FeePaymentSource.GATEWAY
    reg.status = DonationStatus.PENDING
    reg.save(
        update_fields=[
            "transaction",
            "payment_method",
            "source",
            "status",
            "updated_at",
        ]
    )
    record_billing_event(
        member,
        MembershipBillingEvent.Action.PAYMENT_INITIATED,
        actor=actor,
        message=f"Registration fee checkout ৳{reg.amount:g}",
        metadata={"registration_fee_id": str(reg.pk), "tran_id": txn.tran_id},
    )
    gateway = get_gateway(method)
    url = gateway.init_payment(reg, request)
    return reg, url


@transaction.atomic
def complete_registration_fee_payment(reg_fee, *, val_id=None, validation_data=None):
    """Idempotent completion for one-time registration fee gateway payments."""
    reg_fee = (
        MembershipRegistrationFee.objects.select_for_update(of=("self",))
        .select_related("transaction", "member")
        .get(pk=reg_fee.pk)
    )
    if reg_fee.status == DonationStatus.COMPLETED:
        _post_registration_fee_side_effects(reg_fee)
        return reg_fee

    txn = reg_fee.transaction
    if reg_fee.payment_method in (PaymentMethod.SSLCOMMERZ, PaymentMethod.BKASH) or (
        txn and txn.gateway in (PaymentMethod.SSLCOMMERZ, PaymentMethod.BKASH)
    ):
        if not validation_data or not isinstance(validation_data, dict):
            raise ValueError(
                "Gateway validation data is required to complete this registration fee."
            )
        if (validation_data.get("status") or "").upper() not in ("VALID", "VALIDATED"):
            raise ValueError("Gateway validation status is not VALID.")
        if txn and str(validation_data.get("tran_id") or "") != str(txn.tran_id):
            raise ValueError("Validated tran_id does not match registration fee.")
        from donations.money import amounts_equal, normalize_currency

        if not amounts_equal(validation_data.get("amount"), reg_fee.amount):
            raise ValueError("Validated amount does not match registration fee.")
        if txn and not amounts_equal(validation_data.get("amount"), txn.amount):
            raise ValueError("Validated amount does not match transaction.")
        expected_currency = normalize_currency(getattr(txn, "currency", None) or "BDT")
        if validation_data.get("currency") and normalize_currency(
            validation_data.get("currency")
        ) != expected_currency:
            raise ValueError("Validated currency does not match registration fee.")

    if txn:
        if validation_data:
            txn.val_id = val_id
            txn.bank_tran_id = validation_data.get("bank_tran_id")
            txn.card_type = validation_data.get("card_type")
            card_no = validation_data.get("card_no") or ""
            txn.card_no = card_no if ("*" in str(card_no) or len(str(card_no)) <= 4) else ""
            txn.card_issuer = validation_data.get("card_issuer")
            txn.risk_level = validation_data.get("risk_level")
            txn.validated_on = timezone.now()
        txn.status = DonationStatus.COMPLETED
        txn.save()

    reg_fee.status = DonationStatus.COMPLETED
    reg_fee.paid_at = timezone.now()
    reg_fee.save(update_fields=["status", "paid_at", "updated_at"])
    record_billing_event(
        reg_fee.member,
        MembershipBillingEvent.Action.PAYMENT_COMPLETED,
        message=f"Registration fee {txn.tran_id if txn else reg_fee.pk} completed",
        metadata={"registration_fee_id": str(reg_fee.pk)},
    )
    _post_registration_fee_side_effects(reg_fee)
    return reg_fee


@transaction.atomic
def record_admin_registration_fee_payment(member, *, payment_method, actor, notes="", transaction_id=""):
    reg = ensure_registration_fee(member, actor=actor)
    if reg.status == DonationStatus.COMPLETED:
        return reg
    reg.status = DonationStatus.COMPLETED
    reg.paid_at = timezone.now()
    reg.payment_method = payment_method
    reg.source = FeePaymentSource.ADMIN
    reg.notes = notes or ""
    reg.recorded_by = actor
    reg.save()
    record_billing_event(
        member,
        MembershipBillingEvent.Action.ADMIN_RECORDED,
        actor=actor,
        message=f"Admin recorded registration fee via {payment_method}",
        metadata={"registration_fee_id": str(reg.pk), "transaction_id": transaction_id},
    )
    _post_registration_fee_side_effects(reg)
    return reg


def _post_registration_fee_side_effects(reg_fee):
    try:
        from finance.membership_income import ensure_income_for_registration_fee

        ensure_income_for_registration_fee(reg_fee)
    except Exception:
        logger.exception("Finance income posting failed for registration fee %s", reg_fee.pk)
    try:
        from members.fee_notifications import notify_registration_fee_paid

        notify_registration_fee_paid(reg_fee)
    except Exception:
        logger.exception("Registration FEE_PAID notification failed for %s", reg_fee.pk)


def seed_ledger_for_new_member(member, *, actor=None):
    cy, cm = current_year_month()
    ensure_registration_fee(member, actor=actor)
    ensure_ledger_months(member, cy, cm, actor=actor)
    get_or_create_autopay(member)
