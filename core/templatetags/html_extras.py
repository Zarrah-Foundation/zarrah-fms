from django import template
from django.utils.safestring import mark_safe

from core.html_sanitize import looks_like_html, sanitize_html

register = template.Library()


@register.filter(name="richtext")
def richtext(value):
    """Render stored content: HTML (sanitized) or plain text with linebreaks."""
    if not value:
        return ""
    text = str(value)
    if looks_like_html(text):
        return mark_safe(sanitize_html(text))
    from django.template.defaultfilters import linebreaks

    return linebreaks(text)
