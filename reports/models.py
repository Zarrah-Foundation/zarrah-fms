import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import get_language, gettext_lazy as _


class ReportType(models.TextChoices):
    FINANCIAL = "FINANCIAL", _("Financial Transparency")
    ANNUAL = "ANNUAL", _("Annual Reports")
    AUDIT = "AUDIT", _("Audit Reports")
    LEGAL = "LEGAL", _("Legal Documents")
    GOVERNANCE = "GOVERNANCE", _("Governance Documents")
    REGISTRATION = "REGISTRATION", _("Registration Documents")
    POLICY = "POLICY", _("Policies")
    BOARD = "BOARD", _("Board / Committee Documents")
    ACTIVITY = "ACTIVITY", _("Activity Reports")
    CONSTITUTION = "CONSTITUTION", _("Constitution")
    OTHER = "OTHER", _("Other Public Documents")


class Report(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=300, help_text=_("Legacy/default title (English preferred)."))
    title_bn = models.CharField(max_length=300, blank=True, default="")
    title_en = models.CharField(max_length=300, blank=True, default="")
    description = models.TextField(null=True, blank=True)
    description_bn = models.TextField(blank=True, default="")
    description_en = models.TextField(blank=True, default="")
    type = models.CharField(
        max_length=20,
        choices=ReportType.choices,
        db_index=True,
        verbose_name=_("Document category"),
    )
    year = models.IntegerField(null=True, blank=True, verbose_name=_("Publication year"))
    file = models.FileField(upload_to="reports/")
    is_public = models.BooleanField(
        default=True,
        verbose_name=_("Published (public)"),
        help_text=_(
            "Master visibility. When off, the document is hidden from all public pages."
        ),
    )
    show_on_transparency = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_("Show on Transparency"),
        help_text=_(
            "Appear on the Transparency page. Does not auto-publish to Reports."
        ),
    )
    show_on_reports = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=_("Show on Reports"),
        help_text=_(
            "Appear on the public Reports page. Does not auto-publish to Transparency."
        ),
    )
    published_at = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Publication date"),
    )
    display_order = models.PositiveIntegerField(default=0, db_index=True)
    download_count = models.PositiveIntegerField(default=0)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_reports",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "-published_at", "-year", "-created_at"]
        indexes = [
            models.Index(fields=["type"]),
            models.Index(fields=["year"]),
            models.Index(fields=["is_public"]),
        ]

    def __str__(self):
        return self.localized_title()

    def save(self, *args, **kwargs):
        if not self.title_en and self.title:
            self.title_en = self.title
        if not self.title and self.title_en:
            self.title = self.title_en
        super().save(*args, **kwargs)

    def localized_title(self, lang=None):
        lang = lang or get_language()
        if lang == "bn":
            return self.title_bn or self.title_en or self.title
        return self.title_en or self.title_bn or self.title

    def localized_description(self, lang=None):
        lang = lang or get_language()
        if lang == "bn":
            return self.description_bn or self.description_en or (self.description or "")
        return self.description_en or self.description_bn or (self.description or "")

    def is_publicly_downloadable(self):
        return bool(
            self.is_public and (self.show_on_transparency or self.show_on_reports)
        )
