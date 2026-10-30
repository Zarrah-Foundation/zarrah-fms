"""Donation-specific validators (contact = email OR BD mobile)."""

import re

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils.translation import gettext_lazy as _

# 01XXXXXXXXX or +8801XXXXXXXXX / 8801XXXXXXXXX
_BD_MOBILE_RE = re.compile(
    r"^(?:\+?880|0)?1[3-9]\d{8}$"
)


def normalize_bd_mobile(value: str) -> str:
    """Return local 01XXXXXXXXX form, or empty if not a BD mobile."""
    raw = (value or "").strip().replace(" ", "").replace("-", "")
    if not _BD_MOBILE_RE.match(raw):
        return ""
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("880") and len(digits) == 13:
        return "0" + digits[3:]
    if digits.startswith("01") and len(digits) == 11:
        return digits
    if len(digits) == 10 and digits.startswith("1"):
        return "0" + digits
    return ""


def is_bd_mobile(value: str) -> bool:
    return bool(normalize_bd_mobile(value))


def is_email(value: str) -> bool:
    try:
        validate_email((value or "").strip())
        return True
    except ValidationError:
        return False


def parse_contact(value: str) -> tuple[str | None, str | None]:
    """Return (email, phone) — exactly one set when valid."""
    value = (value or "").strip()
    if not value:
        raise ValidationError(_("Enter a phone number or email address."))
    if is_email(value):
        return value.lower(), None
    phone = normalize_bd_mobile(value)
    if phone:
        return None, phone
    raise ValidationError(
        _(
            "Enter a valid email address or a Bangladeshi mobile number "
            "(e.g. 01XXXXXXXXX)."
        )
    )
