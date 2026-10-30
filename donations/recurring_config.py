"""SSLCommerz / recurring donation configuration (env + optional DB; no secrets in logs)."""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings


@dataclass(frozen=True)
class RecurringConfigStatus:
    configured: bool
    reason: str
    plan_refer: str
    has_salt: bool
    failure_threshold: int
    management_token_ttl_seconds: int
    source: str = "none"  # env | database | none


def recurring_failure_threshold() -> int:
    return int(getattr(settings, "RECURRING_DONATION_FAILURE_THRESHOLD", 3) or 3)


def management_token_ttl_seconds() -> int:
    return int(
        getattr(settings, "RECURRING_DONATION_MANAGEMENT_TOKEN_TTL", 60 * 60 * 24 * 30)
        or (60 * 60 * 24 * 30)
    )


def _env_salt() -> str:
    return (getattr(settings, "SSLCOMMERZ_SALT_KEY", None) or "").strip()


def _env_plan() -> str:
    return (getattr(settings, "SSLCOMMERZ_RECURRING_PLAN_REFER", None) or "").strip()


def _db_recurring() -> tuple[str, str]:
    """Return (salt, plan) from PaymentMethodConfig when present."""
    try:
        from core.choices import PaymentMethod
        from donations.models import PaymentMethodConfig

        cfg = PaymentMethodConfig.objects.filter(method=PaymentMethod.SSLCOMMERZ).first()
        if cfg is None:
            return "", ""
        salt = cfg.get_salt_key() if hasattr(cfg, "get_salt_key") else ""
        plan = (cfg.recurring_plan_refer or "").strip()
        return salt, plan
    except Exception:
        return "", ""


def sslcommerz_recurring_salt() -> str:
    env = _env_salt()
    if env:
        return env
    salt, _plan = _db_recurring()
    return salt


def sslcommerz_recurring_plan_refer() -> str:
    env = _env_plan()
    if env:
        return env
    _salt, plan = _db_recurring()
    return plan


def sslcommerz_recurring_configured() -> RecurringConfigStatus:
    """True only when merchant SALT + plan refer are present (never invent)."""
    env_salt, env_plan = _env_salt(), _env_plan()
    db_salt, db_plan = _db_recurring()
    salt = env_salt or db_salt
    plan = env_plan or db_plan
    source = "none"
    if env_salt and env_plan:
        source = "env"
    elif db_salt and db_plan:
        source = "database"
    elif salt and plan:
        source = "mixed"

    has_salt = bool(salt)
    thr = recurring_failure_threshold()
    ttl = management_token_ttl_seconds()
    if not has_salt and not plan:
        return RecurringConfigStatus(
            False,
            "SSLCommerz recurring is not configured (missing SALT key and plan refer).",
            "",
            False,
            thr,
            ttl,
            source,
        )
    if not has_salt:
        return RecurringConfigStatus(
            False,
            "SSLCommerz recurring is not configured (missing SSLCOMMERZ_SALT_KEY).",
            plan,
            False,
            thr,
            ttl,
            source,
        )
    if not plan:
        return RecurringConfigStatus(
            False,
            "SSLCommerz recurring is not configured (missing SSLCOMMERZ_RECURRING_PLAN_REFER).",
            "",
            True,
            thr,
            ttl,
            source,
        )
    return RecurringConfigStatus(True, "", plan, True, thr, ttl, source)
