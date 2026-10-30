"""Helpers for validating / deriving Google Maps embed URLs."""

from urllib.parse import quote


def is_safe_maps_embed_url(url: str) -> bool:
    if not url:
        return False
    url = url.strip()
    allowed_prefixes = (
        "https://www.google.com/maps/embed",
        "https://maps.google.com/maps/embed",
        "https://www.google.com/maps/embed?",
    )
    return any(url.startswith(p) for p in allowed_prefixes)


def build_embed_url_from_coords(lat, lng) -> str:
    if lat is None or lng is None:
        return ""
    q = quote(f"{lat},{lng}")
    return f"https://www.google.com/maps?q={q}&z=15&output=embed"


def resolve_maps_embed_url(site_settings) -> str:
    """Return a safe iframe src, or empty string when none configured."""
    embed = (getattr(site_settings, "google_maps_embed_url", "") or "").strip()
    if is_safe_maps_embed_url(embed):
        return embed
    lat = getattr(site_settings, "maps_latitude", None)
    lng = getattr(site_settings, "maps_longitude", None)
    if lat is not None and lng is not None:
        return build_embed_url_from_coords(lat, lng)
    return ""
