import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.choices import DonationStatus, PaymentMethod


class SubscriptionStatus(models.TextChoices):
    """Recurring donation lifecycle (general donations only — not membership)."""

    DRAFT = "DRAFT", "Draft"
    PENDING_AUTHORIZATION = "PENDING_AUTH", "Pending authorization"
    ACTIVE = "ACTIVE", "Active"
    PAUSED = "PAUSED", "Paused"
    PAYMENT_FAILED = "PAYMENT_FAILED", "Payment failed"
    SUSPENDED = "SUSPENDED", "Suspended"
    CANCEL_REQUESTED = "CANCEL_REQ", "Cancel requested"
    CANCELLED = "CANCELLED", "Cancelled"
    EXPIRED = "EXPIRED", "Expired"


class SubscriptionFrequency(models.TextChoices):
    # DAILY retained for legacy rows; WP3 UI/checkout only offers MONTHLY.
    DAILY = "DAILY", "Daily"
    MONTHLY = "MONTHLY", "Monthly"


class RecurringChargeStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PROCESSING = "PROCESSING", "Processing"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"
    SKIPPED = "SKIPPED", "Skipped"


class RecurringChargeKind(models.TextChoices):
    AUTHORIZATION = "AUTHORIZATION", "Authorization / setup"
    RECURRING = "RECURRING", "Recurring settlement"


class WebhookProcessingStatus(models.TextChoices):
    RECEIVED = "RECEIVED", "Received"
    PROCESSED = "PROCESSED", "Processed"
    IGNORED = "IGNORED", "Ignored"
    FAILED = "FAILED", "Failed"


class DonationCategory(models.Model):
    """CMS-managed donation cause / fund category."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name_bn = models.CharField(max_length=200, verbose_name=_("Name (Bangla)"))
    name_en = models.CharField(max_length=200, verbose_name=_("Name (English)"))
    slug = models.SlugField(unique=True)
    description_bn = models.TextField(null=True, blank=True, verbose_name=_("Description (Bangla)"))
    description_en = models.TextField(null=True, blank=True, verbose_name=_("Description (English)"))
    image = models.ImageField(
        upload_to="donations/categories/",
        null=True,
        blank=True,
        help_text=_("Optional cover image for the category card."),
    )
    icon = models.CharField(
        max_length=80,
        blank=True,
        default="bi-heart-fill",
        help_text=_("Bootstrap Icons class, e.g. bi-heart-fill, bi-book, bi-droplet."),
    )
    display_order = models.PositiveIntegerField(
        default=0,
        db_index=True,
        help_text=_("Lower numbers appear first on the donation page."),
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    is_featured = models.BooleanField(
        default=False,
        help_text=_("Highlight this category visually on the donation page."),
    )
    is_default = models.BooleanField(
        default=False,
        verbose_name=_("Default category"),
        help_text=_("Pre-selected in the donation form. Only one category can be default."),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "name_en"]
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["display_order"]),
        ]
        verbose_name_plural = "donation categories"

    def __str__(self):
        return self.name_en

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_default:
            type(self).objects.exclude(pk=self.pk).filter(is_default=True).update(is_default=False)

    @property
    def active_quick_amounts(self):
        return self.quick_amounts.filter(is_active=True).order_by("display_order", "amount")


class DonationQuickAmount(models.Model):
    """CMS-managed suggested donation amount for a category."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(
        DonationCategory,
        on_delete=models.CASCADE,
        related_name="quick_amounts",
    )
    amount = models.FloatField(help_text=_("Suggested amount in BDT."))
    label_en = models.CharField(
        max_length=80,
        blank=True,
        help_text=_("Optional English chip label (defaults to the amount)."),
    )
    label_bn = models.CharField(
        max_length=80,
        blank=True,
        help_text=_("Optional Bangla chip label (defaults to the amount)."),
    )
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "amount"]
        verbose_name = _("Quick donation amount")
        verbose_name_plural = _("Quick donation amounts")
        indexes = [
            models.Index(fields=["category", "is_active"]),
        ]

    def __str__(self):
        return f"{self.category.name_en}: {self.amount:g}"

    def clean(self):
        if self.amount is not None and self.amount <= 0:
            raise ValidationError({"amount": _("Amount must be greater than zero.")})

    def label(self, lang="en"):
        if lang == "bn":
            return self.label_bn or f"{self.amount:g}"
        return self.label_en or f"{self.amount:g}"


