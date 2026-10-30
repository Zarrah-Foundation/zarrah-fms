"""Direct provider (bKash / Nagad) credential form — write-only secrets."""

from django import forms
from django.utils.translation import gettext_lazy as _


class DirectProviderCredentialForm(forms.Form):
    api_app_key = forms.CharField(
        max_length=200,
        required=False,
        label=_("App key / Merchant ID"),
        widget=forms.TextInput(attrs={"class": "form-input", "autocomplete": "off"}),
    )
    api_secret = forms.CharField(
        max_length=400,
        required=False,
        label=_("API secret"),
        help_text=_("Write-only. Leave blank to keep the current secret."),
        widget=forms.PasswordInput(
            attrs={"class": "form-input", "autocomplete": "new-password", "placeholder": "••••••••"},
            render_value=False,
        ),
    )
    api_username = forms.CharField(
        max_length=200,
        required=False,
        label=_("API username (if required)"),
        widget=forms.TextInput(attrs={"class": "form-input", "autocomplete": "off"}),
    )
    api_password = forms.CharField(
        max_length=400,
        required=False,
        label=_("API password"),
        help_text=_("Write-only."),
        widget=forms.PasswordInput(
            attrs={"class": "form-input", "autocomplete": "new-password", "placeholder": "••••••••"},
            render_value=False,
        ),
    )
    clear_secrets = forms.BooleanField(
        required=False,
        label=_("Clear saved API secrets"),
        widget=forms.CheckboxInput(attrs={"class": "form-checkbox"}),
    )
    is_enabled = forms.BooleanField(
        required=False,
        label=_("Gateway enabled"),
        widget=forms.CheckboxInput(attrs={"class": "form-checkbox"}),
    )
    is_sandbox = forms.BooleanField(
        required=False,
        label=_("Sandbox mode"),
        widget=forms.CheckboxInput(attrs={"class": "form-checkbox"}),
    )
    confirm_production = forms.BooleanField(
        required=False,
        label=_("I confirm enabling Production mode"),
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
    merchant_recurring_enabled = forms.BooleanField(
        required=False,
        label=_("Merchant recurring enabled"),
        help_text=_("Does not expose recurring to donors until live-verified."),
        widget=forms.CheckboxInput(attrs={"class": "form-checkbox"}),
    )
    refunds_enabled = forms.BooleanField(
        required=False,
        label=_("Refunds enabled"),
        widget=forms.CheckboxInput(attrs={"class": "form-checkbox"}),
    )
    admin_notes = forms.CharField(
        required=False,
        label=_("Admin notes"),
        widget=forms.Textarea(attrs={"class": "form-input", "rows": 3}),
    )

    def __init__(self, *args, instance=None, **kwargs):
        self.instance = instance
        super().__init__(*args, **kwargs)
        if instance is not None and not self.is_bound:
            self.fields["api_app_key"].initial = instance.api_app_key or ""
            self.fields["api_username"].initial = instance.api_username or ""
            self.fields["is_enabled"].initial = instance.is_enabled
            self.fields["is_sandbox"].initial = (
                True if instance.is_sandbox is None else bool(instance.is_sandbox)
            )
            self.fields["enabled_for_donation"].initial = instance.enabled_for_donation
            self.fields["enabled_for_membership_fee"].initial = instance.enabled_for_membership_fee
            self.fields["merchant_recurring_enabled"].initial = instance.merchant_recurring_enabled
            self.fields["refunds_enabled"].initial = instance.refunds_enabled
            self.fields["admin_notes"].initial = instance.admin_notes or ""

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("is_sandbox") and not cleaned.get("confirm_production"):
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
        return cleaned

    def save(self):
        from django.utils import timezone

        instance = self.instance
        instance.api_app_key = (self.cleaned_data.get("api_app_key") or "").strip()
        instance.api_username = (self.cleaned_data.get("api_username") or "").strip()
        if self.cleaned_data.get("clear_secrets"):
            instance.clear_api_secrets()
        else:
            if self.cleaned_data.get("api_secret"):
                instance.set_api_secret(self.cleaned_data["api_secret"])
            if self.cleaned_data.get("api_password"):
                instance.set_api_password(self.cleaned_data["api_password"])
        is_sandbox = bool(self.cleaned_data.get("is_sandbox"))
        instance.is_sandbox = is_sandbox
        instance.production_confirmed_at = None if is_sandbox else timezone.now()
        instance.is_enabled = bool(self.cleaned_data.get("is_enabled"))
        instance.enabled_for_donation = bool(self.cleaned_data.get("enabled_for_donation"))
        instance.enabled_for_membership_fee = bool(
            self.cleaned_data.get("enabled_for_membership_fee")
        )
        instance.merchant_recurring_enabled = bool(
            self.cleaned_data.get("merchant_recurring_enabled")
        )
        instance.refunds_enabled = bool(self.cleaned_data.get("refunds_enabled"))
        instance.admin_notes = self.cleaned_data.get("admin_notes") or ""
        instance.channel_kind = "ONLINE_DIRECT"
        instance.save()
        return instance
