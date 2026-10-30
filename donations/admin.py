import csv
import io
from datetime import datetime

from django.contrib import admin, messages
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _

from core.choices import DonationStatus, PaymentMethod
from donations.models import (
    Donation,
    DonationCategory,
    DonationQuickAmount,
    DonationRecurringCharge,
    DonationSubscription,
    GatewayWebhookEvent,
    Transaction,
)


class DonationQuickAmountInline(admin.TabularInline):
    model = DonationQuickAmount
    extra = 3
    fields = ("amount", "label_en", "label_bn", "display_order", "is_active")
    ordering = ("display_order", "amount")


@admin.register(DonationCategory)
class DonationCategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name_en",
        "name_bn",
        "slug",
        "display_order",
        "is_active",
        "is_default",
        "is_featured",
        "icon",
    )
    list_editable = ("display_order", "is_active", "is_default")
    list_filter = ("is_active", "is_default", "is_featured")
    search_fields = ("name_en", "name_bn", "slug")
    prepopulated_fields = {"slug": ("name_en",)}
    ordering = ("display_order", "name_en")
    inlines = [DonationQuickAmountInline]
    fieldsets = (
        (_("Names"), {"fields": ("name_en", "name_bn", "slug")}),
        (_("Description"), {"fields": ("description_en", "description_bn")}),
        (_("Media"), {"fields": ("icon", "image")}),
        (
            _("Display"),
            {"fields": ("display_order", "is_active", "is_default", "is_featured")},
        ),
    )


@admin.register(DonationQuickAmount)
class DonationQuickAmountAdmin(admin.ModelAdmin):
    list_display = ("category", "amount", "label_en", "label_bn", "display_order", "is_active")
    list_filter = ("is_active", "category")
    list_editable = ("display_order", "is_active")
    search_fields = ("category__name_en", "category__name_bn", "label_en", "label_bn")
    ordering = ("category", "display_order", "amount")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "tran_id",
        "gateway",
        "purpose",
        "amount",
        "currency",
        "status",
        "cus_name",
        "created_at",
    )
    list_filter = ("status", "gateway", "purpose", "currency")
    search_fields = ("tran_id", "session_id", "cus_name", "cus_email", "bank_tran_id")
    readonly_fields = (
        "session_id",
        "tran_id",
        "val_id",
        "amount",
        "currency",
        "status",
        "purpose",
        "gateway",
        "bank_tran_id",
        "card_type",
        "card_no",
        "card_issuer",
        "risk_level",
        "validated_on",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        # Allow viewing change form (readonly); block POST mutations.
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return False


def _donation_export_rows(queryset):
    for d in queryset.select_related("category", "transaction"):
        yield [
            d.receipt_number or "",
            d.transaction.tran_id if d.transaction_id else "",
            d.display_name,
            d.donor_email or "",
            d.donor_phone or "",
            d.on_behalf_of or "",
            "Yes" if d.is_anonymous else "No",
            d.category.name_en if d.category_id else "",
            d.amount,
            d.currency,
            d.get_status_display(),
            d.get_payment_method_display(),
            d.created_at.isoformat(sep=" ", timespec="seconds"),
            "Yes" if d.receipt_sent else "No",
        ]


_EXPORT_HEADERS = [
    "Receipt Number",
    "Transaction ID",
    "Donor Name",
    "Email",
    "Phone",
    "On Behalf Of",
    "Anonymous",
    "Category",
    "Amount",
    "Currency",
    "Status",
    "Payment Method",
    "Created At",
    "Receipt Sent",
]


@admin.action(description=_("Export selected donations as CSV"))
def export_donations_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type="text/csv")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    response["Content-Disposition"] = f'attachment; filename="donations_{stamp}.csv"'
    writer = csv.writer(response)
    writer.writerow(_EXPORT_HEADERS)
    for row in _donation_export_rows(queryset):
        writer.writerow(row)
    return response


