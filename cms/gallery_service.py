"""Homepage gallery media helpers — upload, attach, remove, delete-with-protection."""

from __future__ import annotations

import os
from typing import Iterable

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils.translation import gettext as _

from cms.models import CmsMedia, HomepageSection, HomepageSectionImage

MAX_GALLERY_UPLOAD_BYTES = 8 * 1024 * 1024  # 8 MB
ALLOWED_IMAGE_CONTENT_TYPES = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
    }
)
ALLOWED_IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp", ".gif"})


def validate_gallery_image(uploaded) -> None:
    """Server-side image validation. Raises ValidationError on failure."""
    if not uploaded:
        raise ValidationError(_("No image file was provided."))
    name = getattr(uploaded, "name", "") or ""
    ext = os.path.splitext(name)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(
            _("Unsupported image type. Please upload JPG, PNG, WebP or GIF.")
        )
    content_type = (getattr(uploaded, "content_type", "") or "").lower()
    if content_type and content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise ValidationError(
            _("Unsupported image type. Please upload JPG, PNG, WebP or GIF.")
        )
    size = getattr(uploaded, "size", None)
    if size is not None and size > MAX_GALLERY_UPLOAD_BYTES:
        raise ValidationError(_("Image is too large. Maximum size is 8 MB."))
    # Pillow decode check when available.
    try:
        from PIL import Image

        pos = uploaded.tell() if hasattr(uploaded, "tell") else None
        img = Image.open(uploaded)
        img.verify()
        if hasattr(uploaded, "seek") and pos is not None:
            uploaded.seek(pos)
        elif hasattr(uploaded, "seek"):
            uploaded.seek(0)
    except Exception as exc:  # noqa: BLE001 — surface as validation
        raise ValidationError(_("The file is not a valid image.")) from exc


def create_media(*, uploaded, user=None, alt_en="", alt_bn="", caption_en="", caption_bn="") -> CmsMedia:
    validate_gallery_image(uploaded)
    return CmsMedia.objects.create(
        image=uploaded,
        original_filename=(getattr(uploaded, "name", "") or "")[:255],
        alt_en=(alt_en or "")[:200],
        alt_bn=(alt_bn or "")[:200],
        caption_en=(caption_en or "")[:300],
        caption_bn=(caption_bn or "")[:300],
        uploaded_by=user if getattr(user, "is_authenticated", False) else None,
    )


def next_gallery_order(section: HomepageSection) -> int:
    current = (
        HomepageSectionImage.objects.filter(section=section)
        .aggregate(m=Max("order"))
        .get("m")
    )
    return (current or 0) + 1


@transaction.atomic
def attach_media_to_section(
    section: HomepageSection,
    media: CmsMedia,
    *,
    order: int | None = None,
    is_active: bool = True,
    alt_en: str = "",
    alt_bn: str = "",
    caption_en: str = "",
    caption_bn: str = "",
) -> tuple[HomepageSectionImage, bool]:
    """Attach media to a gallery. Returns (membership, created). Prevents duplicates."""
    existing = HomepageSectionImage.objects.filter(section=section, media=media).first()
    if existing:
        return existing, False
    membership = HomepageSectionImage.objects.create(
        section=section,
        media=media,
        order=order if order is not None else next_gallery_order(section),
        is_active=is_active,
        alt_en=alt_en or "",
        alt_bn=alt_bn or "",
        caption_en=caption_en or "",
        caption_bn=caption_bn or "",
    )
    return membership, True


@transaction.atomic
def attach_many(section: HomepageSection, media_ids: Iterable) -> int:
    """Attach multiple media IDs. Skips duplicates. Returns newly attached count."""
    attached = 0
    seen = set()
    for raw in media_ids:
        if not raw:
            continue
        key = str(raw)
        if key in seen:
            continue
        seen.add(key)
        try:
            media = CmsMedia.objects.get(pk=raw)
        except (CmsMedia.DoesNotExist, ValueError, TypeError):
            continue
        _, created = attach_media_to_section(section, media)
        if created:
            attached += 1
    return attached


def remove_from_gallery(membership: HomepageSectionImage) -> None:
    """Remove image from this gallery only — does not delete the reusable media file."""
    membership.delete()


class MediaInUseError(Exception):
    def __init__(self, media: CmsMedia, usage_count: int):
        self.media = media
        self.usage_count = usage_count
        super().__init__(
            _("This image is used in %(count)s gallery(ies) and cannot be deleted.")
            % {"count": usage_count}
        )


@transaction.atomic
def delete_media_permanently(media: CmsMedia, *, force: bool = False) -> None:
    """Permanently delete reusable media. Blocked when still referenced unless force."""
    usages = media.gallery_usages.count()
    if usages and not force:
        raise MediaInUseError(media, usages)
    if force and usages:
        media.gallery_usages.all().delete()
    # Delete file via storage, then row.
    if media.image:
        media.image.delete(save=False)
    media.delete()


def normalize_orders(section: HomepageSection, ordered_membership_ids: list) -> None:
    """Server-validated reorder: only IDs belonging to this section, consecutive orders."""
    memberships = {
        str(m.pk): m
        for m in HomepageSectionImage.objects.filter(section=section).select_for_update()
    }
    order = 1
    seen = set()
    for mid in ordered_membership_ids:
        key = str(mid)
        if key in seen or key not in memberships:
            continue
        seen.add(key)
        m = memberships[key]
        if m.order != order:
            m.order = order
            m.save(update_fields=["order", "updated_at"])
        order += 1
    # Any not listed keep relative order after listed ones.
    for mid, m in memberships.items():
        if mid in seen:
            continue
        if m.order != order:
            m.order = order
            m.save(update_fields=["order", "updated_at"])
        order += 1
