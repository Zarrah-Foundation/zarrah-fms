"""Member-facing membership fee ledger and SSLCommerz one-time checkout."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from core.choices import DonationStatus
from members.billing import (
    activate_autopay,
    add_months,
    current_year_month,
    deactivate_autopay,
    ensure_ledger_months,
    ensure_registration_fee,
    get_or_create_autopay,
    initiate_fee_checkout,
    initiate_registration_fee_checkout,
    is_due_for_current_month,
    is_prepaid_beyond_current,
    paid_through,
)
from members.fee_settings import get_monthly_fee_amount
from members.fee_summary import summarize_member_fees
from members.models import MembershipFee, MembershipRegistrationFee


def _member_or_redirect(request):
    member = getattr(request.user, "member_profile", None)
    if member is None:
        messages.error(request, _("No membership profile is linked to this account."))
        return None
    return member


@login_required
def my_fees(request):
    member = _member_or_redirect(request)
    if member is None:
        return redirect("dashboard")

    cy, cm = current_year_month()
    ey, em = add_months(cy, cm, 11)
    ensure_registration_fee(member)
    ensure_ledger_months(member, ey, em)
    fees = MembershipFee.objects.filter(member=member).order_by("-year", "-month")
    autopay = get_or_create_autopay(member)
    pt = paid_through(member)
    fee_summary = summarize_member_fees(member, ensure_ledger=False)
    try:
        registration_fee = member.registration_fee
    except MembershipRegistrationFee.DoesNotExist:
        registration_fee = None

    return render(
        request,
        "dashboard/membership/my_fees.html",
        {
            "member": member,
            "fees": fees,
            "fee_summary": fee_summary,
            "monthly_fee": get_monthly_fee_amount(),
            "registration_fee": registration_fee,
            "paid_through": pt,
            "autopay": autopay,
            "is_due": is_due_for_current_month(member),
            "is_prepaid": is_prepaid_beyond_current(member),
            "unpaid_fees": [f for f in fees if f.status == DonationStatus.PENDING],
        },
    )


@login_required
@require_POST
def my_fees_pay(request):
    member = _member_or_redirect(request)
    if member is None:
        return redirect("dashboard")

    selected = request.POST.getlist("months")
    months = []
    for raw in selected:
        try:
            y_str, m_str = raw.split("-", 1)
            months.append({"year": int(y_str), "month": int(m_str)})
        except (TypeError, ValueError):
            continue
    if not months:
        messages.error(request, _("Select at least one unpaid month."))
        return redirect("dashboard-my-fees")

    try:
        _payment, url = initiate_fee_checkout(
            member, months, request=request, actor=request.user
        )
    except Exception as exc:
        messages.error(request, str(exc) or _("Could not start payment."))
        return redirect("dashboard-my-fees")
    return redirect(url)


@login_required
@require_POST
def my_fees_pay_registration(request):
    member = _member_or_redirect(request)
    if member is None:
        return redirect("dashboard")
    try:
        _reg, url = initiate_registration_fee_checkout(
            member, request=request, actor=request.user
        )
    except Exception as exc:
        messages.error(request, str(exc) or _("Could not start registration payment."))
        return redirect("dashboard-my-fees")
    return redirect(url)


@login_required
@require_POST
def my_fees_autopay_activate(request):
    member = _member_or_redirect(request)
    if member is None:
        return redirect("dashboard")
    try:
        activate_autopay(member, actor=request.user)
        messages.success(request, _("Auto-payment activated."))
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("dashboard-my-fees")


@login_required
@require_POST
def my_fees_autopay_deactivate(request):
    member = _member_or_redirect(request)
    if member is None:
        return redirect("dashboard")
    deactivate_autopay(member, actor=request.user, reason="Member deactivated")
    messages.success(request, _("Auto-payment deactivated."))
    return redirect("dashboard-my-fees")
