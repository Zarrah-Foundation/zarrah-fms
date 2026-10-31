"""bKash Tokenized Checkout v2 sandbox adapter.

One-time checkout, agreement APIs, and refunds follow the published sandbox
contract. Automatic recurring is not implemented: payment with an agreement
still redirects the customer to enter a PIN. Live checkout is refused.
"""

from __future__ import annotations

import logging
import re

from django.urls import reverse

from core.choices import PaymentMethod
from donations.bkash_config import redact_provider_text, resolve_bkash_credentials
from donations.gateways.base import PaymentGateway, PaymentGatewayError
from donations.gateways.bkash_client import BkashClient, BkashTimeout
from donations.money import amounts_equal, normalize_currency, to_money

logger = logging.getLogger(__name__)

_PHONE = re.compile(r"^01\d{9}$")


def payer_reference(phone: str, tran_id: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    if _PHONE.fullmatch(digits):
        return digits
    safe = re.sub(r"[<>&]", "", tran_id or "")[:255]
    return safe or "ZARRAH"


def _amount_text(amount) -> str:
    return format(to_money(amount), "f")


def _invoice(payload: dict) -> str:
    return str(payload.get("merchantInvoiceNumber") or payload.get("merchantInvoice") or "")


def _status(payload: dict) -> str:
    return str(payload.get("transactionStatus") or "").strip().lower()


class BkashGateway(PaymentGateway):
    code = PaymentMethod.BKASH
    supports_one_time = True
    supports_recurring = False
    supports_refund = True
    supports_cancel_recurring = False
    supports_webhook = True
    supports_validate = True

    def __init__(self, client: BkashClient | None = None):
        self.client = client or BkashClient()

    def init_payment(self, payable, request):
        from donations.bkash_config import bkash_checkout_allowed

        transaction = getattr(payable, "transaction", None)
        purpose = getattr(transaction, "purpose", "") or ""
        ok, err = bkash_checkout_allowed(purpose)
        if not ok or transaction is None or request is None:
            raise PaymentGatewayError(
                err or "bKash sandbox checkout is not available.",
                code="not_configured",
            )

        phone = (
            getattr(payable, "donor_phone", None)
            or getattr(transaction, "cus_phone", None)
            or ""
        )
        callback = request.build_absolute_uri(reverse("bkash-callback"))
        try:
            data = self.client.create_payment(
                payer_reference=payer_reference(phone, transaction.tran_id),
                callback_url=callback,
                amount=_amount_text(payable.amount),
                currency=normalize_currency(getattr(payable, "currency", None) or transaction.currency),
                merchant_invoice=transaction.tran_id,
            )
        except PaymentGatewayError:
            raise
        except Exception as exc:
            logger.exception("bKash create payment failed")
            raise PaymentGatewayError("bKash checkout could not be started.", code="transport") from exc

        payment_id = str(data["paymentId"])
        transaction.val_id = payment_id
        transaction.save(update_fields=["val_id", "updated_at"])
        logger.info("bKash checkout created tran_id=%s", transaction.tran_id)
        return str(data["bkashURL"])

    def validate_transaction(self, val_id, tran_id, amount, currency="BDT"):
        """Execute after a success callback, then accept only a Completed result."""
        if not val_id or not tran_id:
            raise PaymentGatewayError("bKash payment reference is missing.", code="invalid_callback")
        try:
            payload = self.client.execute_payment(val_id)
        except BkashTimeout:
            logger.info("bKash execute timed out; querying payment tran_id=%s", tran_id)
            payload = self.client.query_payment(val_id)
        else:
            external = str(payload.get("externalCode") or "")
            if external == "2062" or _status(payload) != "completed":
                if _status(payload) != "completed":
                    payload = self.client.query_payment(val_id)
        return self._confirmed_payload(payload, tran_id=tran_id, amount=amount, currency=currency)

    def query_payment(self, val_id, tran_id, amount, currency="BDT"):
        payload = self.client.query_payment(val_id)
        if _status(payload) != "completed":
            return None
        return self._confirmed_payload(payload, tran_id=tran_id, amount=amount, currency=currency)

    def init_recurring_authorization(self, payable, request, *, subscription, schedule_day):
        raise PaymentGatewayError(
            "bKash automatic recurring is not implemented. "
            "Tokenized Checkout agreement payments still require the customer to enter a PIN "
            "and are not a scheduled charge.",
            code="not_implemented",
        )

    def cancel_recurring(self, subscription):
        ref = (getattr(subscription, "gateway_subscription_ref", None) or "").strip()
        gateway = getattr(subscription, "payment_gateway", "")
        if gateway != PaymentMethod.BKASH or not ref:
            raise PaymentGatewayError(
                "bKash automatic recurring is not implemented. No agreement id is stored.",
                code="not_implemented",
            )
        data = self.client.cancel_agreement(ref)
        if str(data.get("agreementStatus") or "") != "Cancelled":
            raise PaymentGatewayError(
                self.client._error_text(data),
                code="not_confirmed",
            )
        return data

    def refund(self, *, transaction, amount, reason=""):
        payment_id = (transaction.val_id or "").strip()
        trx_id = (transaction.bank_tran_id or "").strip()
        if not payment_id or not trx_id:
            raise PaymentGatewayError("bKash refund: original payment id and trx id are required.")
        reason_text = re.sub(r"[<>&]", "", (reason or "Refund").strip())[:255] or "Refund"
        amount_text = _amount_text(amount)
        try:
            data = self.client.refund_transaction(
                payment_id=payment_id,
                trx_id=trx_id,
                amount=amount_text,
                reason=reason_text,
            )
        except BkashTimeout:
            data = self._refund_from_status(payment_id, trx_id, amount_text)
        if str(data.get("refundTransactionStatus") or "") != "Completed":
            raise PaymentGatewayError(
                self.client._error_text(data) or "bKash refund was not confirmed.",
                code="not_confirmed",
            )
        if not amounts_equal(data.get("refundAmount"), amount):
            raise PaymentGatewayError("bKash refund amount does not match the approved amount.")
        reference = str(data.get("refundTrxId") or "")
        if not reference:
            raise PaymentGatewayError("bKash refund was not confirmed.", code="not_confirmed")
        return {
            "confirmed": True,
            "reference": reference,
            "message": "bKash refundTransactionStatus Completed",
        }

    def begin_agreement(self, *, payer_reference, callback_url) -> dict:
        return self.client.create_agreement(
            payer_reference=payer_reference, callback_url=callback_url
        )

    def execute_agreement(self, agreement_id: str) -> dict:
        return self.client.execute_agreement(agreement_id)

    def query_agreement(self, agreement_id: str) -> dict:
        return self.client.query_agreement(agreement_id)

    def create_payment_with_agreement(self, **kwargs) -> dict:
        return self.client.create_payment_with_agreement(**kwargs)

    def execute_payment_with_agreement(self, **kwargs) -> dict:
        return self.client.execute_payment_with_agreement(**kwargs)

    def search_transaction(self, trx_id: str) -> dict:
        return self.client.search_transaction(trx_id)

    def _confirmed_payload(self, payload, *, tran_id, amount, currency):
        if not isinstance(payload, dict):
            raise PaymentGatewayError("bKash returned an invalid response.", code="invalid_response")
        if _status(payload) != "completed":
            raise PaymentGatewayError(
                "bKash has not confirmed this payment.",
                code="not_confirmed",
            )
        if _invoice(payload) != str(tran_id):
            raise PaymentGatewayError("bKash invoice does not match this transaction.", code="mismatch")
        if not amounts_equal(payload.get("amount"), amount):
            raise PaymentGatewayError("bKash amount does not match this transaction.", code="mismatch")
        if not payload.get("currency"):
            raise PaymentGatewayError("bKash currency does not match this transaction.", code="mismatch")
        expected = normalize_currency(currency)
        remote = normalize_currency(payload.get("currency"))
        if remote != expected:
            raise PaymentGatewayError("bKash currency does not match this transaction.", code="mismatch")
        trx_id = str(payload.get("trxId") or "")
        if not trx_id:
            raise PaymentGatewayError("bKash completed response has no trxId.", code="invalid_response")
        return {
            "status": "VALID",
            "tran_id": str(tran_id),
            "val_id": str(payload.get("paymentId") or ""),
            "amount": str(payload.get("amount")),
            "currency": remote,
            "bank_tran_id": trx_id,
            "card_type": "bKash",
        }

    def _refund_from_status(self, payment_id, trx_id, amount_text):
        try:
            payload = self.client.refund_status(payment_id=payment_id, trx_id=trx_id)
        except BkashTimeout as exc:
            raise PaymentGatewayError(
                "bKash refund timed out. Query the refund before trying again.",
                code="timeout",
            ) from exc
        matched = self._matching_refund(payload, amount_text)
        if matched is None:
            raise PaymentGatewayError(
                "bKash refund timed out and refund status is not Completed.",
                code="timeout",
            )
        return matched

    @staticmethod
    def _matching_refund(payload, amount_text):
        rows = payload.get("refundTransactions") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            if isinstance(payload, dict) and str(payload.get("refundTransactionStatus") or "") == "Completed":
                return payload
            return None
        for row in rows:
            if not isinstance(row, dict):
                continue
            if str(row.get("refundTransactionStatus") or "") != "Completed":
                continue
            if amounts_equal(row.get("refundAmount"), amount_text):
                return row
        return None


def safe_gateway_message(exc: Exception) -> str:
    creds = resolve_bkash_credentials()
    return redact_provider_text(str(exc), creds)
