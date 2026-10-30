"""Provider capability matrix — never expose unsupported recurring as available."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from core.choices import PaymentMethod
from donations.models import PaymentMethodConfig


@dataclass(frozen=True)
class CapabilityFlag:
    code_support: bool
    configured: bool
    merchant_enabled: bool
    verified: bool
    available: bool
    status: str
    detail: str = ""


@dataclass
class ProviderHealth:
    method: str
    label: str
    implemented: bool
    connection: CapabilityFlag
    one_time: CapabilityFlag
    recurring: CapabilityFlag
    refund: CapabilityFlag
    cancel_recurring: CapabilityFlag
    webhook: CapabilityFlag
    validate: CapabilityFlag
    sandbox: bool | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _cap(*, code, configured, merchant=True, verified=False, detail="", available=None):
    if not code:
        return CapabilityFlag(
            False, False, False, False, False, "Unavailable", detail or "Not supported."
        )
    if not configured:
        return CapabilityFlag(
            True, False, False, False, False, "Not configured", detail or "Not configured."
        )
    if not merchant:
        return CapabilityFlag(
            True, True, False, False, False, "Not configured",
            detail or "Merchant feature not enabled.",
        )
    avail = verified if available is None else available
    if verified:
        return CapabilityFlag(True, True, True, True, True, "Verified", detail)
    return CapabilityFlag(
        True, True, True, False, bool(avail), "Configured",
        detail or "Configured but not live-verified.",
    )


def sslcommerz_health() -> ProviderHealth:
    from donations.credential_service import public_credential_status, resolve_sslcommerz_credentials
    from donations.recurring_config import sslcommerz_recurring_configured

    creds = resolve_sslcommerz_credentials()
    pub = public_credential_status()
    cfg = PaymentMethodConfig.objects.filter(method=PaymentMethod.SSLCOMMERZ).first()
    rec = sslcommerz_recurring_configured()

    conn_status = "Configured" if creds.configured else "Not configured"
    if cfg and cfg.last_test_status == "SUCCESS":
        conn_status = "Verified"
    elif cfg and cfg.last_test_status == "FAILED":
        conn_status = "Failed"

    connection = CapabilityFlag(
        True,
        creds.configured,
        True,
        conn_status == "Verified",
        creds.configured,
        conn_status,
        ((cfg.last_test_message if cfg else "") or "")[:200],
    )
    one_time = _cap(
        code=True,
        configured=creds.configured,
        merchant=bool(not cfg or (cfg.is_enabled and cfg.enabled_for_donation)),
        verified=bool(cfg and cfg.one_time_verified_at),
        available=creds.configured,
    )
    # Recurring: env/DB salt+plan required. Merchant flag is required when
    # recurring secrets live in the DB (matches recurring_checkout_allowed).
    merchant_ok = True
    if cfg is not None and (cfg.encrypted_salt_key or cfg.recurring_plan_refer):
        merchant_ok = bool(cfg.merchant_recurring_enabled)
    recurring = _cap(
        code=True,
        configured=rec.configured,
        merchant=merchant_ok,
        verified=bool(
            cfg and cfg.recurring_auth_verified_at and cfg.recurring_charge_verified_at
        ),
        available=rec.configured and merchant_ok,
        detail=rec.reason if not rec.configured else (
            "" if merchant_ok else "Merchant recurring not confirmed in admin."
        ),
    )
    refund_enabled = bool(cfg and cfg.refunds_enabled and creds.configured)
    refund = _cap(
        code=True,
        configured=refund_enabled,
        merchant=refund_enabled,
        verified=bool(cfg and cfg.refund_verified_at),
        available=False,  # never claim available until live-verified
        detail="" if refund_enabled else "Provider refund: Not configured.",
    )
    webhook = _cap(
        code=True,
        configured=creds.configured,
        verified=bool(cfg and cfg.ipn_verified_at),
        available=creds.configured,
        detail="" if (cfg and cfg.ipn_verified_at) else "Public IPN not live-verified.",
    )
    notes = []
    if not rec.configured:
        notes.append("SSLCommerz recurring: Not configured.")
    if cfg and cfg.last_ipn_status == "FAILED":
        notes.append("Last IPN processing reported failure.")
    notes.append("LIVE VALIDATION PENDING until public HTTPS staging succeeds.")

    return ProviderHealth(
        method=PaymentMethod.SSLCOMMERZ,
        label="SSLCommerz",
        implemented=True,
        connection=connection,
        one_time=one_time,
        recurring=recurring,
        refund=refund,
        cancel_recurring=CapabilityFlag(
            False, False, False, False, False, "Unavailable",
            "Provider cancel API not confirmed.",
        ),
        webhook=webhook,
        validate=_cap(code=True, configured=creds.configured, verified=one_time.verified),
        sandbox=pub.get("is_sandbox"),
        notes=notes,
    )


def bkash_health() -> ProviderHealth:
    cfg = PaymentMethodConfig.objects.filter(method=PaymentMethod.BKASH).first()
    has_creds = bool(cfg and cfg.api_app_key and cfg.encrypted_api_secret and cfg.is_enabled)
    one_time = _cap(
        code=True,
        configured=has_creds,
        merchant=bool(cfg and cfg.enabled_for_donation) if has_creds else False,
        verified=bool(cfg and cfg.one_time_verified_at),
        available=False,  # not live-verified
        detail="" if has_creds else "bKash is not configured.",
    )
    # Recurring agreement/charge APIs are not implemented — never "Configured".
    recurring = CapabilityFlag(
        False,
        False,
        False,
        False,
        False,
        "Not implemented",
        "bKash recurring: NOT IMPLEMENTED (adapter refuses; no merchant agreement API wired).",
    )
    return ProviderHealth(
        method=PaymentMethod.BKASH,
        label="bKash",
        implemented=True,
        connection=_cap(code=True, configured=has_creds, verified=bool(cfg and cfg.last_test_status == "SUCCESS")),
        one_time=one_time,
        recurring=recurring,
        refund=CapabilityFlag(
            False, False, False, False, False, "Not implemented", "bKash refund: NOT IMPLEMENTED."
        ),
        cancel_recurring=CapabilityFlag(
            False, False, False, False, False, "Not implemented",
            "bKash cancel recurring: NOT IMPLEMENTED.",
        ),
        webhook=_cap(code=True, configured=has_creds, verified=bool(cfg and cfg.ipn_verified_at)),
        validate=_cap(code=True, configured=has_creds, verified=False),
        sandbox=None if not cfg else cfg.is_sandbox,
        notes=[
            "bKash must not appear as an operational recurring provider.",
            "LIVE VALIDATION PENDING.",
        ],
    )


def nagad_health() -> ProviderHealth:
    cfg = PaymentMethodConfig.objects.filter(method=PaymentMethod.NAGAD).first()
    has_creds = bool(cfg and cfg.api_app_key and cfg.encrypted_api_secret and cfg.is_enabled)
    return ProviderHealth(
        method=PaymentMethod.NAGAD,
        label="Nagad",
        implemented=True,
        connection=_cap(code=True, configured=has_creds, verified=bool(cfg and cfg.last_test_status == "SUCCESS")),
        one_time=_cap(
            code=True,
            configured=has_creds,
            verified=bool(cfg and cfg.one_time_verified_at),
            available=False,
            detail="" if has_creds else "Nagad is not configured.",
        ),
        recurring=CapabilityFlag(
            False, False, False, False, False, "Not implemented",
            "Nagad recurring: NOT IMPLEMENTED.",
        ),
        refund=CapabilityFlag(
            False, False, False, False, False, "Not implemented", "Nagad refund: NOT IMPLEMENTED."
        ),
        cancel_recurring=CapabilityFlag(
            False, False, False, False, False, "Not implemented",
            "Nagad cancel recurring: NOT IMPLEMENTED.",
        ),
        webhook=_cap(code=True, configured=has_creds, verified=bool(cfg and cfg.ipn_verified_at)),
        validate=_cap(code=True, configured=has_creds, verified=False),
        sandbox=None if not cfg else cfg.is_sandbox,
        notes=[
            "Nagad must not appear as an operational recurring provider.",
            "LIVE VALIDATION PENDING.",
        ],
    )


def all_provider_health() -> list[ProviderHealth]:
    return [sslcommerz_health(), bkash_health(), nagad_health()]


def recurring_providers_for_checkout() -> list[dict]:
    out = []
    for h in all_provider_health():
        if h.recurring.available:
            out.append({"method": h.method, "label": h.label, "status": h.recurring.status})
    return out


def provider_capability_matrix() -> list[dict]:
    return [h.to_dict() for h in all_provider_health()]