class ChannelKind(models.TextChoices):
    ONLINE_HOSTED = "ONLINE_HOSTED", "Online (hosted)"
    ONLINE_DIRECT = "ONLINE_DIRECT", "Online (direct)"
    MANUAL_OFFLINE = "MANUAL_OFFLINE", "Manual / offline"


class PaymentMethodConfig(models.Model):
    """CMS toggle, purpose gates, and optional encrypted gateway credentials.

    Environment variables remain the recommended production secret source.
    Database credentials (store password encrypted at rest) are opt-in via
    ``use_database_credentials`` and never exposed after save.
    """

    class TestStatus(models.TextChoices):
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"
        NOT_CONFIGURED = "NOT_CONFIGURED", "Not configured"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    method = models.CharField(max_length=20, choices=PaymentMethod.choices, unique=True)
    display_name = models.CharField(max_length=100, blank=True, default="")
    instructions_bn = models.TextField(blank=True, default="")
    instructions_en = models.TextField(blank=True, default="")
    account_details = models.CharField(
        max_length=255, blank=True, default="",
        help_text=_("Account/wallet number shown for manual payments."),
    )
    channel_kind = models.CharField(
        max_length=20,
        choices=ChannelKind.choices,
        default=ChannelKind.MANUAL_OFFLINE,
    )
    hosted_via = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        null=True,
        blank=True,
        help_text=_("If this channel is only available inside another hosted gateway."),
    )
    supports_one_time = models.BooleanField(default=True)
    supports_recurring = models.BooleanField(
        default=False,
        help_text=_("Must stay false unless a documented recurring integration is verified."),
    )
    is_enabled = models.BooleanField(
        default=True,
        help_text=_("Master switch for this payment method channel."),
    )
    enabled_for_donation = models.BooleanField(
        default=True,
        help_text=_("Allow this method for donation checkout."),
    )
    enabled_for_membership_fee = models.BooleanField(
        default=True,
        help_text=_("Allow this method for membership fee checkout."),
    )
    # --- Optional gateway credentials (SSLCommerz) ---
    store_id = models.CharField(
        max_length=120,
        blank=True,
        default="",
        help_text=_("SSLCommerz Store ID when using dashboard credentials."),
    )
    encrypted_store_password = models.TextField(
        blank=True,
        default="",
        help_text=_("Encrypted store password — never returned to browsers."),
    )
    use_database_credentials = models.BooleanField(
        default=False,
        help_text=_(
            "When enabled, use Store ID + encrypted password from this record instead of "
            "environment variables. Leave off to keep using production .env credentials."
        ),
    )
    is_sandbox = models.BooleanField(
        null=True,
        blank=True,
        help_text=_(
            "Sandbox (True) or Production (False). Null follows environment SSLCOMMERZ_IS_SANDBOX "
            "when using environment credentials."
        ),
    )
    production_confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Set when an administrator deliberately confirmed Production mode."),
    )
    admin_notes = models.TextField(blank=True, default="")
    last_tested_at = models.DateTimeField(null=True, blank=True)
    last_test_status = models.CharField(
        max_length=20,
        blank=True,
        default="",
        choices=TestStatus.choices,
    )
    last_test_message = models.CharField(max_length=300, blank=True, default="")
    # --- Recurring / refund / verification (additive; secrets write-only) ---
    encrypted_salt_key = models.TextField(
        blank=True,
        default="",
        help_text=_("Encrypted SSLCommerz SALT for EasyCheckout recurring — never shown."),
    )
    recurring_plan_refer = models.CharField(
        max_length=120,
        blank=True,
        default="",
        help_text=_("SSLCommerz merchant plan refer for recurring."),
    )
    merchant_recurring_enabled = models.BooleanField(
        default=False,
        help_text=_(
            "Administrator confirms the merchant account has recurring enabled. "
            "Does not alone mean recurring is production-verified."
        ),
    )
    refunds_enabled = models.BooleanField(
        default=False,
        help_text=_("Allow refund requests against this provider when API support exists."),
    )
    # Generic direct-provider credential slots (bKash / Nagad). Never rendered.
    api_app_key = models.CharField(max_length=200, blank=True, default="")
    encrypted_api_secret = models.TextField(blank=True, default="")
    api_username = models.CharField(max_length=200, blank=True, default="")
    encrypted_api_password = models.TextField(blank=True, default="")
    # Live-validation timestamps (set only after real success — never by unit tests alone).
    one_time_verified_at = models.DateTimeField(null=True, blank=True)
    recurring_auth_verified_at = models.DateTimeField(null=True, blank=True)
    recurring_charge_verified_at = models.DateTimeField(null=True, blank=True)
    refund_verified_at = models.DateTimeField(null=True, blank=True)
    ipn_verified_at = models.DateTimeField(null=True, blank=True)
    last_ipn_at = models.DateTimeField(null=True, blank=True)
    last_ipn_status = models.CharField(max_length=20, blank=True, default="")
    display_order = models.PositiveIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "method"]

    def __str__(self):
        return self.display_name or self.get_method_display()

    def set_store_password(self, raw_password: str) -> None:
        """Encrypt and store password. Empty string leaves existing password unchanged."""
        from donations.credential_crypto import encrypt_secret

        if raw_password:
            self.encrypted_store_password = encrypt_secret(raw_password)

    def clear_store_password(self) -> None:
        self.encrypted_store_password = ""

    def set_salt_key(self, raw_salt: str) -> None:
        from donations.credential_crypto import encrypt_secret

        if raw_salt:
            self.encrypted_salt_key = encrypt_secret(raw_salt)

    def clear_salt_key(self) -> None:
        self.encrypted_salt_key = ""

    def get_salt_key(self) -> str:
        from donations.credential_crypto import decrypt_secret

        if not self.encrypted_salt_key:
            return ""
        try:
            return decrypt_secret(self.encrypted_salt_key)
        except Exception:
            return ""

    def set_api_secret(self, raw: str) -> None:
        from donations.credential_crypto import encrypt_secret

        if raw:
            self.encrypted_api_secret = encrypt_secret(raw)

    def set_api_password(self, raw: str) -> None:
        from donations.credential_crypto import encrypt_secret

        if raw:
            self.encrypted_api_password = encrypt_secret(raw)

    def clear_api_secrets(self) -> None:
        self.encrypted_api_secret = ""
        self.encrypted_api_password = ""


