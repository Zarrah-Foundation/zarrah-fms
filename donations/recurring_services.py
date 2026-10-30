"""Recurring donation domain services (SSLCommerz-first, gateway-scheduled).

Membership AutoPay is intentionally separate. One-time donations unchanged.
"""

from __future__ import annotations

import logging
import secrets
import uuid
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.choices import DonationStatus, PaymentMethod
from donations.money import amounts_equal, normalize_currency
from donations.models import (
    Donation,
    DonationRecurringCharge,
    DonationSubscription,
    GatewayWebhookEvent,
    RecurringChargeKind,
    RecurringChargeStatus,
    SubscriptionFrequency,
    SubscriptionStatus,
    Transaction,
    TransactionPurpose,
    WebhookProcessingStatus,
)
from donations.recurring_config import (
    management_token_ttl_seconds,
    recurring_failure_threshold,
    sslcommerz_recurring_configured,
)
from donations.webhook_services import (
    mark_webhook_failed,
    mark_webhook_processed,
    record_webhook_event,
)

logger = logging.getLogger(__name__)

MIN_RECURRING_AMOUNT = 1.0
MAX_RECURRING_AMOUNT = 1_000_000.0


class RecurringDonationError(Exception):
    def __init__(self, message, *, code="error"):
        super().__init__(message)
        self.code = code


def _add_month(dt):
    """Advance ~1 calendar month without requiring dateutil."""
    year, month = dt.year, dt.month
    if month == 12:
        year, month = year + 1, 1
    else:
        month += 1
    day = min(dt.day, 28)
    return dt.replace(year=year, month=month, day=day)


def issue_management_token(subscription: DonationSubscription) -> str:
    token = secrets.token_urlsafe(32)
    subscription.management_token = token
    subscription.management_token_expires_at = timezone.now() + timedelta(
        seconds=management_token_ttl_seconds()
    )
    subscription.save(
        update_fields=["management_token", "management_token_expires_at", "updated_at"]
    )
    return token


def get_subscription_by_management_token(token: str):
    token = (token or "").strip()
    if not token:
        return None
    sub = DonationSubscription.objects.filter(management_token=token).first()
    if sub is None:
        return None
    if sub.management_token_expires_at and sub.management_token_expires_at < timezone.now():
        return None
    return sub


@transaction.atomic
def create_recurring_subscription(
    *,
    amount,
    category,
    donor_name,
    donor_email="",
    donor_phone="",
    message="",
    is_anonymous=False,
    user=None,
    frequency=SubscriptionFrequency.MONTHLY,
    gateway=PaymentMethod.SSLCOMMERZ,
):
    from donations.gateway_capabilities import (
        CMS_RECURRING_DISABLED_MSG,
        recurring_checkout_allowed,
    )

    ok, err = recurring_checkout_allowed(gateway)
    if not ok:
        code = "cms_disabled" if err == CMS_RECURRING_DISABLED_MSG else "not_configured"
        raise RecurringDonationError(err, code=code)

    if frequency != SubscriptionFrequency.MONTHLY:
        raise RecurringDonationError(
            "Only monthly recurring donations are supported.",
            code="frequency",
        )

    try:
        amount = float(amount)
    except (TypeError, ValueError) as exc:
        raise RecurringDonationError("Invalid amount.", code="amount") from exc
    if amount < MIN_RECURRING_AMOUNT or amount > MAX_RECURRING_AMOUNT:
        raise RecurringDonationError("Amount is out of allowed range.", code="amount")

    if not donor_name and not is_anonymous:
        raise RecurringDonationError("Donor name is required.", code="donor")
    if is_anonymous:
        donor_name = donor_name or "Anonymous"
    if not (donor_email or "").strip() and not (donor_phone or "").strip():
        raise RecurringDonationError(
            "Email or phone is required for recurring donations.",
            code="contact",
        )

    cfg = sslcommerz_recurring_configured()
    sub = DonationSubscription.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        category=category,
        donor_name=donor_name.strip(),
        donor_email=(donor_email or "").strip() or None,
        donor_phone=(donor_phone or "").strip(),
        amount=amount,
        currency="BDT",
        frequency=SubscriptionFrequency.MONTHLY,
        payment_gateway=PaymentMethod.SSLCOMMERZ,
        status=SubscriptionStatus.DRAFT,
        gateway_plan_refer=cfg.plan_refer,
        message=message or None,
        is_anonymous=bool(is_anonymous),
    )
    issue_management_token(sub)
    _audit_subscription(sub, "subscription_created", actor=user, extra={"frequency": sub.frequency})
    return sub


