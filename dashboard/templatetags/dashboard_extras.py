"""Template helpers for the admin dashboard."""

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# Map common status codes (across models) to a badge tone.
STATUS_TONES = {
    # DonationStatus
    "COMPLETED": "success",
    "PENDING": "warning",
    "FAILED": "danger",
    "CANCELLED": "danger",
    "REFUNDED": "info",
    # Member / Application status
    "APPROVED": "success",
    "REJECTED": "danger",
    "SUSPENDED": "danger",
    "UNDER_REVIEW": "info",
    # Subscription
    "ACTIVE": "success",
    "PAUSED": "warning",
    # Generic booleans
    "PUBLISHED": "success",
    "DRAFT": "warning",
    "CLOSED": "danger",
}


@register.simple_tag(takes_context=True)
def query_replace(context, **kwargs):
    """Return the current query string with the given params replaced.

    Usage: ``?{% query_replace page=3 %}`` preserves existing filters.
    """
    request = context.get("request")
    params = request.GET.copy() if request else None
    if params is None:
        from django.http import QueryDict

        params = QueryDict(mutable=True)
    for key, value in kwargs.items():
        if value is None:
            params.pop(key, None)
        else:
            params[key] = value
    return params.urlencode()


@register.simple_tag
def status_badge(status, label=None):
    """Render a badge for a status code, choosing a tone automatically."""
    if status is None:
        return ""
    code = str(status).upper()
    tone = STATUS_TONES.get(code, "primary")
    text = label if label is not None else status
    return mark_safe(f'<span class="badge-{tone}">{text}</span>')


@register.filter
def status_tone(status):
    return STATUS_TONES.get(str(status).upper(), "primary")


@register.filter
def get_attr(obj, name):
    """Resolve ``obj.name`` for generic tables; calls it if it's a method."""
    value = getattr(obj, name, "")
    if callable(value):
        try:
            value = value()
        except Exception:
            value = ""
    if value is None:
        return ""
    return value