class TransactionPurpose(models.TextChoices):
    DONATION = "DONATION", "Donation"
    MEMBERSHIP_FEE = "MEMBERSHIP_FEE", "Membership fee"
    # Short code keeps CharField(max_length=20); accounting label is registration fee.
    MEMBERSHIP_REGISTRATION = "MEMBERSHIP_REG", "Membership registration fee"


class Transaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session_id = models.CharField(max_length=255, unique=True)
    tran_id = models.CharField(max_length=255, unique=True)
    val_id = models.CharField(max_length=255, null=True, blank=True)
    amount = models.FloatField()
    currency = models.CharField(max_length=10, default="BDT")
    status = models.CharField(
        max_length=20, choices=DonationStatus.choices, default=DonationStatus.PENDING
    )
    purpose = models.CharField(
        max_length=32,
        choices=TransactionPurpose.choices,
        default=TransactionPurpose.DONATION,
        db_index=True,
    )
    # Which gateway created / owns this transaction. Defaults to SSLCommerz to
    # stay compatible with existing rows; future adapters write their own value.
    gateway = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.SSLCOMMERZ,
        db_index=True,
    )
    cus_name = models.CharField(max_length=200)
    cus_email = models.EmailField(null=True, blank=True)
    cus_phone = models.CharField(max_length=20, null=True, blank=True)
    bank_tran_id = models.CharField(max_length=255, null=True, blank=True)
    error = models.TextField(null=True, blank=True)
    card_type = models.CharField(max_length=50, null=True, blank=True)
    card_no = models.CharField(max_length=50, null=True, blank=True)
    card_issuer = models.CharField(max_length=100, null=True, blank=True)
    risk_level = models.CharField(max_length=50, null=True, blank=True)
    validated_on = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.tran_id


