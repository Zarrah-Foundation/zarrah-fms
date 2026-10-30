"""Shared dashboard forms and widget-styling helpers.

Keeps the admin dashboard on the same design-system input classes
(``form-input`` / ``form-select`` / ``form-textarea``) used across the public
site, so nothing needs bespoke CSS.
"""

from django import forms
from django.forms.widgets import CheckboxInput, Select, SelectMultiple, Textarea
from django.utils.translation import gettext_lazy as _

from accounts.models import User
from cms.models import CmsMedia, HomepageSection, HomepageSectionImage, ImpactStatistic, SectionType
from community.models import FAQ, LeadershipPerson, Partner, Testimonial, Volunteer
from core.choices import PaymentMethod
from core.models import SiteSettings, SmsSettings, SmtpSettings
from rbac.models import Permission, Role as RbacRole
from finance.models import Expense, Income
from news.models import News, NewsCategory
from reports.models import Report
from donations.models import (
    DonationCategory,
    DonationQuickAmount,
    PaymentMethodConfig,
)
from members.models import (
    Member,
    MemberApplication,
    MemberDocument,
    MemberGroup,
    MemberGroupMembership,
    MemberNote,
    MembershipFeeSettings,
    MembershipType,
    OrganizationalPosition,
)


def style_fields(form):
    """Apply design-system classes to every widget on a form (in place)."""
    for field in form.fields.values():
        widget = field.widget
        existing = widget.attrs.get("class", "")
        if isinstance(widget, CheckboxInput):
            base = "form-checkbox"
        elif isinstance(widget, (Select, SelectMultiple)):
            base = "form-select"
        elif isinstance(widget, Textarea):
            base = "form-textarea"
        else:
            base = "form-input"
        widget.attrs["class"] = (existing + " " + base).strip() if base not in existing else existing
    return form


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)


class SiteSettingsForm(StyledModelForm):
    class Meta:
        model = SiteSettings
        fields = [
            "foundation_name_bn", "foundation_name_en", "short_name",
            "tagline_bn", "tagline_en",
            "site_logo", "site_logo_white", "site_favicon",
            "primary_email", "secondary_email", "primary_phone", "secondary_phone",
            "whatsapp", "website_url", "address_bn", "address_en",
            "google_maps_url", "google_maps_embed_url", "maps_latitude", "maps_longitude",
            "facebook_url", "youtube_url", "linkedin_url", "instagram_url",
            "twitter_url", "telegram_url", "github_url",
            "meta_title", "meta_description", "meta_keywords", "og_image",
            "footer_text_bn", "footer_text_en", "copyright_text",
            "foundation_description_bn",
            "foundation_description_en",
            "registration_number",
            "registration_date",
            "office_hours",
            "brand_primary_color",
            "brand_secondary_color",
            "dark_logo",
            "twitter_card_image",
        ]


class SmtpSettingsForm(StyledModelForm):
    class Meta:
        model = SmtpSettings
        fields = [
            "host", "port", "username", "password", "encryption", "is_active",
            "from_name", "from_email", "reply_to",
        ]
        widgets = {
            "password": forms.PasswordInput(render_value=True),
        }


class SmsSettingsForm(StyledModelForm):
    class Meta:
        model = SmsSettings
        fields = [
            "enabled",
            "provider",
            "api_url",
            "api_key",
            "sender_id",
            "verification_timeout_seconds",
            "resend_cooldown_seconds",
            "max_attempts",
            "max_sends_per_hour",
        ]
        widgets = {
            "api_key": forms.PasswordInput(render_value=True),
        }


