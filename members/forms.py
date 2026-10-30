import re
from datetime import date

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from core.bd_geo import BD_DISTRICTS, BD_DIVISIONS
from core.countries import COUNTRIES
from core.education_data import EDUCATION_CLASSES
from members.models import EducationStatus, MemberApplication, MembershipType

CLASS_BEARING_STAGES = set(EDUCATION_CLASSES.keys())

_DIVISION_CHOICES = [("", "---------")] + [(d, d) for d in BD_DIVISIONS]
_DISTRICT_CHOICES = [("", "---------")] + [(d, d) for d in BD_DISTRICTS]
# Upazila/Union options are populated client-side (bd-address.js) from the
# local Bangladesh geo dataset once a parent Division/District is chosen —
# there are ~494 upazilas and ~4,540 unions, far too many to hard-code here.
_EMPTY_CASCADE_CHOICES = [("", "---------")]
# Education stage/marhala/level and class options are populated client-side
# (education-selector.js) from core/education_data.py, keyed by education_type.
_EMPTY_EDUCATION_CHOICES = [("", "---------")]

BANGLA_NAME_RE = re.compile(r"^[\u0980-\u09FF.\s]+$")
ENGLISH_NAME_RE = re.compile(r"^[A-Za-z.\s]+$")
BD_PHONE_RE = re.compile(r"^(?:\+?880|0)1[3-9]\d{8}$")
MIN_AGE = 18


