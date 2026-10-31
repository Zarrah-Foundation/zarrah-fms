"""Durable gateway webhook/IPN persistence (shared one-time + recurring).

Never store passwords, store_passwd, SALT keys, or unmasked PANs.
"""

from __future__ import annotations

import hashlib
import logging

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.choices import PaymentMethod
from donations.models import (
    GatewayWebhookEvent,
    PaymentMethodConfig,
    WebhookProcessingStatus,
)

logger = logging.getLogger(__name__)


def sanitize_ipn_payload(data: dict) -> dict:
    allowed = {
        "status",
        "tran_id",
        "val_id",
        "amount",
        "currency",
        "bank_tran_id",
        "card_type",
        "card_issuer",
        "risk_level",
        "subscription_id",
        "value_a",
        "value_b",
        "value_c",
        "value_d",
        "purpose",
        "paymentID",
        "paymentId",
        "signature",
        "agreementId",
        "trxId",
        "merchantInvoiceNumber",
        "merchantInvoice",
    }
    out = {}
    for key in allowed:
        if key in data and data[key] is not None:
            out[key] = str(data[key])[:255]
    card_no = data.get("card_no")
    if card_no and ("*" in str(card_no) or len(str(card_no)) <= 4):
        out["card_no"] = str(card_no)[:20]
    return out


def external_event_id(data: dict) -> str:
    for key in ("val_id", "paymentID", "paymentId", "bank_tran_id", "tran_id", "trxId"):
        if data.get(key):
            return f"{key}:{data.get(key)}"
    digest = hashlib.sha256(repr(sorted((str(k), str(v)) for k, v in data.items())).encode("utf-8")).hexdigest()
    return f"digest:{digest}"


def record_webhook_event(provider, data: dict, *, event_type="ipn"):
    """Idempotent durable receipt. Returns (event, created).

    Success/IPN settlement paths share the same external_event_id (val_id/…)
    so duplicate gateway deliveries collapse to one business effect.

    Fail/cancel returns are namespaced by event_type so they never block a
    later valid settlement IPN that reuses the same tran_id.
    """
    external_id = external_event_id(data)
    et = (event_type or "ipn")[:80]
    et_l = et.lower()
    if "fail" in et_l or "cancel" in et_l:
        external_id = f"{et}:{external_id}"[:255]
    safe = sanitize_ipn_payload(data)
    digest = hashlib.sha256(repr(sorted(safe.items())).encode("utf-8")).hexdigest()
    existing = GatewayWebhookEvent.objects.filter(
        provider=provider, external_event_id=external_id
    ).first()
    if existing:
        return existing, False
    try:
        # Nested atomic so IntegrityError does not poison the outer request txn.
        with transaction.atomic():
            event = GatewayWebhookEvent.objects.create(
                provider=provider,
                event_type=et,
                external_event_id=external_id,
                payload_digest=digest,
                safe_payload=safe,
            )
        return event, True
    except IntegrityError:
        event = GatewayWebhookEvent.objects.get(
            provider=provider, external_event_id=external_id
        )
        return event, False


def mark_webhook_processed(event: GatewayWebhookEvent, *, subscription=None, charge=None):
    if event is None:
        return
    event.processing_status = WebhookProcessingStatus.PROCESSED
    event.processed_at = timezone.now()
    fields = ["processing_status", "processed_at"]
    if subscription is not None:
        event.subscription = subscription
        fields.append("subscription")
    if charge is not None:
        event.charge = charge
        fields.append("charge")
    event.save(update_fields=fields)
    _touch_provider_ipn(event.provider, status="SUCCESS")


def mark_webhook_failed(event: GatewayWebhookEvent, message: str):
    if event is None:
        return
    event.processing_status = WebhookProcessingStatus.FAILED
    event.error_message = (message or "")[:300]
    event.processed_at = timezone.now()
    event.save(update_fields=["processing_status", "error_message", "processed_at"])
    _touch_provider_ipn(event.provider, status="FAILED")


def mark_webhook_ignored(event: GatewayWebhookEvent, message: str = ""):
    if event is None:
        return
    event.processing_status = WebhookProcessingStatus.IGNORED
    event.error_message = (message or "")[:300]
    event.processed_at = timezone.now()
    event.save(update_fields=["processing_status", "error_message", "processed_at"])


def webhook_already_processed(event: GatewayWebhookEvent) -> bool:
    return bool(
        event
        and event.processing_status == WebhookProcessingStatus.PROCESSED
    )


def _touch_provider_ipn(provider: str, *, status: str):
    """Best-effort ops timestamp; never fail payment processing on lock contention."""
    try:
        with transaction.atomic():
            PaymentMethodConfig.objects.filter(method=provider).update(
                last_ipn_at=timezone.now(),
                last_ipn_status=(status or "")[:20],
            )
    except Exception:
        logger.exception("Failed to update last_ipn for %s", provider)


# Back-compat aliases used by recurring_services historically.
_sanitize_ipn_payload = sanitize_ipn_payload
_external_event_id = external_event_id
