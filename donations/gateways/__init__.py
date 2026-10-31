"""Payment gateway factory.

SSLCommerz remains the hosted checkout used for live-style one-time payments.
bKash Tokenized Checkout v2 runs in sandbox only and refuses live hosts.
Nagad still refuses every operation. Adapters never fall back to MOCK.
"""

from core.choices import PaymentMethod
from donations.gateways.base import PaymentGateway, PaymentGatewayError
from donations.gateways.bkash import BkashGateway
from donations.gateways.nagad import NagadGateway
from donations.gateways.sslcommerz import SSLCommerzGateway

_REGISTRY = {
    PaymentMethod.SSLCOMMERZ: SSLCommerzGateway,
    PaymentMethod.BKASH: BkashGateway,
    PaymentMethod.NAGAD: NagadGateway,
}


def get_gateway(method=None):
    """Return a gateway adapter instance for ``method``.

    Falls back to SSLCommerz when method is omitted (legacy callers).
    """
    key = method or PaymentMethod.SSLCOMMERZ
    if key == PaymentMethod.ROCKET:
        raise PaymentGatewayError(
            f"Payment gateway '{key}' is registered but not yet implemented."
        )
    if key == PaymentMethod.BANK_TRANSFER:
        raise PaymentGatewayError(
            "Bank transfer is a manual offline channel, not an online gateway."
        )
    cls = _REGISTRY.get(key)
    if cls is None:
        raise PaymentGatewayError(f"Unknown payment gateway: {key}")
    return cls()


__all__ = [
    "PaymentGateway",
    "PaymentGatewayError",
    "SSLCommerzGateway",
    "BkashGateway",
    "NagadGateway",
    "get_gateway",
]
