"""Public recurring donation form (server-authoritative amount/frequency/provider)."""

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from donations.models import DonationCategory
from donations.validators import parse_contact


class RecurringDonationForm(forms.Form):
    """Monthly SSLCommerz recurring donation — frequency/provider are server-fixed."""

    category = forms.ModelChoiceField(
        queryset=DonationCategory.objects.none(),
        empty_label=_("Select a category"),
        label=_("Donation Category"),
        widget=forms.Select(attrs={"class": "form-input"}),
    )
    amount = forms.FloatField(
        min_value=1,
        label=_("Monthly amount (BDT)"),
        widget=forms.NumberInput(
            attrs={
                "class": "form-input",
                "step": "1",
                "min": "1",
                "inputmode": "numeric",
            }
        ),
    )
    donor_name = forms.CharField(
        max_length=200,
        required=False,
        label=_("Name"),
        widget=forms.TextInput(
            attrs={"class": "form-input", "autocomplete": "name"}
        ),
    )
    contact = forms.CharField(
        max_length=200,
        label=_("Phone or Email"),
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "autocomplete": "email",
                "placeholder": _("01XXXXXXXXX or email@example.com"),
            }
        ),
        help_text=_("Required so we can send receipts and manage your subscription."),
    )
    message = forms.CharField(
        required=False,
        label=_("Message (optional)"),
        widget=forms.Textarea(attrs={"class": "form-input", "rows": 3}),
    )
    is_anonymous = forms.BooleanField(
        required=False,
        label=_("Anonymous Donation"),
        widget=forms.CheckboxInput(attrs={"class": "form-checkbox"}),
    )
    # Display-only; ignored if tampered — server forces MONTHLY + SSLCommerz.
    frequency = forms.CharField(
        required=False,
        initial="MONTHLY",
        widget=forms.HiddenInput(),
    )
    payment_provider = forms.CharField(
        required=False,
        initial="SSLCOMMERZ",
        widget=forms.HiddenInput(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        categories = DonationCategory.objects.filter(is_active=True).order_by(
            "display_order", "name_en"
        )
        self.fields["category"].queryset = categories
        if not self.is_bound and not self.initial.get("category"):
            default = categories.filter(is_default=True).first() or categories.first()
            if default:
                self.initial["category"] = default.pk
        from core.templatetags.i18n_extras import apply_zf_form_labels, zf_text

        apply_zf_form_labels(self)
        self.fields["category"].empty_label = zf_text("Select a category")

    def clean_contact(self):
        value = self.cleaned_data.get("contact", "")
        email, phone = parse_contact(value)
        self._contact_email = email
        self._contact_phone = phone
        if not email and not phone:
            raise ValidationError(_("Enter a valid email or Bangladeshi mobile number."))
        return value

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if amount is None or amount < 1:
            raise ValidationError(_("Amount must be at least ৳1."))
        if amount > 1_000_000:
            raise ValidationError(_("Amount exceeds the allowed maximum."))
        return amount

    def clean(self):
        cleaned = super().clean()
        # Reject client attempts to switch frequency/provider.
        freq = (cleaned.get("frequency") or "MONTHLY").upper()
        if freq and freq != "MONTHLY":
            raise ValidationError(_("Only monthly recurring donations are supported."))
        provider = (cleaned.get("payment_provider") or "SSLCOMMERZ").upper()
        if provider and provider != "SSLCOMMERZ":
            raise ValidationError(
                _("Recurring donations currently support SSLCommerz only.")
            )
        cleaned["frequency"] = "MONTHLY"
        cleaned["payment_provider"] = "SSLCOMMERZ"
        is_anonymous = cleaned.get("is_anonymous")
        if is_anonymous:
            cleaned["donor_name"] = "Anonymous"
        elif not (cleaned.get("donor_name") or "").strip():
            from core.templatetags.i18n_extras import zf_text

            self.add_error("donor_name", zf_text("Please enter your name."))
        return cleaned

    def build_subscription_kwargs(self):
        cleaned = self.cleaned_data
        return {
            "category": cleaned["category"],
            "amount": cleaned["amount"],
            "donor_name": cleaned["donor_name"],
            "donor_email": getattr(self, "_contact_email", None) or "",
            "donor_phone": getattr(self, "_contact_phone", None) or "",
            "message": (cleaned.get("message") or "").strip(),
            "is_anonymous": bool(cleaned.get("is_anonymous")),
        }
