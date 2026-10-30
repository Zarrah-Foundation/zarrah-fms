"""Public SSLCommerz return/IPN handlers for membership fee payments."""

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST

from core.choices import DonationStatus
from members.billing import (
    complete_fee_payment,
    complete_registration_fee_payment,
    mark_fee_payment_failed,
)
from members.models import MembershipFeePayment, MembershipRegistrationFee
from members.periods import format_fee_period
from members.public_fee_payment import (
    SESSION_PUBLIC_PAYMENT_KEY,
    is_public_fee_payment,
)


def _lookup_payable(tran_id):
    payment = (
        MembershipFeePayment.objects.select_related("transaction", "member")
        .filter(transaction__tran_id=tran_id)
        .first()
    )
    if payment:
        return "monthly", payment
    reg = (
        MembershipRegistrationFee.objects.select_related("transaction", "member")
        .filter(transaction__tran_id=tran_id)
        .first()
    )
    if reg:
        return "registration", reg
    return None, None


def _complete_from_gateway(request, *, from_post=False, event_type="membership_fee_callback"):
    from core.choices import PaymentMethod
    from donations.services import validate_transaction
    from donations.webhook_services import (
        mark_webhook_failed,
        mark_webhook_processed,
        record_webhook_event,
        webhook_already_processed,
    )

    src = request.POST if from_post else request.GET
    payload = src.dict() if hasattr(src, "dict") else dict(src)
    event, _created = record_webhook_event(
        PaymentMethod.SSLCOMMERZ, payload, event_type=event_type
    )
    if webhook_already_processed(event):
        # Recover payable for response context if possible.
        kind, payable = _lookup_payable(payload.get("tran_id") or "")
        return kind, payable, None

    val_id = payload.get("val_id")
    tran_id = payload.get("tran_id")
    if not val_id or not tran_id:
        mark_webhook_failed(event, "Missing val_id or tran_id")
        return None, None, _("Invalid payment response.")

    kind, payable = _lookup_payable(tran_id)
    if payable is None:
        mark_webhook_failed(event, "Payment not found")
        return None, None, _("Payment not found.")

    if payable.status == DonationStatus.COMPLETED:
        mark_webhook_processed(event)
        return kind, payable, None

    currency = (
        payable.transaction.currency
        if getattr(payable, "transaction_id", None)
        else "BDT"
    )
    data = validate_transaction(
        val_id,
        tran_id,
        payable.amount,
        method=payable.payment_method,
        currency=currency,
    )
    if not data:
        mark_webhook_failed(event, "Gateway validation failed")
        return None, None, _("Payment validation failed.")

    if kind == "registration":
        complete_registration_fee_payment(payable, val_id=val_id, validation_data=data)
    else:
        complete_fee_payment(payable, val_id=val_id, validation_data=data)
    payable.refresh_from_db()
    mark_webhook_processed(event)
    return kind, payable, None


def _is_guest_public_monthly(request, kind, payment) -> bool:
    if kind != "monthly" or payment is None:
        return False
    if is_public_fee_payment(payment):
        return True
    session_id = request.session.get(SESSION_PUBLIC_PAYMENT_KEY)
    return bool(session_id and str(payment.pk) == str(session_id))


def _public_fee_context(payment):
    member = payment.member
    months = payment.months or []
    if months:
        y, m = int(months[0]["year"]), int(months[0]["month"])
        period_label = format_fee_period(y, m)
    else:
        period_label = ""
    display_name = (
        f"{member.first_name or ''} {member.last_name or ''}".strip() or member.member_id
    )
    txn = getattr(payment, "transaction", None)
    return {
        "payment": payment,
        "payment_kind": "monthly",
        "display_name": display_name,
        "member_id": member.member_id,
        "period_label": period_label,
        "amount": payment.amount,
        "tran_id": getattr(txn, "tran_id", "") if txn else "",
        "status": payment.status,
    }


def _fail_redirect(request, kind, payable):
    if payable is not None and _is_guest_public_monthly(request, kind, payable):
        return redirect("public-membership-fee-payment")
    if request.user.is_authenticated:
        return redirect("dashboard-my-fees")
    return redirect("public-membership-fee-payment")


