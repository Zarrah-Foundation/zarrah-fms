from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from donations.models import DonationCategory
from donations.validators import parse_contact


class DonationForm(forms.Form):
    """Simplified public donation form (no address fields)."""

    category = forms.ModelChoiceField(
        queryset=DonationCategory.objects.none(),
        empty_label=_("Select a category"),
        label=_("Donation Category"),
        widget=forms.Select(attrs={"class": "form-input", "data-donation-category": "true"}),
    )
    amount = forms.FloatField(
        min_value=1,
        label=_("Donation Amount (BDT)"),
        widget=forms.NumberInput(
            attrs={
                "class": "form-input",
                "step": "1",
                "min": "1",
                "inputmode": "numeric",
                "data-donation-amount": "true",
            }
        ),
    )
    donor_name = forms.CharField(
        max_length=200,
        required=False,
        label=_("Name"),
        widget=forms.TextInput(
            attrs={"class": "form-input", "data-donation-name": "true", "autocomplete": "name"}
        ),
    )
    contact = forms.CharField(
        max_length=200,
        label=_("Phone or Email"),
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "data-donation-contact": "true",
                "autocomplete": "email",
                "placeholder": _("01XXXXXXXXX or email@example.com"),
            }
        ),
        help_text=_("Enter a Bangladeshi mobile number or a valid email address."),
    )
    on_behalf_of = forms.CharField(
        max_length=200,
        required=False,
        label=_("Donate on behalf of"),
        widget=forms.TextInput(attrs={"class": "form-input"}),
    )
    is_anonymous = forms.BooleanField(
        required=False,
        label=_("Anonymous Donation"),
        widget=forms.CheckboxInput(
            attrs={"class": "form-checkbox", "data-donation-anonymous": "true"}
        ),
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

        anon = self.data.get("is_anonymous") if self.is_bound else None
        if anon in (True, "on", "true", "True", "1"):
            self.fields["donor_name"].widget.attrs["readonly"] = True

    def clean_contact(self):
        value = self.cleaned_data.get("contact", "")
        email, phone = parse_contact(value)
        self._contact_email = email
        self._contact_phone = phone
        return value

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if amount is None or amount <= 0:
            from core.templatetags.i18n_extras import zf_text

            raise ValidationError(zf_text("Amount must be greater than zero."))
        return amount

    def clean(self):
        cleaned = super().clean()
        is_anonymous = cleaned.get("is_anonymous")
        if is_anonymous:
            cleaned["donor_name"] = "Anonymous"
        elif not (cleaned.get("donor_name") or "").strip():
            from core.templatetags.i18n_extras import zf_text

            self.add_error("donor_name", zf_text("Please enter your name."))
        return cleaned

    def build_donation_kwargs(self):
        """Map cleaned form data onto Donation field kwargs (no save)."""
        cleaned = self.cleaned_data
        return {
            "category": cleaned["category"],
            "amount": cleaned["amount"],
            "donor_name": cleaned["donor_name"],
            "donor_email": getattr(self, "_contact_email", None),
            "donor_phone": getattr(self, "_contact_phone", None),
            "on_behalf_of": (cleaned.get("on_behalf_of") or "").strip(),
            "is_anonymous": bool(cleaned.get("is_anonymous")),
        }
