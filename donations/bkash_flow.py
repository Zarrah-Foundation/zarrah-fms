"""bKash browser callback and reconciliation.

The callback status is not payment proof. A payment is completed only after
Execute or Query returns transactionStatus Completed and the invoice, amount,
currency, and purpose match the server Transaction.
"""

from __future__ import annotations

import logging

from django.db import transaction as db_transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from core.choices import DonationStatus, PaymentMethod
from donations.gateways.base import PaymentGatewayError
from donations.gateways.bkash import BkashGateway, safe_gateway_message
from donations.models import Transaction, TransactionPurpose
from donations.money import amounts_equal, normalize_currency

logger = logging.getLogger(__name__)


def _params(request) -> dict:
    source = request.POST if request.method == "POST" else request.GET
    if hasattr(source, "dict"):
        return source.dict()
    return dict(source)


def _payment_id(params: dict) -> str:
    return (params.get("paymentID") or params.get("paymentId") or "").strip()


def _callback_status(params: dict) -> str:
    return (params.get("status") or "").strip().lower()


def handle_bkash_callback(request):
    params = _params(request)
    payment_id = _payment_id(params)
    status = _callback_status(params)
    if not payment_id:
        _record(params, event_type="bkash_invalid_callback", provider_payload=params)
        return _invalid(request, _("Invalid payment response."))

    txn = (
        Transaction.objects.select_related()
        .filter(val_id=payment_id, gateway=PaymentMethod.BKASH)
        .first()
    )
    if txn is None:
        _record(
            _normalized(params, payment_id=payment_id),
            event_type="bkash_invalid_callback",
        )
        return _invalid(request, _("Invalid payment response."))

    mismatch = _posted_mismatch(params, txn)
    if mismatch:
        event, _created = _record(_normalized(params, txn), event_type="bkash_invalid_callback")
        _mark_failed(event, mismatch)
        return _invalid(request, _("Invalid payment response."))

    if status in ("failure", "fail", "failed"):
        return _close_open_payment(request, txn, params, outcome="failed")
    if status in ("cancel", "cancelled", "canceled"):
        return _close_open_payment(request, txn, params, outcome="cancelled")
    if status != "success":
        event, _created = _record(_normalized(params, txn), event_type="bkash_invalid_callback")
        _mark_failed(event, "Callback status is not success, failure, or cancel.")
        return _invalid(request, _("Invalid payment response."))

    event, _created = _record(_normalized(params, txn), event_type="bkash_callback")
    if txn.status == DonationStatus.COMPLETED or _already_processed(event):
        txn.refresh_from_db()
        if txn.status == DonationStatus.COMPLETED:
            _mark_processed(event)
            return _success_response(request, txn)
    try:
        gateway = BkashGateway()
        data = gateway.validate_transaction(
            txn.val_id, txn.tran_id, txn.amount, currency=txn.currency
        )
    except PaymentGatewayError as exc:
        _mark_failed(event, safe_gateway_message(exc))
        logger.info("bKash callback not confirmed tran_id=%s code=%s", txn.tran_id, getattr(exc, "code", ""))
        return _pending_response(request, _("Payment is not confirmed yet. It will stay pending until bKash confirms it."))

    try:
        _complete(txn, data)
    except Exception as exc:
        _mark_failed(event, safe_gateway_message(exc))
        logger.exception("bKash completion refused tran_id=%s", txn.tran_id)
        return _invalid(request, _("Payment validation failed."))
    _mark_processed(event)
    txn.refresh_from_db()
    return _success_response(request, txn)


def reconcile_bkash_transaction(txn: Transaction) -> Transaction:
    """Query a pending payment. Complete only when bKash reports Completed."""
    if txn.gateway != PaymentMethod.BKASH:
        raise PaymentGatewayError("This transaction is not a bKash payment.")
    if txn.status == DonationStatus.COMPLETED:
        return txn
    if not txn.val_id:
        raise PaymentGatewayError("bKash payment id is missing.")
    gateway = BkashGateway()
    data = gateway.query_payment(txn.val_id, txn.tran_id, txn.amount, currency=txn.currency)
    if not data:
        return txn
    _complete(txn, data)
    txn.refresh_from_db()
    return txn