@csrf_exempt
@require_http_methods(["GET", "POST"])
def membership_fee_pay_success(request):
    """Browser return URL — CSRF-exempt; completion still requires validation API."""
    kind, payment, err = _complete_from_gateway(
        request, from_post=request.method == "POST"
    )
    if err:
        messages.error(request, err)
        if request.user.is_authenticated:
            return redirect("dashboard-my-fees")
        return redirect("public-membership-fee-payment")

    if _is_guest_public_monthly(request, kind, payment):
        request.session.pop(SESSION_PUBLIC_PAYMENT_KEY, None)
        return render(
            request,
            "members/public_fee_success.html",
            _public_fee_context(payment),
        )

    if kind == "registration":
        messages.success(request, _("Registration fee payment successful."))
    else:
        messages.success(request, _("Membership fee payment successful."))
    return render(
        request,
        "dashboard/membership/fee_pay_success.html",
        {"payment": payment, "payment_kind": kind},
    )


@csrf_exempt
@require_http_methods(["GET", "POST"])
def membership_fee_pay_fail(request):
    from core.choices import PaymentMethod
    from donations.webhook_services import (
        mark_webhook_ignored,
        mark_webhook_processed,
        record_webhook_event,
    )

    src = request.POST if request.method == "POST" else request.GET
    payload = src.dict() if hasattr(src, "dict") else dict(src)
    event, _created = record_webhook_event(
        PaymentMethod.SSLCOMMERZ, payload, event_type="membership_fee_fail_return"
    )
    tran_id = src.get("tran_id")
    kind, payable = None, None
    if tran_id:
        kind, payable = _lookup_payable(tran_id)
        if payable and payable.status == DonationStatus.COMPLETED:
            mark_webhook_ignored(event, "Payment already completed")
        elif payable:
            if kind == "monthly":
                mark_fee_payment_failed(payable)
            else:
                payable.status = DonationStatus.FAILED
                payable.save(update_fields=["status", "updated_at"])
                if payable.transaction_id:
                    payable.transaction.status = DonationStatus.FAILED
                    payable.transaction.save(update_fields=["status", "updated_at"])
            mark_webhook_processed(event)
        else:
            mark_webhook_ignored(event, "Payment not found")
    else:
        mark_webhook_ignored(event, "Missing tran_id")
    messages.error(request, _("Membership fee payment failed."))
    return _fail_redirect(request, kind, payable)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def membership_fee_pay_cancel(request):
    from core.choices import PaymentMethod
    from donations.webhook_services import (
        mark_webhook_ignored,
        mark_webhook_processed,
        record_webhook_event,
    )

    src = request.POST if request.method == "POST" else request.GET
    payload = src.dict() if hasattr(src, "dict") else dict(src)
    event, _created = record_webhook_event(
        PaymentMethod.SSLCOMMERZ, payload, event_type="membership_fee_cancel_return"
    )
    tran_id = src.get("tran_id")
    kind, payable = None, None
    if tran_id:
        kind, payable = _lookup_payable(tran_id)
        updated_m = MembershipFeePayment.objects.filter(
            transaction__tran_id=tran_id
        ).exclude(status=DonationStatus.COMPLETED).update(
            status=DonationStatus.CANCELLED
        )
        updated_r = MembershipRegistrationFee.objects.filter(
            transaction__tran_id=tran_id
        ).exclude(status=DonationStatus.COMPLETED).update(
            status=DonationStatus.CANCELLED
        )
        if updated_m or updated_r:
            mark_webhook_processed(event)
        else:
            mark_webhook_ignored(event, "Already completed or not found")
    else:
        mark_webhook_ignored(event, "Missing tran_id")
    messages.warning(request, _("Membership fee payment cancelled."))
    return _fail_redirect(request, kind, payable)


@csrf_exempt
@require_POST
def membership_fee_pay_ipn(request):
    kind, payment, err = _complete_from_gateway(
        request, from_post=True, event_type="membership_fee_ipn"
    )
    if payment is None:
        return HttpResponse(err or "Invalid", status=400)
    return HttpResponse("OK")