class _AuthPayable:
    """Adapter object for SSLCommerz init_recurring_authorization."""

    payment_purpose = "DONATION_RECURRING"
    is_recurring_authorization = True
    product_name = "Recurring donation"

    def __init__(self, subscription, transaction):
        self.subscription = subscription
        self.transaction = transaction
        self.amount = subscription.amount
        self.currency = subscription.currency or "BDT"
        self.donor_name = subscription.donor_name
        self.donor_email = subscription.donor_email or ""
        self.donor_phone = subscription.donor_phone or ""


@transaction.atomic
def start_recurring_authorization(subscription, *, request):
    """Move DRAFT → PENDING_AUTH and redirect to SSLCommerz with schedule."""
    from donations.gateways import get_gateway
    from donations.services import generate_tran_id

    subscription = DonationSubscription.objects.select_for_update().get(pk=subscription.pk)
    if subscription.status not in (
        SubscriptionStatus.DRAFT,
        SubscriptionStatus.PENDING_AUTHORIZATION,
    ):
        raise RecurringDonationError(
            "This subscription cannot start authorization.",
            code="state",
        )

    from donations.gateway_capabilities import recurring_checkout_allowed

    ok, err = recurring_checkout_allowed(subscription.payment_gateway)
    if not ok:
        raise RecurringDonationError(err, code="not_configured")

    txn = Transaction.objects.create(
        session_id=str(uuid.uuid4()),
        tran_id=generate_tran_id(),
        amount=subscription.amount,
        currency="BDT",
        status=DonationStatus.PENDING,
        gateway=PaymentMethod.SSLCOMMERZ,
        purpose=TransactionPurpose.DONATION,
        cus_name=subscription.donor_name,
        cus_email=subscription.donor_email,
        cus_phone=subscription.donor_phone or None,
    )
    charge = DonationRecurringCharge.objects.create(
        subscription=subscription,
        kind=RecurringChargeKind.AUTHORIZATION,
        attempt_number=1,
        amount=subscription.amount,
        currency="BDT",
        status=RecurringChargeStatus.PENDING,
        provider=PaymentMethod.SSLCOMMERZ,
        idempotency_key=f"auth:{subscription.pk}:{txn.tran_id}",
        transaction=txn,
    )
    subscription.status = SubscriptionStatus.PENDING_AUTHORIZATION
    subscription.save(update_fields=["status", "updated_at"])

    payable = _AuthPayable(subscription, txn)
    gateway = get_gateway(PaymentMethod.SSLCOMMERZ)
    day = timezone.localdate().day
    url = gateway.init_recurring_authorization(
        payable, request, subscription=subscription, schedule_day=day
    )
    return subscription, charge, url


