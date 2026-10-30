"""Payment Management Center aggregates and recurring setup status.

Figures come from the database. Secret values are never included.
"""

from __future__ import annotations

from django.conf import settings
from django.db.models import Count, Q, Sum
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from core.choices import DonationStatus, PaymentMethod
from donations.credential_crypto import has_encrypted_password
from donations.models import (
    Donation,
    DonationRecurringCharge,
    DonationSubscription,
    GatewayWebhookEvent,
    PaymentMethodConfig,
    PaymentSystemSettings,
    RefundRequest,
    RefundStatus,
    SubscriptionStatus,
    Transaction,
)

# Distinct capability conditions. Do not collapse these into one "Active" flag.
NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
NOT_CONFIGURED = "NOT_CONFIGURED"
CONFIGURED = "CONFIGURED"
PENDING_MERCHANT_APPROVAL = "PENDING_MERCHANT_APPROVAL"
VERIFIED_IN_SANDBOX = "VERIFIED_IN_SANDBOX"
VERIFIED_IN_PRODUCTION = "VERIFIED_IN_PRODUCTION"
ENABLED = "ENABLED"
DISABLED = "DISABLED"
FAILED = "FAILED"


def operational_metrics() -> dict:
    """Live operational totals. Empty tables return zero, never invented amounts."""
    today = timezone.localdate()
    completed = Q(status=DonationStatus.COMPLETED)
    donations_today = Donation.objects.filter(completed, created_at__date=today).aggregate(
        total=Sum("amount"), count=Count("id")
    )
    donations_month = Donation.objects.filter(
        completed,
        created_at__year=today.year,
        created_at__month=today.month,
    ).aggregate(total=Sum("amount"), count=Count("id"))
    txn_stats = Transaction.objects.aggregate(
        total=Count("id"),
        completed=Count("id", filter=Q(status=DonationStatus.COMPLETED)),
        failed=Count("id", filter=Q(status=DonationStatus.FAILED)),
        pending=Count("id", filter=Q(status=DonationStatus.PENDING)),
        cancelled=Count("id", filter=Q(status=DonationStatus.CANCELLED)),
    )
    sub_stats = DonationSubscription.objects.aggregate(
        active=Count("id", filter=Q(status=SubscriptionStatus.ACTIVE)),
        failed=Count("id", filter=Q(status=SubscriptionStatus.PAYMENT_FAILED)),
        suspended=Count("id", filter=Q(status=SubscriptionStatus.SUSPENDED)),
    )
    failed_charges = DonationRecurringCharge.objects.filter(
        status="FAILED"
    ).count()
    refunds = RefundRequest.objects.aggregate(
        pending=Count("id", filter=Q(status=RefundStatus.REQUESTED)),
        processed=Count("id", filter=Q(status=RefundStatus.REFUNDED)),
        failed=Count("id", filter=Q(status=RefundStatus.FAILED)),
    )
    webhook_failed = GatewayWebhookEvent.objects.filter(processing_status="FAILED").count()

    from members.models import MembershipAutoPay, MembershipFee, MembershipRegistrationFee

    outstanding = MembershipFee.objects.filter(status=DonationStatus.PENDING).aggregate(
        total=Sum("amount"), count=Count("id")
    )
    registration = MembershipRegistrationFee.objects.filter(
        status=DonationStatus.COMPLETED
    ).aggregate(total=Sum("amount"), count=Count("id"))
    autopay_active = MembershipAutoPay.objects.filter(is_enabled=True).count()

    return {
        "donations_today_total": donations_today["total"] or 0,
        "donations_today_count": donations_today["count"] or 0,
        "donations_month_total": donations_month["total"] or 0,
        "donations_month_count": donations_month["count"] or 0,
        "txn_stats": txn_stats,
        "sub_stats": sub_stats,
        "failed_recurring_charges": failed_charges,
        "refunds_pending": refunds["pending"] or 0,
        "refunds_processed": refunds["processed"] or 0,
        "refunds_failed": refunds["failed"] or 0,
        "webhook_failed": webhook_failed,
        "outstanding_fees_total": outstanding["total"] or 0,
        "outstanding_fees_count": outstanding["count"] or 0,
        "registration_collected_total": registration["total"] or 0,
        "registration_collected_count": registration["count"] or 0,
        "autopay_active": autopay_active,
        "due_count": DonationSubscription.objects.filter(
            status=SubscriptionStatus.ACTIVE, next_billing__lte=timezone.now()
        ).count(),
    }


