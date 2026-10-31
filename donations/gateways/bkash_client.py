"""HTTP client for bKash Tokenized Checkout v2 sandbox.

Official contract (sandbox host only):
https://developer.bka.sh/docs/grant-token
https://developer.bka.sh/docs/create-payment-3
https://developer.bka.sh/docs/execute-payment-4
https://developer.bka.sh/docs/query-payment
https://developer.bka.sh/docs/search-transaction
https://developer.bka.sh/docs/create-agreement-1
https://developer.bka.sh/docs/execute-agreement-1
https://developer.bka.sh/docs/query-agreement-1
https://developer.bka.sh/docs/cancel-agreement-1
https://developer.bka.sh/docs/create-payment-with-agreement
https://developer.bka.sh/docs/execute-payment-with-agreement
https://developer.bka.sh/docs/refund
https://developer.bka.sh/docs/refund-status

Tokens are cached and never logged. Live hosts are never called.
"""

from __future__ import annotations

import hashlib
import logging
import time

import requests
from django.core.cache import cache

from donations.bkash_config import BkashCredentials, redact_provider_text, resolve_bkash_credentials
from donations.gateways.base import PaymentGatewayError

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 30
_CACHE_TTL = 60 * 60 * 24


class BkashTimeout(PaymentGatewayError):
    def __init__(self, message="bKash request timed out."):
        super().__init__(message, code="timeout")