@transaction.atomic
def complete_authorization_from_gateway(
    *,
    tran_id,
    val_id,
    validation_data,
    event: GatewayWebhookEvent | None = None,
):
    """Activate subscription after validated authorization payment."""
    charge = (
        DonationRecurringCharge.objects.select_for_update()
        .select_related("subscription", "transaction")
        .filter(
            transaction__tran_id=tran_id,
            kind=RecurringChargeKind.AUTHORIZATION,
        )
        .first()
    )
    if charge is None:
        raise RecurringDonationError("Authorization charge not found.", code="not_found")

    if charge.status == RecurringChargeStatus.COMPLETED:
        _ensure_income_for_charge(charge)
        return charge

    sub = DonationSubscription.objects.select_for_update().get(pk=charge.subscription_id)
    txn = charge.transaction
    if not validation_data:
        raise RecurringDonationError("Gateway validation required.", code="validation")
    if (validation_data.get("status") or "").upper() not in ("VALID", "VALIDATED"):
        raise RecurringDonationError("Gateway validation status invalid.", code="validation")
    if str(validation_data.get("tran_id") or "") != str(txn.tran_id):
        raise RecurringDonationError("tran_id mismatch.", code="validation")
    if not amounts_equal(validation_data.get("amount"), charge.amount):
        raise RecurringDonationError("Amount mismatch.", code="amount")
    if validation_data.get("currency") and normalize_currency(
        validation_data.get("currency")
    ) != normalize_currency(charge.currency):
        raise RecurringDonationError("Currency mismatch.", code="currency")

    now = timezone.now()
    txn.val_id = val_id
    txn.bank_tran_id = validation_data.get("bank_tran_id")
    card_no = validation_data.get("card_no") or ""
    txn.card_type = validation_data.get("card_type")
    txn.card_no = card_no if ("*" in str(card_no) or len(str(card_no)) <= 4) else ""
    txn.card_issuer = validation_data.get("card_issuer")
    txn.risk_level = validation_data.get("risk_level")
    txn.validated_on = now
    txn.status = DonationStatus.COMPLETED
    txn.save()

    gateway_sub = (
        validation_data.get("subscription_id")
        or validation_data.get("subscriptionId")
        or ""
    )
    if gateway_sub:
        sub.gateway_subscription_ref = str(gateway_sub)[:255]
        sub.payment_token = str(gateway_sub)[:255]

    donation = Donation.objects.create(
        donor_name=sub.donor_name,
        donor_email=sub.donor_email,
        donor_phone=sub.donor_phone or None,
        user=sub.user,
        amount=charge.amount,
        currency="BDT",
        category=sub.category,
        message=sub.message,
        payment_method=PaymentMethod.SSLCOMMERZ,
        status=DonationStatus.COMPLETED,
        transaction=txn,
        subscription=sub,
        is_anonymous=sub.is_anonymous,
    )
    from donations.services import assign_receipt_number

    assign_receipt_number(donation)

    charge.status = RecurringChargeStatus.COMPLETED
    charge.donation = donation
    charge.provider_reference = str(
        validation_data.get("bank_tran_id") or val_id or ""
    )[:255]
    charge.processed_at = now
    if event:
        charge.gateway_event = event
    charge.save()

    sub.status = SubscriptionStatus.ACTIVE
    sub.activated_at = now
    sub.last_billed = now
    sub.last_success_at = now
    sub.consecutive_failures = 0
    sub.next_billing = _add_month(now)
    sub.save()

    if event:
        event.subscription = sub
        event.charge = charge
        event.processing_status = WebhookProcessingStatus.PROCESSED
        event.processed_at = now
        event.save(
            update_fields=[
                "subscription",
                "charge",
                "processing_status",
                "processed_at",
            ]
        )

    _ensure_income_for_charge(charge)
    _audit_subscription(sub, "subscription_activated", extra={"charge_id": str(charge.pk)})
    _notify_subscription_event(sub, "active", charge=charge)
    return charge


def _ensure_income_for_charge(charge: DonationRecurringCharge):
    donation = charge.donation
    if donation is None:
        return None, False
    from finance.donation_income import ensure_income_for_donation

    return ensure_income_for_donation(donation)