def _posted_mismatch(params: dict, txn: Transaction) -> str:
    posted_tran = (params.get("tran_id") or "").strip()
    if posted_tran and posted_tran != txn.tran_id:
        return "Callback tran_id does not match the payment."
    posted_purpose = (params.get("purpose") or "").strip()
    if posted_purpose and posted_purpose != txn.purpose:
        return "Callback purpose does not match the payment."
    if params.get("amount") not in (None, "") and not amounts_equal(params.get("amount"), txn.amount):
        return "Callback amount does not match the payment."
    if params.get("currency") and normalize_currency(params.get("currency")) != normalize_currency(txn.currency):
        return "Callback currency does not match the payment."
    return ""


def _normalized(params: dict, txn: Transaction | None = None, payment_id: str = "") -> dict:
    payload = {
        "paymentID": _payment_id(params) or payment_id,
        "paymentId": _payment_id(params) or payment_id,
        "status": _callback_status(params),
        "signature": params.get("signature") or "",
    }
    if txn is not None:
        payload.update(
            {
                "val_id": txn.val_id or "",
                "tran_id": txn.tran_id,
                "amount": txn.amount,
                "currency": txn.currency,
                "purpose": txn.purpose,
            }
        )
    else:
        payload["val_id"] = payload["paymentID"]
    return payload


def _record(payload: dict, *, event_type: str):
    from donations.webhook_services import record_webhook_event

    return record_webhook_event(PaymentMethod.BKASH, payload, event_type=event_type)


def _mark_processed(event):
    from donations.webhook_services import mark_webhook_processed

    mark_webhook_processed(event)


def _mark_failed(event, message: str):
    from donations.webhook_services import mark_webhook_failed

    mark_webhook_failed(event, message)


def _already_processed(event) -> bool:
    from donations.webhook_services import webhook_already_processed

    return webhook_already_processed(event)


def _close_open_payment(request, txn: Transaction, params: dict, *, outcome: str):
    event_type = "bkash_failure_return" if outcome == "failed" else "bkash_cancel_return"
    event, _created = _record(_normalized(params, txn), event_type=event_type)
    if txn.status != DonationStatus.COMPLETED:
        _mark_local_closed(txn, outcome)
        _mark_processed(event)
    else:
        from donations.webhook_services import mark_webhook_ignored

        mark_webhook_ignored(event, "Payment already completed")
    if outcome == "cancelled":
        return _message_redirect(request, txn, _("Payment was cancelled."), error=True)
    return _message_redirect(request, txn, _("Payment failed."), error=True)


def _mark_local_closed(txn: Transaction, outcome: str):
    status = DonationStatus.CANCELLED if outcome == "cancelled" else DonationStatus.FAILED
    with db_transaction.atomic():
        locked = Transaction.objects.select_for_update().get(pk=txn.pk)
        if locked.status == DonationStatus.COMPLETED:
            return
        locked.status = status
        locked.save(update_fields=["status", "updated_at"])
        _mark_payable_closed(locked, status)


def _related(txn: Transaction, name: str):
    try:
        return getattr(txn, name)
    except Exception:
        return None


def _mark_payable_closed(txn: Transaction, status: str):
    if txn.purpose == TransactionPurpose.DONATION:
        donation = _related(txn, "donation")
        if donation is not None and donation.status != DonationStatus.COMPLETED:
            donation.status = status
            donation.save(update_fields=["status", "updated_at"])
        return
    if txn.purpose == TransactionPurpose.MEMBERSHIP_FEE:
        payment = _related(txn, "membership_fee_payment")
        if payment is not None and payment.status != DonationStatus.COMPLETED:
            payment.status = status
            payment.save(update_fields=["status", "updated_at"])
        return
    if txn.purpose == TransactionPurpose.MEMBERSHIP_REGISTRATION:
        reg = _related(txn, "membership_registration_fee")
        if reg is not None and reg.status != DonationStatus.COMPLETED:
            reg.status = status
            reg.save(update_fields=["status", "updated_at"])


def _complete(txn: Transaction, data: dict):
    with db_transaction.atomic():
        locked = Transaction.objects.select_for_update().get(pk=txn.pk)
        if locked.status == DonationStatus.COMPLETED:
            _replay_completion(locked, data)
            return
        if locked.purpose == TransactionPurpose.DONATION:
            from donations.services import complete_donation

            complete_donation(locked.donation, val_id=data.get("val_id") or locked.val_id, validation_data=data)
            return
        if locked.purpose == TransactionPurpose.MEMBERSHIP_FEE:
            from members.billing import complete_fee_payment
            from members.models import MembershipFeePayment

            payment = MembershipFeePayment.objects.get(transaction=locked)
            complete_fee_payment(payment, val_id=data.get("val_id") or locked.val_id, validation_data=data)
            return
        if locked.purpose == TransactionPurpose.MEMBERSHIP_REGISTRATION:
            from members.billing import complete_registration_fee_payment

            reg = locked.membership_registration_fee
            complete_registration_fee_payment(
                reg, val_id=data.get("val_id") or locked.val_id, validation_data=data
            )
            return
        raise PaymentGatewayError("Unsupported bKash payment purpose.", code="purpose")


