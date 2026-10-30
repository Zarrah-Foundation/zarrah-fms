"""Dashboard forms for governance meetings and resolutions."""

from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

from core.html_sanitize import sanitize_html
from core.validators import ImageFileValidator, MaxFileSizeValidator
from dashboard.forms import StyledModelForm, style_fields
from governance.models import (
    GuestStatus,
    Meeting,
    MeetingAgendaItem,
    MeetingGuest,
    MeetingProceeding,
    MeetingType,
    ParticipantStatus,
    Resolution,
)
from members.models import Member, MemberGroup, MemberStatus


class MeetingTypeForm(StyledModelForm):
    class Meta:
        model = MeetingType
        fields = [
            "slug",
            "name_en",
            "name_bn",
            "description_en",
            "description_bn",
            "quorum_numerator",
            "quorum_denominator",
            "eligibility_mode",
            "eligibility_groups",
            "reminder_hours_before",
            "reminder_enabled",
            "display_order",
            "is_active",
        ]
        widgets = {
            "eligibility_groups": forms.SelectMultiple(attrs={"size": 8}),
            "description_en": forms.Textarea(attrs={"rows": 3}),
            "description_bn": forms.Textarea(attrs={"rows": 3}),
        }


class MeetingForm(StyledModelForm):
    class Meta:
        model = Meeting
        fields = [
            "meeting_type",
            "title_bn",
            "title_en",
            "description_bn",
            "description_en",
            "mode",
            "starts_at",
            "ends_at",
            "timezone",
            "venue_name",
            "venue_address",
            "room_details",
            "online_platform",
            "meeting_url",
            "meeting_id_code",
            "meeting_password",
            "joining_instructions",
            "reminder_enabled",
            "reminder_hours_before",
        ]
        widgets = {
            "starts_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
            "ends_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
            "description_bn": forms.Textarea(attrs={"rows": 3}),
            "description_en": forms.Textarea(attrs={"rows": 3}),
            "venue_address": forms.Textarea(attrs={"rows": 2}),
            "joining_instructions": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["meeting_type"].queryset = MeetingType.objects.filter(
            is_active=True
        ).order_by("display_order", "name_en")
        self.fields["starts_at"].input_formats = [
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
        ]
        self.fields["ends_at"].input_formats = self.fields["starts_at"].input_formats
        self.fields["ends_at"].required = False
        self.fields["reminder_hours_before"].required = False


class AddParticipantMemberForm(forms.Form):
    member = forms.ModelChoiceField(
        queryset=Member.objects.none(),
        label=_("Approved member"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["member"].queryset = Member.objects.filter(
            status=MemberStatus.APPROVED
        ).order_by("member_id")
        style_fields(self)


class AddParticipantGroupForm(forms.Form):
    group = forms.ModelChoiceField(
        queryset=MemberGroup.objects.all().order_by("name_en"),
        label=_("Member group"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)


class GuestForm(StyledModelForm):
    class Meta:
        model = MeetingGuest
        fields = [
            "full_name",
            "organization",
            "designation",
            "email",
            "phone",
            "notes",
            "status",
        ]
        widgets = {"notes": forms.Textarea(attrs={"rows": 2})}


class AgendaItemForm(StyledModelForm):
    class Meta:
        model = MeetingAgendaItem
        fields = [
            "title_bn",
            "title_en",
            "description_bn",
            "description_en",
            "presenter_name",
            "supporting_document",
        ]
        widgets = {
            "description_bn": forms.Textarea(attrs={"rows": 2}),
            "description_en": forms.Textarea(attrs={"rows": 2}),
        }


class ProceedingsForm(forms.ModelForm):
    class Meta:
        model = MeetingProceeding
        fields = ["content_bn", "content_en"]
        labels = {
            "content_bn": _("Proceedings (Bangla)"),
            "content_en": _("Proceedings (English, optional)"),
        }
        widgets = {
            "content_bn": forms.Textarea(
                attrs={"rows": 10, "class": "form-textarea js-richtext"}
            ),
            "content_en": forms.Textarea(
                attrs={"rows": 8, "class": "form-textarea js-richtext"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)
        for name in ("content_bn", "content_en"):
            self.fields[name].widget.attrs["class"] = (
                self.fields[name].widget.attrs.get("class", "") + " js-richtext"
            ).strip()

    def clean_content_bn(self):
        return sanitize_html(self.cleaned_data.get("content_bn") or "")

    def clean_content_en(self):
        return sanitize_html(self.cleaned_data.get("content_en") or "")


class ResolutionForm(forms.Form):
    title_bn = forms.CharField(max_length=300, label=_("Title (Bangla)"))
    title_en = forms.CharField(
        max_length=300, required=False, label=_("Title (English, optional)")
    )
    content_bn = forms.CharField(
        label=_("Resolution body (Bangla)"),
        widget=forms.Textarea(attrs={"rows": 12, "class": "form-textarea js-richtext"}),
    )
    content_en = forms.CharField(
        required=False,
        label=_("Resolution body (English, optional)"),
        widget=forms.Textarea(attrs={"rows": 10, "class": "form-textarea js-richtext"}),
    )
    decision_bn = forms.CharField(
        required=False,
        label=_("Decision (Bangla)"),
        widget=forms.Textarea(attrs={"rows": 6, "class": "form-textarea js-richtext"}),
    )
    decision_en = forms.CharField(
        required=False,
        label=_("Decision (English, optional)"),
        widget=forms.Textarea(attrs={"rows": 6, "class": "form-textarea js-richtext"}),
    )
    agenda_item = forms.ModelChoiceField(
        queryset=MeetingAgendaItem.objects.none(),
        required=False,
        label=_("Agenda item (optional)"),
    )

    def __init__(self, *args, meeting=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.meeting = meeting
        if meeting is not None:
            self.fields["agenda_item"].queryset = meeting.agenda_items.all()
        style_fields(self)
        for name in ("content_bn", "content_en", "decision_bn", "decision_en"):
            cls = self.fields[name].widget.attrs.get("class", "")
            if "js-richtext" not in cls:
                self.fields[name].widget.attrs["class"] = f"{cls} js-richtext".strip()

    def clean_content_bn(self):
        return sanitize_html(self.cleaned_data.get("content_bn") or "")

    def clean_content_en(self):
        return sanitize_html(self.cleaned_data.get("content_en") or "")

    def clean_decision_bn(self):
        return sanitize_html(self.cleaned_data.get("decision_bn") or "")

    def clean_decision_en(self):
        return sanitize_html(self.cleaned_data.get("decision_en") or "")


class SignerSelectForm(forms.Form):
    members = forms.MultipleChoiceField(
        required=True,
        widget=forms.CheckboxSelectMultiple,
        label=_("Present members to sign"),
    )

    def __init__(self, *args, choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["members"].choices = choices or []
        style_fields(self)


class PublicShareAdminForm(forms.Form):
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False),
        label=_("Password (optional)"),
        help_text=_("Leave blank for no password. Existing password is never shown."),
    )
    clear_password = forms.BooleanField(
        required=False,
        label=_("Remove password protection"),
    )
    expires_at = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
        ),
        input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"],
        label=_("Expires at (optional)"),
    )
    show_signer_details = forms.BooleanField(
        required=False,
        initial=True,
        label=_("Show signatory names publicly"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)


class NewVersionForm(forms.Form):
    reason = forms.CharField(
        max_length=300,
        label=_("Reason for new version"),
        widget=forms.TextInput(),
    )
    content_bn = forms.CharField(
        required=False,
        label=_("Updated body (Bangla, optional)"),
        widget=forms.Textarea(attrs={"rows": 8, "class": "form-textarea js-richtext"}),
    )
    content_en = forms.CharField(
        required=False,
        label=_("Updated body (English, optional)"),
        widget=forms.Textarea(attrs={"rows": 6, "class": "form-textarea js-richtext"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)

    def clean_content_bn(self):
        return sanitize_html(self.cleaned_data.get("content_bn") or "")

    def clean_content_en(self):
        return sanitize_html(self.cleaned_data.get("content_en") or "")


class MeetingRsvpForm(forms.Form):
    response = forms.ChoiceField(
        choices=[
            (ParticipantStatus.ACCEPTED, _("Accept")),
            (ParticipantStatus.DECLINED, _("Decline")),
        ],
        widget=forms.RadioSelect,
        label=_("Your response"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)


class ResolutionSignForm(forms.Form):
    confirmation = forms.BooleanField(
        required=True,
        label=_(
            "I have reviewed this resolution and confirm that I agree with and "
            "approve the decisions recorded herein."
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)


class PublicSharePasswordForm(forms.Form):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
        label=_("Password"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)


class MemberSignatureForm(forms.Form):
    """Upload or replace the member's digital signature image (profile only)."""

    signature_image = forms.ImageField(
        required=True,
        label=_("Signature image"),
        help_text=_(
            "PNG or JPEG, max 2 MB. This signature is used when you approve "
            "and sign official foundation resolutions."
        ),
        validators=[MaxFileSizeValidator(2), ImageFileValidator()],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)