class Donation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    donor_name = models.CharField(max_length=200)
    donor_email = models.EmailField(null=True, blank=True)
    donor_phone = models.CharField(max_length=20, null=True, blank=True)
    # Legacy address fields retained for existing rows; no longer collected on the form.
    donor_address = models.TextField(null=True, blank=True)
    donor_city = models.CharField(max_length=100, null=True, blank=True)
    donor_country = models.CharField(max_length=100, null=True, blank=True)
    on_behalf_of = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name=_("Donate on behalf of"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="donations",
    )
    amount = models.FloatField()
    currency = models.CharField(max_length=10, default="BDT")
    category = models.ForeignKey(
        DonationCategory, on_delete=models.CASCADE, related_name="donations"
    )
    message = models.TextField(null=True, blank=True)
    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.SSLCOMMERZ
    )
    status = models.CharField(
        max_length=20, choices=DonationStatus.choices, default=DonationStatus.PENDING
    )
    transaction = models.OneToOneField(
        Transaction, on_delete=models.CASCADE, related_name="donation"
    )
    subscription = models.ForeignKey(
        "DonationSubscription",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="donations",
        help_text=_("Set for recurring-charge donations; null for one-time gifts."),
    )
    is_anonymous = models.BooleanField(default=False)
    receipt_number = models.CharField(
        max_length=40,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_("Receipt Number"),
    )
    receipt_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        return f"{self.display_name} - {self.amount} {self.currency}"

    @property
    def display_name(self):
        if self.is_anonymous:
            return "Anonymous"
        return self.donor_name or "Anonymous"

    @property
    def transaction_id(self):
        try:
            return self.transaction.tran_id
        except Transaction.DoesNotExist:
            return ""


class DonationSubscription(models.Model):
    """General recurring donation agreement (not membership AutoPay)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscriptions",
    )
    category = models.ForeignKey(
        DonationCategory, on_delete=models.CASCADE, related_name="subscriptions"
    )
    donor_name = models.CharField(max_length=200)
    donor_email = models.EmailField(null=True, blank=True)
    donor_phone = models.CharField(max_length=20, blank=True, default="")
    amount = models.FloatField()
    currency = models.CharField(max_length=10, default="BDT")
    frequency = models.CharField(
        max_length=10,
        choices=SubscriptionFrequency.choices,
        default=SubscriptionFrequency.MONTHLY,
    )
    payment_gateway = models.CharField(
        max_length=50,
        choices=PaymentMethod.choices,
        default=PaymentMethod.SSLCOMMERZ,
    )
    # Provider-safe recurring reference (e.g. SSLCommerz subscription_id). Never store PAN/PIN.
    payment_token = models.CharField(max_length=255, null=True, blank=True)
    gateway_subscription_ref = models.CharField(max_length=255, null=True, blank=True)
    gateway_plan_refer = models.CharField(max_length=120, blank=True, default="")
    status = models.CharField(
        max_length=32,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.DRAFT,
        db_index=True,
    )
    next_billing = models.DateTimeField(null=True, blank=True)
    last_billed = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_failure_at = models.DateTimeField(null=True, blank=True)
    last_failure_reason = models.CharField(max_length=300, blank=True, default="")
    consecutive_failures = models.PositiveSmallIntegerField(default=0)
    activated_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.CharField(max_length=300, blank=True, default="")
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cancelled_donation_subscriptions",
    )
    # Cryptographically random guest management secret (hashed at rest via signing salt + store).
    management_token = models.CharField(max_length=64, unique=True, null=True, blank=True, db_index=True)
    management_token_expires_at = models.DateTimeField(null=True, blank=True)
    message = models.TextField(null=True, blank=True)
    is_anonymous = models.BooleanField(default=False)
    # Soft claim lock for reconciliation workers.
    processing_locked_at = models.DateTimeField(null=True, blank=True)
    processing_lock_token = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["user"]),
            models.Index(fields=["next_billing"]),
            models.Index(fields=["gateway_subscription_ref"]),
        ]

    def __str__(self):
        return f"{self.donor_name} - {self.frequency} ৳{self.amount:g} ({self.status})"


class DonationRecurringCharge(models.Model):
    """One authorization or settlement attempt for a DonationSubscription."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(
        DonationSubscription,
        on_delete=models.CASCADE,
        related_name="charges",
    )
    kind = models.CharField(
        max_length=20,
        choices=RecurringChargeKind.choices,
        default=RecurringChargeKind.RECURRING,
    )
    attempt_number = models.PositiveIntegerField(default=1)
    amount = models.FloatField()
    currency = models.CharField(max_length=10, default="BDT")
    status = models.CharField(
        max_length=20,
        choices=RecurringChargeStatus.choices,
        default=RecurringChargeStatus.PENDING,
        db_index=True,
    )
    provider = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.SSLCOMMERZ,
    )
    provider_reference = models.CharField(max_length=255, blank=True, default="")
    idempotency_key = models.CharField(max_length=120, unique=True)
    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recurring_charge",
    )
    donation = models.OneToOneField(
        Donation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recurring_charge",
    )
    failure_category = models.CharField(max_length=80, blank=True, default="")
    failure_reason = models.CharField(max_length=300, blank=True, default="")
    gateway_event = models.ForeignKey(
        "GatewayWebhookEvent",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="charges",
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["subscription", "status"]),
            models.Index(fields=["provider_reference"]),
        ]

    def __str__(self):
        return f"Charge {self.pk} ({self.kind}/{self.status})"


