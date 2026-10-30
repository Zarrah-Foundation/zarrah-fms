"""Payment & Recurring Management Center (dashboard)."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from core.choices import DonationStatus, PaymentMethod
from donations.models import (
    DonationSubscription,
    GatewayWebhookEvent,
    PaymentOpsEvent,
    PaymentSystemSettings,
    RefundRequest,
    RefundStatus,
    SubscriptionStatus,
    Transaction,
)
from donations.payment_ops import log_payment_event
from donations.provider_capabilities import all_provider_health, provider_capability_matrix
from donations.refund_services import (
    RefundError,
    approve_refund,
    reject_refund,
    request_refund,
)
from rbac.decorators import require_action
from rbac.permissions import has_action


def _can(request, module, action):
    return has_action(request.user, module, action)


@login_required
@require_action("payments", "view")
def payments_overview(request):
    health = all_provider_health()
    now = timezone.now()
    txn_stats = Transaction.objects.aggregate(
        total=Count("id"),
        completed=Count("id", filter=Q(status=DonationStatus.COMPLETED)),
        failed=Count("id", filter=Q(status=DonationStatus.FAILED)),
        pending=Count("id", filter=Q(status=DonationStatus.PENDING)),
    )
    sub_stats = DonationSubscription.objects.aggregate(
        active=Count("id", filter=Q(status=SubscriptionStatus.ACTIVE)),
        failed=Count("id", filter=Q(status=SubscriptionStatus.PAYMENT_FAILED)),
        suspended=Count("id", filter=Q(status=SubscriptionStatus.SUSPENDED)),
    )
    due = DonationSubscription.objects.filter(
        status=SubscriptionStatus.ACTIVE, next_billing__lte=now
    ).count()
    webhook_failed = GatewayWebhookEvent.objects.filter(
        processing_status="FAILED"
    ).count()
    refunds_open = RefundRequest.objects.filter(status=RefundStatus.REQUESTED).count()
    settings_obj = PaymentSystemSettings.load()
    return render(
        request,
        "dashboard/payments/overview.html",
        {
            "providers": health,
            "txn_stats": txn_stats,
            "sub_stats": sub_stats,
            "due_count": due,
            "webhook_failed": webhook_failed,
            "refunds_open": refunds_open,
            "payment_settings": settings_obj,
            "live_validation_pending": True,
            "can_configure": _can(request, "payments", "configuration"),
        },
    )


@login_required
@require_action("payments", "configuration")
def payments_settings(request):
    obj = PaymentSystemSettings.load()
    if request.method == "POST":
        before = {
            "one_time": obj.one_time_donation_enabled,
            "recurring": obj.recurring_donation_enabled,
            "min": obj.min_donation_amount,
            "max": obj.max_donation_amount,
        }
        obj.one_time_donation_enabled = request.POST.get("one_time_donation_enabled") == "on"
        obj.recurring_donation_enabled = request.POST.get("recurring_donation_enabled") == "on"
        obj.public_membership_fee_enabled = (
            request.POST.get("public_membership_fee_enabled") == "on"
        )
        obj.membership_autopay_enabled = request.POST.get("membership_autopay_enabled") == "on"
        try:
            obj.min_donation_amount = float(request.POST.get("min_donation_amount") or 1)
            obj.max_donation_amount = float(
                request.POST.get("max_donation_amount") or 1_000_000
            )
        except ValueError:
            messages.error(request, _("Invalid amount limits."))
            return redirect("dashboard-payments-settings")
        obj.allowed_recurring_frequencies = "MONTHLY"
        obj.updated_by = request.user
        obj.save()
        log_payment_event(
            actor=request.user,
            action="payment_settings_updated",
            entity="PaymentSystemSettings",
            entity_id="1",
            message="Payment system settings updated",
            metadata={"before": before},
        )
        messages.success(request, _("Payment settings saved."))
        return redirect("dashboard-payments-settings")
    return render(
        request,
        "dashboard/payments/settings.html",
        {"payment_settings": obj},
    )


@login_required
@require_action("payments", "transactions_view")
def payments_transactions(request):
    qs = Transaction.objects.order_by("-created_at")
    q = (request.GET.get("q") or "").strip()
    status = request.GET.get("status") or ""
    purpose = request.GET.get("purpose") or ""
    gateway = request.GET.get("gateway") or ""
    if q:
        qs = qs.filter(
            Q(tran_id__icontains=q)
            | Q(cus_name__icontains=q)
            | Q(cus_email__icontains=q)
            | Q(bank_tran_id__icontains=q)
        )
    if status:
        qs = qs.filter(status=status)
    if purpose:
        qs = qs.filter(purpose=purpose)
    if gateway:
        qs = qs.filter(gateway=gateway)
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    return render(
        request,
        "dashboard/payments/transactions.html",
        {
            "page_obj": page,
            "transactions": page,
            "q": q,
            "status": status,
            "purpose": purpose,
            "gateway": gateway,
            "status_choices": DonationStatus.choices,
            "can_refund": _can(request, "payments", "refunds_request"),
        },
    )


@login_required
@require_action("payments", "transactions_view")
def payments_transaction_detail(request, pk):
    txn = get_object_or_404(Transaction, pk=pk)
    refunds = txn.refund_requests.order_by("-created_at")
    return render(
        request,
        "dashboard/payments/transaction_detail.html",
        {
            "txn": txn,
            "refunds": refunds,
            "can_refund": _can(request, "payments", "refunds_request"),
        },
    )


@login_required
@require_action("payments", "webhooks")
def payments_webhooks(request):
    qs = GatewayWebhookEvent.objects.select_related(
        "subscription", "charge"
    ).order_by("-received_at")
    provider = request.GET.get("provider") or ""
    status = request.GET.get("status") or ""
    if provider:
        qs = qs.filter(provider=provider)
    if status:
        qs = qs.filter(processing_status=status)
    page = Paginator(qs, 40).get_page(request.GET.get("page"))
    return render(
        request,
        "dashboard/payments/webhooks.html",
        {
            "page_obj": page,
            "events": page,
            "provider": provider,
            "status": status,
            "read_only": True,
        },
    )


@login_required
@require_action("payments", "webhooks")
def payments_webhook_detail(request, pk):
    event = get_object_or_404(GatewayWebhookEvent, pk=pk)
    return render(
        request,
        "dashboard/payments/webhook_detail.html",
        {"event": event},
    )


@login_required
@require_action("payments", "recurring_view")
def payments_recurring(request):
    """Unified recurring center (donations today; membership autopay listed separately)."""
    qs = DonationSubscription.objects.select_related("category", "user").order_by(
        "-created_at"
    )
    status = request.GET.get("status") or ""
    provider = request.GET.get("provider") or ""
    q = (request.GET.get("q") or "").strip()
    due = request.GET.get("due") == "1"
    if status:
        qs = qs.filter(status=status)
    if provider:
        qs = qs.filter(payment_gateway=provider)
    if q:
        qs = qs.filter(
            Q(donor_name__icontains=q)
            | Q(donor_email__icontains=q)
            | Q(donor_phone__icontains=q)
        )
    if due:
        qs = qs.filter(
            status=SubscriptionStatus.ACTIVE, next_billing__lte=timezone.now()
        )
    page = Paginator(qs, 25).get_page(request.GET.get("page"))

    from members.models import MembershipAutoPay

    autopays = MembershipAutoPay.objects.filter(is_enabled=True).select_related(
        "member"
    )[:50]
    return render(
        request,
        "dashboard/payments/recurring.html",
        {
            "page_obj": page,
            "subscriptions": page,
            "status": status,
            "provider": provider,
            "q": q,
            "due": due,
            "status_choices": SubscriptionStatus.choices,
            "autopays": autopays,
            "type_filter": "donation",
        },
    )


@login_required
@require_action("payments", "refunds_view")
def payments_refunds(request):
    qs = RefundRequest.objects.select_related(
        "transaction", "requested_by", "approved_by"
    ).order_by("-created_at")
    status = request.GET.get("status") or ""
    if status:
        qs = qs.filter(status=status)
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    return render(
        request,
        "dashboard/payments/refunds.html",
        {
            "page_obj": page,
            "refunds": page,
            "status": status,
            "can_approve": _can(request, "payments", "refunds_approve"),
            "can_request": _can(request, "payments", "refunds_request"),
        },
    )


@login_required
@require_action("payments", "refunds_view")
def payments_refund_detail(request, pk):
    refund = get_object_or_404(
        RefundRequest.objects.select_related(
            "transaction", "requested_by", "approved_by"
        ),
        pk=pk,
    )
    return render(
        request,
        "dashboard/payments/refund_detail.html",
        {
            "refund": refund,
            "can_approve": _can(request, "payments", "refunds_approve"),
        },
    )


@login_required
@require_POST
@require_action("payments", "refunds_request")
def payments_refund_request(request, txn_pk):
    txn = get_object_or_404(Transaction, pk=txn_pk)
    try:
        req = request_refund(
            transaction_obj=txn,
            amount=request.POST.get("amount") or txn.amount,
            reason=request.POST.get("reason") or "",
            actor=request.user,
        )
        messages.success(request, _("Refund requested. Awaiting Super Admin approval."))
        return redirect("dashboard-payments-refund-detail", pk=req.pk)
    except RefundError as exc:
        messages.error(request, str(exc))
        return redirect("dashboard-payments-transaction-detail", pk=txn.pk)


@login_required
@require_POST
@require_action("payments", "refunds_approve")
def payments_refund_approve(request, pk):
    refund = get_object_or_404(RefundRequest, pk=pk)
    try:
        approve_refund(refund=refund, actor=request.user)
        messages.success(
            request,
            _("Refund approved. Provider confirmation is required before REFUNDED status."),
        )
    except RefundError as exc:
        messages.error(request, str(exc))
    return redirect("dashboard-payments-refund-detail", pk=pk)


@login_required
@require_POST
@require_action("payments", "refunds_approve")
def payments_refund_reject(request, pk):
    refund = get_object_or_404(RefundRequest, pk=pk)
    try:
        reject_refund(
            refund=refund,
            actor=request.user,
            reason=request.POST.get("reason") or "",
        )
        messages.success(request, _("Refund rejected."))
    except RefundError as exc:
        messages.error(request, str(exc))
    return redirect("dashboard-payments-refund-detail", pk=pk)


@login_required
@require_action("payments", "logs_view")
def payments_logs(request):
    qs = PaymentOpsEvent.objects.select_related("actor").order_by("-created_at")
    action = request.GET.get("action") or ""
    if action:
        qs = qs.filter(action__icontains=action)
    page = Paginator(qs, 50).get_page(request.GET.get("page"))
    return render(
        request,
        "dashboard/payments/logs.html",
        {"page_obj": page, "events": page, "action": action},
    )


@login_required
@require_action("payments", "view")
def payments_capabilities(request):
    return render(
        request,
        "dashboard/payments/capabilities.html",
        {
            "matrix": provider_capability_matrix(),
            "live_validation_pending": True,
        },
    )
