"""Django admin registration for governance models."""

from django.contrib import admin

from governance.models import (
    Meeting,
    MeetingAgendaItem,
    MeetingEligibleMember,
    MeetingGuest,
    MeetingNotificationLog,
    MeetingParticipant,
    MeetingProceeding,
    MeetingType,
    Resolution,
    ResolutionPublicShare,
    ResolutionSignature,
    ResolutionSigner,
    ResolutionVersion,
    SequenceCounter,
)


@admin.register(MeetingType)
class MeetingTypeAdmin(admin.ModelAdmin):
    list_display = ("name_en", "slug", "quorum_numerator", "quorum_denominator", "is_active")
    list_filter = ("is_active", "eligibility_mode")
    search_fields = ("name_en", "name_bn", "slug")
    filter_horizontal = ("eligibility_groups",)


class MeetingParticipantInline(admin.TabularInline):
    model = MeetingParticipant
    extra = 0
    raw_id_fields = ("member",)


class MeetingGuestInline(admin.TabularInline):
    model = MeetingGuest
    extra = 0


class MeetingAgendaItemInline(admin.TabularInline):
    model = MeetingAgendaItem
    extra = 0


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ("reference_id", "title_bn", "meeting_type", "status", "starts_at")
    list_filter = ("status", "mode", "meeting_type")
    search_fields = ("reference_id", "title_bn", "title_en")
    readonly_fields = ("reference_id", "eligible_frozen_at", "participants_frozen_at")
    inlines = [MeetingParticipantInline, MeetingGuestInline, MeetingAgendaItemInline]


@admin.register(MeetingParticipant)
class MeetingParticipantAdmin(admin.ModelAdmin):
    list_display = ("meeting", "member", "status", "invited_at", "responded_at")
    list_filter = ("status",)
    raw_id_fields = ("meeting", "member")


@admin.register(MeetingGuest)
class MeetingGuestAdmin(admin.ModelAdmin):
    list_display = ("full_name", "meeting", "organization", "status")
    list_filter = ("status",)


@admin.register(MeetingAgendaItem)
class MeetingAgendaItemAdmin(admin.ModelAdmin):
    list_display = ("meeting", "number", "title_bn", "status")
    list_filter = ("status",)


@admin.register(MeetingProceeding)
class MeetingProceedingAdmin(admin.ModelAdmin):
    list_display = ("meeting", "updated_at", "updated_by")


@admin.register(MeetingEligibleMember)
class MeetingEligibleMemberAdmin(admin.ModelAdmin):
    list_display = ("meeting", "member", "frozen_at")
    raw_id_fields = ("meeting", "member")


class ResolutionSignerInline(admin.TabularInline):
    model = ResolutionSigner
    extra = 0
    raw_id_fields = ("member",)


class ResolutionVersionInline(admin.TabularInline):
    model = ResolutionVersion
    extra = 0
    readonly_fields = ("version_number", "is_frozen", "created_at")


@admin.register(Resolution)
class ResolutionAdmin(admin.ModelAdmin):
    list_display = ("resolution_id", "meeting", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("resolution_id", "title_bn", "title_en")
    readonly_fields = ("resolution_id", "finalized_at")
    inlines = [ResolutionVersionInline, ResolutionSignerInline]


@admin.register(ResolutionVersion)
class ResolutionVersionAdmin(admin.ModelAdmin):
    list_display = ("resolution", "version_number", "is_frozen", "created_at")
    list_filter = ("is_frozen",)


@admin.register(ResolutionSigner)
class ResolutionSignerAdmin(admin.ModelAdmin):
    list_display = ("resolution", "member", "signed_at", "is_required")
    raw_id_fields = ("resolution", "member", "version")


@admin.register(ResolutionSignature)
class ResolutionSignatureAdmin(admin.ModelAdmin):
    list_display = ("member", "version", "signed_at", "signer_name")
    readonly_fields = (
        "signer",
        "version",
        "member",
        "signer_name",
        "signer_designation",
        "member_id_snapshot",
        "signature_image",
        "signed_at",
        "ip_address",
        "user_agent",
        "confirmation_text",
        "created_at",
    )


@admin.register(ResolutionPublicShare)
class ResolutionPublicShareAdmin(admin.ModelAdmin):
    list_display = ("resolution", "is_enabled", "expires_at", "revoked_at")
    list_filter = ("is_enabled",)
    readonly_fields = ("token", "password_hash")


@admin.register(MeetingNotificationLog)
class MeetingNotificationLogAdmin(admin.ModelAdmin):
    list_display = ("notification_type", "channel", "status", "sent_at", "created_at")
    list_filter = ("notification_type", "channel", "status")
    search_fields = ("idempotency_key", "recipient_address")


@admin.register(SequenceCounter)
class SequenceCounterAdmin(admin.ModelAdmin):
    list_display = ("key", "year", "month", "last_value", "updated_at")
    list_filter = ("key",)
