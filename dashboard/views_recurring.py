"""Admin recurring donation list/detail (RBAC-gated)."""

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from donations.models import DonationSubscription, SubscriptionStatus
from donations.recurring_config import sslcommerz_recurring_configured
from donations.recurring_services import cancel_subscription
from rbac.decorators import require_action


@require_action("donations", "recurring_view")
def recurring_subscriptions_list(request):
    qs = DonationSubscription.objects.select_related("category", "user").order_by(
        "-created_at"
    )
    status = request.GET.get("status") or ""
    provider = request.GET.get("provider") or ""
    q = (request.GET.get("q") or "").strip()
    if status:
        qs = qs.filter(status=status)
    if provider:
        qs = qs.filter(payment_gateway=provider)
    if q:
        qs = qs.filter(
            Q(donor_name__icontains=q)
            | Q(donor_email__icontains=q)
            | Q(donor_phone__icontains=q)
            | Q(gateway_subscription_ref__icontains=q)
        )
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    cfg = sslcommerz_recurring_configured()
    return render(
        request,
        "dashboard/donations/recurring_list.html",
        {
            "page_obj": page,
            "subscriptions": page,
            "status_filter": status,
            "provider_filter": provider,
            "q": q,
            "status_choices": SubscriptionStatus.choices,
            "recurring_configured": cfg.configured,
            "recurring_config_reason": cfg.reason,
        },
    )


@require_action("donations", "recurring_view")
def recurring_subscription_detail(request, pk):
    sub = get_object_or_404(
        DonationSubscription.objects.select_related("category", "user", "cancelled_by"),
        pk=pk,
    )
    charges = sub.charges.select_related("transaction", "donation").order_by(
        "-created_at"
    )[:100]
    events = sub.webhook_events.order_by("-received_at")[:50]
    return render(
        request,
        "dashboard/donations/recurring_detail.html",
        {
            "subscription": sub,
            "charges": charges,
            "events": events,
            "can_manage": True,
        },
    )


@require_action("donations", "recurring_cancel")
def recurring_subscription_cancel(request, pk):
    if request.method != "POST":
        return redirect("dashboard-recurring-detail", pk=pk)
    sub = get_object_or_404(DonationSubscription, pk=pk)
    reason = (request.POST.get("reason") or "Cancelled by administrator").strip()
    cancel_subscription(sub, actor=request.user, reason=reason)
    messages.success(request, _("Subscription cancelled."))
    return redirect("dashboard-recurring-detail", pk=sub.pk)


@require_action("donations", "recurring_manage")
def recurring_subscription_suspend(request, pk):
    if request.method != "POST":
        return redirect("dashboard-recurring-detail", pk=pk)
    sub = get_object_or_404(DonationSubscription, pk=pk)
    if sub.status not in (
        SubscriptionStatus.ACTIVE,
        SubscriptionStatus.PAYMENT_FAILED,
    ):
        messages.error(request, _("This subscription cannot be suspended."))
        return redirect("dashboard-recurring-detail", pk=pk)
    sub.status = SubscriptionStatus.SUSPENDED
    sub.save(update_fields=["status", "updated_at"])
    messages.success(request, _("Subscription suspended."))
    return redirect("dashboard-recurring-detail", pk=pk)