def _replay_completion(txn: Transaction, data: dict):
    """Idempotent side effects when a duplicate callback arrives after completion."""
    if txn.purpose == TransactionPurpose.DONATION:
        from donations.services import complete_donation

        complete_donation(txn.donation, val_id=data.get("val_id") or txn.val_id, validation_data=data)
    elif txn.purpose == TransactionPurpose.MEMBERSHIP_FEE:
        from members.billing import complete_fee_payment
        from members.models import MembershipFeePayment

        payment = MembershipFeePayment.objects.get(transaction=txn)
        complete_fee_payment(payment, val_id=data.get("val_id") or txn.val_id, validation_data=data)
    elif txn.purpose == TransactionPurpose.MEMBERSHIP_REGISTRATION:
        from members.billing import complete_registration_fee_payment

        complete_registration_fee_payment(
            txn.membership_registration_fee,
            val_id=data.get("val_id") or txn.val_id,
            validation_data=data,
        )


def _public_registration_context(reg) -> dict:
    member = reg.member
    display_name = f"{member.first_name or ''} {member.last_name or ''}".strip() or member.member_id
    txn = getattr(reg, "transaction", None)
    return {
        "payment": reg,
        "payment_kind": "registration",
        "display_name": display_name,
        "member_id": member.member_id,
        "period_label": _("Registration fee"),
        "amount": reg.amount,
        "tran_id": getattr(txn, "tran_id", "") if txn else "",
        "status": reg.status,
    }


def _success_response(request, txn: Transaction):
    if txn.purpose == TransactionPurpose.DONATION:
        from donations.models import Donation

        donation = Donation.objects.select_related("transaction", "category").get(transaction=txn)
        request.session["donation_receipt_access"] = str(donation.pk)
        return render(request, "donations/success.html", {"donation": donation})
    if txn.purpose == TransactionPurpose.MEMBERSHIP_REGISTRATION:
        reg = txn.membership_registration_fee
        if request.user.is_authenticated:
            from django.contrib import messages

            messages.success(request, _("Registration fee payment successful."))
            return render(
                request,
                "dashboard/membership/fee_pay_success.html",
                {"payment": reg, "payment_kind": "registration"},
            )
        return render(request, "members/public_fee_success.html", _public_registration_context(reg))
    from members.fee_payment_views import (
        _is_guest_public_monthly,
        _public_fee_context,
    )
    from members.models import MembershipFeePayment

    payment = MembershipFeePayment.objects.select_related("transaction", "member").get(transaction=txn)
    if _is_guest_public_monthly(request, "monthly", payment) or not request.user.is_authenticated:
        request.session.pop("public_fee_payment_id", None)
        return render(request, "members/public_fee_success.html", _public_fee_context(payment))
    from django.contrib import messages

    messages.success(request, _("Membership fee payment successful."))
    return render(
        request,
        "dashboard/membership/fee_pay_success.html",
        {"payment": payment, "payment_kind": "monthly"},
    )


def _pending_response(request, message: str):
    from django.contrib import messages

    messages.warning(request, message)
    if request.user.is_authenticated:
        return redirect("dashboard")
    return redirect("donation")


def _invalid(request, message: str):
    from django.contrib import messages

    messages.error(request, message)
    if request.user.is_authenticated:
        return redirect("dashboard")
    return redirect("donation")


def _message_redirect(request, txn: Transaction, message: str, *, error: bool):
    from django.contrib import messages

    if error:
        messages.error(request, message)
    else:
        messages.info(request, message)
    if txn.purpose == TransactionPurpose.DONATION:
        return redirect("donation")
    if request.user.is_authenticated:
        return redirect("dashboard-my-fees")
    return redirect("public-membership-fee-payment")


@csrf_exempt
@require_http_methods(["GET", "POST"])
def bkash_callback(request):
    """CSRF-exempt provider return. Browser status alone never completes a payment."""
    try:
        return handle_bkash_callback(request)
    except Exception:
        logger.exception("bKash callback failed closed")
        return HttpResponse(status=400)