class MembershipFeeSettingsForm(StyledModelForm):
    fee_starting_month = forms.CharField(
        label=_("Fee Starting Month"),
        help_text=_(
            "Existing members become liable for monthly fees from the configured "
            "starting month. New members become liable from the month their "
            "membership is approved."
        ),
        widget=forms.TextInput(attrs={"type": "month"}),
    )

    class Meta:
        model = MembershipFeeSettings
        fields = [
            "monthly_fee_amount",
            "registration_fee_amount",
            "is_active",
            "admin_note",
        ]
        labels = {
            "monthly_fee_amount": _("Monthly Fee"),
            "registration_fee_amount": _("Registration Fee"),
            "is_active": _("Active"),
            "admin_note": _("Admin note"),
        }
        help_texts = {
            "monthly_fee_amount": _("Amount charged for each membership month (BDT)."),
            "registration_fee_amount": _(
                "One-time registration fee, separate from the monthly membership fee."
            ),
        }
        widgets = {
            "admin_note": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get("instance") or getattr(self, "instance", None)
        if instance and instance.pk and instance.fee_start_year >= 1000:
            self.fields["fee_starting_month"].initial = (
                f"{instance.fee_start_year:04d}-{instance.fee_start_month:02d}"
            )

    def clean_fee_starting_month(self):
        raw = (self.cleaned_data.get("fee_starting_month") or "").strip()
        if not raw:
            raise forms.ValidationError(_("Select a fee starting month."))
        try:
            year_s, month_s = raw.split("-", 1)
            year, month = int(year_s), int(month_s)
        except (TypeError, ValueError):
            raise forms.ValidationError(_("Use YYYY-MM format."))
        if month < 1 or month > 12:
            raise forms.ValidationError(_("Month must be between 1 and 12."))
        self.cleaned_data["_fee_start_year"] = year
        self.cleaned_data["_fee_start_month"] = month
        return raw

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.fee_start_year = self.cleaned_data["_fee_start_year"]
        instance.fee_start_month = self.cleaned_data["_fee_start_month"]
        if commit:
            instance.save()
        return instance


class MembershipTypeForm(StyledModelForm):
    class Meta:
        model = MembershipType
        fields = [
            "name_bn", "name_en", "slug", "description_bn", "description_en",
            "fee_amount", "is_lifetime", "display_order", "is_active",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["slug"].required = False


class MemberGroupForm(StyledModelForm):
    members = forms.ModelMultipleChoiceField(
        queryset=Member.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": "12"}),
        help_text=_("Approved members in this group (used for election eligibility)."),
    )

    class Meta:
        model = MemberGroup
        fields = ["name_bn", "name_en", "slug", "description", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["slug"].required = False
        from members.models import MemberStatus

        self.fields["members"].queryset = Member.objects.filter(
            status=MemberStatus.APPROVED
        ).order_by("first_name", "last_name")
        if self.instance and self.instance.pk:
            self.fields["members"].initial = Member.objects.filter(
                group_memberships__group=self.instance
            )

    def clean_slug(self):
        from django.utils.text import slugify

        slug = (self.cleaned_data.get("slug") or "").strip()
        if not slug:
            slug = slugify(self.cleaned_data.get("name_en") or "")[:50]
        return slug

    def save(self, commit=True):
        group = super().save(commit=commit)
        if commit:
            self._save_members(group)
        return group

    def save_m2m(self):
        """Called by generic create views after save(commit=False) patterns."""
        if self.instance and self.instance.pk:
            self._save_members(self.instance)

    def _save_members(self, group):
        selected = list(self.cleaned_data.get("members") or [])
        existing = {
            row.member_id: row
            for row in MemberGroupMembership.objects.filter(group=group)
        }
        selected_ids = {m.pk for m in selected}
        for mid, row in list(existing.items()):
            if mid not in selected_ids:
                row.delete()
        for member in selected:
            if member.pk not in existing:
                MemberGroupMembership.objects.create(group=group, member=member)


class MemberForm(StyledModelForm):
    """Edit an existing member's profile (does not touch the login account)."""

    class Meta:
        model = Member
        fields = [
            "first_name", "last_name", "phone", "gender", "date_of_birth",
            "blood_group", "nid_number", "membership_type", "status", "is_founder",
            "present_address", "permanent_address", "district", "upazila",
            "occupation", "organization", "education",
            "emergency_name", "emergency_phone", "emergency_relation",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
        }


class MemberCreateForm(forms.Form):
    """Manual member creation — also provisions a login account."""

    email = forms.EmailField(required=False, help_text="Optional. A temporary password is generated if provided.")
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100, required=False)
    phone = forms.CharField(max_length=20)
    district = forms.CharField(max_length=100)
    present_address = forms.CharField(widget=forms.Textarea)
    membership_type = forms.ModelChoiceField(
        queryset=MembershipType.objects.filter(is_active=True), required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)


class MemberNoteForm(StyledModelForm):
    class Meta:
        model = MemberNote
        fields = ["body"]
        widgets = {"body": forms.Textarea(attrs={"rows": 3})}


class MemberDocumentForm(StyledModelForm):
    class Meta:
        model = MemberDocument
        fields = ["title", "file"]


class MemberPositionAssignForm(forms.Form):
    """Assign an organizational position to a member."""

    position = forms.ModelChoiceField(
        queryset=OrganizationalPosition.objects.none(),
        label=_("Position"),
    )
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        label=_("Start date"),
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        label=_("End date"),
    )
    is_primary = forms.BooleanField(
        required=False,
        initial=False,
        label=_("Primary position"),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
        label=_("Notes"),
    )
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
        label=_("Reason"),
        help_text=_("Optional note recorded in the activity log."),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["position"].queryset = OrganizationalPosition.objects.filter(
            is_active=True
        ).order_by("display_order", "name_en")
        style_fields(self)


class MemberPositionEditForm(forms.Form):
    """Edit dates / primary / notes on an existing assignment."""

    start_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        label=_("Start date"),
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        label=_("End date"),
    )
    is_primary = forms.BooleanField(required=False, label=_("Primary position"))
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
        label=_("Notes"),
    )
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
        label=_("Reason"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)


class MemberEditForm(MemberForm):
    """Member profile edit with audit reason for sensitive changes."""

    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        label=_("Reason for change"),
        help_text=_("Required when changing official / sensitive fields."),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)


class ApplicationEditForm(StyledModelForm):
    """Admin edit of application fields (no private file contents)."""

    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        label=_("Reason for change"),
        help_text=_("Required when changing official / sensitive fields."),
    )

    class Meta:
        model = MemberApplication
        fields = [
            "bangla_name",
            "english_name",
            "father_name",
            "mother_name",
            "phone",
            "email",
            "gender",
            "date_of_birth",
            "identity_type",
            "identity_number",
            "present_district",
            "present_upazila",
            "present_address",
            "occupation",
            "organization",
            "emergency_name",
            "emergency_phone",
            "emergency_relation",
            "admin_message",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "present_address": forms.Textarea(attrs={"rows": 2}),
            "admin_message": forms.Textarea(attrs={"rows": 2}),
        }


# ----- Donations -----