@transaction.atomic
def settle_recurring_ipn(*, validation_data, event: GatewayWebhookEvent):
    """Settle a gateway-scheduled recurring charge (not the setup authorization)."""
    if event.processing_status == WebhookProcessingStatus.PROCESSED:
        return event.charge

    sub_id = validation_data.get("value_a") or ""
    gateway_sub = validation_data.get("subscription_id") or ""
    sub = None
    if sub_id:
        sub = DonationSubscription.objects.filter(pk=sub_id).first()
    if sub is None and gateway_sub:
        sub = DonationSubscription.objects.filter(
            gateway_subscription_ref=str(gateway_sub)
        ).first()
    if sub is None:
        event.processing_status = WebhookProcessingStatus.IGNORED
        event.error_message = "No matching subscription"
        event.processed_at = timezone.now()
        event.save(update_fields=["processing_status", "error_message", "processed_at"])
        return None

    sub = DonationSubscription.objects.select_for_update().get(pk=sub.pk)
    # Authorization IPNs for the setup tran are handled separately.
    existing_auth = DonationRecurringCharge.objects.filter(
        subscription=sub,
        kind=RecurringChargeKind.AUTHORIZATION,
        transaction__tran_id=validation_data.get("tran_id"),
    ).first()
    if existing_auth:
        return complete_authorization_from_gateway(
            tran_id=validation_data.get("tran_id"),
            val_id=validation_data.get("val_id"),
            validation_data=validation_data,
            event=event,
        )

    provider_ref = str(
        validation_data.get("val_id")
        or validation_data.get("bank_tran_id")
        or validation_data.get("tran_id")
        or ""
    )
    idem = f"recurring:{sub.pk}:{provider_ref}"
    existing = DonationRecurringCharge.objects.filter(idempotency_key=idem).first()
    if existing and existing.status == RecurringChargeStatus.COMPLETED:
        event.processing_status = WebhookProcessingStatus.PROCESSED
        event.charge = existing
        event.subscription = sub
        event.processed_at = timezone.now()
        event.save()
        return existing

    if not amounts_equal(validation_data.get("amount"), sub.amount):
        _record_failure(sub, reason="Amount mismatch", event=event)
        return None
    if validation_data.get("currency") and normalize_currency(
        validation_data.get("currency")
    ) != "BDT":
        _record_failure(sub, reason="Currency mismatch", event=event)
        return None

    from donations.services import assign_receipt_number, generate_tran_id

    now = timezone.now()
    txn = Transaction.objects.create(
        session_id=str(uuid.uuid4()),
        tran_id=validation_data.get("tran_id") or generate_tran_id(),
        val_id=validation_data.get("val_id"),
        amount=sub.amount,
        currency="BDT",
        status=DonationStatus.COMPLETED,
        gateway=PaymentMethod.SSLCOMMERZ,
        purpose=TransactionPurpose.DONATION,
        cus_name=sub.donor_name,
        cus_email=sub.donor_email,
        cus_phone=sub.donor_phone or None,
        bank_tran_id=validation_data.get("bank_tran_id"),
        validated_on=now,
    )
    donation = Donation.objects.create(
        donor_name=sub.donor_name,
        donor_email=sub.donor_email,
        donor_phone=sub.donor_phone or None,
        user=sub.user,
        amount=sub.amount,
        currency="BDT",
        category=sub.category,
        message=sub.message,
        payment_method=PaymentMethod.SSLCOMMERZ,
        status=DonationStatus.COMPLETED,
        transaction=txn,
        subscription=sub,
        is_anonymous=sub.is_anonymous,
    )
    assign_receipt_number(donation)

    attempt = sub.charges.filter(kind=RecurringChargeKind.RECURRING).count() + 1
    try:
        charge = DonationRecurringCharge.objects.create(
            subscription=sub,
            kind=RecurringChargeKind.RECURRING,
            attempt_number=attempt,
            amount=sub.amount,
            currency="BDT",
            status=RecurringChargeStatus.COMPLETED,
            provider=PaymentMethod.SSLCOMMERZ,
            provider_reference=provider_ref[:255],
            idempotency_key=idem,
            transaction=txn,
            donation=donation,
            gateway_event=event,
            processed_at=now,
        )
    except IntegrityError:
        # Concurrent IPN/worker race — keep the winning charge, discard this txn/donation.
        existing = DonationRecurringCharge.objects.filter(idempotency_key=idem).first()
        if existing:
            donation.delete()
            txn.delete()
            event.processing_status = WebhookProcessingStatus.PROCESSED
            event.charge = existing
            event.subscription = sub
            event.processed_at = now
            event.save()
            return existing
        raise
    sub.last_billed = now
    sub.last_success_at = now
    sub.consecutive_failures = 0
    sub.next_billing = _add_month(now)
    if sub.status in (
        SubscriptionStatus.PAYMENT_FAILED,
        SubscriptionStatus.PENDING_AUTHORIZATION,
    ):
        sub.status = SubscriptionStatus.ACTIVE
    sub.save()

    event.subscription = sub
    event.charge = charge
    event.processing_status = WebhookProcessingStatus.PROCESSED
    event.processed_at = now
    event.save()

    _ensure_income_for_charge(charge)
    _notify_subscription_event(sub, "payment_success", charge=charge)
    return charge


