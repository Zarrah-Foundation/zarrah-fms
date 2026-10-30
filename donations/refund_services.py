"""Refund workflow — Super Admin approval required; no fake provider success."""

from __future__ import annotations

import logging
import uuid

from django.db import transaction
from django.utils import timezone

from core.choices import DonationStatus, PaymentMethod
from donations.models import RefundRequest, RefundStatus, Transaction
from donations.payment_ops import log_payment_event

logger = logging.getLogger(__name__)


class RefundError(Exception):
    def __init__(self, message, *, code="error"):
        super().__init__(message)
        self.code = code


def refundable_amount(txn: Transaction) -> float:
    if txn.status != DonationStatus.COMPLETED:
        return 0.0
    prior = (
        RefundRequest.objects.filter(
            transaction=txn,
            status__in=[
                RefundStatus.REQUESTED,
                RefundStatus.APPROVED,
                RefundStatus.PROCESSING,
                RefundStatus.REFUNDED,
            ],
        ).count()
    )
    # Sum completed/pending refund amounts
    from django.db.models import Sum

    used = (
        RefundRequest.objects.filter(
            transaction=txn,
            status__in=[
                RefundStatus.REQUESTED,
                RefundStatus.APPROVED,
                RefundStatus.PROCESSING,
                RefundStatus.REFUNDED,
            ],
        ).aggregate(total=Sum("amount"))["total"]
        or 0.0
    )
    return max(0.0, float(txn.amount) - float(used))


@transaction.atomic
def request_refund(*, transaction_obj: Transaction, amount, reason, actor):
    if not reason or not str(reason).strip():
        raise RefundError("Refund reason is required.", code="reason")
    try:
        amount = float(amount)
    except (TypeError, ValueError) as exc:
        raise RefundError("Invalid refund amount.", code="amount") from exc
    if amount <= 0:
        raise RefundError("Refund amount must be positive.", code="amount")

    txn = Transaction.objects.select_for_update().get(pk=transaction_obj.pk)
    if txn.status != DonationStatus.COMPLETED:
        raise RefundError("Only completed transactions can be refunded.", code="status")
    available = refundable_amount(txn)
    if amount > available + 1e-6:
        raise RefundError(
            f"Refund amount exceeds refundable balance (৳{available:g}).",
            code="overflow",
        )

    # Provider refund support gate
    from donations.provider_capabilities import all_provider_health

    health = {h.method: h for h in all_provider_health()}.get(txn.gateway)
    if health is None or not health.refund.code_support:
        raise RefundError("Provider refund: Not supported.", code="unsupported")
    if not health.refund.configured and txn.gateway != PaymentMethod.SSLCOMMERZ:
        raise RefundError("Provider refund: Not configured.", code="not_configured")
    # SSLCommerz: allow request when refunds_enabled on config; still no fake success.
    from donations.models import PaymentMethodConfig

    cfg = PaymentMethodConfig.objects.filter(method=txn.gateway).first()
    if cfg is not None and not cfg.refunds_enabled:
        raise RefundError("Provider refund: Not configured.", code="not_configured")

    idem = f"refund:{txn.pk}:{uuid.uuid4().hex[:12]}"
    req = RefundRequest.objects.create(
        transaction=txn,
        amount=amount,
        currency=txn.currency or "BDT",
        reason=str(reason).strip()[:2000],
        status=RefundStatus.REQUESTED,
        requested_by=actor,
        provider=txn.gateway,
        idempotency_key=idem,
    )
    log_payment_event(
        actor=actor,
        action="refund_requested",
        provider=txn.gateway,
        entity="RefundRequest",
        entity_id=str(req.pk),
        message=f"Refund ৳{amount:g} requested",
    )
    return req


def _is_super_admin(user) -> bool:
    from accounts.models import Role

    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return getattr(user, "role", None) == Role.SUPER_ADMIN


