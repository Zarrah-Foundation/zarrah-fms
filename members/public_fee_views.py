"""Public Membership Fee Payment views (PAY-WP2)."""

from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from members.billing import current_year_month
from members.public_fee_payment import (
    PublicFeeError,
    initiate_public_current_month_checkout,
    verify_public_membership_id,
)


def _posted_period(request):
    """Extract a crafted period from POST if present (for rejection only)."""
    year = request.POST.get("year")
    month = request.POST.get("month")
    period_key = (request.POST.get("period_key") or request.POST.get("period") or "").strip()
    if year and month:
        try:
            return int(year), int(month)
        except (TypeError, ValueError):
            return None
    if period_key and "-" in period_key:
        parts = period_key.split("-")
        if len(parts) == 2:
            try:
                return int(parts[0]), int(parts[1])
            except (TypeError, ValueError):
                return None
    return None


def _reject_crafted_period_if_any(request):
    crafted = _posted_period(request)
    if crafted is None:
        return None
    cy, cm = current_year_month()
    if crafted != (cy, cm):
        return _(
            "Payments for other months require you to log in to your account."
        )
    return None


@require_GET
def public_fee_payment_start(request):
    """Initial Membership ID entry screen."""
    return render(
        request,
        "members/public_fee_payment.html",
        {
            "stage": "lookup",
            "member_id_value": "",
        },
    )


@require_http_methods(["GET", "POST"])
def public_fee_payment_verify(request):
    """CSRF-protected Membership ID verification (server-side only)."""
    if request.method == "GET":
        return redirect("public-membership-fee-payment")

    member_id = (request.POST.get("member_id") or "").strip()
    period_err = _reject_crafted_period_if_any(request)
    if period_err:
        messages.error(request, period_err)
        return render(
            request,
            "members/public_fee_payment.html",
            {"stage": "lookup", "member_id_value": member_id},
            status=400,
        )

    if not member_id:
        messages.error(request, _("Please enter a Membership ID."))
        return render(
            request,
            "members/public_fee_payment.html",
            {"stage": "lookup", "member_id_value": ""},
            status=400,
        )

    try:
        confirmed = verify_public_membership_id(member_id, request=request)
    except PublicFeeError as exc:
        if exc.code == "already_paid":
            return render(
                request,
                "members/public_fee_payment.html",
                {
                    "stage": "already_paid",
                    "already_paid_message": str(exc),
                    "login_url": reverse("login"),
                    "member_id_value": member_id,
                },
            )
        messages.error(request, str(exc))
        return render(
            request,
            "members/public_fee_payment.html",
            {
                "stage": "lookup",
                "member_id_value": member_id,
                "error_code": exc.code,
            },
            status=400,
        )

    return render(
        request,
        "members/public_fee_payment.html",
        {
            "stage": "confirm",
            "confirmed": confirmed,
            "member_id_value": confirmed["member_id"],
        },
    )


@require_POST
def public_fee_payment_pay(request):
    """CSRF-protected Pay Now — token is the only client authority."""
    period_err = _reject_crafted_period_if_any(request)
    if period_err:
        messages.error(request, period_err)
        return redirect("public-membership-fee-payment")

    # Purpose / amount / member_id POST values are ignored (never trusted).
    token = (request.POST.get("checkout_token") or "").strip()
    if not token:
        messages.error(request, _("Please verify your Membership ID first."))
        return redirect("public-membership-fee-payment")

    try:
        _payment, url, _snapshot = initiate_public_current_month_checkout(
            token=token, request=request
        )
    except PublicFeeError as exc:
        if exc.code == "already_paid":
            return render(
                request,
                "members/public_fee_payment.html",
                {
                    "stage": "already_paid",
                    "already_paid_message": str(exc),
                    "login_url": reverse("login"),
                },
            )
        messages.error(request, str(exc))
        return redirect("public-membership-fee-payment")
    except Exception:
        messages.error(
            request,
            _("Online payment could not be started. Please try again later."),
        )
        return redirect("public-membership-fee-payment")

    return redirect(url)
