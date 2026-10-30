"""Abstract payment-gateway interface.

Concrete adapters (SSLCommerz, bKash, Nagad) implement this contract.
Views never talk to a provider SDK directly — they go through ``get_gateway()``.
"""


class PaymentGatewayError(Exception):
    """Raised when a gateway cannot initialise or validate a payment."""


class PaymentGateway:
    """Minimal adapter surface shared by every provider."""

    code = None  # PaymentMethod value

    # Capability declarations (override in subclasses). Code support ≠ available.
    supports_one_time = True
    supports_recurring = False
    supports_refund = False
    supports_cancel_recurring = False
    supports_webhook = True
    supports_validate = True

    def init_payment(self, donation, request):
        """Create a checkout session and return the redirect URL (str)."""
        raise NotImplementedError

    def validate_transaction(self, val_id, tran_id, amount, currency="BDT"):
        """Validate a completed payment. Return provider payload or None."""
        raise NotImplementedError

    def init_recurring_authorization(self, payable, request, *, subscription, schedule_day):
        raise PaymentGatewayError(f"{self.code} recurring: Not configured.")

    def cancel_recurring(self, subscription):
        raise PaymentGatewayError(f"{self.code} cancel recurring: Not configured.")

    def refund(self, *, transaction, amount, reason=""):
        raise PaymentGatewayError(f"{self.code} refund: Not configured.")