def _record_failure(sub, *, reason, event=None):
    now = timezone.now()
    sub.consecutive_failures = int(sub.consecutive_failures or 0) + 1
    sub.last_failure_at = now
    sub.last_failure_reason = (reason or "")[:300]
    threshold = recurring_failure_threshold()
    if sub.consecutive_failures >= threshold:
        sub.status = SubscriptionStatus.SUSPENDED
        _notify_subscription_event(sub, "suspended")
    else:
        sub.status = SubscriptionStatus.PAYMENT_FAILED
        _notify_subscription_event(sub, "payment_failed")
    sub.save(
        update_fields=[
            "consecutive_failures",
            "last_failure_at",
            "last_failure_reason",
            "status",
            "updated_at",
        ]
    )
    if event:
        event.subscription = sub
        event.processing_status = WebhookProcessingStatus.FAILED
        event.error_message = (reason or "")[:300]
        event.processed_at = now
        event.save()


@transaction.atomic
def cancel_subscription(subscription, *, actor=None, reason="", provider_cancelled=None):
    """Cancel locally. Do not claim gateway cancel unless ``provider_cancelled`` is True.

    Flow: ACTIVE/… → CANCEL_REQUESTED → CANCELLED (local). Provider-side cancel
    is optional and merchant-API dependent; WP3 does not invent a cancel API.
    """
    subscription = DonationSubscription.objects.select_for_update().get(
        pk=subscription.pk
    )
    if subscription.status == SubscriptionStatus.CANCELLED:
        return subscription

    now = timezone.now()
    subscription.status = SubscriptionStatus.CANCEL_REQUESTED
    subscription.cancel_reason = (reason or "Cancelled by donor")[:300]
    if actor and getattr(actor, "is_authenticated", False):
        subscription.cancelled_by = actor
    subscription.save(
        update_fields=["status", "cancel_reason", "cancelled_by", "updated_at"]
    )

    # Local cancel is authoritative for donor UX. Gateway cancel is not claimed
    # unless an explicit provider confirmation is supplied by the caller.
    note = subscription.cancel_reason
    if provider_cancelled is True:
        note = (note + " | provider cancelled").strip(" |")[:300]
    elif provider_cancelled is False:
        note = (note + " | provider cancel not confirmed").strip(" |")[:300]
    elif subscription.gateway_subscription_ref:
        note = (note + " | local cancel only (provider API not invoked)").strip(" |")[
            :300
        ]

    subscription.status = SubscriptionStatus.CANCELLED
    subscription.cancelled_at = now
    subscription.cancel_reason = note
    subscription.next_billing = None
    subscription.save(
        update_fields=[
            "status",
            "cancelled_at",
            "cancel_reason",
            "next_billing",
            "updated_at",
        ]
    )
    _audit_subscription(subscription, "subscription_cancelled", actor=actor)
    _notify_subscription_event(subscription, "cancelled")
    return subscription


def _audit_subscription(subscription, action, *, actor=None, extra=None):
    """Record administrative/donor actions when an authenticated actor is present."""
    if not actor or not getattr(actor, "is_authenticated", False):
        return
    try:
        from audit.models import ActivityLog

        ActivityLog.objects.create(
            user=actor,
            action=action[:100],
            entity="DonationSubscription",
            entity_id=str(subscription.pk),
            description=f"{action} for subscription {subscription.pk}",
            new_values={
                "status": subscription.status,
                "amount": subscription.amount,
                **(extra or {}),
            },
        )
    except Exception:
        logger.exception("Audit log failed for subscription %s", subscription.pk)


