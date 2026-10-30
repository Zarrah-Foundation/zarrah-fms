"""Payment & Recurring Management Center (dashboard)."""

from __future__ import annotations

import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
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
from donations.payment_center import (
    operational_metrics,
    purpose_capability_rows,
    recurring_setup_cards,
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
    metrics = operational_metrics()
    settings_obj = PaymentSystemSettings.load()
    return render(
        request,
        "dashboard/payments/overview.html",
        {
            "providers": health,
            "metrics": metrics,
            "txn_stats": metrics["txn_stats"],
            "sub_stats": metrics["sub_stats"],
            "due_count": metrics["due_count"],
            "webhook_failed": metrics["webhook_failed"],
            "refunds_open": metrics["refunds_pending"],
            "payment_settings": settings_obj,
            "live_validation_pending": True,
            "can_configure": _can(request, "payments", "configuration"),
            "setup_cards": recurring_setup_cards(),
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


def _parse_filter_date(raw: str):
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return datetime.date.fromisoformat(raw)
    except ValueError:
        return None


@login_required
@require_action("payments", "transactions_view")
def payments_transactions(request):
    qs = Transaction.objects.order_by("-created_at")
    q = (request.GET.get("q") or "").strip()
    status = request.GET.get("status") or ""
    purpose = request.GET.get("purpose") or ""
    gateway = request.GET.get("gateway") or ""
    date_from = _parse_filter_date(request.GET.get("date_from") or "")
    date_to = _parse_filter_date(request.GET.get("date_to") or "")
    if q:
        qs = qs.filter(
            Q(tran_id__icontains=q)
            | Q(cus_name__icontains=q)
            | Q(cus_email__icontains=q)
            | Q(bank_tran_id__icontains=q)
            | Q(val_id__icontains=q)
            | Q(session_id__icontains=q)
        )
    if status:
        qs = qs.filter(status=status)
    if purpose:
        qs = qs.filter(purpose=purpose)
    if gateway:
        qs = qs.filter(gateway=gateway)
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)
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
            "date_from": date_from.isoformat() if date_from else "",
            "date_to": date_to.isoformat() if date_to else "",
            "status_choices": DonationStatus.choices,
            "gateway_choices": PaymentMethod.choices,
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
            "can_configure": _can(request, "payments", "configuration"),
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
@require_action("payments", "configuration")
def payments_recurring_setup(request):
    """Administrator control center for recurring provider readiness.

    Shows configuration and verification state only. Secret fields stay write-only
    on the payment-method configure form and are not rendered here.
    """
    return render(
        request,
        "dashboard/payments/recurring_setup.html",
        {
            "cards": recurring_setup_cards(),
            "live_validation_pending": True,
        },
    )


@login_required
@require_action("payments", "view")
def payments_registration_fees(request):
    from members.models import MembershipRegistrationFee

    qs = MembershipRegistrationFee.objects.select_related("member").order_by("-created_at")
    status = request.GET.get("status") or ""
    if status:
        qs = qs.filter(status=status)
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    collected = operational_metrics()
    return render(
        request,
        "dashboard/payments/registration_fees.html",
        {
            "page_obj": page,
            "fees": page,
            "status": status,
            "status_choices": DonationStatus.choices,
            "collected_total": collected["registration_collected_total"],
            "collected_count": collected["registration_collected_count"],
        },
    )


@login_required
@require_action("payments", "view")
def payments_capabilities(request):
    return render(
        request,
        "dashboard/payments/capabilities.html",
        {
            "matrix": provider_capability_matrix(),
            "purpose_rows": purpose_capability_rows(),
            "live_validation_pending": True,
        },
    )
