import uuid

from django.core.cache import cache
from django.db import models
from django.utils.translation import get_language, gettext_lazy as _

from core.validators import FaviconFileValidator, ImageFileValidator, MaxFileSizeValidator

SITE_SETTINGS_CACHE_KEY = "core:site_settings"
SMTP_SETTINGS_CACHE_KEY = "core:smtp_settings"
SMS_SETTINGS_CACHE_KEY = "core:sms_settings"


class SiteSettings(models.Model):
    """Global foundation branding, contact, social and SEO — singleton."""

    SINGLETON_ID = uuid.UUID(int=1)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # --- General / Identity ---
    foundation_name_bn = models.CharField(
        max_length=150,
        blank=True,
        default="জার্‌রাহ",
        verbose_name=_("Foundation Name (Bangla)"),
    )
    foundation_name_en = models.CharField(
        max_length=150,
        blank=True,
        default="Zarrah Foundation",
        verbose_name=_("Foundation Name (English)"),
    )
    short_name = models.CharField(
        max_length=80,
        blank=True,
        default="জার্‌রাহ",
        verbose_name=_("Short Name"),
        help_text=_("Compact name for tight UI spaces (nav, receipts)."),
    )
    tagline_bn = models.CharField(max_length=300, blank=True, default="")
    tagline_en = models.CharField(
        max_length=300,
        blank=True,
        default="Serving humanity through compassion and community.",
    )

    # Legacy aliases kept for older templates / migrations — synced on save.
    site_title = models.CharField(max_length=150, blank=True, default="Zarrah Foundation")
    site_tagline = models.CharField(max_length=300, blank=True, default="")

    site_logo = models.ImageField(
        upload_to="brand/logo/",
        null=True,
        blank=True,
        validators=[MaxFileSizeValidator(2), ImageFileValidator()],
        verbose_name=_("Logo"),
        help_text=_("Primary logo for light backgrounds (header)."),
    )
    site_logo_white = models.ImageField(
        upload_to="brand/logo/",
        null=True,
        blank=True,
        validators=[MaxFileSizeValidator(2), ImageFileValidator()],
        verbose_name=_("Logo (light / white)"),
        help_text=_("Light logo for dark backgrounds (footer)."),
    )
    site_favicon = models.ImageField(
        upload_to="brand/favicon/",
        null=True,
        blank=True,
        validators=[MaxFileSizeValidator(1), FaviconFileValidator()],
        verbose_name=_("Favicon"),
    )

    # --- Contact ---
    primary_email = models.EmailField(blank=True, default="")
    secondary_email = models.EmailField(blank=True, default="")
    primary_phone = models.CharField(max_length=30, blank=True, default="")
    secondary_phone = models.CharField(max_length=30, blank=True, default="")
    whatsapp = models.CharField(max_length=30, blank=True, default="")
    address_bn = models.TextField(blank=True, default="")
    address_en = models.TextField(blank=True, default="")
    google_maps_url = models.URLField(
        blank=True,
        default="",
        max_length=500,
        verbose_name=_("Google Maps URL"),
        help_text=_(
            "Public share link to the location (opens in Google Maps). "
            "Example: https://maps.google.com/?q=..."
        ),
    )
    google_maps_embed_url = models.URLField(
        blank=True,
        default="",
        max_length=500,
        verbose_name=_("Google Maps Embed URL"),
        help_text=_(
            "Embed/iframe src URL only (must start with https://www.google.com/maps/embed). "
            "Used for the map on the Contact page. Do not paste raw HTML."
        ),
    )
    maps_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name=_("Latitude"),
        help_text=_("Optional. Used with longitude if no embed URL is set."),
    )
    maps_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name=_("Longitude"),
        help_text=_("Optional. Used with latitude if no embed URL is set."),
    )

    # --- Social ---
    facebook_url = models.URLField(blank=True, default="")
    youtube_url = models.URLField(blank=True, default="")
    linkedin_url = models.URLField(blank=True, default="")
    instagram_url = models.URLField(blank=True, default="")
    twitter_url = models.URLField(
        blank=True,
        default="",
        verbose_name=_("X (Twitter)"),
    )
    telegram_url = models.URLField(blank=True, default="")
    github_url = models.URLField(blank=True, default="")

    website_url = models.URLField(blank=True, default="", verbose_name=_("Website URL"))

    foundation_description_en = models.TextField(blank=True, default="")
    foundation_description_bn = models.TextField(blank=True, default="")

    office_hours = models.CharField(max_length=255, blank=True, default="")

    registration_number = models.CharField(max_length=100, blank=True, default="")
    registration_date = models.DateField(null=True, blank=True)

    brand_primary_color = models.CharField(max_length=7, blank=True, default="#0B592F")
    brand_secondary_color = models.CharField(max_length=7, blank=True, default="#F2A900")

    dark_logo = models.ImageField(
    upload_to="brand/logo/",
    null=True,
    blank=True,
    validators=[MaxFileSizeValidator(2), ImageFileValidator()],
    )

    twitter_card_image = models.ImageField(
    upload_to="brand/og/",
    null=True,
    blank=True,
    validators=[MaxFileSizeValidator(2), ImageFileValidator()],
    )

    # --- SEO ---
    meta_title = models.CharField(max_length=200, blank=True, default="")
    meta_description = models.TextField(max_length=500, blank=True, default="")
    meta_keywords = models.CharField(max_length=300, blank=True, default="")
    og_image = models.ImageField(
        upload_to="brand/og/",
        null=True,
        blank=True,
        validators=[MaxFileSizeValidator(2), ImageFileValidator()],
        verbose_name=_("Open Graph Image"),
    )

    # --- Footer ---
    footer_text_bn = models.TextField(blank=True, default="", verbose_name=_("Footer Text (Bangla)"))
    footer_text_en = models.TextField(blank=True, default="", verbose_name=_("Footer Text (English)"))
    copyright_text = models.CharField(
        max_length=300,
        blank=True,
        default="",
        verbose_name=_("Copyright Text"),
        help_text=_("Shown in the footer. Leave blank to auto-generate from the foundation name."),
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Site Settings")
        verbose_name_plural = _("Site Settings")

    def __str__(self):
        return self.foundation_name_en or self.site_title or "Site Settings"

    def _pick(self, bn_value, en_value, lang=None):
        lang = lang or get_language()
        if lang == "bn":
            return bn_value or en_value or ""
        return en_value or bn_value or ""

    def localized_name(self, lang=None):
        return self._pick(self.foundation_name_bn, self.foundation_name_en, lang) or self.short_name or self.site_title

    def localized_tagline(self, lang=None):
        return self._pick(self.tagline_bn, self.tagline_en, lang) or self.site_tagline

    def localized_address(self, lang=None):
        return self._pick(self.address_bn, self.address_en, lang)

    def localized_footer_text(self, lang=None):
        return self._pick(self.footer_text_bn, self.footer_text_en, lang)

    @property
    def canonical_origin(self):
        return (self.website_url or "").strip().rstrip("/")

    def save(self, *args, **kwargs):
        self.pk = self.SINGLETON_ID
        # Keep legacy fields in sync for any remaining template references.
        self.site_title = self.foundation_name_en or self.short_name or self.site_title
        self.site_tagline = self.tagline_en or self.tagline_bn or self.site_tagline
        if not self.meta_title:
            self.meta_title = self.foundation_name_en or self.site_title
        super().save(*args, **kwargs)
        cache.delete(SITE_SETTINGS_CACHE_KEY)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        cached = cache.get(SITE_SETTINGS_CACHE_KEY)
        if cached is not None:
            return cached
        obj, _created = cls.objects.get_or_create(pk=cls.SINGLETON_ID)
        cache.set(SITE_SETTINGS_CACHE_KEY, obj, timeout=300)
        return obj


class SmtpSettings(models.Model):
    """Singleton SMTP configuration. When active, overrides .env email settings."""

    SINGLETON_ID = uuid.UUID(int=2)

    class Encryption(models.TextChoices):
        TLS = "TLS", _("TLS (STARTTLS)")
        SSL = "SSL", _("SSL")
        NONE = "NONE", _("None")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    host = models.CharField(max_length=255, blank=True, default="")
    port = models.PositiveIntegerField(default=587)
    username = models.CharField(max_length=255, blank=True, default="")
    password = models.CharField(max_length=255, blank=True, default="")
    from_name = models.CharField(max_length=150, blank=True, default="Zarrah Foundation")
    from_email = models.EmailField(blank=True, default="")
    reply_to = models.EmailField(blank=True, default="")
    encryption = models.CharField(
        max_length=10,
        choices=Encryption.choices,
        default=Encryption.TLS,
        verbose_name=_("TLS / SSL"),
    )
    is_active = models.BooleanField(
        default=False,
        verbose_name=_("Active"),
        help_text=_(
            "When active, outgoing mail uses these settings. "
            "When inactive, the project falls back to SMTP_* values from .env."
        ),
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("SMTP Settings")
        verbose_name_plural = _("SMTP Settings")

    def __str__(self):
        status = "active" if self.is_active else "inactive"
        return f"SMTP ({self.host or 'not configured'}, {status})"

    @property
    def use_tls(self):
        return self.encryption == self.Encryption.TLS

    @property
    def use_ssl(self):
        return self.encryption == self.Encryption.SSL

    def save(self, *args, **kwargs):
        self.pk = self.SINGLETON_ID
        super().save(*args, **kwargs)
        cache.delete(SMTP_SETTINGS_CACHE_KEY)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        cached = cache.get(SMTP_SETTINGS_CACHE_KEY)
        if cached is not None:
            return cached
        obj, _created = cls.objects.get_or_create(pk=cls.SINGLETON_ID)
        cache.set(SMTP_SETTINGS_CACHE_KEY, obj, timeout=300)
        return obj


class SmsSettings(models.Model):
    """Singleton SMS configuration. Provider-agnostic; secrets stay server-side."""

    SINGLETON_ID = uuid.UUID(int=3)

    class Provider(models.TextChoices):
        CONSOLE = "CONSOLE", _("Console (log only)")
        HTTP_GENERIC = "HTTP_GENERIC", _("HTTP Generic")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enabled = models.BooleanField(
        default=False,
        verbose_name=_("Enabled"),
        help_text=_("When disabled, SMS is not sent (console logging may still apply in DEBUG)."),
    )
    provider = models.CharField(
        max_length=20,
        choices=Provider.choices,
        default=Provider.CONSOLE,
        verbose_name=_("Provider"),
    )
    api_url = models.URLField(blank=True, default="", verbose_name=_("API URL"))
    api_key = models.CharField(max_length=255, blank=True, default="", verbose_name=_("API Key"))
    sender_id = models.CharField(max_length=50, blank=True, default="", verbose_name=_("Sender ID"))
    verification_timeout_seconds = models.PositiveIntegerField(
        default=300,
        verbose_name=_("Verification timeout (seconds)"),
    )
    resend_cooldown_seconds = models.PositiveIntegerField(
        default=60,
        verbose_name=_("Resend cooldown (seconds)"),
    )
    max_attempts = models.PositiveIntegerField(
        default=5,
        verbose_name=_("Max verification attempts"),
    )
    max_sends_per_hour = models.PositiveIntegerField(
        default=5,
        verbose_name=_("Max sends per hour"),
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("SMS Settings")
        verbose_name_plural = _("SMS Settings")

    def __str__(self):
        status = "enabled" if self.enabled else "disabled"
        return f"SMS ({self.provider}, {status})"

    def save(self, *args, **kwargs):
        self.pk = self.SINGLETON_ID
        super().save(*args, **kwargs)
        cache.delete(SMS_SETTINGS_CACHE_KEY)

    def delete(self, *args, **kwargs):
        # Singleton must not be removed.
        return

    @classmethod
    def load(cls):
        cached = cache.get(SMS_SETTINGS_CACHE_KEY)
        if cached is not None:
            return cached
        obj, _created = cls.objects.get_or_create(pk=cls.SINGLETON_ID)
        cache.set(SMS_SETTINGS_CACHE_KEY, obj, timeout=300)
        return obj
