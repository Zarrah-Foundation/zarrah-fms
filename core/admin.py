from django.contrib import admin, messages
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _

from core.email import send_test_email
from core.models import SiteSettings, SmsSettings, SmtpSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """Singleton admin: changelist redirects to the single change form."""

    fieldsets = (
        (
            _("General"),
            {
                "fields": (
                    "foundation_name_bn",
                    "foundation_name_en",
                    "short_name",
                    "tagline_bn",
                    "tagline_en",
                    "site_logo",
                    "site_logo_white",
                    "site_favicon",
                ),
            },
        ),
        (
            _("Contact"),
            {
                "fields": (
                    "primary_email",
                    "secondary_email",
                    "primary_phone",
                    "secondary_phone",
                    "whatsapp",
                    "website_url",
                    "address_bn",
                    "address_en",
                    "google_maps_url",
                    "google_maps_embed_url",
                    "maps_latitude",
                    "maps_longitude",
                ),
            },
        ),
        (
            _("Social"),
            {
                "fields": (
                    "facebook_url",
                    "youtube_url",
                    "linkedin_url",
                    "instagram_url",
                    "twitter_url",
                    "telegram_url",
                    "github_url",
                ),
            },
        ),
        (
            _("Foundation"),
            {
                "fields": (
                    "foundation_description_bn",
                    "foundation_description_en",
                    "registration_number",
                    "registration_date",
                    "office_hours",
                    "brand_primary_color",
                    "brand_secondary_color",
                    "dark_logo",
                    "twitter_card_image",
                ),
            },
        ),
        (
            _("SEO"),
            {
                "fields": (
                    "meta_title",
                    "meta_description",
                    "meta_keywords",
                    "og_image",
                ),
            },
        ),
        (
            _("Footer"),
            {
                "fields": (
                    "footer_text_bn",
                    "footer_text_en",
                    "copyright_text",
                ),
            },
        ),
        (
            _("Legacy (auto-synced)"),
            {
                "classes": ("collapse",),
                "fields": ("site_title", "site_tagline", "updated_at"),
                "description": _(
                    "Kept for backward compatibility. Updated automatically from "
                    "Foundation Name (English) and Tagline (English)."
                ),
            },
        ),
    )
    readonly_fields = ("site_title", "site_tagline", "updated_at")

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = SiteSettings.load()
        return redirect(reverse("admin:core_sitesettings_change", args=[obj.pk]))


@admin.register(SmtpSettings)
class SmtpSettingsAdmin(admin.ModelAdmin):
    """Singleton SMTP configuration with a Send Test Email action."""

    fieldsets = (
        (
            _("Server"),
            {
                "fields": ("host", "port", "username", "password", "encryption", "is_active"),
            },
        ),
        (
            _("Sender"),
            {
                "fields": ("from_name", "from_email", "reply_to"),
            },
        ),
        (_("Meta"), {"fields": ("updated_at",)}),
    )
    readonly_fields = ("updated_at",)

    def has_add_permission(self, request):
        return not SmtpSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = SmtpSettings.load()
        return redirect(reverse("admin:core_smtpsettings_change", args=[obj.pk]))

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<path:object_id>/send-test/",
                self.admin_site.admin_view(self.send_test_view),
                name="core_smtpsettings_send_test",
            ),
        ]
        return custom + urls

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["show_send_test"] = True
        extra_context["send_test_url"] = reverse(
            "admin:core_smtpsettings_send_test", args=[object_id]
        )
        return super().change_view(request, object_id, form_url, extra_context)

    def send_test_view(self, request, object_id):
        smtp = SmtpSettings.load()
        if request.method == "POST":
            to_email = (request.POST.get("to_email") or "").strip()
            if not to_email:
                messages.error(request, _("Please enter a recipient email address."))
            else:
                try:
                    send_test_email(to_email)
                    messages.success(
                        request,
                        _("Test email sent to %(email)s.") % {"email": to_email},
                    )
                except Exception as exc:
                    messages.error(
                        request,
                        _("Failed to send test email: %(error)s") % {"error": exc},
                    )
            return redirect(reverse("admin:core_smtpsettings_change", args=[smtp.pk]))

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": _("Send Test Email"),
            "smtp": smtp,
            "default_to": request.user.email or smtp.from_email,
        }
        return render(request, "admin/core/smtpsettings/send_test.html", context)


@admin.register(SmsSettings)
class SmsSettingsAdmin(admin.ModelAdmin):
    """Singleton SMS configuration. API key is never shown in list displays."""

    fieldsets = (
        (
            _("Provider"),
            {
                "fields": ("enabled", "provider", "api_url", "api_key", "sender_id"),
            },
        ),
        (
            _("Verification limits"),
            {
                "fields": (
                    "verification_timeout_seconds",
                    "resend_cooldown_seconds",
                    "max_attempts",
                    "max_sends_per_hour",
                ),
            },
        ),
        (_("Meta"), {"fields": ("updated_at",)}),
    )
    readonly_fields = ("updated_at",)
    list_display = ("provider", "enabled", "masked_api_key", "sender_id", "updated_at")

    @admin.display(description=_("API Key"))
    def masked_api_key(self, obj):
        if not obj.api_key:
            return "—"
        if len(obj.api_key) <= 4:
            return "****"
        return f"****{obj.api_key[-4:]}"

    def has_add_permission(self, request):
        return not SmsSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = SmsSettings.load()
        return redirect(reverse("admin:core_smssettings_change", args=[obj.pk]))