def _abs(name: str) -> str:
    try:
        path = reverse(name)
    except NoReverseMatch:
        return ""
    base = (getattr(settings, "SITE_URL", "") or "").rstrip("/")
    return f"{base}{path}" if base else path


def _verified_state(*, verified: bool, sandbox: bool | None) -> str:
    if not verified:
        return CONFIGURED
    if sandbox is False:
        return VERIFIED_IN_PRODUCTION
    return VERIFIED_IN_SANDBOX


def _ssl_card() -> dict:
    from donations.credential_service import public_credential_status, resolve_sslcommerz_credentials
    from donations.gateway_capabilities import recurring_checkout_allowed
    from donations.recurring_config import sslcommerz_recurring_configured

    creds = resolve_sslcommerz_credentials()
    pub = public_credential_status()
    rec = sslcommerz_recurring_configured()
    cfg = PaymentMethodConfig.objects.filter(method=PaymentMethod.SSLCOMMERZ).first()
    settings_obj = PaymentSystemSettings.load()
    checkout_ok, checkout_reason = recurring_checkout_allowed(PaymentMethod.SSLCOMMERZ)
    sandbox = pub.get("is_sandbox")
    has_salt = bool(rec.has_salt)
    has_plan = bool(rec.plan_refer)
    merchant_flag = bool(cfg and cfg.merchant_recurring_enabled)
    db_recurring_material = bool(cfg and (cfg.encrypted_salt_key or cfg.recurring_plan_refer))
    auth_verified = bool(cfg and cfg.recurring_auth_verified_at)
    charge_verified = bool(cfg and cfg.recurring_charge_verified_at)
    recurring_verified = auth_verified and charge_verified
    one_time_verified = bool(cfg and cfg.one_time_verified_at)

    if cfg is not None and not cfg.is_enabled:
        one_time_state = DISABLED
    elif not creds.configured:
        one_time_state = NOT_CONFIGURED
    elif one_time_verified:
        one_time_state = _verified_state(verified=True, sandbox=sandbox)
    else:
        one_time_state = CONFIGURED

    if cfg is not None and not cfg.is_enabled:
        recurring_state = DISABLED
    elif not rec.configured:
        recurring_state = NOT_CONFIGURED
    elif db_recurring_material and not merchant_flag:
        recurring_state = PENDING_MERCHANT_APPROVAL
    elif recurring_verified:
        recurring_state = _verified_state(verified=True, sandbox=sandbox)
    else:
        recurring_state = CONFIGURED

    if not settings_obj.recurring_donation_enabled and recurring_state not in (
        NOT_CONFIGURED,
        DISABLED,
    ):
        accepting_new = False
    else:
        accepting_new = bool(checkout_ok)

    connection_state = NOT_CONFIGURED if not creds.configured else CONFIGURED
    if cfg and cfg.last_test_status == "SUCCESS":
        connection_state = _verified_state(verified=True, sandbox=sandbox)
    elif cfg and cfg.last_test_status == "FAILED":
        connection_state = FAILED

    refund_state = NOT_CONFIGURED
    if cfg and cfg.refunds_enabled and creds.configured:
        refund_state = (
            _verified_state(verified=True, sandbox=sandbox)
            if cfg.refund_verified_at
            else CONFIGURED
        )

    checklist = [
        {"step": 1, "label": "Store ID and store password are configured", "done": creds.configured},
        {"step": 2, "label": "Sandbox or production mode is selected", "done": sandbox is not None},
        {
            "step": 3,
            "label": "Merchant confirms recurring is enabled on the SSLCommerz store",
            "done": merchant_flag or (rec.configured and rec.source == "env"),
        },
        {"step": 4, "label": "SALT key is stored (environment or encrypted database)", "done": has_salt},
        {"step": 5, "label": "Recurring plan reference is stored", "done": has_plan},
        {"step": 6, "label": "Public recurring IPN URL is known", "done": bool(_abs("donation-recurring-ipn"))},
        {
            "step": 7,
            "label": "Connection test succeeded (no payment is created)",
            "done": bool(cfg and cfg.last_test_status == "SUCCESS"),
        },
        {
            "step": 8,
            "label": "Sandbox or production recurring authorization was verified",
            "done": auth_verified,
        },
        {
            "step": 9,
            "label": "A real scheduled settlement IPN was verified",
            "done": charge_verified,
        },
        {
            "step": 10,
            "label": "New recurring donations are enabled in Payment Settings",
            "done": bool(settings_obj.recurring_donation_enabled),
        },
    ]

    return {
        "method": PaymentMethod.SSLCOMMERZ,
        "title": "SSLCommerz Recurring",
        "summary": (
            "SSLCommerz schedules card recurring after donor authorization. "
            "Django records IPN settlements. It does not run a separate card-charging job."
        ),
        "one_time_state": one_time_state,
        "recurring_state": recurring_state,
        "refund_state": refund_state,
        "cancel_state": NOT_IMPLEMENTED,
        "connection_state": connection_state,
        "environment": "Sandbox" if sandbox else "Production" if sandbox is False else "Unknown",
        "credential_source": pub.get("source") or "",
        "store_id_masked": pub.get("store_id_masked") or "",
        "has_store_password": bool(creds.configured),
        "has_saved_database_password": bool(cfg and pub.get("has_saved_secret")),
        "has_salt": has_salt,
        "salt_source": rec.source if has_salt else "",
        "has_plan": has_plan,
        "plan_refer": rec.plan_refer if has_plan else "",
        "merchant_recurring_enabled": merchant_flag,
        "cms_recurring_enabled": bool(settings_obj.recurring_donation_enabled),
        "cms_autopay_enabled": bool(settings_obj.membership_autopay_enabled),
        "accepting_new_subscriptions": accepting_new,
        "accepting_new_reason": "" if accepting_new else (checkout_reason or rec.reason),
        "ipn_url": _abs("donation-recurring-ipn"),
        "one_time_ipn_url": _abs("donation-ipn"),
        "membership_ipn_url": _abs("membership-fee-pay-ipn"),
        "last_tested_at": cfg.last_tested_at if cfg else None,
        "last_test_status": (cfg.last_test_status if cfg else "") or "",
        "last_test_message": ((cfg.last_test_message if cfg else "") or "")[:200],
        "recurring_auth_verified_at": cfg.recurring_auth_verified_at if cfg else None,
        "recurring_charge_verified_at": cfg.recurring_charge_verified_at if cfg else None,
        "ipn_verified_at": cfg.ipn_verified_at if cfg else None,
        "configure_url_name": "dashboard-payment-method-configure" if cfg else "dashboard-payment-methods",
        "configure_pk": cfg.pk if cfg else None,
        "test_available": bool(cfg),
        "checklist": checklist,
        "merchant_must_supply": [],
        "notes": [
            "One-time checkout stays available when recurring is not configured.",
            "Provider cancel API is not confirmed.",
            "Refund execution stays unverified until a live provider confirmation is recorded.",
            "LIVE VALIDATION PENDING until public HTTPS staging succeeds.",
        ],
    }