class BkashClient:
    def __init__(self, creds: BkashCredentials | None = None):
        self.creds = creds or resolve_bkash_credentials()

    def grant_token(self, *, force: bool = False) -> str:
        self._require_sandbox_api()
        if not force:
            cached = self._cached_id_token()
            if cached:
                return cached
        data = self._post(
            "/auth/grant-token",
            {"app_key": self.creds.app_key, "app_secret": self.creds.app_secret},
            auth=False,
        )
        return self._accept_token(data)

    def refresh_token(self, refresh_token: str) -> str:
        self._require_sandbox_api()
        data = self._post(
            "/auth/refresh-token",
            {
                "app_key": self.creds.app_key,
                "app_secret": self.creds.app_secret,
                "refresh_token": refresh_token,
            },
            auth=False,
        )
        return self._accept_token(data)

    def authorization_token(self) -> str:
        cached = self._cached_id_token()
        if cached:
            return cached
        bundle = cache.get(self._cache_key()) or {}
        refresh = bundle.get("refresh_token") or ""
        if refresh:
            try:
                return self.refresh_token(refresh)
            except PaymentGatewayError:
                logger.info("bKash token refresh failed; granting a new sandbox token.")
        return self.grant_token(force=True)

    def create_payment(self, *, payer_reference, callback_url, amount, currency, merchant_invoice) -> dict:
        data = self._post(
            "/payment/create",
            {
                "payerReference": payer_reference,
                "callbackURL": callback_url,
                "amount": amount,
                "currency": currency,
                "intent": "sale",
                "merchantInvoiceNumber": merchant_invoice,
            },
        )
        self._require_fields(data, "paymentId", "bkashURL")
        if not str(data.get("bkashURL") or "").startswith("https://"):
            raise PaymentGatewayError("bKash did not return a checkout URL.", code="invalid_response")
        return data

    def execute_payment(self, payment_id: str) -> dict:
        return self._post("/payment/execute", {"paymentId": payment_id})

    def query_payment(self, payment_id: str) -> dict:
        return self._post("/query/payment", {"paymentId": payment_id})

    def search_transaction(self, trx_id: str) -> dict:
        return self._post("/general/search-transaction", {"trxId": trx_id})

    def create_agreement(self, *, payer_reference, callback_url) -> dict:
        data = self._post(
            "/agreement/create",
            {"payerReference": payer_reference, "callbackURL": callback_url},
        )
        self._require_fields(data, "agreementId", "bkashURL")
        return data

    def execute_agreement(self, agreement_id: str) -> dict:
        return self._post("/agreement/execute", {"agreementId": agreement_id})

    def query_agreement(self, agreement_id: str) -> dict:
        return self._post("/query/agreement", {"agreementId": agreement_id})

    def cancel_agreement(self, agreement_id: str) -> dict:
        return self._post("/agreement/cancel", {"agreementId": agreement_id})

    def create_payment_with_agreement(
        self, *, agreement_id, callback_url, amount, currency, merchant_invoice
    ) -> dict:
        """Starts a PIN checkout. The returned URL is not a completed payment."""
        data = self._post(
            "/payment-with-agreement/create",
            {
                "agreementId": agreement_id,
                "callbackURL": callback_url,
                "amount": amount,
                "currency": currency,
                "intent": "sale",
                "merchantInvoiceNumber": merchant_invoice,
            },
        )
        self._require_fields(data, "paymentId", "bkashURL")
        return data

    def execute_payment_with_agreement(self, *, payment_id, agreement_id) -> dict:
        return self._post(
            "/payment-with-agreement/execute",
            {"paymentId": payment_id, "agreementId": agreement_id},
        )

    def refund_transaction(self, *, payment_id, trx_id, amount, reason, sku="ZARRAH") -> dict:
        return self._post(
            "/refund/payment/transaction",
            {
                "paymentId": payment_id,
                "trxId": trx_id,
                "refundAmount": amount,
                "reason": reason,
                "sku": sku,
            },
        )

    def refund_status(self, *, payment_id, trx_id) -> dict:
        return self._post(
            "/refund/payment/status",
            {"paymentId": payment_id, "trxId": trx_id},
        )

    def _require_sandbox_api(self) -> None:
        if not self.creds.api_callable or self.creds.environment != "sandbox":
            raise PaymentGatewayError(
                self.creds.reason or "bKash sandbox credentials are not configured.",
                code="not_configured" if not self.creds.configured else "live_disabled",
            )

    def _cache_key(self) -> str:
        material = "|".join(
            [
                self.creds.environment,
                self.creds.base_url,
                self.creds.username,
                self.creds.app_key,
                hashlib.sha256(self.creds.password.encode("utf-8")).hexdigest(),
                hashlib.sha256(self.creds.app_secret.encode("utf-8")).hexdigest(),
            ]
        )
        digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
        return f"bkash-token:{digest}"

    def _cached_id_token(self) -> str:
        bundle = cache.get(self._cache_key()) or {}
        token = bundle.get("id_token") or ""
        expires_at = float(bundle.get("expires_at") or 0)
        if token and expires_at - 600 > time.time():
            return token
        return ""

    def _accept_token(self, data: dict) -> str:
        status = str(data.get("statusCode") or "")
        token = data.get("id_token") or ""
        if status != "0000" or not token:
            raise PaymentGatewayError(
                redact_provider_text(
                    data.get("statusMessage") or data.get("errorMessageEn") or "bKash token request failed.",
                    self.creds,
                ),
                code="auth",
            )
        try:
            expires_in = int(data.get("expires_in") or 3600)
        except (TypeError, ValueError):
            expires_in = 3600
        cache.set(
            self._cache_key(),
            {
                "id_token": token,
                "refresh_token": data.get("refresh_token") or "",
                "expires_at": time.time() + max(60, expires_in),
            },
            _CACHE_TTL,
        )
        logger.info("bKash sandbox token stored in cache.")
        return token

    def _auth_headers(self) -> dict:
        return {
            "Authorization": self.authorization_token(),
            "X-App-Key": self.creds.app_key,
        }

    def _post(self, path: str, body: dict, *, auth: bool = True) -> dict:
        self._require_sandbox_api()
        url = self.creds.base_url.rstrip("/") + path
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if auth:
            headers.update(self._auth_headers())
        else:
            headers["username"] = self.creds.username
            headers["password"] = self.creds.password
        logger.info("bKash sandbox POST %s", path)
        try:
            response = requests.post(url, json=body, headers=headers, timeout=TIMEOUT_SECONDS)
        except requests.Timeout as exc:
            raise BkashTimeout() from exc
        except requests.RequestException as exc:
            raise PaymentGatewayError("bKash request failed.", code="transport") from exc
        try:
            data = response.json()
        except ValueError as exc:
            raise PaymentGatewayError("bKash returned an invalid response.", code="invalid_response") from exc
        if not isinstance(data, dict):
            raise PaymentGatewayError("bKash returned an invalid response.", code="invalid_response")
        return data

    def _require_fields(self, data: dict, *fields: str) -> None:
        if data.get("errorMessageEn") or data.get("externalCode") or data.get("internalCode"):
            raise PaymentGatewayError(self._error_text(data), code="rejected")
        missing = [name for name in fields if not data.get(name)]
        if missing:
            raise PaymentGatewayError("bKash returned an invalid response.", code="invalid_response")

    def _error_text(self, data: dict) -> str:
        return redact_provider_text(
            data.get("errorMessageEn") or data.get("statusMessage") or "bKash rejected the request.",
            self.creds,
        )
