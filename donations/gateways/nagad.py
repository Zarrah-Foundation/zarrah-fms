"""Nagad gateway adapter — never invents success without merchant credentials."""

from __future__ import annotations

import logging

from core.choices import PaymentMethod
from donations.gateways.base import PaymentGateway, PaymentGatewayError

logger = logging.getLogger(__name__)


class NagadGateway(PaymentGateway):
    """Direct Nagad adapter shell.

    Without merchant credentials every operation raises PaymentGatewayError.
    Does not return fake success payloads.
    """

    code = PaymentMethod.NAGAD

    def _require_configured(self):
        from donations.models import PaymentMethodConfig
        from donations.provider_capabilities import nagad_health

        health = nagad_health()
        if not health.one_time.configured:
            raise PaymentGatewayError("Nagad is not configured.")
        cfg = PaymentMethodConfig.objects.filter(method=PaymentMethod.NAGAD).first()
        if cfg is None or not cfg.is_enabled:
            raise PaymentGatewayError("Nagad is not configured.")
        if not cfg.api_app_key or not cfg.encrypted_api_secret:
            raise PaymentGatewayError("Nagad is not configured.")
        return cfg

    def init_payment(self, payable, request):
        self._require_configured()
        raise PaymentGatewayError(
            "Nagad one-time checkout is not live-verified for this merchant account."
        )

    def validate_transaction(self, val_id, tran_id, amount, currency="BDT"):
        self._require_configured()
        raise PaymentGatewayError(
            "Nagad payment validation is not live-verified for this merchant account."
        )

    def init_recurring_authorization(self, payable, request, *, subscription, schedule_day):
        raise PaymentGatewayError("Nagad recurring: Not configured.")

    def cancel_recurring(self, subscription):
        raise PaymentGatewayError("Nagad cancel recurring: Not configured.")

    def refund(self, *, transaction, amount, reason=""):
        raise PaymentGatewayError("Nagad refund: Not configured.")