def _direct_wallet_card(*, method: str, title: str, recurring_supported: bool) -> dict:
    cfg = PaymentMethodConfig.objects.filter(method=method).first()
    has_app_key = bool(cfg and (cfg.api_app_key or "").strip())
    has_secret = bool(cfg and has_encrypted_password(cfg.encrypted_api_secret))
    has_username = bool(cfg and (cfg.api_username or "").strip())
    has_password = bool(cfg and has_encrypted_password(cfg.encrypted_api_password))
    creds_present = has_app_key and has_secret
    enabled = bool(cfg and cfg.is_enabled)

    # Direct HTTP contracts are not wired. Saved credentials do not make checkout live.
    one_time_state = NOT_IMPLEMENTED
    recurring_state = NOT_IMPLEMENTED if not recurring_supported else NOT_CONFIGURED
    if cfg is not None and not enabled:
        connection_state = DISABLED
    elif creds_present:
        connection_state = CONFIGURED
    else:
        connection_state = NOT_CONFIGURED

    if method == PaymentMethod.BKASH:
        must_supply = [
            "bKash merchant App Key, App Secret, username, and password from the official merchant portal.",
            "Written merchant approval for Tokenized Checkout (create, execute, query).",
            "Sandbox and production base URLs supplied by bKash for this merchant.",
            "Callback URL registered with bKash for this site.",
            "Separate Subscription Payment API approval if automatic recurring is required.",
            "Refund API approval if provider refunds are required.",
        ]
        summary = (
            "Direct bKash checkout is not wired to a verified merchant API. "
            "A bKash button inside SSLCommerz hosted checkout is not this integration. "
            "Subscription recurring stays unavailable until bKash grants the Subscription Payment API."
        )
    else:
        must_supply = [
            "Nagad merchant ID and the official key material from Nagad merchant onboarding.",
            "Current official checkout, verify, and callback contract for this merchant.",
            "Sandbox credentials and the public callback URL Nagad must call.",
            "A written Nagad product that supports automatic recurring, if recurring is required. "
            "One-time checkout does not imply recurring.",
            "Refund API documentation if provider refunds are required.",
        ]
        summary = (
            "Direct Nagad checkout is not wired to a verified merchant contract. "
            "Recurring is not implemented. Nagad must not be offered as a recurring provider."
        )

    checklist = [
        {"step": 1, "label": "Merchant credentials saved (write-only secrets)", "done": creds_present},
        {"step": 2, "label": "Username present", "done": has_username},
        {"step": 3, "label": "API password saved", "done": has_password},
        {"step": 4, "label": "Official API contract implemented in this application", "done": False},
        {"step": 5, "label": "Merchant approval recorded", "done": False},
        {"step": 6, "label": "Sandbox payment verified", "done": bool(cfg and cfg.one_time_verified_at)},
        {"step": 7, "label": "Capability enabled for public checkout", "done": False},
    ]
    return {
        "method": method,
        "title": title,
        "summary": summary,
        "one_time_state": one_time_state,
        "recurring_state": recurring_state,
        "refund_state": NOT_IMPLEMENTED,
        "cancel_state": NOT_IMPLEMENTED,
        "connection_state": connection_state,
        "environment": (
            "Sandbox" if cfg and cfg.is_sandbox else "Production" if cfg and cfg.is_sandbox is False else "Unknown"
        ),
        "credential_source": "database" if creds_present else "",
        "store_id_masked": "",
        "has_store_password": False,
        "has_saved_database_password": has_password,
        "has_app_key": has_app_key,
        "has_api_secret": has_secret,
        "has_username": has_username,
        "has_salt": False,
        "salt_source": "",
        "has_plan": False,
        "plan_refer": "",
        "merchant_recurring_enabled": False,
        "cms_recurring_enabled": False,
        "cms_autopay_enabled": False,
        "accepting_new_subscriptions": False,
        "accepting_new_reason": "Direct recurring API is not implemented.",
        "ipn_url": "",
        "one_time_ipn_url": "",
        "membership_ipn_url": "",
        "last_tested_at": cfg.last_tested_at if cfg else None,
        "last_test_status": (cfg.last_test_status if cfg else "") or "",
        "last_test_message": ((cfg.last_test_message if cfg else "") or "")[:200],
        "recurring_auth_verified_at": None,
        "recurring_charge_verified_at": None,
        "ipn_verified_at": cfg.ipn_verified_at if cfg else None,
        "configure_url_name": "dashboard-payment-method-configure" if cfg else "dashboard-payment-methods",
        "configure_pk": cfg.pk if cfg else None,
        "test_available": False,
        "checklist": checklist,
        "merchant_must_supply": must_supply,
        "notes": [
            "Credentials, when saved, stay encrypted and are not shown here.",
            "Public checkout continues to use SSLCommerz only.",
            "LIVE VALIDATION PENDING.",
        ],
    }


