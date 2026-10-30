from django.db import models


class DonationStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    # Stored as COMPLETED for backward compatibility; shown as Success in UI/admin.
    COMPLETED = "COMPLETED", "Success"
    FAILED = "FAILED", "Failed"
    CANCELLED = "CANCELLED", "Cancelled"
    REFUNDED = "REFUNDED", "Refunded"


class PaymentMethod(models.TextChoices):
    """Supported payment channels.

    Checkout currently routes through SSLCommerz only; the extra values are
    registered so the data model and future gateway adapters can grow without
    another schema change. Do not expose non-SSLCommerz methods in the public
    donation form until their adapters are implemented.
    """

    SSLCOMMERZ = "SSLCOMMERZ", "SSLCommerz"
    BKASH = "BKASH", "bKash"
    NAGAD = "NAGAD", "Nagad"
    ROCKET = "ROCKET", "Rocket"
    BANK_TRANSFER = "BANK_TRANSFER", "Bank Transfer"
    CASH = "CASH", "Cash"
    OTHER = "OTHER", "Other"
