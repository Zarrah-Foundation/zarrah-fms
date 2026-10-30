"""Helpers for homepage section rendering (no second CMS)."""

from __future__ import annotations

from pages.organization_data import (
    AREAS_OF_WORK,
    NATURE_BN,
    NATURE_EN,
    PURPOSE_BN,
    PURPOSE_EN,
)

MISSION_VISION_SEPARATOR = "\n---\n"

DATA_DRIVEN_SECTION_TYPES = frozenset(
    {
        "TESTIMONIALS",
        "PARTNERS",
        "NEWS_GRID",
        "LEADERSHIP",
        "IMPACT_STATS",
    }
)


def split_mission_vision(content: str | None) -> tuple[str, str]:
    """Split CMS content into (purpose, nature/vision). Second part may be empty."""
    text = (content or "").strip()
    if not text:
        return "", ""
    if MISSION_VISION_SEPARATOR.strip() in text or "\n---\n" in text:
        parts = text.split("---", 1)
        mission = parts[0].strip()
        vision = parts[1].strip() if len(parts) > 1 else ""
        return mission, vision
    return text, ""


def default_mission_vision_pair():
    """Documented purpose + organizational nature (not an invented Vision statement)."""
    return PURPOSE_EN, PURPOSE_BN, NATURE_EN, NATURE_BN


def pack_mission_vision(mission: str, vision: str) -> str:
    mission = (mission or "").strip()
    vision = (vision or "").strip()
    if vision:
        return f"{mission}{MISSION_VISION_SEPARATOR}{vision}"
    return mission


def focus_areas():
    """Areas of work derived from Memorandum objectives."""
    return list(AREAS_OF_WORK)


def approach_defaults():
    from pages.organization_data import INTRO_BN, INTRO_EN

    return {
        "title_en": "Who we are",
        "title_bn": "আমরা কারা",
        "content_en": INTRO_EN,
        "content_bn": INTRO_BN,
    }
