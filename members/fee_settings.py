"""Membership fee configuration (monthly, registration, starting month)."""

from __future__ import annotations

from decimal import Decimal
from threading import local

from django.utils import timezone

# Documented configuration defaults (not hardcoded business amounts in views).
DEFAULT_MONTHLY_FEE_BDT = Decimal("50.00")
DEFAULT_REGISTRATION_FEE_BDT = Decimal("100.00")
# Sentinel start: max(configured, approval) == approval until admin sets a later month.
DEFAULT_FEE_START_YEAR = 1
DEFAULT_FEE_START_MONTH = 1

_request_cache = local()


def clear_fee_settings_cache():
    for attr in ("settings", "monthly", "registration", "start"):
        if hasattr(_request_cache, attr):
            delattr(_request_cache, attr)


def get_fee_settings():
    from members.models import MembershipFeeSettings

    cached = getattr(_request_cache, "settings", None)
    if cached is not None:
        return cached
    obj = MembershipFeeSettings.load()
    _request_cache.settings = obj
    return obj


def get_monthly_fee_amount() -> float:
    cached = getattr(_request_cache, "monthly", None)
    if cached is not None:
        return cached
    amount = float(get_fee_settings().monthly_fee_amount)
    _request_cache.monthly = amount
    return amount


def get_registration_fee_amount() -> float:
    cached = getattr(_request_cache, "registration", None)
    if cached is not None:
        return cached
    amount = float(get_fee_settings().registration_fee_amount)
    _request_cache.registration = amount
    return amount


def configured_fee_start_period() -> tuple[int, int]:
    cached = getattr(_request_cache, "start", None)
    if cached is not None:
        return cached
    settings = get_fee_settings()
    period = (int(settings.fee_start_year), int(settings.fee_start_month))
    _request_cache.start = period
    return period


def member_approval_period(member) -> tuple[int, int]:
    """Authoritative liability anchor: membership approval timestamp."""
    stamp = getattr(member, "approved_at", None) or getattr(member, "joined_at", None)
    if stamp is None:
        stamp = getattr(member, "created_at", None)
    if stamp:
        local = timezone.localtime(stamp).date() if timezone.is_aware(stamp) else stamp
        if hasattr(local, "year"):
            return int(local.year), int(local.month)
    today = timezone.localdate()
    return today.year, today.month


def member_fee_start_period(member) -> tuple[int, int]:
    """First month a member is liable for monthly fees.

    Existing members (approved before the configured start) begin at the
    configured Membership Fee Starting Month. New members begin at their
    approval month. Implemented as max(configured_start, approval_month).
    """
    configured = configured_fee_start_period()
    approval = member_approval_period(member)
    return max(configured, approval)


def format_amount_bdt(amount, *, language: str = "en") -> str:
    value = Decimal(str(amount)).quantize(Decimal("0.01"))
    if value == value.to_integral():
        text = f"৳{int(value)}"
    else:
        text = f"৳{value}"
    if (language or "en").startswith("bn"):
        return text.translate(str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯"))
    return text