class GatewayWebhookEvent(models.Model):
    """Durable, idempotent gateway IPN/webhook receipt (sanitized)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=20, choices=PaymentMethod.choices, db_index=True)
    event_type = models.CharField(max_length=80, blank=True, default="")
    external_event_id = models.CharField(max_length=255, db_index=True)
    processing_status = models.CharField(
        max_length=20,
        choices=WebhookProcessingStatus.choices,
        default=WebhookProcessingStatus.RECEIVED,
        db_index=True,
    )
    subscription = models.ForeignKey(
        DonationSubscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="webhook_events",
    )
    charge = models.ForeignKey(
        DonationRecurringCharge,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="webhook_events",
    )
    # Sanitized metadata only — never store passwords/PAN/PIN.
    payload_digest = models.CharField(max_length=64, blank=True, default="")
    safe_payload = models.JSONField(null=True, blank=True)
    error_message = models.CharField(max_length=300, blank=True, default="")
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "external_event_id"],
                name="uniq_gateway_webhook_provider_event",
            )
        ]
        ordering = ["-received_at"]

    def __str__(self):
        return f"{self.provider}:{self.external_event_id} ({self.processing_status})"

class RefundStatus(models.TextChoices):
    REQUESTED = 'REQUESTED', 'Requested'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    PROCESSING = 'PROCESSING', 'Processing'
    REFUNDED = 'REFUNDED', 'Refunded'
    FAILED = 'FAILED', 'Failed'


class RefundRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction = models.ForeignKey(Transaction, on_delete=models.PROTECT, related_name='refund_requests')
    amount = models.FloatField()
    currency = models.CharField(max_length=10, default='BDT')
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=RefundStatus.choices, default=RefundStatus.REQUESTED, db_index=True)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='refund_requests_made')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='refund_requests_approved')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default='')
    provider = models.CharField(max_length=20, choices=PaymentMethod.choices)
    provider_reference = models.CharField(max_length=255, blank=True, default='')
    provider_message = models.CharField(max_length=300, blank=True, default='')
    idempotency_key = models.CharField(max_length=120, unique=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['status']), models.Index(fields=['provider'])]

    def __str__(self):
        return f'Refund {self.pk} ({self.status})'


class PaymentOpsEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='payment_ops_events')
    action = models.CharField(max_length=80, db_index=True)
    provider = models.CharField(max_length=20, blank=True, default='')
    entity = models.CharField(max_length=80, blank=True, default='')
    entity_id = models.CharField(max_length=80, blank=True, default='')
    message = models.CharField(max_length=400, blank=True, default='')
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.action} @ {self.created_at}'


class PaymentSystemSettings(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    one_time_donation_enabled = models.BooleanField(default=True)
    recurring_donation_enabled = models.BooleanField(default=True)
    min_donation_amount = models.FloatField(default=1.0)
    max_donation_amount = models.FloatField(default=1_000_000.0)
    allowed_recurring_frequencies = models.CharField(max_length=80, default='MONTHLY')
    public_membership_fee_enabled = models.BooleanField(default=True)
    membership_autopay_enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    class Meta:
        verbose_name_plural = 'payment system settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return 'Payment system settings'
