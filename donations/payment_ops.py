"""Payment operations audit log (never stores secrets)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_SECRET_KEYS = {
    "password",
    "passwd",
    "store_passwd",
    "store_password",
    "salt",
    "salt_key",
    "api_secret",
    "secret",
    "pin",
    "cvv",
    "card_no",
    "card_number",
}


def _sanitize_metadata(meta: dict | None) -> dict | None:
    if not meta:
        return None
    out = {}
    for k, v in meta.items():
        key = str(k).lower()
        if any(s in key for s in _SECRET_KEYS):
            out[k] = "[redacted]"
        else:
            out[k] = v
    return out


def log_payment_event(
    *,
    action: str,
    actor=None,
    provider="",
    entity="",
    entity_id="",
    message="",
    metadata=None,
):
    try:
        from donations.models import PaymentOpsEvent

        return PaymentOpsEvent.objects.create(
            actor=actor if actor and getattr(actor, "is_authenticated", False) else None,
            action=(action or "")[:80],
            provider=(provider or "")[:20],
            entity=(entity or "")[:80],
            entity_id=str(entity_id or "")[:80],
            message=(message or "")[:400],
            metadata=_sanitize_metadata(metadata),
        )
    except Exception:
        logger.exception("Failed to write PaymentOpsEvent for %s", action)
        return None