class DonationCategoryForm(StyledModelForm):
    class Meta:
        model = DonationCategory
        fields = [
            "name_bn", "name_en", "slug", "description_bn", "description_en",
            "image", "icon", "display_order", "is_active", "is_featured", "is_default",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["slug"].required = False


class DonationQuickAmountForm(StyledModelForm):
    class Meta:
        model = DonationQuickAmount
        fields = ["category", "amount", "label_en", "label_bn", "display_order", "is_active"]


class PaymentMethodConfigForm(StyledModelForm):
    """CMS toggle form for non-secret fields. SSLCommerz secrets use a separate form."""

    class Meta:
        model = PaymentMethodConfig
        fields = [
            "method",
            "display_name",
            "channel_kind",
            "hosted_via",
            "supports_one_time",
            "supports_recurring",
            "account_details",
            "instructions_bn",
            "instructions_en",
            "is_enabled",
            "enabled_for_donation",
            "enabled_for_membership_fee",
            "display_order",
            "admin_notes",
        ]

    def clean_supports_recurring(self):
        value = self.cleaned_data.get("supports_recurring")
        method = self.cleaned_data.get("method") or getattr(self.instance, "method", None)
        # Never allow marking direct bKash/Nagad recurring as implemented.
        if value and method in (
            PaymentMethod.BKASH,
            PaymentMethod.NAGAD,
            PaymentMethod.ROCKET,
        ):
            raise forms.ValidationError(
                "Direct recurring for this method is not implemented."
            )
        if value and method == PaymentMethod.SSLCOMMERZ:
            from donations.gateway_capabilities import sslcommerz_supports_recurring

            if not sslcommerz_supports_recurring():
                raise forms.ValidationError(
                    "SSLCommerz recurring is not configured "
                    "(set SSLCOMMERZ_SALT_KEY and SSLCOMMERZ_RECURRING_PLAN_REFER)."
                )
        return value


class SSLCommerzCredentialForm(forms.Form):
    """Secure credential configuration. Store password is write-only (never prefilled)."""

    store_id = forms.CharField(
        max_length=120,
        required=False,
        label=_("Store ID"),
        help_text=_("Merchant Store ID. Leave blank to keep current value."),
        widget=forms.TextInput(attrs={"class": "form-input", "autocomplete": "off"}),
    )
    store_password = forms.CharField(
        max_length=200,
        required=False,
        label=_("Store Password"),
        help_text=_(
            "Leave blank to keep the current password. The password is never shown after save."
        ),
        widget=forms.PasswordInput(
            attrs={
                "class": "form-input",
                "autocomplete": "new-password",
                "placeholder": "••••••••",
            },
            render_value=False,
        ),
    )
    clear_password = forms.BooleanField(
        required=False,
        label=_("Clear saved password"),
        help_text=_("Remove the database password (falls back to environment variables)."),
        widget=forms.CheckboxInput(attrs={"class": "form-checkbox"}),
    )
    use_database_credentials = forms.BooleanField(
        required=False,
        label=_("Use dashboard credentials"),
        help_text=_(
            "When checked, checkout uses the Store ID and password saved here. "
            "When unchecked, production environment variables are preferred."
        ),
        widget=forms.CheckboxInput(attrs={"class": "form-checkbox"}),
    )
    is_sandbox = forms.BooleanField(
        required=False,
        label=_("Sandbox mode"),
        help_text=_("Checked = Sandbox. Uncheck for Production (requires confirmation)."),
        widget=forms.CheckboxInput(attrs={"class": "form-checkbox"}),
    )
    confirm_production = forms.BooleanField(
        required=False,
        label=_("I confirm enabling Production mode"),
        help_text=_("Required when switching Sandbox off. Live payments will be accepted."),
        widget=forms.CheckboxInput(attrs={"class": "form-checkbox"}),
    )
    is_enabled = forms.BooleanField(
        required=False,
        label=_("Gateway enabled"),
        widget=forms.CheckboxInput(attrs={"class": "form-checkbox"}),
    )
    enabled_for_donation = forms.BooleanField(
        required=False,
        label=_("Enable for donations"),
        widget=forms.CheckboxInput(attrs={"class": "form-checkbox"}),
    )
    enabled_for_membership_fee = forms.BooleanField(
        required=False,
        label=_("Enable for membership fees"),
        widget=forms.CheckboxInput(attrs={"class": "form-checkbox"}),
    )
    admin_notes = forms.CharField(
        required=False,
        label=_("Admin notes"),
        widget=forms.Textarea(attrs={"class": "form-input", "rows": 3}),
    )
    salt_key = forms.CharField(
        max_length=200,
        required=False,
        label=_("Recurring SALT key"),
        help_text=_("Write-only. Leave blank to keep the current SALT. Never displayed after save."),
        widget=forms.PasswordInput(
            attrs={"class": "form-input", "autocomplete": "new-password", "placeholder": "••••••••"},
            render_value=False,
        ),
    )
    clear_salt_key = forms.BooleanField(
        required=False,
        label=_("Clear saved SALT key"),
        widget=forms.CheckboxInput(attrs={"class": "form-checkbox"}),
    )
    recurring_plan_refer = forms.CharField(
        max_length=120,
        required=False,
        label=_("Recurring plan refer"),
        help_text=_("SSLCommerz merchant plan reference for EasyCheckout recurring."),
        widget=forms.TextInput(attrs={"class": "form-input", "autocomplete": "off"}),
    )
    merchant_recurring_enabled = forms.BooleanField(
        required=False,
        label=_("Merchant recurring enabled"),
        help_text=_("Confirm the SSLCommerz merchant account has recurring enabled."),
        widget=forms.CheckboxInput(attrs={"class": "form-checkbox"}),
    )
    refunds_enabled = forms.BooleanField(
        required=False,
        label=_("Refunds enabled"),
        help_text=_("Allow refund requests. Does not invent a successful gateway refund."),
        widget=forms.CheckboxInput(attrs={"class": "form-checkbox"}),
    )

    def __init__(self, *args, instance=None, **kwargs):
        self.instance = instance
        super().__init__(*args, **kwargs)
        if instance is not None and not self.is_bound:
            self.fields["store_id"].initial = instance.store_id or ""
            self.fields["use_database_credentials"].initial = instance.use_database_credentials
            self.fields["is_sandbox"].initial = (
                True if instance.is_sandbox is None else bool(instance.is_sandbox)
            )
            self.fields["is_enabled"].initial = instance.is_enabled
            self.fields["enabled_for_donation"].initial = instance.enabled_for_donation
            self.fields["enabled_for_membership_fee"].initial = instance.enabled_for_membership_fee
            self.fields["admin_notes"].initial = instance.admin_notes or ""
            self.fields["recurring_plan_refer"].initial = instance.recurring_plan_refer or ""
            self.fields["merchant_recurring_enabled"].initial = instance.merchant_recurring_enabled
            self.fields["refunds_enabled"].initial = instance.refunds_enabled

    def clean(self):
        cleaned = super().clean()
        is_sandbox = cleaned.get("is_sandbox")
        confirm_production = cleaned.get("confirm_production")
        if not is_sandbox and not confirm_production:
            already = bool(
                self.instance
                and self.instance.is_sandbox is False
                and self.instance.production_confirmed_at
            )
            if not already:
                self.add_error(
                    "confirm_production",
                    _("Confirm Production mode before disabling Sandbox."),
                )
        if cleaned.get("use_database_credentials"):
            store_id = (cleaned.get("store_id") or "").strip() or (
                (self.instance.store_id or "").strip() if self.instance else ""
            )
            has_pw = bool(cleaned.get("store_password"))
            if (
                self.instance
                and self.instance.encrypted_store_password
                and not cleaned.get("clear_password")
            ):
                has_pw = True
            if not store_id or not has_pw:
                raise forms.ValidationError(
                    _(
                        "Dashboard credentials require both Store ID and a Store Password "
                        "(or an existing saved password)."
                    )
                )
        # Merchant recurring cannot be enabled without SALT + plan refer (env or form).
        if cleaned.get("merchant_recurring_enabled"):
            from django.conf import settings as dj_settings

            plan = (cleaned.get("recurring_plan_refer") or "").strip() or (
                (self.instance.recurring_plan_refer or "").strip() if self.instance else ""
            ) or (getattr(dj_settings, "SSLCOMMERZ_RECURRING_PLAN_REFER", "") or "").strip()
            has_salt = bool(cleaned.get("salt_key"))
            if not has_salt and self.instance and not cleaned.get("clear_salt_key"):
                has_salt = bool(self.instance.encrypted_salt_key) or bool(
                    (getattr(dj_settings, "SSLCOMMERZ_SALT_KEY", "") or "").strip()
                )
            if cleaned.get("clear_salt_key") and not cleaned.get("salt_key"):
                has_salt = bool(
                    (getattr(dj_settings, "SSLCOMMERZ_SALT_KEY", "") or "").strip()
                )
            if not has_salt or not plan:
                self.add_error(
                    "merchant_recurring_enabled",
                    _(
                        "Cannot enable merchant recurring without SALT key and plan refer "
                        "(provide them here or via environment)."
                    ),
                )
        return cleaned

    def save(self):
        from django.utils import timezone

        instance = self.instance
        if instance is None:
            raise ValueError("SSLCommerzCredentialForm requires an instance.")
        store_id = (self.cleaned_data.get("store_id") or "").strip()
        if store_id:
            instance.store_id = store_id
        if self.cleaned_data.get("clear_password"):
            instance.clear_store_password()
        elif self.cleaned_data.get("store_password"):
            instance.set_store_password(self.cleaned_data["store_password"])
        instance.use_database_credentials = bool(
            self.cleaned_data.get("use_database_credentials")
        )
        is_sandbox = bool(self.cleaned_data.get("is_sandbox"))
        instance.is_sandbox = is_sandbox
        if not is_sandbox:
            instance.production_confirmed_at = timezone.now()
        else:
            instance.production_confirmed_at = None
        instance.is_enabled = bool(self.cleaned_data.get("is_enabled"))
        instance.enabled_for_donation = bool(self.cleaned_data.get("enabled_for_donation"))
        instance.enabled_for_membership_fee = bool(
            self.cleaned_data.get("enabled_for_membership_fee")
        )
        instance.admin_notes = self.cleaned_data.get("admin_notes") or ""
        if self.cleaned_data.get("clear_salt_key"):
            instance.clear_salt_key()
        elif self.cleaned_data.get("salt_key"):
            instance.set_salt_key(self.cleaned_data["salt_key"])
        instance.recurring_plan_refer = (
            self.cleaned_data.get("recurring_plan_refer") or ""
        ).strip()
        instance.merchant_recurring_enabled = bool(
            self.cleaned_data.get("merchant_recurring_enabled")
        )
        instance.refunds_enabled = bool(self.cleaned_data.get("refunds_enabled"))
        instance.save()
        return instance


class ManualDonationForm(forms.Form):
    """Record an offline donation (cash / bank / mobile wallet)."""

    amount = forms.FloatField(min_value=1)
    category = forms.ModelChoiceField(queryset=DonationCategory.objects.filter(is_active=True))
    payment_method = forms.ChoiceField(
        choices=[(m.value, m.label) for m in PaymentMethod if m != PaymentMethod.SSLCOMMERZ]
    )
    donor_name = forms.CharField(max_length=200, required=False)
    donor_phone = forms.CharField(max_length=20, required=False)
    donor_email = forms.EmailField(required=False)
    is_anonymous = forms.BooleanField(required=False)
    message = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("is_anonymous") and not cleaned.get("donor_name"):
            self.add_error("donor_name", "Provide a donor name or mark as anonymous.")
        return cleaned


# ----- Finance -----

_DATE_INPUT_FORMATS = ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"]


class IncomeForm(StyledModelForm):
    class Meta:
        model = Income
        fields = ["title", "description", "amount", "received_date", "source"]
        widgets = {
            "received_date": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["received_date"].input_formats = _DATE_INPUT_FORMATS


class ExpenseForm(StyledModelForm):
    class Meta:
        model = Expense
        fields = ["title", "description", "amount", "expense_date", "category", "approved_by"]
        widgets = {
            "expense_date": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["expense_date"].input_formats = _DATE_INPUT_FORMATS


# ----- Content: News, categories, reports/transparency -----

class NewsCategoryForm(StyledModelForm):
    class Meta:
        model = NewsCategory
        fields = ["name_bn", "name_en", "slug", "display_order", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["slug"].required = False


class NewsForm(StyledModelForm):
    class Meta:
        model = News
        fields = [
            "title",
            "title_bn",
            "slug",
            "category",
            "excerpt",
            "excerpt_bn",
            "content",
            "content_bn",
            "featured_image",
            "is_published",
            "published_at",
        ]
        labels = {
            "title": _("Title (English)"),
            "title_bn": _("Title (Bangla)"),
            "excerpt": _("Excerpt (English)"),
            "excerpt_bn": _("Excerpt (Bangla)"),
            "content": _("Content (English)"),
            "content_bn": _("Content (Bangla)"),
            "is_published": _("Published"),
            "published_at": _("Publication date/time"),
            "featured_image": _("Featured image"),
            "slug": _("URL slug"),
        }
        help_texts = {
            "slug": _("Leave blank to generate from the English title."),
            "content": _(
                "Rich text supported: headings, paragraphs, bold, italic, lists, links, "
                "blockquotes and tables. Scripts are removed for security."
            ),
            "content_bn": _(
                "Bangla rich text. Same sanitization rules as English. Optional — "
                "English content is shown when Bangla is empty."
            ),
            "is_published": _("Draft articles stay hidden on the public site."),
        }
        widgets = {
            "published_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
            "content": forms.Textarea(
                attrs={
                    "rows": 16,
                    "class": "form-textarea js-richtext",
                    "data-richtext": "1",
                }
            ),
            "content_bn": forms.Textarea(
                attrs={
                    "rows": 16,
                    "class": "form-textarea js-richtext",
                    "data-richtext": "1",
                }
            ),
            "excerpt": forms.Textarea(attrs={"rows": 3}),
            "excerpt_bn": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["slug"].required = False
        self.fields["title_bn"].required = False
        self.fields["content_bn"].required = False
        self.fields["excerpt_bn"].required = False
        self.fields["published_at"].input_formats = _DATE_INPUT_FORMATS
        # Avoid HTML5 blocking submit while TinyMCE hides the textarea.
        self.fields["content"].widget.attrs.pop("required", None)
        self.fields["content"].required = True  # server-side still required

    def clean_slug(self):
        from django.utils.text import slugify

        slug = (self.cleaned_data.get("slug") or "").strip()
        title = (self.cleaned_data.get("title") or "").strip()
        if not slug:
            slug = slugify(title) or "article"
        base = slug
        n = 2
        qs = News.objects.filter(slug=slug)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        while qs.exists():
            slug = f"{base}-{n}"
            n += 1
            qs = News.objects.filter(slug=slug)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
        return slug

    def clean_content(self):
        from core.html_sanitize import sanitize_html

        return sanitize_html(self.cleaned_data.get("content") or "")

    def clean_content_bn(self):
        from core.html_sanitize import sanitize_html

        return sanitize_html(self.cleaned_data.get("content_bn") or "")


class ReportForm(StyledModelForm):
    class Meta:
        model = Report
        fields = [
            "title",
            "title_bn",
            "title_en",
            "description",
            "description_bn",
            "description_en",
            "type",
            "year",
            "file",
            "is_public",
            "show_on_transparency",
            "show_on_reports",
            "published_at",
            "display_order",
        ]
        labels = {
            "type": _("Document category"),
            "title": _("Document title (legacy / default)"),
            "title_bn": _("Title (Bangla)"),
            "title_en": _("Title (English)"),
            "description": _("Description (legacy)"),
            "description_bn": _("Description (Bangla)"),
            "description_en": _("Description (English)"),
            "is_public": _("Publish publicly"),
            "show_on_transparency": _("Show on Transparency"),
            "show_on_reports": _("Show on Reports"),
            "year": _("Publication year"),
            "published_at": _("Publication date"),
            "display_order": _("Display order"),
        }
        help_texts = {
            "type": _(
                "Category for grouping (governance, financial transparency, policies, etc.)."
            ),
            "is_public": _(
                "Master public switch. When off, the document appears nowhere publicly."
            ),
            "show_on_transparency": _(
                "Choose where this public document should appear. These destinations are independent."
            ),
            "show_on_reports": _(
                "Choose where this public document should appear. These destinations are independent."
            ),
            "year": _("Year shown next to the document (optional)."),
        }
        widgets = {
            "published_at": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 2}),
            "description_bn": forms.Textarea(attrs={"rows": 2}),
            "description_en": forms.Textarea(attrs={"rows": 2}),
        }


# ----- Community: testimonials, FAQs, partners -----

class TestimonialForm(StyledModelForm):
    class Meta:
        model = Testimonial
        fields = [
            "author_name", "designation", "content_bn", "content_en",
            "photo", "display_order", "is_published",
        ]
        widgets = {
            "content_bn": forms.Textarea(attrs={"rows": 3}),
            "content_en": forms.Textarea(attrs={"rows": 3}),
        }


class FAQForm(StyledModelForm):
    class Meta:
        model = FAQ
        fields = [
            "question_bn", "question_en", "answer_bn", "answer_en",
            "display_order", "is_active",
        ]
        widgets = {
            "answer_bn": forms.Textarea(attrs={"rows": 3}),
            "answer_en": forms.Textarea(attrs={"rows": 3}),
        }


class PartnerForm(StyledModelForm):
    class Meta:
        model = Partner
        fields = [
            "name", "slug", "logo", "url", "relationship_type",
            "description_en", "description_bn", "display_order", "is_active",
        ]
        widgets = {
            "description_en": forms.Textarea(attrs={"rows": 2}),
            "description_bn": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["slug"].required = False


class ImpactStatisticForm(StyledModelForm):
    class Meta:
        model = ImpactStatistic
        fields = [
            "value", "label_en", "label_bn", "description_en", "description_bn",
            "period_year", "icon", "display_order", "is_published",
        ]
        widgets = {
            "description_en": forms.Textarea(attrs={"rows": 2}),
            "description_bn": forms.Textarea(attrs={"rows": 2}),
        }


class LeadershipPersonForm(StyledModelForm):
    class Meta:
        model = LeadershipPerson
        fields = [
            "role", "name", "role_label_bn", "role_label_en",
            "bio_bn", "bio_en", "photo", "display_order", "is_published",
        ]
        widgets = {
            "bio_bn": forms.Textarea(attrs={"rows": 3}),
            "bio_en": forms.Textarea(attrs={"rows": 3}),
        }


class VolunteerForm(StyledModelForm):
    class Meta:
        model = Volunteer
        fields = ["name", "email", "phone", "area_of_interest", "message", "status"]
        widgets = {"message": forms.Textarea(attrs={"rows": 4})}


# ----- Administration: users & roles -----

class UserCreateForm(StyledModelForm):
    password1 = forms.CharField(
        label="Password", required=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Leave blank to auto-generate a temporary password.",
    )
    password2 = forms.CharField(
        label="Confirm password", required=False, widget=forms.PasswordInput,
    )
    rbac_roles = forms.ModelMultipleChoiceField(
        label="Assigned roles", queryset=RbacRole.objects.filter(is_active=True),
        required=False, widget=forms.SelectMultiple,
    )

    class Meta:
        model = User
        fields = ["email", "name", "role", "is_active_member", "is_staff"]

    def clean_email(self):
        email = self.cleaned_data["email"]
        qs = User.objects.filter(email__iexact=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 or p2:
            if p1 != p2:
                raise forms.ValidationError("Passwords do not match.")
        return cleaned


class UserEditForm(StyledModelForm):
    rbac_roles = forms.ModelMultipleChoiceField(
        label="Assigned roles", queryset=RbacRole.objects.filter(is_active=True),
        required=False, widget=forms.SelectMultiple,
    )

    class Meta:
        model = User
        fields = ["name", "role", "is_active_member", "is_staff"]


class SetPasswordForm(forms.Form):
    password1 = forms.CharField(label="New password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") != cleaned.get("password2"):
            raise forms.ValidationError("Passwords do not match.")
        return cleaned


class RoleForm(StyledModelForm):
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all(), required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = RbacRole
        fields = ["name", "description", "legacy_role", "is_active", "permissions"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Checkbox widgets shouldn't get the form-select class.
        self.fields["permissions"].widget.attrs.pop("class", None)


# ----- Website CMS: homepage sections -----

from cms.home_content import pack_mission_vision, split_mission_vision
from cms.section_meta import section_meta


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """Accept multiple uploads; returns a list of files."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={"accept": "image/*"}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        if not data:
            return []
        if not isinstance(data, (list, tuple)):
            data = [data]
        result = []
        single_clean = super().clean
        for item in data:
            cleaned = single_clean(item, initial)
            if cleaned:
                result.append(cleaned)
        return result


class HomepageSectionImageForm(StyledModelForm):
    """Edit membership metadata. Physical file lives on CmsMedia (reusable)."""

    class Meta:
        model = HomepageSectionImage
        fields = [
            "alt_en",
            "alt_bn",
            "caption_en",
            "caption_bn",
            "order",
            "is_active",
        ]
        labels = {
            "alt_en": _("Alt text (English)"),
            "alt_bn": _("Alt text (Bangla)"),
            "caption_en": _("Caption (English)"),
            "caption_bn": _("Caption (Bangla)"),
            "is_active": _("Active on homepage"),
            "order": _("Order"),
        }
        help_texts = {
            "is_active": _("Inactive images stay in the library but are hidden on the public slider."),
            "caption_en": _("Leave blank to use the library default caption."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["order"].required = False

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("order") in (None, ""):
            cleaned["order"] = 0
        return cleaned


HomepageSectionImageFormSet = forms.inlineformset_factory(
    HomepageSection,
    HomepageSectionImage,
    form=HomepageSectionImageForm,
    extra=0,
    can_delete=True,
    max_num=48,
)


class HomepageSectionForm(StyledModelForm):
    """Type-aware homepage section editor over the existing HomepageSection model."""

    eyebrow_en = forms.CharField(required=False, label=_("Eyebrow (English)"), max_length=200)
    eyebrow_bn = forms.CharField(required=False, label=_("Eyebrow (Bangla)"), max_length=200)
    secondary_button_text_en = forms.CharField(
        required=False, label=_("Secondary CTA label (English)"), max_length=100
    )
    secondary_button_text_bn = forms.CharField(
        required=False, label=_("Secondary CTA label (Bangla)"), max_length=100
    )
    secondary_button_link = forms.CharField(
        required=False, label=_("Secondary CTA URL"), max_length=500
    )
    display_count = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=24,
        label=_("Number to display"),
        help_text=_("How many items from the data source to show on the homepage."),
    )
    mission_title_en = forms.CharField(
        required=False, label=_("Mission title (English)"), max_length=200, initial="Our Mission"
    )
    mission_title_bn = forms.CharField(
        required=False,
        label=_("Mission title (Bangla)"),
        max_length=200,
        initial="আমাদের লক্ষ্য",
    )
    vision_title_en = forms.CharField(
        required=False, label=_("Vision title (English)"), max_length=200, initial="Our Vision"
    )
    vision_title_bn = forms.CharField(
        required=False,
        label=_("Vision title (Bangla)"),
        max_length=200,
        initial="আমাদের অভিলক্ষ্য",
    )
    mission_content_en = forms.CharField(
        required=False,
        label=_("Mission content (English)"),
        widget=forms.Textarea(attrs={"rows": 5}),
    )
    mission_content_bn = forms.CharField(
        required=False,
        label=_("Mission content (Bangla)"),
        widget=forms.Textarea(attrs={"rows": 5}),
    )
    vision_content_en = forms.CharField(
        required=False,
        label=_("Vision content (English)"),
        widget=forms.Textarea(attrs={"rows": 5}),
    )
    vision_content_bn = forms.CharField(
        required=False,
        label=_("Vision content (Bangla)"),
        widget=forms.Textarea(attrs={"rows": 5}),
    )
    gallery_autoplay = forms.BooleanField(
        required=False,
        label=_("Autoplay slider"),
        initial=True,
    )
    gallery_autoplay_interval = forms.IntegerField(
        required=False,
        min_value=2000,
        max_value=30000,
        label=_("Autoplay interval (ms)"),
        initial=5000,
        help_text=_("Milliseconds between slides when autoplay is on (2000–30000)."),
    )
    gallery_show_arrows = forms.BooleanField(
        required=False, label=_("Show previous/next arrows"), initial=True
    )
    gallery_show_dots = forms.BooleanField(
        required=False, label=_("Show slide indicators"), initial=True
    )
    gallery_show_captions = forms.BooleanField(
        required=False, label=_("Show captions when available"), initial=True
    )
    attach_media_ids = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        label="",
    )
    new_gallery_images = MultipleFileField(
        required=False,
        label=_("Add new images"),
        help_text=_("Select multiple images at once (JPG, PNG, WebP, GIF — max 8 MB each)."),
    )

    class Meta:
        model = HomepageSection
        fields = [
            "section_type",
            "order",
            "is_visible",
            "is_published",
            "title_bn",
            "title_en",
            "content_bn",
            "content_en",
            "image",
            "button_text_bn",
            "button_text_en",
            "button_link",
        ]
        labels = {
            "title_en": _("Heading (English)"),
            "title_bn": _("Heading (Bangla)"),
            "content_en": _("Description / intro (English)"),
            "content_bn": _("Description / intro (Bangla)"),
            "button_text_en": _("Primary CTA label (English)"),
            "button_text_bn": _("Primary CTA label (Bangla)"),
            "button_link": _("Primary CTA URL"),
            "image": _("Image"),
            "is_published": _("Published"),
            "is_visible": _("Visible (not disabled)"),
            "order": _("Display order"),
            "section_type": _("Section type"),
        }
        widgets = {
            "content_bn": forms.Textarea(attrs={"rows": 4}),
            "content_en": forms.Textarea(attrs={"rows": 4}),
        }

    # Fields shown per editor profile (plus always: order, is_visible, is_published).
    EDITOR_FIELDS = {
        "hero": [
            "eyebrow_en",
            "eyebrow_bn",
            "title_en",
            "title_bn",
            "content_en",
            "content_bn",
            "button_text_en",
            "button_text_bn",
            "button_link",
            "secondary_button_text_en",
            "secondary_button_text_bn",
            "secondary_button_link",
            "image",
        ],
        "trust": ["title_en", "title_bn", "content_en", "content_bn"],
        "mission_vision": [
            "title_en",
            "title_bn",
            "mission_title_en",
            "mission_title_bn",
            "mission_content_en",
            "mission_content_bn",
            "vision_title_en",
            "vision_title_bn",
            "vision_content_en",
            "vision_content_bn",
            "button_text_en",
            "button_text_bn",
            "button_link",
        ],
        "approach": [
            "title_en",
            "title_bn",
            "content_en",
            "content_bn",
            "image",
            "button_text_en",
            "button_text_bn",
            "button_link",
        ],
        "focus": ["title_en", "title_bn", "content_en", "content_bn", "button_text_en", "button_text_bn", "button_link"],
        "leadership": [
            "title_en",
            "title_bn",
            "content_en",
            "content_bn",
            "display_count",
            "button_text_en",
            "button_text_bn",
            "button_link",
        ],
        "testimonials": [
            "title_en",
            "title_bn",
            "content_en",
            "content_bn",
            "display_count",
        ],
        "partners": [
            "title_en",
            "title_bn",
            "content_en",
            "content_bn",
            "display_count",
        ],
        "news": [
            "title_en",
            "title_bn",
            "content_en",
            "content_bn",
            "display_count",
            "button_text_en",
            "button_text_bn",
            "button_link",
        ],
        "transparency": [
            "title_en",
            "title_bn",
            "content_en",
            "content_bn",
            "display_count",
            "button_text_en",
            "button_text_bn",
            "button_link",
        ],
        "cta": [
            "title_en",
            "title_bn",
            "content_en",
            "content_bn",
            "button_text_en",
            "button_text_bn",
            "button_link",
            "image",
        ],
        "gallery": [
            "title_en",
            "title_bn",
            "content_en",
            "content_bn",
            "gallery_autoplay",
            "gallery_autoplay_interval",
            "gallery_show_arrows",
            "gallery_show_dots",
            "gallery_show_captions",
            "attach_media_ids",
            "new_gallery_images",
        ],
        "generic": [
            "title_en",
            "title_bn",
            "content_en",
            "content_bn",
            "image",
            "button_text_en",
            "button_text_bn",
            "button_link",
        ],
    }

    def __init__(self, *args, **kwargs):
        self.lock_section_type = kwargs.pop("lock_section_type", False)
        super().__init__(*args, **kwargs)
        instance = self.instance
        cfg = instance.get_config() if instance and instance.pk else {}

        self.fields["eyebrow_en"].initial = cfg.get("eyebrow_en", "")
        self.fields["eyebrow_bn"].initial = cfg.get("eyebrow_bn", "")
        self.fields["secondary_button_text_en"].initial = cfg.get("secondary_button_text_en", "")
        self.fields["secondary_button_text_bn"].initial = cfg.get("secondary_button_text_bn", "")
        self.fields["secondary_button_link"].initial = cfg.get("secondary_button_link", "")
        self.fields["display_count"].initial = cfg.get("display_count") or 6
        self.fields["mission_title_en"].initial = cfg.get("mission_title_en") or "Our Mission"
        self.fields["mission_title_bn"].initial = cfg.get("mission_title_bn") or "আমাদের লক্ষ্য"
        self.fields["vision_title_en"].initial = cfg.get("vision_title_en") or "Our Vision"
        self.fields["vision_title_bn"].initial = cfg.get("vision_title_bn") or "আমাদের অভিলক্ষ্য"

        if instance and instance.pk and instance.section_type == SectionType.MISSION_VISION:
            m_en, v_en = split_mission_vision(instance.content_en)
            m_bn, v_bn = split_mission_vision(instance.content_bn)
            self.fields["mission_content_en"].initial = m_en
            self.fields["vision_content_en"].initial = v_en
            self.fields["mission_content_bn"].initial = m_bn
            self.fields["vision_content_bn"].initial = v_bn

        st = None
        if self.data.get("section_type"):
            st = self.data.get("section_type")
        elif instance and instance.section_type:
            st = instance.section_type
        elif self.initial.get("section_type"):
            st = self.initial.get("section_type")
        self.editor_key = section_meta(st or "").get("editor", "generic")
        self.source_help = section_meta(st or "").get("source_help", "")
        self.manage_url_name = section_meta(st or "").get("manage_url_name")

        allowed = set(self.EDITOR_FIELDS.get(self.editor_key, self.EDITOR_FIELDS["generic"]))
        allowed |= {"order", "is_visible", "is_published"}
        if self.lock_section_type and "section_type" in self.fields:
            self.fields["section_type"].disabled = True
            self.fields["section_type"].required = False
        else:
            allowed.add("section_type")

        for name in list(self.fields.keys()):
            if name == "section_type":
                continue
            if name not in allowed:
                self.fields.pop(name)

        if self.editor_key == "trust":
            self.fields["title_en"].help_text = _(
                "Short trust line. Registration number/date are taken from Site Settings."
            )
        if self.editor_key == "focus":
            self.fields["content_en"].help_text = _(
                "Section intro only. Focus area cards come from About / Objectives."
            )
        if self.editor_key == "hero" and "image" in self.fields:
            self.fields["image"].label = _("Hero / background image")
        if self.editor_key in ("leadership", "testimonials", "partners", "news"):
            defaults = {
                "leadership": 6,
                "testimonials": 8,
                "partners": 16,
                "news": 3,
            }
            self.fields["display_count"].initial = cfg.get("display_count") or defaults.get(
                self.editor_key, 6
            )
        if self.editor_key == "mission_vision":
            for key in (
                "mission_title_bn",
                "vision_title_bn",
                "mission_content_bn",
                "vision_content_bn",
            ):
                if key in self.fields and key.endswith("_bn") and "title" in key:
                    self.fields[key].help_text = _(
                        "Use exactly “আমাদের লক্ষ্য” / “আমাদের অভিলক্ষ্য” for Mission / Vision."
                    )
        if self.editor_key == "gallery":
            gs = instance.gallery_settings() if instance and instance.pk else {
                "autoplay": True,
                "autoplay_interval": 5000,
                "show_arrows": True,
                "show_dots": True,
                "show_captions": True,
            }
            if "gallery_autoplay" in self.fields:
                self.fields["gallery_autoplay"].initial = gs["autoplay"]
            if "gallery_autoplay_interval" in self.fields:
                self.fields["gallery_autoplay_interval"].initial = gs["autoplay_interval"]
            if "gallery_show_arrows" in self.fields:
                self.fields["gallery_show_arrows"].initial = gs["show_arrows"]
            if "gallery_show_dots" in self.fields:
                self.fields["gallery_show_dots"].initial = gs["show_dots"]
            if "gallery_show_captions" in self.fields:
                self.fields["gallery_show_captions"].initial = gs["show_captions"]

        style_fields(self)

    def clean(self):
        cleaned = super().clean()
        if self.lock_section_type and self.instance.pk:
            cleaned["section_type"] = self.instance.section_type
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        cfg = dict(instance.get_config() if instance.pk else {})

        for key in (
            "eyebrow_en",
            "eyebrow_bn",
            "secondary_button_text_en",
            "secondary_button_text_bn",
            "secondary_button_link",
            "mission_title_en",
            "mission_title_bn",
            "vision_title_en",
            "vision_title_bn",
        ):
            if key in self.cleaned_data:
                val = (self.cleaned_data.get(key) or "").strip()
                if val:
                    cfg[key] = val
                else:
                    cfg.pop(key, None)

        if "display_count" in self.cleaned_data and self.cleaned_data.get("display_count"):
            cfg["display_count"] = int(self.cleaned_data["display_count"])

        st = self.cleaned_data.get("section_type") or instance.section_type
        if st == SectionType.MISSION_VISION or self.editor_key == "mission_vision":
            instance.content_en = pack_mission_vision(
                self.cleaned_data.get("mission_content_en", ""),
                self.cleaned_data.get("vision_content_en", ""),
            )
            instance.content_bn = pack_mission_vision(
                self.cleaned_data.get("mission_content_bn", ""),
                self.cleaned_data.get("vision_content_bn", ""),
            )
            cfg.setdefault("mission_title_en", "Our Mission")
            cfg.setdefault("mission_title_bn", "আমাদের লক্ষ্য")
            cfg.setdefault("vision_title_en", "Our Vision")
            cfg.setdefault("vision_title_bn", "আমাদের অভিলক্ষ্য")

        if self.editor_key == "gallery" or st == SectionType.GALLERY_PREVIEW:
            if "gallery_autoplay" in self.cleaned_data:
                cfg["autoplay"] = bool(self.cleaned_data.get("gallery_autoplay"))
            if "gallery_autoplay_interval" in self.cleaned_data:
                try:
                    cfg["autoplay_interval"] = int(
                        self.cleaned_data.get("gallery_autoplay_interval") or 5000
                    )
                except (TypeError, ValueError):
                    cfg["autoplay_interval"] = 5000
            if "gallery_show_arrows" in self.cleaned_data:
                cfg["show_arrows"] = bool(self.cleaned_data.get("gallery_show_arrows"))
            if "gallery_show_dots" in self.cleaned_data:
                cfg["show_dots"] = bool(self.cleaned_data.get("gallery_show_dots"))
            if "gallery_show_captions" in self.cleaned_data:
                cfg["show_captions"] = bool(self.cleaned_data.get("gallery_show_captions"))

        instance.config = cfg
        if commit:
            instance.save()
            self.save_m2m()
        return instance
