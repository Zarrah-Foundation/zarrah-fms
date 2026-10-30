"""Forms for elections (admin dashboard + member ballot)."""

from django import forms
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _

from dashboard.forms import StyledModelForm, style_fields
from members.models import MemberGroup, MembershipType
from voting.models import (
    Election,
    ElectionCandidate,
    ElectionOption,
    ElectionQuestion,
    ElectionType,
    EligibilityMode,
)


class ElectionForm(StyledModelForm):
    class Meta:
        model = Election
        fields = [
            "title_bn",
            "title_en",
            "description_bn",
            "description_en",
            "election_type",
            "start_at",
            "window_hours",
            "total_seats",
            "quorum_numerator",
            "quorum_denominator",
            "allow_self_vote",
            "auto_candidates",
            "eligibility_mode",
            "membership_types",
            "member_groups",
            "allow_multiple_selections",
            "max_selections",
        ]
        widgets = {
            "start_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "description_bn": forms.Textarea(attrs={"rows": 3}),
            "description_en": forms.Textarea(attrs={"rows": 3}),
            "membership_types": forms.SelectMultiple(attrs={"class": "form-select"}),
            "member_groups": forms.SelectMultiple(attrs={"class": "form-select"}),
        }
        help_texts = {
            "window_hours": _(
                "Advisory Council window is fixed at 48 hours on open. Extensions require an explicit Extend action."
            ),
            "quorum_numerator": _(
                "Advisory Council quorum is fixed at 2 (of 3) and cannot be weakened."
            ),
            "quorum_denominator": _(
                "Advisory Council quorum denominator is fixed at 3."
            ),
            "auto_candidates": _(
                "Advisory Council: every eligible approved member becomes a candidate automatically."
            ),
            "allow_self_vote": _("Keep unchecked for Advisory Council (self-voting forbidden)."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["membership_types"].queryset = MembershipType.objects.filter(
            is_active=True
        )
        self.fields["member_groups"].queryset = MemberGroup.objects.filter(is_active=True)
        self.fields["membership_types"].required = False
        self.fields["member_groups"].required = False
        # Status / results_published / end_at are service-managed — not on form.
        is_ac = (
            self.instance
            and self.instance.pk
            and self.instance.election_type == ElectionType.ADVISORY_COUNCIL
        )
        if is_ac:
            for name in (
                "quorum_numerator",
                "quorum_denominator",
                "window_hours",
                "allow_self_vote",
                "auto_candidates",
                "eligibility_mode",
            ):
                if name in self.fields:
                    self.fields[name].disabled = True
            self.fields["quorum_numerator"].help_text = _(
                "Advisory Council quorum is fixed at 2/3 and cannot be changed."
            )
            self.fields["window_hours"].help_text = _(
                "Advisory Council voting window is fixed at 48 hours."
            )
        if self.instance and self.instance.pk and self.instance.configuration_locked():
            for name in (
                "election_type",
                "eligibility_mode",
                "membership_types",
                "member_groups",
                "total_seats",
                "auto_candidates",
                "quorum_numerator",
                "quorum_denominator",
                "window_hours",
                "allow_self_vote",
            ):
                if name in self.fields:
                    self.fields[name].disabled = True

    def clean(self):
        cleaned = super().clean()
        etype = cleaned.get("election_type")
        mode = cleaned.get("eligibility_mode")
        if etype == ElectionType.ADVISORY_COUNCIL:
            # Constitutional hard rules — posted 1/2 (or other) values are ignored.
            cleaned["auto_candidates"] = True
            cleaned["allow_self_vote"] = False
            cleaned["window_hours"] = 48
            cleaned["eligibility_mode"] = EligibilityMode.ALL_APPROVED
            cleaned["quorum_numerator"] = 2
            cleaned["quorum_denominator"] = 3
            mode = EligibilityMode.ALL_APPROVED
        if mode == EligibilityMode.BY_MEMBERSHIP_TYPES and not cleaned.get(
            "membership_types"
        ):
            self.add_error(
                "membership_types",
                _("Select at least one membership type for this eligibility mode."),
            )
        if mode == EligibilityMode.BY_GROUPS and not cleaned.get("member_groups"):
            self.add_error(
                "member_groups",
                _("Select at least one member group for this eligibility mode."),
            )
        return cleaned


class ElectionCandidateForm(StyledModelForm):
    class Meta:
        model = ElectionCandidate
        fields = ["member", "name", "display_order", "is_active"]


ElectionCandidateFormSet = inlineformset_factory(
    Election,
    ElectionCandidate,
    form=ElectionCandidateForm,
    extra=0,
    can_delete=True,
)


class ElectionQuestionForm(StyledModelForm):
    class Meta:
        model = ElectionQuestion
        fields = ["question_bn", "question_en", "display_order", "is_active"]


class ElectionOptionForm(StyledModelForm):
    class Meta:
        model = ElectionOption
        fields = ["label_bn", "label_en", "display_order", "is_active"]


ElectionQuestionFormSet = inlineformset_factory(
    Election,
    ElectionQuestion,
    form=ElectionQuestionForm,
    extra=1,
    can_delete=True,
)

ElectionOptionFormSet = inlineformset_factory(
    ElectionQuestion,
    ElectionOption,
    form=ElectionOptionForm,
    extra=2,
    can_delete=True,
)


class RankedBallotForm(forms.Form):
    """Member ranked ballot — ranks submitted as ordered candidate UUID list."""

    def __init__(self, *args, candidates=None, required_count=1, **kwargs):
        super().__init__(*args, **kwargs)
        self.candidates = list(candidates or [])
        self.required_count = required_count
        choices = [(str(c.pk), c.name) for c in self.candidates]
        for i in range(1, required_count + 1):
            self.fields[f"rank_{i}"] = forms.ChoiceField(
                label=_("Preference %(n)s") % {"n": i},
                choices=[("", _("— Select —"))] + choices,
                required=True,
            )
        style_fields(self)

    def clean(self):
        cleaned = super().clean()
        selected = []
        for i in range(1, self.required_count + 1):
            value = cleaned.get(f"rank_{i}")
            if value:
                selected.append(value)
        if len(selected) != self.required_count:
            raise forms.ValidationError(
                _("You must rank exactly %(count)s candidates.")
                % {"count": self.required_count}
            )
        if len(set(selected)) != len(selected):
            raise forms.ValidationError(_("Each candidate may only appear once."))
        cleaned["ordered_candidate_ids"] = selected
        return cleaned


class ChoiceBallotForm(forms.Form):
    """YES_NO / MULTI_CHOICE ballot."""

    def __init__(self, *args, options=None, multiple=False, max_selections=1, **kwargs):
        super().__init__(*args, **kwargs)
        self.options = list(options or [])
        self.multiple = multiple
        self.max_selections = max_selections
        choices = [(str(o.pk), o.localized_label()) for o in self.options]
        if multiple:
            self.fields["options"] = forms.MultipleChoiceField(
                label=_("Select options"),
                choices=choices,
                widget=forms.CheckboxSelectMultiple,
                required=True,
            )
        else:
            self.fields["options"] = forms.ChoiceField(
                label=_("Select an option"),
                choices=[("", _("— Select —"))] + choices,
                required=True,
            )
        style_fields(self)

    def clean(self):
        cleaned = super().clean()
        raw = cleaned.get("options")
        if self.multiple:
            selected = list(raw or [])
        else:
            selected = [raw] if raw else []
        if not selected:
            raise forms.ValidationError(_("Please select an option."))
        if len(selected) > self.max_selections:
            raise forms.ValidationError(
                _("You may select at most %(n)s option(s).") % {"n": self.max_selections}
            )
        cleaned["option_ids"] = selected
        return cleaned