@admin.action(description=_("Export selected donations as Excel"))
def export_donations_excel(modeladmin, request, queryset):
    try:
        from openpyxl import Workbook
    except ImportError:
        messages.error(
            request,
            _("openpyxl is not installed. Run: pip install openpyxl"),
        )
        return None

    wb = Workbook()
    ws = wb.active
    ws.title = "Donations"
    ws.append(_EXPORT_HEADERS)
    for row in _donation_export_rows(queryset):
        ws.append(row)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="donations_{stamp}.xlsx"'
    return response


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = (
        "receipt_number",
        "donor_name",
        "amount",
        "currency",
        "category",
        "status",
        "payment_method",
        "is_anonymous",
        "receipt_sent",
        "created_at",
    )
    list_filter = (
        "status",
        "payment_method",
        "is_anonymous",
        "receipt_sent",
        "category",
        "created_at",
    )
    search_fields = (
        "donor_name",
        "donor_email",
        "donor_phone",
        "receipt_number",
        "on_behalf_of",
        "transaction__tran_id",
    )
    readonly_fields = (
        "amount",
        "currency",
        "payment_method",
        "status",
        "transaction",
        "receipt_number",
        "receipt_sent",
        "created_at",
        "updated_at",
    )
    raw_id_fields = ("user", "category")
    date_hierarchy = "created_at"
    actions = (export_donations_csv, export_donations_excel)
    fieldsets = (
        (
            _("Donor"),
            {
                "fields": (
                    "donor_name",
                    "donor_email",
                    "donor_phone",
                    "on_behalf_of",
                    "is_anonymous",
                    "user",
                )
            },
        ),
        (
            _("Donation (payment fields are read-only)"),
            {
                "fields": (
                    "amount",
                    "currency",
                    "category",
                    "message",
                    "payment_method",
                    "status",
                    "transaction",
                ),
                "description": _(
                    "Gateway donation status cannot be changed here. "
                    "Record offline donations via the dashboard manual donation form."
                ),
            },
        ),
        (
            _("Receipt"),
            {"fields": ("receipt_number", "receipt_sent", "created_at", "updated_at")},
        ),
        (
            _("Legacy address"),
            {
                "classes": ("collapse",),
                "fields": ("donor_address", "donor_city", "donor_country"),
            },
        ),
    )

    def has_add_permission(self, request):
        # Offline donations go through dashboard create_manual_donation.
        return False

    def save_model(self, request, obj, form, change):
        if change and obj.pk:
            original = Donation.objects.filter(pk=obj.pk).first()
            if original and original.payment_method == PaymentMethod.SSLCOMMERZ:
                # Never allow status/amount mutations on gateway donations.
                obj.status = original.status
                obj.amount = original.amount
                obj.currency = original.currency
                obj.payment_method = original.payment_method
                obj.transaction_id = original.transaction_id
        super().save_model(request, obj, form, change)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        qs = self.get_queryset(request)
        success = qs.filter(status=DonationStatus.COMPLETED)
        summary = {
            "total_count": qs.count(),
            "success_count": success.count(),
            "success_amount": success.aggregate(total=Sum("amount"))["total"] or 0,
            "pending_count": qs.filter(status=DonationStatus.PENDING).count(),
            "failed_count": qs.filter(status=DonationStatus.FAILED).count(),
            "cancelled_count": qs.filter(status=DonationStatus.CANCELLED).count(),
            "refunded_count": qs.filter(status=DonationStatus.REFUNDED).count(),
            "by_category": list(
                success.values("category__name_en")
                .annotate(count=Count("id"), total=Sum("amount"))
                .order_by("-total")[:8]
            ),
        }
        extra_context["donation_summary"] = summary
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(DonationSubscription)
class DonationSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "donor_name",
        "amount",
        "frequency",
        "payment_gateway",
        "status",
        "next_billing",
        "last_billed",
        "consecutive_failures",
    )
    list_filter = ("status", "frequency", "payment_gateway")
    search_fields = (
        "donor_name",
        "donor_email",
        "donor_phone",
        "gateway_subscription_ref",
    )
    readonly_fields = (
        "amount",
        "currency",
        "frequency",
        "payment_gateway",
        "status",
        "payment_token",
        "gateway_subscription_ref",
        "gateway_plan_refer",
        "next_billing",
        "last_billed",
        "last_success_at",
        "last_failure_at",
        "last_failure_reason",
        "consecutive_failures",
        "activated_at",
        "cancelled_at",
        "cancel_reason",
        "management_token",
        "management_token_expires_at",
        "processing_locked_at",
        "processing_lock_token",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DonationRecurringCharge)
class DonationRecurringChargeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "subscription",
        "kind",
        "amount",
        "status",
        "attempt_number",
        "created_at",
    )
    list_filter = ("status", "kind", "provider")
    search_fields = ("idempotency_key", "provider_reference")
    readonly_fields = (
        "subscription",
        "kind",
        "attempt_number",
        "amount",
        "currency",
        "status",
        "provider",
        "provider_reference",
        "idempotency_key",
        "transaction",
        "donation",
        "failure_category",
        "failure_reason",
        "gateway_event",
        "processed_at",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(GatewayWebhookEvent)
class GatewayWebhookEventAdmin(admin.ModelAdmin):
    list_display = (
        "provider",
        "external_event_id",
        "event_type",
        "processing_status",
        "received_at",
        "processed_at",
    )
    list_filter = ("provider", "processing_status", "event_type")
    search_fields = ("external_event_id",)
    readonly_fields = (
        "provider",
        "event_type",
        "external_event_id",
        "processing_status",
        "subscription",
        "charge",
        "payload_digest",
        "safe_payload",
        "error_message",
        "received_at",
        "processed_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
