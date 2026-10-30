"""Admin-facing metadata for HomepageSection types (no second CMS)."""

from __future__ import annotations

from django.utils.translation import gettext_lazy as _

from cms.models import SectionType

# kind: CORE (CMS copy) | DATA_DRIVEN (external records) | MEDIA (gallery)
SECTION_ADMIN_META = {
    SectionType.HERO: {
        "kind": "CORE",
        "source_label": _("CMS"),
        "source_help": _("Hero copy and media are edited in this section."),
        "editor": "hero",
    },
    SectionType.TRUST_BAR: {
        "kind": "CORE",
        "source_label": _("CMS + Site Settings"),
        "source_help": _(
            "Section labels are edited here. Registration number and date come from "
            "Site Settings (authoritative)."
        ),
        "editor": "trust",
    },
    SectionType.MISSION_VISION: {
        "kind": "CORE",
        "source_label": _("CMS"),
        "source_help": _(
            "Purpose and organizational-nature copy are edited here. "
            "Do not invent a formal Mission/Vision unless it is from an approved source."
        ),
        "editor": "mission_vision",
    },
    SectionType.APPROACH: {
        "kind": "CORE",
        "source_label": _("CMS"),
        "source_help": _("Approach heading, body and optional image are edited here."),
        "editor": "approach",
    },
    SectionType.PROGRAM_LIST: {
        "kind": "CORE",
        "source_label": _("About / Objectives"),
        "source_help": _(
            "Section heading and intro are edited here. Focus area cards are managed "
            "from approved About / Objectives content (not duplicated in this form)."
        ),
        "editor": "focus",
    },
    SectionType.LEADERSHIP: {
        "kind": "DATA-DRIVEN",
        "source_label": _("Community → Leadership"),
        "source_help": _(
            "Leaders (name, photo, designation) are managed under Community → Leadership. "
            "Edit presentation only here."
        ),
        "editor": "leadership",
        "manage_url_name": "dashboard-leadership",
    },
    SectionType.TESTIMONIALS: {
        "kind": "DATA-DRIVEN",
        "source_label": _("Community → Testimonials"),
        "source_help": _(
            "Testimonials are managed from Community → Testimonials. "
            "Only published testimonials with content appear publicly."
        ),
        "editor": "testimonials",
        "manage_url_name": "dashboard-testimonials",
    },
    SectionType.PARTNERS: {
        "kind": "DATA-DRIVEN",
        "source_label": _("Community → Partners"),
        "source_help": _(
            "Partners and technology supporters are managed from Community → Partners. "
            "Use relationship type to distinguish benefits from formal partnerships. "
            "Edit presentation only here."
        ),
        "editor": "partners",
        "manage_url_name": "dashboard-partners",
    },
    SectionType.NEWS_GRID: {
        "kind": "DATA-DRIVEN",
        "source_label": _("News"),
        "source_help": _("News articles are managed from News. Edit presentation only here."),
        "editor": "news",
        "manage_url_name": "dashboard-news",
    },
    SectionType.TRANSPARENCY_PREVIEW: {
        "kind": "CORE",
        "source_label": _("Reports / Transparency"),
        "source_help": _(
            "Documents remain controlled by Reports / Transparency. "
            "Edit homepage presentation here."
        ),
        "editor": "transparency",
    },
    SectionType.CTA: {
        "kind": "CORE",
        "source_label": _("CMS"),
        "source_help": _("Membership or donation call-to-action copy and link."),
        "editor": "cta",
    },
    SectionType.GALLERY_PREVIEW: {
        "kind": "MEDIA",
        "source_label": _("CMS Gallery"),
        "source_help": _(
            "Use Gallery Manager to add new images or select existing library images. "
            "Remove from Gallery keeps files available for reuse."
        ),
        "editor": "gallery",
    },
    SectionType.FEATURED_CAMPAIGN: {
        "kind": "CORE",
        "source_label": _("CMS"),
        "source_help": _("Legacy featured campaign block."),
        "editor": "generic",
    },
    SectionType.IMPACT_STATS: {
        "kind": "DATA-DRIVEN",
        "source_label": _("Website → Impact Statistics"),
        "source_help": _(
            "Individual statistics are managed under Website → Impact Statistics. "
            "Unpublish this homepage section to hide the block even if statistics exist. "
            "The public site also hides the block when no published statistics exist. "
            "Do not enter estimated or marketing numbers."
        ),
        "editor": "generic",
        "manage_url_name": "dashboard-impact-stats",
    },
    SectionType.VOLUNTEER_CTA: {
        "kind": "CORE",
        "source_label": _("CMS"),
        "source_help": _("Volunteer call-to-action."),
        "editor": "cta",
    },
}


def section_meta(section_type: str) -> dict:
    return SECTION_ADMIN_META.get(
        section_type,
        {
            "kind": "CORE",
            "source_label": _("CMS"),
            "source_help": "",
            "editor": "generic",
        },
    )


def language_completeness(section) -> dict:
    """Return EN/BN presence for admin list badges."""
    en = bool(
        (getattr(section, "title_en", None) or "").strip()
        or (getattr(section, "content_en", None) or "").strip()
    )
    bn = bool(
        (getattr(section, "title_bn", None) or "").strip()
        or (getattr(section, "content_bn", None) or "").strip()
    )
    return {"en": en, "bn": bn}


def publish_status(section) -> str:
    """Published | Draft | Disabled for admin list."""
    if not section.is_visible:
        return "disabled"
    if section.is_published:
        return "published"
    return "draft"


def display_count_from_config(config: dict | None, default: int, *, lo: int = 1, hi: int = 24) -> int:
    cfg = config if isinstance(config, dict) else {}
    try:
        n = int(cfg.get("display_count") or default)
    except (TypeError, ValueError):
        n = default
    return max(lo, min(n, hi))
