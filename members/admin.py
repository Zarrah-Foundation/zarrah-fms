from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _

from members.models import (
    ApplicationDocumentRequest,
    ApplicationEvent,
    ApplicationStatus,
    Member,
    MemberApplication,
    MemberGroup,
    MemberGroupMembership,
    MemberPositionAssignment,
    MembershipAutoPay,
    MembershipFee,
    MembershipFeePayment,
    OrganizationalPosition,
)
from members.transitions import TransitionError, transition_application


class MemberGroupMembershipInline(admin.TabularInline):
    model = MemberGroupMembership
    extra = 0
    raw_id_fields = ("member",)


@admin.register(MemberGroup)
class MemberGroupAdmin(admin.ModelAdmin):
    list_display = ("name_en", "slug", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name_en", "name_bn", "slug")
    prepopulated_fields = {"slug": ("name_en",)}
    inlines = [MemberGroupMembershipInline]


@admin.register(OrganizationalPosition)
class OrganizationalPositionAdmin(admin.ModelAdmin):
    list_display = (
        "name_en",
        "name_bn",
        "council_body",
        "is_active",
        "is_primary_eligible",
        "display_order",
    )
    list_filter = ("council_body", "is_active", "is_primary_eligible")
    search_fields = ("name_en", "name_bn")
    ordering = ("display_order", "name_en")


class MemberPositionAssignmentInline(admin.TabularInline):
    model = MemberPositionAssignment
    extra = 0
    raw_id_fields = ("position", "created_by")
    readonly_fields = ("created_at", "updated_at")


@admin.register(MemberPositionAssignment)
class MemberPositionAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "member",
        "position",
        "start_date",
        "end_date",
        "is_active",
        "is_primary",
    )
    list_filter = ("is_active", "is_primary", "position__council_body")
    search_fields = ("member__member_id", "member__first_name", "position__name_en")
    raw_id_fields = ("member", "position", "created_by")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ("member_id", "first_name", "last_name", "district", "status", "is_founder", "joined_at")
    list_filter = ("status", "is_founder", "district", "gender")
    search_fields = ("member_id", "first_name", "last_name", "user__email", "phone")
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("user", "approved_by")
    inlines = [MemberPositionAssignmentInline]


@admin.register(MemberApplication)
class MemberApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "reference_code",
        "email",
        "phone",
        "present_district",
        "status",
        "created_at",
    )
    list_filter = ("status", "gender", "identity_type", "is_expat")
    search_fields = (
        "full_name",
        "bangla_name",
        "english_name",
        "email",
        "phone",
        "identity_number",
        "reference_code",
    )
    readonly_fields = (
        "reference_code",
        "created_at",
        "updated_at",
        "reviewed_by",
        "reviewed_at",
        "status_token",
        "status_token_expiry",
    )
    actions = ["approve_applications", "reject_applications", "mark_under_review"]

    @admin.action(description=_("Approve selected applications"))
    def approve_applications(self, request, queryset):
        approved = 0
        for application in queryset.exclude(status=ApplicationStatus.APPROVED):
            try:
                transition_application(
                    application, ApplicationStatus.APPROVED, request.user
                )
                approved += 1
            except (TransitionError, ValueError) as exc:
                self.message_user(request, str(exc), messages.ERROR)
        self.message_user(request, _("%(count)d application(s) approved.") % {"count": approved})

    @admin.action(description=_("Reject selected applications"))
    def reject_applications(self, request, queryset):
        rejected = 0
        for application in queryset.exclude(status=ApplicationStatus.APPROVED):
            try:
                transition_application(
                    application,
                    ApplicationStatus.REJECTED,
                    request.user,
                    reason="Rejected via admin.",
                )
                rejected += 1
            except (TransitionError, ValueError) as exc:
                self.message_user(request, str(exc), messages.ERROR)
        self.message_user(request, _("%(count)d application(s) rejected.") % {"count": rejected})

    @admin.action(description=_("Mark selected as under review"))
    def mark_under_review(self, request, queryset):
        updated = 0
        for application in queryset:
            try:
                transition_application(
                    application, ApplicationStatus.UNDER_REVIEW, request.user
                )
                updated += 1
            except (TransitionError, ValueError):
                continue
        self.message_user(request, _("%(count)d application(s) updated.") % {"count": updated})


@admin.register(ApplicationDocumentRequest)
class ApplicationDocumentRequestAdmin(admin.ModelAdmin):
    list_display = ("document_label", "application", "is_satisfied", "created_at")
    list_filter = ("is_satisfied",)
    search_fields = ("document_label", "application__reference_code", "application__email")
    raw_id_fields = ("application", "created_by")


@admin.register(ApplicationEvent)
class ApplicationEventAdmin(admin.ModelAdmin):
    list_display = ("action", "application", "actor", "created_at")
    list_filter = ("action",)
    search_fields = ("application__reference_code", "message")
    readonly_fields = ("application", "actor", "action", "message", "metadata", "created_at")


@admin.register(MembershipFee)
class MembershipFeeAdmin(admin.ModelAdmin):
    list_display = ("member", "year", "month", "amount", "status", "payment_method", "paid_at")
    list_filter = ("year", "month", "status", "payment_method")
    search_fields = ("member__member_id", "transaction_id")
    readonly_fields = (
        "member",
        "year",
        "month",
        "amount",
        "status",
        "payment_method",
        "paid_at",
        "transaction_id",
        "source",
        "fee_payment",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return False


@admin.register(MembershipFeePayment)
class MembershipFeePaymentAdmin(admin.ModelAdmin):
    list_display = ("member", "amount", "status", "payment_method", "source", "created_at")
    list_filter = ("status", "payment_method", "source")
    search_fields = ("member__member_id", "transaction__tran_id")
    readonly_fields = (
        "member",
        "transaction",
        "amount",
        "status",
        "payment_method",
        "source",
        "months",
        "notes",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return False


@admin.action(description=_("Deactivate auto-pay (service layer)"))
def deactivate_autopay_action(modeladmin, request, queryset):
    from members.billing import deactivate_autopay

    count = 0
    for profile in queryset.select_related("member"):
        deactivate_autopay(
            profile.member, actor=request.user, reason="Deactivated via Django admin"
        )
        count += 1
    modeladmin.message_user(
        request, _("%(count)d auto-pay profile(s) deactivated.") % {"count": count}
    )


@admin.register(MembershipAutoPay)
class MembershipAutoPayAdmin(admin.ModelAdmin):
    list_display = ("member", "is_enabled", "mode", "gateway", "next_charge_on")
    list_filter = ("is_enabled", "mode")
    actions = (deactivate_autopay_action,)
    readonly_fields = (
        "member",
        "is_enabled",
        "mode",
        "gateway",
        "next_charge_on",
        "payment_token",
        "gateway_subscription_ref",
        "deactivated_at",
        "deactivated_by",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        # View-only change form; enabling autopay is impossible here.
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return False

    def save_model(self, request, obj, form, change):
        # Belt-and-suspenders: never persist an admin enable.
        if change and obj.pk:
            original = MembershipAutoPay.objects.filter(pk=obj.pk).first()
            if original:
                obj.is_enabled = original.is_enabled
                obj.mode = original.mode
                if not original.is_enabled:
                    obj.is_enabled = False
        else:
            obj.is_enabled = False
        super().save_model(request, obj, form, change)
