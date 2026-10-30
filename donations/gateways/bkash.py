"""bKash gateway adapter — never invents success without merchant credentials."""

from __future__ import annotations

import logging

from core.choices import PaymentMethod
from donations.gateways.base import PaymentGateway, PaymentGatewayError

logger = logging.getLogger(__name__)


class BkashGateway(PaymentGateway):
    """Direct bKash adapter shell.

    Production use requires merchant credentials + approved API capability.
    Without them every operation raises PaymentGatewayError (Not configured).
    Does not return fake success payloads.
    """

    code = PaymentMethod.BKASH

    def _require_configured(self):
        from donations.models import PaymentMethodConfig
        from donations.provider_capabilities import bkash_health

        health = bkash_health()
        if not health.one_time.configured:
            raise PaymentGatewayError("bKash is not configured.")
        cfg = PaymentMethodConfig.objects.filter(method=PaymentMethod.BKASH).first()
        if cfg is None or not cfg.is_enabled:
            raise PaymentGatewayError("bKash is not configured.")
        if not cfg.api_app_key or not cfg.encrypted_api_secret:
            raise PaymentGatewayError("bKash is not configured.")
        return cfg

    def init_payment(self, payable, request):
        self._require_configured()
        # Official Create Payment API must be wired with verified merchant docs.
        raise PaymentGatewayError(
            "bKash one-time checkout is not live-verified for this merchant account."
        )

    def validate_transaction(self, val_id, tran_id, amount, currency="BDT"):
        self._require_configured()
        raise PaymentGatewayError(
            "bKash payment validation is not live-verified for this merchant account."
        )

    def init_recurring_authorization(self, payable, request, *, subscription, schedule_day):
        raise PaymentGatewayError("bKash recurring: Not configured.")

    def cancel_recurring(self, subscription):
        raise PaymentGatewayError("bKash cancel recurring: Not configured.")

    def refund(self, *, transaction, amount, reason=""):
        raise PaymentGatewayError("bKash refund: Not configured.")
