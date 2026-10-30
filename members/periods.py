"""Human-readable membership fee period labels (never expose raw YYYY-MM alone)."""

from __future__ import annotations

from calendar import month_abbr, month_name

from django.utils.translation import get_language, gettext as _

# Bangla month names (Gregorian calendar) for UI consistency.
_BN_MONTHS_LONG = (
    "",
    "জানুয়ারি",
    "ফেব্রুয়ারি",
    "মার্চ",
    "এপ্রিল",
    "মে",
    "জুন",
    "জুলাই",
    "আগস্ট",
    "সেপ্টেম্বর",
    "অক্টোবর",
    "নভেম্বর",
    "ডিসেম্বর",
)
_BN_MONTHS_SHORT = (
    "",
    "জানু",
    "ফেব্রু",
    "মার্চ",
    "এপ্রি",
    "মে",
    "জুন",
    "জুলা",
    "আগ",
    "সেপ্টে",
    "অক্টো",
    "নভে",
    "ডিসে",
)


def _coerce_ym(year, month=None):
    """Accept (y, m), MembershipFee-like object, or year+month kwargs."""
    if month is None and hasattr(year, "year") and hasattr(year, "month"):
        return int(year.year), int(year.month)
    if isinstance(year, (tuple, list)) and len(year) == 2 and month is None:
        return int(year[0]), int(year[1])
    if month is None:
        return None
    return int(year), int(month)


def format_fee_period(year, month=None, *, short: bool = False, language: str | None = None) -> str:
    """Return 'December 2026' / 'Dec 2026' (or Bangla equivalents)."""
    ym = _coerce_ym(year, month)
    if ym is None:
        return ""
    y, m = ym
    if m < 1 or m > 12:
        return f"{y}-{m:02d}"
    lang = (language or get_language() or "en").split("-")[0].lower()
    if lang == "bn":
        name = _BN_MONTHS_SHORT[m] if short else _BN_MONTHS_LONG[m]
        return f"{name} {y}"
    name = month_abbr[m] if short else month_name[m]
    return f"{name} {y}"


def format_fee_period_short(year, month=None, *, language: str | None = None) -> str:
    return format_fee_period(year, month, short=True, language=language)


def format_fee_period_list(months, *, short: bool = False, language: str | None = None) -> str:
    """Format a list of {'year','month'} or (y,m) tuples for notifications."""
    labels = []
    for item in months or []:
        if isinstance(item, dict):
            labels.append(
                format_fee_period(item.get("year"), item.get("month"), short=short, language=language)
            )
        else:
            labels.append(format_fee_period(item, short=short, language=language))
    return ", ".join(label for label in labels if label)
