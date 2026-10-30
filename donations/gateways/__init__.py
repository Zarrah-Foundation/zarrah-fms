"""Payment gateway factory.

SSLCommerz is the only fully operational hosted checkout today.
bKash / Nagad adapters exist but refuse operations until credentials + live
verification are in place — they never silently route to SSLCommerz or MOCK.
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
