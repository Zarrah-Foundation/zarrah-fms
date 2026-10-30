import uuid

from django.conf import settings
from django.db import models


class SectionType(models.TextChoices):
    HERO = "HERO", "Hero"
    TRUST_BAR = "TRUST_BAR", "Trust / Identity Bar"
    MISSION_VISION = "MISSION_VISION", "Mission & Vision"
    APPROACH = "APPROACH", "Approach / Philosophy"
    PROGRAM_LIST = "PROGRAM_LIST", "Focus Areas"
    LEADERSHIP = "LEADERSHIP", "Leadership"
    TESTIMONIALS = "TESTIMONIALS", "Testimonials"
    PARTNERS = "PARTNERS", "Partners"
    NEWS_GRID = "NEWS_GRID", "News Grid"
    TRANSPARENCY_PREVIEW = "TRANSPARENCY_PREVIEW", "Transparency Preview"
    CTA = "CTA", "Call to Action (Membership / Donation)"
    # Legacy / optional types (templates retained; not seeded by default)
    FEATURED_CAMPAIGN = "FEATURED_CAMPAIGN", "Featured Campaign"
    IMPACT_STATS = "IMPACT_STATS", "Impact Statistics"
    GALLERY_PREVIEW = "GALLERY_PREVIEW", "Gallery Preview"
    VOLUNTEER_CTA = "VOLUNTEER_CTA", "Volunteer CTA"


class HomepageSection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    section_type = models.CharField(max_length=30, choices=SectionType.choices)
    order = models.IntegerField()
    is_visible = models.BooleanField(default=True)
    is_published = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    title_bn = models.CharField(max_length=300, null=True, blank=True)
    title_en = models.CharField(max_length=300, null=True, blank=True)
    content_bn = models.TextField(null=True, blank=True)
    content_en = models.TextField(null=True, blank=True)
    image = models.ImageField(upload_to="cms/", null=True, blank=True)
    button_text_bn = models.CharField(max_length=100, null=True, blank=True)
    button_text_en = models.CharField(max_length=100, null=True, blank=True)
    button_link = models.CharField(max_length=500, null=True, blank=True)
    # Type-specific presentation knobs (eyebrow, secondary CTA, display_count, MV titles, gallery).
    config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order"]
        indexes = [
            models.Index(fields=["order"]),
            models.Index(fields=["is_published"]),
            models.Index(fields=["is_deleted"]),
        ]

    @property
    def template_name(self):
        return f"cms/sections/{self.section_type.lower()}.html"

    def get_config(self) -> dict:
        data = self.config
        return data if isinstance(data, dict) else {}

    def gallery_settings(self) -> dict:
        """Public slider presentation defaults + stored overrides."""
        cfg = self.get_config()
        try:
            interval = int(cfg.get("autoplay_interval") or 5000)
        except (TypeError, ValueError):
            interval = 5000
        interval = max(2000, min(interval, 30000))
        return {
            "autoplay": bool(cfg.get("autoplay", True)),
            "autoplay_interval": interval,
            "show_arrows": bool(cfg.get("show_arrows", True)),
            "show_dots": bool(cfg.get("show_dots", True)),
            "show_captions": bool(cfg.get("show_captions", True)),
        }

    def __str__(self):
        return f"{self.section_type} (#{self.order})"


class ImpactStatistic(models.Model):
    """Admin-managed public statistic. Never render unless published and the
    homepage IMPACT_STATS section is visible. Do not seed fabricated values.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    value = models.CharField(max_length=40, help_text="Display value, e.g. 12 or 12+")
    label_en = models.CharField(max_length=120)
    label_bn = models.CharField(max_length=120, blank=True, default="")
    description_en = models.CharField(max_length=300, blank=True, default="")
    description_bn = models.CharField(max_length=300, blank=True, default="")
    period_year = models.PositiveIntegerField(null=True, blank=True)
    icon = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Optional Bootstrap icon class, e.g. bi-people",
    )
    display_order = models.PositiveIntegerField(default=0, db_index=True)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "created_at"]
        verbose_name = "Impact statistic"
        verbose_name_plural = "Impact statistics"

    def __str__(self):
        return f"{self.value} {self.label_en}".strip()

    def localized_label(self, lang=None):
        from django.utils.translation import get_language

        lang = lang or get_language()
        if (lang or "").startswith("bn"):
            return self.label_bn or self.label_en
        return self.label_en or self.label_bn

    def localized_description(self, lang=None):
        from django.utils.translation import get_language

        lang = lang or get_language()
        if (lang or "").startswith("bn"):
            return self.description_bn or self.description_en
        return self.description_en or self.description_bn


class CmsMedia(models.Model):
    """Reusable public CMS image asset (gallery library). One file, many gallery uses."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    image = models.ImageField(upload_to="cms/gallery/")
    original_filename = models.CharField(max_length=255, blank=True, default="")
    alt_en = models.CharField(max_length=200, blank=True, default="")
    alt_bn = models.CharField(max_length=200, blank=True, default="")
    caption_en = models.CharField(max_length=300, blank=True, default="")
    caption_bn = models.CharField(max_length=300, blank=True, default="")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cms_media_uploads",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "CMS media"
        verbose_name_plural = "CMS media"

    def __str__(self):
        return self.original_filename or (self.image.name.split("/")[-1] if self.image else str(self.pk))

    @property
    def display_name(self):
        return self.original_filename or (self.image.name.split("/")[-1] if self.image else "Image")

    def usage_count(self) -> int:
        return self.gallery_usages.count()


class HomepageSectionImage(models.Model):
    """Gallery membership: links a reusable CmsMedia into a HomepageSection."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    section = models.ForeignKey(
        HomepageSection,
        on_delete=models.CASCADE,
        related_name="gallery_images",
    )
    media = models.ForeignKey(
        CmsMedia,
        on_delete=models.PROTECT,
        related_name="gallery_usages",
    )
    # Optional per-gallery overrides (blank → use media defaults).
    alt_en = models.CharField(max_length=200, blank=True, default="")
    alt_bn = models.CharField(max_length=200, blank=True, default="")
    caption_en = models.CharField(max_length=300, blank=True, default="")
    caption_bn = models.CharField(max_length=300, blank=True, default="")
    order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["section", "media"],
                name="uniq_homepage_section_media",
            )
        ]

    def __str__(self):
        return f"Gallery image #{self.order} ({self.section_id})"

    @property
    def image(self):
        """Template-compatible accessor for the underlying stored file."""
        return self.media.image if self.media_id else None

    def resolved_alt_en(self):
        return (self.alt_en or "").strip() or (self.media.alt_en if self.media_id else "")

    def resolved_alt_bn(self):
        return (self.alt_bn or "").strip() or (self.media.alt_bn if self.media_id else "")

    def resolved_caption_en(self):
        return (self.caption_en or "").strip() or (self.media.caption_en if self.media_id else "")

    def resolved_caption_bn(self):
        return (self.caption_bn or "").strip() or (self.media.caption_bn if self.media_id else "")
