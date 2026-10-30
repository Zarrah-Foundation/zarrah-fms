"""Template filters for membership fee period display."""

from django import template

from members.periods import format_fee_period, format_fee_period_list, format_fee_period_short

register = template.Library()


@register.filter(name="fee_period")
def fee_period(value, arg=None):
    """Format a fee period as 'December 2026'.

    Usage:
        {{ fee|fee_period }}
        {{ fee|fee_period:"short" }}  -> Dec 2026
        {{ "2026-12"|fee_period }}
    """
    short = str(arg or "").lower() in {"short", "abbr", "1"}
    if value is None:
        return ""
    if isinstance(value, dict) and "year" in value and "month" in value:
        return format_fee_period(value["year"], value["month"], short=short)
    if hasattr(value, "year") and hasattr(value, "month") and not isinstance(value, dict):
        return format_fee_period(value, short=short)
    if isinstance(value, (tuple, list)) and len(value) == 2 and not isinstance(value[0], dict):
        return format_fee_period(value[0], value[1], short=short)
    if isinstance(value, str) and "-" in value:
        try:
            y, m = value.split("-", 1)
            return format_fee_period(int(y), int(m), short=short)
        except (TypeError, ValueError):
            return value
    return str(value)


@register.filter(name="fee_period_short")
def fee_period_short(value):
    return fee_period(value, "short")


@register.filter(name="fee_months")
def fee_months(months):
    """Format a list of {year, month} dicts for payment history."""
    return format_fee_period_list(months) or "—"