@transaction.atomic
def claim_subscription_for_reconciliation(subscription, *, lock_token: str, lock_seconds=120):
    """Atomic soft-lock for reconcile workers. Returns True if claimed."""
    now = timezone.now()
    stale_before = now - timedelta(seconds=lock_seconds)
    updated = DonationSubscription.objects.filter(pk=subscription.pk).filter(
        models_q_unlocked(stale_before)
    ).update(
        processing_locked_at=now,
        processing_lock_token=lock_token,
        updated_at=now,
    )
    return updated == 1


def models_q_unlocked(stale_before):
    from django.db.models import Q

    return Q(processing_locked_at__isnull=True) | Q(
        processing_locked_at__lt=stale_before
    ) | Q(processing_lock_token="")


def release_subscription_lock(subscription, *, lock_token: str):
    DonationSubscription.objects.filter(
        pk=subscription.pk, processing_lock_token=lock_token
    ).update(processing_locked_at=None, processing_lock_token="", updated_at=timezone.now())


def reconcile_due_subscriptions(*, limit=100):
    """Reconcile due ACTIVE subscriptions (gateway-scheduled — no invented charge).

    Marks overdue subscriptions for ops visibility; settlements arrive via IPN.
    """
    now = timezone.now()
    due = (
        DonationSubscription.objects.filter(
            status=SubscriptionStatus.ACTIVE,
            next_billing__lte=now,
        )
        .order_by("next_billing")[:limit]
    )
    claimed = 0
    for sub in due:
        token = secrets.token_hex(16)
        if not claim_subscription_for_reconciliation(sub, lock_token=token):
            continue
        claimed += 1
        try:
            # Gateway-scheduled: if no successful charge since next_billing window,
            # record a soft failure for monitoring (does not invent a charge API).
            recent = sub.charges.filter(
                kind=RecurringChargeKind.RECURRING,
                status=RecurringChargeStatus.COMPLETED,
                processed_at__gte=sub.next_billing - timedelta(days=2)
                if sub.next_billing
                else now - timedelta(days=40),
            ).exists()
            if not recent and sub.last_success_at and sub.last_success_at < now - timedelta(
                days=35
            ):
                logger.warning(
                    "Recurring subscription %s appears overdue without settlement IPN",
                    sub.pk,
                )
        finally:
            release_subscription_lock(sub, lock_token=token)
    return claimed


def _notify_subscription_event(subscription, event_key, charge=None):
    """Best-effort notifications via existing infrastructure."""
    try:
        from audit.models import NotificationPriority, NotificationType
        from audit.notifications import notify
        from core.email import send_email

        titles = {
            "active": ("Recurring donation active", NotificationType.GENERAL),
            "payment_success": (
                "Recurring donation payment received",
                NotificationType.NEW_DONATION,
            ),
            "payment_failed": (
                "Recurring donation payment failed",
                NotificationType.PAYMENT_FAILED,
            ),
            "suspended": (
                "Recurring donation suspended",
                NotificationType.PAYMENT_FAILED,
            ),
            "cancelled": ("Recurring donation cancelled", NotificationType.GENERAL),
        }
        title, ntype = titles.get(
            event_key, ("Recurring donation update", NotificationType.GENERAL)
        )
        message = (
            f"{title}. Amount ৳{subscription.amount:g}/month."
        )
        if subscription.user_id:
            notify(
                title=title,
                message=message,
                ntype=ntype,
                user=subscription.user,
                priority=NotificationPriority.NORMAL,
                related_object=subscription,
            )
        if subscription.donor_email:
            send_email(
                subject=title,
                message=message,
                recipient_list=[subscription.donor_email],
            )
    except Exception:
        logger.exception(
            "Recurring donation notification failed for %s", subscription.pk
        )
