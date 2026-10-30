from django.contrib import admin

from voting.models import (
    Election,
    ElectionAdminAction,
    ElectionBallot,
    ElectionBallotChoice,
    ElectionBallotPreference,
    ElectionCandidate,
    ElectionElectorate,
    ElectionOption,
    ElectionParticipation,
    ElectionQuestion,
    Vote,
    VoteRecord,
)


class _HiddenBallotAdmin(admin.ModelAdmin):
    """Ballots/preferences/choices must not be browsable or exportable."""

    def has_module_permission(self, request):
        return False

    def has_view_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    """Legacy — read-only historical records. Prefer Election."""

    list_display = ("title", "status", "start_date", "end_date", "created_by", "created_at")
    list_filter = ("status",)
    search_fields = ("title", "description", "created_by")
    readonly_fields = ("created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(VoteRecord)
class VoteRecordAdmin(_HiddenBallotAdmin):
    """Legacy — links voter to choice; keep out of product admin UI."""


class ElectionCandidateInline(admin.TabularInline):
    model = ElectionCandidate
    extra = 0
    raw_id_fields = ("member",)
    fields = ("name", "member", "is_founder_candidate", "display_order", "is_active")
    readonly_fields = ("is_founder_candidate",)


class ElectionQuestionInline(admin.StackedInline):
    model = ElectionQuestion
    extra = 0
    fields = ("question_en", "question_bn", "display_order", "is_active")


@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
    list_display = (
        "title_en",
        "election_type",
        "status",
        "eligibility_mode",
        "start_at",
        "end_at",
        "total_seats",
        "results_published",
        "electorate_frozen_at",
    )
    list_filter = ("election_type", "status", "eligibility_mode", "results_published")
    search_fields = ("title_en", "title_bn")
    raw_id_fields = ("created_by",)
    filter_horizontal = ("membership_types", "member_groups")
    inlines = [ElectionCandidateInline, ElectionQuestionInline]
    readonly_fields = (
        "created_at",
        "updated_at",
        "electorate_frozen_at",
        "candidates_locked",
        "results_published",
        "status",
        "end_at",
    )

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        from voting.models import ElectionType

        if obj and obj.election_type == ElectionType.ADVISORY_COUNCIL:
            for name in (
                "quorum_numerator",
                "quorum_denominator",
                "window_hours",
                "allow_self_vote",
                "auto_candidates",
                "eligibility_mode",
            ):
                if name not in fields:
                    fields.append(name)
        return fields

    def save_model(self, request, obj, form, change):
        from voting.models import ElectionType
        from voting.services import apply_advisory_council_constitution

        if obj.election_type == ElectionType.ADVISORY_COUNCIL:
            apply_advisory_council_constitution(obj)
        super().save_model(request, obj, form, change)


class ElectionOptionInline(admin.TabularInline):
    model = ElectionOption
    extra = 2
    fields = ("label_en", "label_bn", "display_order", "is_active")


@admin.register(ElectionQuestion)
class ElectionQuestionAdmin(admin.ModelAdmin):
    list_display = ("question_en", "election", "display_order", "is_active")
    search_fields = ("question_en", "question_bn", "election__title_en")
    raw_id_fields = ("election",)
    inlines = [ElectionOptionInline]


@admin.register(ElectionOption)
class ElectionOptionAdmin(admin.ModelAdmin):
    list_display = ("label_en", "question", "display_order", "is_active")
    search_fields = ("label_en", "label_bn")
    raw_id_fields = ("question",)


@admin.register(ElectionCandidate)
class ElectionCandidateAdmin(admin.ModelAdmin):
    list_display = ("name", "election", "is_founder_candidate", "display_order", "is_active")
    list_filter = ("is_founder_candidate", "is_active")
    search_fields = ("name", "election__title_en")
    raw_id_fields = ("election", "member")
    readonly_fields = ("is_founder_candidate",)


@admin.register(ElectionParticipation)
class ElectionParticipationAdmin(admin.ModelAdmin):
    """Who voted — no choices attached."""

    list_display = ("election", "user", "voted_at")
    search_fields = ("election__title_en", "user__email")
    raw_id_fields = ("election", "user")
    readonly_fields = ("voted_at", "election", "user")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ElectionElectorate)
class ElectionElectorateAdmin(admin.ModelAdmin):
    list_display = ("election", "member", "user", "frozen_at")
    search_fields = ("election__title_en", "user__email", "member__member_id")
    raw_id_fields = ("election", "member", "user")
    readonly_fields = ("election", "member", "user", "frozen_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ElectionAdminAction)
class ElectionAdminActionAdmin(admin.ModelAdmin):
    list_display = ("election", "action", "actor", "created_at")
    list_filter = ("action",)
    search_fields = ("election__title_en", "notes")
    raw_id_fields = ("election", "actor")
    readonly_fields = ("created_at",)


@admin.register(ElectionBallot)
class ElectionBallotAdmin(_HiddenBallotAdmin):
    pass


@admin.register(ElectionBallotPreference)
class ElectionBallotPreferenceAdmin(_HiddenBallotAdmin):
    pass


@admin.register(ElectionBallotChoice)
class ElectionBallotChoiceAdmin(_HiddenBallotAdmin):
    pass