class MemberApplicationForm(forms.ModelForm):
    """Multi-section membership application form.

    ``SECTIONS`` describes the grouping used by templates/members/apply.html
    to render the form as clearly separated, professional sections instead
    of one long field dump.
    """

    SECTIONS = [
        (
            "personal",
            _("Personal Information"),
            "bi-person-vcard",
            [
                "bangla_name", "english_name", "father_name", "mother_name",
                "gender", "date_of_birth", "blood_group", "marital_status",
                "religion", "photo", "email", "phone",
                "emergency_name", "emergency_phone", "emergency_relation",
            ],
        ),
        (
            "identity",
            _("Identity"),
            "bi-person-badge",
            ["identity_type", "identity_number", "identity_document"],
        ),
        (
            "address",
            _("Address"),
            "bi-geo-alt",
            [
                "present_division", "present_district", "present_upazila", "present_union",
                "present_address", "permanent_same_as_present",
                "permanent_division", "permanent_district", "permanent_upazila",
                "permanent_union", "permanent_address",
            ],
        ),
        (
            "expat",
            _("Expatriates"),
            "bi-airplane",
            [
                "is_expat", "country", "expat_state_province", "expat_city",
                "expat_postal_code", "full_foreign_address", "passport_number",
            ],
        ),
        (
            "education",
            _("Education"),
            "bi-mortarboard",
            [
                "education_type", "education_level", "education_class", "education_status",
                "education_institution", "education_passing_year", "education_result",
            ],
        ),
        (
            "occupation",
            _("Occupation"),
            "bi-briefcase",
            ["is_student", "occupation", "designation", "organization", "workplace_address"],
        ),
        (
            "additional",
            _("Additional Information"),
            "bi-award",
            ["facebook_url", "volunteer_experience", "cv"],
        ),
    ]

    class Meta:
        model = MemberApplication
        exclude = [
            "full_name",
            "education",
            "status",
            "reference_code",
            "admin_message",
            "review_note",
            "rejection_reason",
            "reviewed_by",
            "reviewed_at",
            "status_token",
            "status_token_expiry",
            "created_at",
            "updated_at",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date", "class": "form-input"}),
            "present_address": forms.Textarea(attrs={"rows": 3, "class": "form-input"}),
            "permanent_address": forms.Textarea(attrs={"rows": 3, "class": "form-input"}),
            "full_foreign_address": forms.Textarea(attrs={"rows": 3, "class": "form-input"}),
            "workplace_address": forms.Textarea(attrs={"rows": 3, "class": "form-input"}),
            "volunteer_experience": forms.Textarea(attrs={"rows": 3, "class": "form-input"}),
            "permanent_same_as_present": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "is_expat": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "is_student": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }

    country = forms.ChoiceField(
        choices=[("", "---------")] + [(c, c) for c in COUNTRIES],
        required=False,
        label=_("Country"),
    )
    present_division = forms.ChoiceField(choices=_DIVISION_CHOICES, required=False, label=_("Division"))
    present_district = forms.CharField(
        required=False, label=_("District"), widget=forms.Select(choices=_DISTRICT_CHOICES)
    )
    present_upazila = forms.CharField(
        required=False, label=_("Upazila"), widget=forms.Select(choices=_EMPTY_CASCADE_CHOICES)
    )
    # Union is the smallest administrative tier (~4,540 nationwide). It is
    # kept as a plain text field rather than a fully-populated select — see
    # README "Known limitations" for why and how to upgrade it later.
    present_union = forms.CharField(
        required=False,
        label=_("Union / Ward"),
        widget=forms.TextInput(),
        help_text=_("Type your Union Parishad or Ward name."),
    )
    permanent_division = forms.ChoiceField(choices=_DIVISION_CHOICES, required=False, label=_("Division"))
    permanent_district = forms.CharField(
        required=False, label=_("District"), widget=forms.Select(choices=_DISTRICT_CHOICES)
    )
    permanent_upazila = forms.CharField(
        required=False, label=_("Upazila"), widget=forms.Select(choices=_EMPTY_CASCADE_CHOICES)
    )
    permanent_union = forms.CharField(
        required=False,
        label=_("Union / Ward"),
        widget=forms.TextInput(),
        help_text=_("Type your Union Parishad or Ward name."),
    )
    education_level = forms.CharField(
        required=False, label=_("Stage / Marhala / Level"), widget=forms.Select(choices=_EMPTY_EDUCATION_CHOICES)
    )
    education_class = forms.CharField(
        required=False, label=_("Class"), widget=forms.Select(choices=_EMPTY_EDUCATION_CHOICES)
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-checkbox")
            elif "class" not in field.widget.attrs:
                field.widget.attrs.setdefault("class", "form-input")
            field.widget.attrs.setdefault("data-field", name)
            if field.required:
                field.widget.attrs.setdefault("aria-required", "true")
        self.fields["date_of_birth"].widget.attrs["max"] = date.today().isoformat()
        self.fields["education_passing_year"].widget.attrs.update(
            {"min": 1970, "max": date.today().year}
        )
        from core.templatetags.i18n_extras import apply_zf_form_labels

        apply_zf_form_labels(
            self,
            {
                "bangla_name": "Name (in Bangla)",
                "english_name": "Name (in English)",
                "father_name": "Father's Name",
                "mother_name": "Mother's Name",
                "gender": "Gender",
                "date_of_birth": "Date of Birth",
                "blood_group": "Blood Group",
                "marital_status": "Marital Status",
                "religion": "Religion",
                "photo": "Photo",
                "email": "Email Address",
                "phone": "Mobile Number",
                "emergency_name": "Emergency Contact Name",
                "emergency_phone": "Emergency Contact Number",
                "emergency_relation": "Relation",
                "identity_type": "Identity Type",
                "identity_number": "ID Number",
                "identity_document": "Identity Document",
                "present_division": "Division",
                "present_district": "District",
                "present_upazila": "Upazila",
                "present_union": "Union / Ward",
                "present_address": "Present Address (Details)",
                "permanent_same_as_present": "Permanent address same as present address",
                "permanent_division": "Division",
                "permanent_district": "District",
                "permanent_upazila": "Upazila",
                "permanent_union": "Union / Ward",
                "permanent_address": "Permanent Address (Details)",
                "is_expat": "I am an expatriate",
                "country": "Country",
                "expat_state_province": "State / Province",
                "expat_city": "City",
                "expat_postal_code": "Postal Code",
                "full_foreign_address": "Full Foreign Address",
                "passport_number": "Passport Number",
                "education_type": "Education Type",
                "education_level": "Stage / Marhala / Level",
                "education_class": "Class",
                "education_status": "Current Status",
                "education_institution": "Institution Name",
                "education_passing_year": "Passing Year",
                "education_result": "Result",
                "is_student": "I am a student",
                "occupation": "Occupation",
                "designation": "Designation",
                "organization": "Organization Name",
                "workplace_address": "Workplace Address",
                "facebook_url": "Facebook Profile Link",
                "volunteer_experience": "Volunteer Experience",
                "cv": "CV / Resume",
            },
        )

    def sections(self):
        """Yield (key, label, icon, [bound fields]) for template rendering."""
        from core.templatetags.i18n_extras import zf_text

        for key, label, icon, field_names in self.SECTIONS:
            yield key, zf_text(str(label)), icon, [self[name] for name in field_names if name in self.fields]

    # ---- field-level validation ----

    def clean_bangla_name(self):
        value = self.cleaned_data["bangla_name"].strip()
        if not BANGLA_NAME_RE.match(value):
            raise ValidationError(_("Bangla name must contain only Bangla characters."))
        return value

    def clean_english_name(self):
        value = self.cleaned_data["english_name"].strip()
        if not ENGLISH_NAME_RE.match(value):
            raise ValidationError(_("English name must contain only English characters."))
        return value

    def clean_phone(self):
        value = self.cleaned_data["phone"].strip().replace(" ", "")
        if not BD_PHONE_RE.match(value):
            raise ValidationError(_("Enter a valid Bangladeshi phone number (e.g. 01XXXXXXXXX)."))
        return value

    def clean_emergency_phone(self):
        value = (self.cleaned_data.get("emergency_phone") or "").strip().replace(" ", "")
        if value and not BD_PHONE_RE.match(value):
            raise ValidationError(_("Enter a valid Bangladeshi phone number (e.g. 01XXXXXXXXX)."))
        return value

    def clean_date_of_birth(self):
        dob = self.cleaned_data["date_of_birth"]
        if dob:
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            if age < MIN_AGE:
                from core.templatetags.i18n_extras import zf_text

                raise ValidationError(zf_text("You must be at least 18 years old to apply."))
            if dob > today:
                raise ValidationError(_("Date of birth cannot be in the future."))
        return dob

    # Note: photo / identity_document / cv are validated by the
    # MaxFileSizeValidator / FileTypeValidator / ImageFileValidator attached
    # directly to the model fields (core/validators.py) — ModelForm runs
    # those automatically via instance.full_clean(), so no manual
    # clean_<field>() is needed here.

    # ---- cross-field validation ----

    def clean(self):
        cleaned = super().clean()
        is_expat = cleaned.get("is_expat")
        permanent_same = cleaned.get("permanent_same_as_present")
        is_student = cleaned.get("is_student")

        if is_expat:
            for field in ("country", "full_foreign_address", "passport_number"):
                if not cleaned.get(field):
                    self.add_error(field, _("This field is required for expatriate applicants."))
        else:
            for field in ("present_division", "present_district", "present_upazila", "present_union", "present_address"):
                if not cleaned.get(field):
                    self.add_error(field, _("This field is required."))
            if not permanent_same:
                for field in ("permanent_division", "permanent_district", "permanent_upazila", "permanent_union", "permanent_address"):
                    if not cleaned.get(field):
                        self.add_error(field, _("This field is required unless the permanent address is the same as present address."))

        if is_student:
            cleaned["organization"] = ""
            cleaned["workplace_address"] = ""
            cleaned["designation"] = ""
        elif not cleaned.get("occupation"):
            self.add_error("occupation", _("This field is required."))

        if not cleaned.get("education_type"):
            self.add_error("education_type", _("This field is required."))
        if not cleaned.get("education_level"):
            self.add_error("education_level", _("This field is required."))
        elif cleaned.get("education_type") == "GENERAL" and cleaned.get("education_level") in CLASS_BEARING_STAGES:
            if not cleaned.get("education_class"):
                self.add_error("education_class", _("This field is required."))
        if not cleaned.get("education_status"):
            self.add_error("education_status", _("This field is required."))

        education_status = cleaned.get("education_status")
        if education_status == EducationStatus.COMPLETED:
            for field in ("education_institution", "education_passing_year", "education_result"):
                if not cleaned.get(field):
                    self.add_error(field, _("This field is required for a completed education level."))
        elif education_status == EducationStatus.CURRENT and not cleaned.get("education_institution"):
            self.add_error("education_institution", _("This field is required."))

        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.permanent_same_as_present:
            instance.permanent_division = instance.present_division
            instance.permanent_district = instance.present_district
            instance.permanent_upazila = instance.present_upazila
            instance.permanent_union = instance.present_union
            instance.permanent_address = instance.present_address
        if instance.is_student:
            instance.occupation = "Student"
        if commit:
            instance.save()
        return instance


class AdminMemberApplicationForm(MemberApplicationForm):
    """Public application fields plus admin-only membership type / auto-approve."""

    membership_type = forms.ModelChoiceField(
        queryset=MembershipType.objects.filter(is_active=True),
        required=False,
        label=_("Membership type"),
    )
    auto_approve = forms.BooleanField(
        required=False,
        initial=False,
        label=_("Approve immediately"),
        help_text=_(
            "Creates the member account now without the public email-verification registration flow."
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["membership_type"].widget.attrs.setdefault("class", "form-input")
        self.fields["auto_approve"].widget.attrs.setdefault("class", "form-checkbox")


class ApplicationStatusLookupForm(forms.Form):
    reference_code = forms.CharField(
        max_length=32,
        label=_("Application reference"),
        widget=forms.TextInput(attrs={"class": "form-input", "autocomplete": "off"}),
    )
    email = forms.EmailField(
        label=_("Email used on the application"),
        widget=forms.EmailInput(attrs={"class": "form-input", "autocomplete": "email"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from core.templatetags.i18n_extras import apply_zf_form_labels

        apply_zf_form_labels(
            self,
            {
                "reference_code": "Application reference",
                "email": "Email used on the application",
            },
        )


class MissingDocumentUploadForm(forms.Form):
    uploaded_file = forms.FileField(label=_("Upload document"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["uploaded_file"].widget.attrs.setdefault("class", "form-input")
        from core.templatetags.i18n_extras import apply_zf_form_labels

        apply_zf_form_labels(self, {"uploaded_file": "Upload document"})
