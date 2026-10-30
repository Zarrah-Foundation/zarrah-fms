"""Safe HTML sanitization for rich-text fields (news, etc.)."""

ALLOWED_TAGS = [
    "p", "br", "strong", "b", "em", "i", "u", "s",
    "h2", "h3", "h4",
    "ul", "ol", "li",
    "a", "blockquote",
    "table", "thead", "tbody", "tr", "th", "td",
    "img", "figure", "figcaption",
    "span", "div",
]

ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "rel", "target"],
    "img": ["src", "alt", "title", "width", "height"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan"],
    "*": ["class"],
}

ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


def sanitize_html(value: str) -> str:
    if not value:
        return ""
    try:
        import bleach
    except ImportError:
        # Fallback: strip tags if bleach missing (should be in requirements).
        from django.utils.html import strip_tags

        return strip_tags(value)

    cleaned = bleach.clean(
        value,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
    return bleach.linkify(cleaned, parse_email=True)


def looks_like_html(value: str) -> bool:
    if not value:
        return False
    return "<" in value and ">" in value
