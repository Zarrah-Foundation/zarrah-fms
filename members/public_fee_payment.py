"""Public current-month membership fee payment (PAY-WP2).

Server-authoritative checkout: browser never controls member, period, amount,
or purpose. Reuses MembershipFeePayment + Transaction + SSLCommerz one-time
checkout. No schema changes.
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass
from typing import Optional

from django.core import signing
from django.core.cache import cache
from django.db import transaction
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _lazy

from core.choices import DonationStatus
from members.billing import (
    current_year_month,
    ensure_ledger_months,
    initiate_fee_checkout,
)
from members.fee_settings import member_fee_start_period
from members.models import Member, MemberStatus, MembershipFee
from members.periods import format_fee_period

logger = logging.getLogger(__name__)

TOKEN_SALT = "members.public_fee.v1"
TOKEN_MAX_AGE_SECONDS = 15 * 60
PUBLIC_PAYMENT_NOTE_PREFIX = "public_checkout:"
VERIFY_COOLDOWN_SECONDS = 3
VERIFY_MAX_PER_HOUR = 20
SESSION_PUBLIC_PAYMENT_KEY = "public_fee_payment_id"

# Stable, non-enumerating failure copy for verify failures.
GENERIC_VERIFY_FAILURE = _lazy(
    "We could not verify this Membership ID for payment."
)
OTHER_MONTHS_REQUIRE_LOGIN = _lazy(
    "Payments for other months require you to log in to your account."
)


class PublicFeeError(Exception):
    """User-facing public fee payment error (safe to display)."""

    def __init__(self, message, *, code="error"):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class PublicFeeSnapshot:
    member_pk: str
    member_id: str
    display_name: str
    year: int
    month: int
    amount: float
    period_label: str
    already_paid: bool


def _client_key(request) -> str:
    from accounts.signals import get_client_ip

    ip = (get_client_ip(request) or "unknown").strip()
    return ip or "unknown"


def _verify_cd_key(ip: str) -> str:
    return f"public_fee_verify_cd:{ip}"


def _verify_hr_key(ip: str) -> str:
    return f"public_fee_verify_hr:{ip}"


def can_attempt_public_fee_verify(request) -> tuple[bool, int, Optional[str]]:
    ip = _client_key(request)
    wait = cache.get(_verify_cd_key(ip))
    if wait:
        return False, int(wait), "cooldown"
    count = cache.get(_verify_hr_key(ip)) or 0
    if count >= VERIFY_MAX_PER_HOUR:
        return False, 3600, "hourly_limit"
    return True, 0, None


def mark_public_fee_verify_attempt(request) -> None:
    ip = _client_key(request)
    cache.set(_verify_cd_key(ip), VERIFY_COOLDOWN_SECONDS, VERIFY_COOLDOWN_SECONDS)
    hourly = cache.get(_verify_hr_key(ip)) or 0
    cache.set(_verify_hr_key(ip), hourly + 1, 3600)


def _member_display_name(member: Member) -> str:
    name = f"{member.first_name or ''} {member.last_name or ''}".strip()
    return name or member.member_id


def resolve_public_fee_member(member_id: str) -> Optional[Member]:
    """Return approved member or None. Do not distinguish failure reasons to callers."""
    code = (member_id or "").strip()
    if not code:
        return None
    return (
        Member.objects.filter(member_id__iexact=code, status=MemberStatus.APPROVED)
        .select_related("user")
        .first()
    )


def build_public_current_month_snapshot(member: Member) -> Optional[PublicFeeSnapshot]:
    """Authoritative current-month payable snapshot, or None if not publicly payable."""
    cy, cm = current_year_month()
    start_y, start_m = member_fee_start_period(member)
    if (cy, cm) < (start_y, start_m):
        return None

    ensure_ledger_months(member, cy, cm)
    fee = MembershipFee.objects.filter(member=member, year=cy, month=cm).first()
    if fee is None:
        return None

    already_paid = fee.status == DonationStatus.COMPLETED
    return PublicFeeSnapshot(
        member_pk=str(member.pk),
        member_id=member.member_id,
        display_name=_member_display_name(member),
        year=cy,
        month=cm,
        amount=float(fee.amount),
        period_label=format_fee_period(cy, cm),
        already_paid=already_paid,
    )


def issue_public_fee_checkout_token(snapshot: PublicFeeSnapshot) -> str:
    """Opaque signed token binding member + current period + amount."""
    if snapshot.already_paid:
        raise PublicFeeError(
            _("Membership fee for %(period)s has already been paid.")
            % {"period": snapshot.period_label},
            code="already_paid",
        )
    payload = {
        "v": 1,
        "mid": snapshot.member_pk,
        "member_id": snapshot.member_id,
        "y": int(snapshot.year),
        "m": int(snapshot.month),
        "amount": f"{float(snapshot.amount):.2f}",
        "nonce": secrets.token_hex(8),
    }
    return signing.dumps(payload, salt=TOKEN_SALT)


def load_public_fee_checkout_token(token: str) -> dict:
    try:
        payload = signing.loads(
            token, salt=TOKEN_SALT, max_age=TOKEN_MAX_AGE_SECONDS
        )
    except signing.SignatureExpired as exc:
        raise PublicFeeError(
            _("This payment session has expired. Please verify your Membership ID again."),
            code="expired",
        ) from exc
    except signing.BadSignature as exc:
        raise PublicFeeError(
            _("Invalid payment session. Please verify your Membership ID again."),
            code="bad_token",
        ) from exc

    if not isinstance(payload, dict) or payload.get("v") != 1:
        raise PublicFeeError(
            _("Invalid payment session. Please verify your Membership ID again."),
            code="bad_token",
        )
    return payload


def verify_public_membership_id(member_id: str, *, request) -> dict:
    """
    Verify Membership ID for public current-month payment.

    Returns a dict suitable for the confirm UI. Raises PublicFeeError with
    safe messages (generic for most failures; specific for already-paid).
    """
    allowed, wait, reason = can_attempt_public_fee_verify(request)
    if not allowed:
        if reason == "hourly_limit":
            raise PublicFeeError(
                _("Too many attempts. Please try again later."),
                code="rate_limited",
            )
        raise PublicFeeError(
            _("Please wait a moment before trying again."),
            code="rate_limited",
        )
    mark_public_fee_verify_attempt(request)

    member = resolve_public_fee_member(member_id)
    if member is None:
        raise PublicFeeError(GENERIC_VERIFY_FAILURE, code="not_found")

    snapshot = build_public_current_month_snapshot(member)
    if snapshot is None:
        raise PublicFeeError(GENERIC_VERIFY_FAILURE, code="not_payable")

    if snapshot.already_paid:
        raise PublicFeeError(
            _("Membership fee for %(period)s has already been paid.")
            % {"period": snapshot.period_label},
            code="already_paid",
        )

    token = issue_public_fee_checkout_token(snapshot)
    return {
        "token": token,
        "member_id": snapshot.member_id,
        "display_name": snapshot.display_name,
        "period_label": snapshot.period_label,
        "year": snapshot.year,
        "month": snapshot.month,
        "amount": snapshot.amount,
        # Never include email/phone/address/history in this payload.
    }


def _assert_token_still_authoritative(payload: dict, member: Member) -> PublicFeeSnapshot:
    """Re-derive server truth and reject any drift or tampering."""
    cy, cm = current_year_month()
    token_y = int(payload.get("y") or 0)
    token_m = int(payload.get("m") or 0)
    if (token_y, token_m) != (cy, cm):
        # Period in token is not today's current month (clock rollover or tamper).
        raise PublicFeeError(OTHER_MONTHS_REQUIRE_LOGIN, code="wrong_period")

    if str(payload.get("member_id") or "") != member.member_id:
        raise PublicFeeError(GENERIC_VERIFY_FAILURE, code="member_mismatch")

    snapshot = build_public_current_month_snapshot(member)
    if snapshot is None:
        raise PublicFeeError(GENERIC_VERIFY_FAILURE, code="not_payable")

    if snapshot.already_paid:
        raise PublicFeeError(
            _("Membership fee for %(period)s has already been paid.")
            % {"period": snapshot.period_label},
            code="already_paid",
        )

    if (snapshot.year, snapshot.month) != (cy, cm):
        raise PublicFeeError(OTHER_MONTHS_REQUIRE_LOGIN, code="wrong_period")

    token_amount = f"{float(payload.get('amount') or 0):.2f}"
    live_amount = f"{float(snapshot.amount):.2f}"
    if token_amount != live_amount:
        raise PublicFeeError(
            _("The fee amount changed. Please verify your Membership ID again."),
            code="amount_changed",
        )
    return snapshot


@transaction.atomic
def initiate_public_current_month_checkout(*, token: str, request):
    """
    Validate signed token, re-check server authority, start SSLCommerz checkout
    for the current month only via existing initiate_fee_checkout.
    """
    payload = load_public_fee_checkout_token(token)
    member_pk = payload.get("mid")
    if not member_pk:
        raise PublicFeeError(
            _("Invalid payment session. Please verify your Membership ID again."),
            code="bad_token",
        )

    member = (
        Member.objects.select_related("user")
        .filter(pk=member_pk, status=MemberStatus.APPROVED)
        .first()
    )
    if member is None:
        raise PublicFeeError(GENERIC_VERIFY_FAILURE, code="not_found")

    snapshot = _assert_token_still_authoritative(payload, member)

    # Ignore any client-supplied months/amount/purpose — only current month.
    months = [{"year": snapshot.year, "month": snapshot.month}]
    try:
        payment, url = initiate_fee_checkout(
            member, months, request=request, actor=None
        )
    except ValueError as exc:
        msg = str(exc)
        if "already paid" in msg.lower():
            raise PublicFeeError(
                _("Membership fee for %(period)s has already been paid.")
                % {"period": snapshot.period_label},
                code="already_paid",
            ) from exc
        logger.info("Public fee checkout refused: %s", msg)
        raise PublicFeeError(
            _("Online payment is temporarily unavailable. Please try again later."),
            code="checkout_refused",
        ) from exc

    # Tag for guest success UX / audit (no migration).
    note = f"{PUBLIC_PAYMENT_NOTE_PREFIX}{snapshot.member_id}:{snapshot.year}-{snapshot.month:02d}"
    if payment.notes:
        payment.notes = f"{note}\n{payment.notes}"
    else:
        payment.notes = note
    payment.save(update_fields=["notes", "updated_at"])

    if hasattr(request, "session"):
        request.session[SESSION_PUBLIC_PAYMENT_KEY] = str(payment.pk)

    return payment, url, snapshot


def is_public_fee_payment(payment) -> bool:
    notes = (getattr(payment, "notes", None) or "").strip()
    return notes.startswith(PUBLIC_PAYMENT_NOTE_PREFIX)


def reject_non_current_period_attempt(year, month) -> None:
    """Explicit guard for crafted period parameters."""
    cy, cm = current_year_month()
    if (int(year), int(month)) != (cy, cm):
        raise PublicFeeError(OTHER_MONTHS_REQUIRE_LOGIN, code="wrong_period")