def recurring_setup_cards() -> list[dict]:
    return [
        _ssl_card(),
        _direct_wallet_card(
            method=PaymentMethod.BKASH,
            title="bKash Subscription Payment",
            recurring_supported=False,
        ),
        _direct_wallet_card(
            method=PaymentMethod.NAGAD,
            title="Nagad",
            recurring_supported=False,
        ),
    ]


def _purpose_one_time_state(card: dict, *, purpose_enabled: bool) -> str:
    """SSLCommerz purpose gate. Direct wallets stay unimplemented."""
    if card["method"] != PaymentMethod.SSLCOMMERZ:
        return NOT_IMPLEMENTED
    state = card["one_time_state"]
    if state in (NOT_CONFIGURED, DISABLED, FAILED):
        return state
    if not purpose_enabled:
        return DISABLED
    return state


def purpose_capability_rows() -> list[dict]:
    """Purpose-specific states. A hosted wallet inside SSLCommerz is not a direct provider."""
    from donations.gateway_capabilities import autopay_activation_allowed, online_checkout_allowed
    from donations.models import TransactionPurpose

    cards = {card["method"]: card for card in recurring_setup_cards()}
    rows = []
    for method, label in (
        (PaymentMethod.SSLCOMMERZ, "SSLCommerz"),
        (PaymentMethod.BKASH, "bKash"),
        (PaymentMethod.NAGAD, "Nagad"),
    ):
        card = cards[method]
        cfg = PaymentMethodConfig.objects.filter(method=method).first()
        donation_enabled = cfg is None or cfg.enabled_for_donation
        fee_enabled = cfg is None or cfg.enabled_for_membership_fee
        donation_ok, _donation_err = online_checkout_allowed(
            method, TransactionPurpose.DONATION
        )
        fee_ok, _fee_err = online_checkout_allowed(
            method, TransactionPurpose.MEMBERSHIP_FEE
        )
        reg_ok, _reg_err = online_checkout_allowed(
            method, TransactionPurpose.MEMBERSHIP_REGISTRATION
        )
        autopay_ok, _autopay_msg, autopay_mode = autopay_activation_allowed()
        if method != PaymentMethod.SSLCOMMERZ:
            autopay_state = NOT_IMPLEMENTED
            autopay_mode = "OFF"
            gateway_autopay = False
        elif not PaymentSystemSettings.load().membership_autopay_enabled:
            autopay_state = DISABLED
            gateway_autopay = False
        elif autopay_mode == "MOCK":
            autopay_state = NOT_CONFIGURED
            gateway_autopay = False
        else:
            autopay_state = card["recurring_state"]
            gateway_autopay = bool(autopay_ok and autopay_mode == "GATEWAY")
        rows.append(
            {
                "method": method,
                "label": label,
                "donation_one_time": _purpose_one_time_state(
                    card, purpose_enabled=donation_enabled
                ),
                "donation_one_time_live": donation_ok,
                "donation_recurring": card["recurring_state"]
                if method == PaymentMethod.SSLCOMMERZ
                else NOT_IMPLEMENTED,
                "donation_recurring_live": bool(
                    method == PaymentMethod.SSLCOMMERZ and card["accepting_new_subscriptions"]
                ),
                "membership_one_time": _purpose_one_time_state(
                    card, purpose_enabled=fee_enabled
                ),
                "membership_one_time_live": fee_ok,
                "registration_one_time_live": reg_ok,
                "membership_autopay": autopay_state,
                "membership_autopay_live": gateway_autopay,
                "autopay_mode": autopay_mode,
                "refund": card["refund_state"],
                "code_implemented": method == PaymentMethod.SSLCOMMERZ,
                "credentials_configured": card["connection_state"]
                not in (NOT_CONFIGURED, NOT_IMPLEMENTED, DISABLED),
                "merchant_approval": card["recurring_state"]
                not in (NOT_IMPLEMENTED, NOT_CONFIGURED, PENDING_MERCHANT_APPROVAL, DISABLED),
                "sandbox_tested": card["recurring_state"] == VERIFIED_IN_SANDBOX
                or card["one_time_state"] == VERIFIED_IN_SANDBOX,
                "production_verified": card["one_time_state"] == VERIFIED_IN_PRODUCTION
                or card["recurring_state"] == VERIFIED_IN_PRODUCTION,
            }
        )
    return rows