def approve_refund(*, refund: RefundRequest, actor):
    if not _is_super_admin(actor):
        raise RefundError("Only Super Admin can approve refunds.", code="forbidden")
    with transaction.atomic():
        refund = RefundRequest.objects.select_for_update().get(pk=refund.pk)
        if refund.status != RefundStatus.REQUESTED:
            raise RefundError("Refund is not awaiting approval.", code="state")
        refund.status = RefundStatus.APPROVED
        refund.approved_by = actor
        refund.approved_at = timezone.now()
        refund.save(
            update_fields=["status", "approved_by", "approved_at", "updated_at"]
        )
        log_payment_event(
            actor=actor,
            action="refund_approved",
            provider=refund.provider,
            entity="RefundRequest",
            entity_id=str(refund.pk),
            message="Refund approved by Super Admin",
        )
    # Separate transaction so provider failure does not roll back approval.
    return process_approved_refund(refund=refund, actor=actor)


@transaction.atomic
def reject_refund(*, refund: RefundRequest, actor, reason=""):
    if not _is_super_admin(actor):
        raise RefundError("Only Super Admin can reject refunds.", code="forbidden")
    refund = RefundRequest.objects.select_for_update().get(pk=refund.pk)
    if refund.status != RefundStatus.REQUESTED:
        raise RefundError("Refund is not awaiting approval.", code="state")
    refund.status = RefundStatus.REJECTED
    refund.approved_by = actor
    refund.approved_at = timezone.now()
    refund.rejection_reason = (reason or "Rejected")[:2000]
    refund.save()
    log_payment_event(
        actor=actor,
        action="refund_rejected",
        provider=refund.provider,
        entity="RefundRequest",
        entity_id=str(refund.pk),
        message="Refund rejected",
    )
    return refund


def process_approved_refund(*, refund: RefundRequest, actor=None):
    """Call provider refund API. Marks REFUNDED only on confirmed success."""
    with transaction.atomic():
        refund = RefundRequest.objects.select_for_update().get(pk=refund.pk)
        if refund.status not in (RefundStatus.APPROVED, RefundStatus.PROCESSING):
            raise RefundError("Refund cannot be processed in current state.", code="state")
        refund.status = RefundStatus.PROCESSING
        refund.save(update_fields=["status", "updated_at"])

    from donations.gateways import get_gateway
    from donations.gateways.base import PaymentGatewayError

    try:
        gateway = get_gateway(refund.provider)
        result = gateway.refund(
            transaction=refund.transaction,
            amount=refund.amount,
            reason=refund.reason,
        )
    except PaymentGatewayError as exc:
        RefundRequest.objects.filter(pk=refund.pk).update(
            status=RefundStatus.FAILED,
            provider_message=str(exc)[:300],
            updated_at=timezone.now(),
        )
        log_payment_event(
            actor=actor,
            action="refund_failed",
            provider=refund.provider,
            entity="RefundRequest",
            entity_id=str(refund.pk),
            message=str(exc)[:300],
        )
        raise RefundError(str(exc), code="provider") from exc

    # Only mark refunded when provider returns a confirmed payload.
    if not result or not result.get("confirmed"):
        RefundRequest.objects.filter(pk=refund.pk).update(
            status=RefundStatus.FAILED,
            provider_message="Provider did not confirm refund.",
            updated_at=timezone.now(),
        )
        raise RefundError("Provider refund: Not confirmed.", code="provider")

    with transaction.atomic():
        refund = RefundRequest.objects.select_for_update().get(pk=refund.pk)
        refund.status = RefundStatus.REFUNDED
        refund.provider_reference = str(result.get("reference") or "")[:255]
        refund.provider_message = str(result.get("message") or "")[:300]
        refund.processed_at = timezone.now()
        refund.save()

        txn = refund.transaction
        if refundable_amount(txn) <= 1e-6:
            txn.status = DonationStatus.REFUNDED
            txn.save(update_fields=["status"])
            try:
                donation = txn.donation
                donation.status = DonationStatus.REFUNDED
                donation.save(update_fields=["status", "updated_at"])
            except Exception:
                pass

    log_payment_event(
        actor=actor,
        action="refund_completed",
        provider=refund.provider,
        entity="RefundRequest",
        entity_id=str(refund.pk),
        message="Refund completed after provider confirmation",
    )
    return refund
