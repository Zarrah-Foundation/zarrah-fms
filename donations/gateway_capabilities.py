"""Payment gateway capability detection (no invented recurring APIs)."""

from core.choices import PaymentMethod
from donations.models import PaymentMethodConfig, TransactionPurpose


def sslcommerz_credentials_status():
    from donations.credential_service import public_credential_status

    status = public_credential_status()
    # Back-compat keys used by templates/tests.
    status.setdefault("sandbox", bool(status.get("is_sandbox")))
    return status


def sslcommerz_supports_one_time():
    from donations.credential_service import resolve_sslcommerz_credentials

    return resolve_sslcommerz_credentials().configured


def sslcommerz_supports_recurring():
    """True only when merchant recurring SALT + plan refer are configured.

    Official EasyCheckout recurring (encrypted schedule) is gated — never
    invented when credentials are missing.
    """
    from donations.recurring_config import sslcommerz_recurring_configured

    return sslcommerz_recurring_configured().configured


CMS_RECURRING_DISABLED_MSG = "New recurring donations are disabled."


def cms_new_recurring_enabled():
    """CMS switch for NEW public recurring signup. Does not cancel existing subs."""
    try:
        from donations.models import PaymentSystemSettings

        return bool(PaymentSystemSettings.load().recurring_donation_enabled)
    except Exception:
        return True


def public_recurring_option_visible():
    """True only when CMS allows new recurring AND a provider can actually run it."""
    ok, _err = recurring_checkout_allowed()
    return ok


def recurring_checkout_allowed(method=PaymentMethod.SSLCOMMERZ):
    """Return (ok, error_message) for recurring donation authorization."""
    if not cms_new_recurring_enabled():
        return False, CMS_RECURRING_DISABLED_MSG
    if method != PaymentMethod.SSLCOMMERZ:
        return False, "Recurring donations currently support SSLCommerz only."
    if not sslcommerz_supports_one_time():
        return False, "SSLCommerz credentials are not configured."
    if not sslcommerz_supports_recurring():
        status = __import__(
            "donations.recurring_config", fromlist=["sslcommerz_recurring_configured"]
        ).sslcommerz_recurring_configured()
        return False, status.reason or "SSLCommerz recurring is not configured."
    cfg = PaymentMethodConfig.objects.filter(method=method).first()
    if cfg is not None:
        if not cfg.is_enabled:
            return False, "SSLCommerz is temporarily disabled by an administrator."
        if not cfg.enabled_for_donation:
            return False, "Online donation payment is temporarily disabled."
        if not cfg.merchant_recurring_enabled and not sslcommerz_supports_recurring():
            return False, "Recurring donations are not enabled for this payment method."
        # If SALT/plan come from env only, allow without merchant flag; if DB has salt, prefer flag.
        if cfg.encrypted_salt_key or cfg.recurring_plan_refer:
            if not cfg.merchant_recurring_enabled:
                return False, "Merchant recurring is not confirmed in payment method settings."
    return True, ""


def method_capabilities(method):
    """Public capability map for admin UI and checkout gating."""
    if method == PaymentMethod.SSLCOMMERZ:
        creds = sslcommerz_credentials_status()
        return {
            "method": method,
            "implemented": True,
            "channel_kind": "ONLINE_HOSTED",
            "hosted_via": None,
            "supports_one_time": sslcommerz_supports_one_time(),
            "supports_recurring": sslcommerz_supports_recurring(),
            "credentials": creds,
            "label_note": "Hosted checkout (may include cards/wallets enabled on the SSLCommerz store).",
        }
    if method == PaymentMethod.BKASH:
        from donations.bkash_config import bkash_readiness

        ready = bkash_readiness()
        return {
            "method": method,
            "implemented": True,
            "channel_kind": "ONLINE_DIRECT",
            "hosted_via": None,
            "supports_one_time": bool(ready["api_callable"]),
            "supports_recurring": False,
            "credentials": {
                "configured": bool(ready["api_callable"]),
                "sandbox": ready["environment"] == "sandbox" and bool(ready["api_callable"]),
                "status": ready["connection"],
            },
            "label_note": (
                "Tokenized Checkout v2 sandbox. Live payments are disabled. "
                "Automatic recurring is not implemented because each agreement "
                "charge still requires the customer PIN."
            ),
        }
    if method in (PaymentMethod.NAGAD, PaymentMethod.ROCKET):
        return {
            "method": method,
            "implemented": False,
            "channel_kind": "ONLINE_DIRECT",
            "hosted_via": PaymentMethod.SSLCOMMERZ,
            "supports_one_time": False,
            "supports_recurring": False,
            "credentials": {"configured": False, "sandbox": False, "status": "not_implemented"},
            "label_note": (
                "Direct integration not implemented. May appear inside SSLCommerz "
                "hosted checkout when the merchant store enables it — not a first-party adapter."
            ),
        }
    if method in (PaymentMethod.BANK_TRANSFER, PaymentMethod.CASH, PaymentMethod.OTHER):
        return {
            "method": method,
            "implemented": True,
            "channel_kind": "MANUAL_OFFLINE",
            "hosted_via": None,
            "supports_one_time": True,
            "supports_recurring": False,
            "credentials": {"configured": True, "sandbox": False, "status": "manual"},
            "label_note": "Offline / manual recording only.",
        }
    return {
        "method": method,
        "implemented": False,
        "channel_kind": "UNKNOWN",
        "hosted_via": None,
        "supports_one_time": False,
        "supports_recurring": False,
        "credentials": {"configured": False, "sandbox": False, "status": "unknown"},
        "label_note": "",
    }


def online_checkout_allowed(method=PaymentMethod.SSLCOMMERZ, purpose=TransactionPurpose.DONATION):
    """Return (ok, error_message) for online checkout by payment purpose."""
    if method == PaymentMethod.BKASH:
        from donations.bkash_config import bkash_checkout_allowed

        return bkash_checkout_allowed(purpose)
    if method != PaymentMethod.SSLCOMMERZ:
        return False, "Online checkout is only available via SSLCommerz hosted checkout."
    caps = method_capabilities(method)
    if not caps["supports_one_time"]:
        return False, "SSLCommerz credentials are not configured."
    cfg = PaymentMethodConfig.objects.filter(method=method).first()
    if cfg is not None:
        if not cfg.is_enabled:
            return False, "SSLCommerz is temporarily disabled by an administrator."
        if purpose in (
            TransactionPurpose.MEMBERSHIP_FEE,
            TransactionPurpose.MEMBERSHIP_REGISTRATION,
        ) and not cfg.enabled_for_membership_fee:
            return False, "Online membership fee payment is temporarily disabled."
        if purpose == TransactionPurpose.DONATION and not cfg.enabled_for_donation:
            return False, "Online donation payment is temporarily disabled."
    return True, ""


def autopay_activation_allowed():
    """Return (allowed, message, mode). Mock never contacts a gateway."""
    try:
        from donations.models import PaymentSystemSettings

        if not PaymentSystemSettings.load().membership_autopay_enabled:
            return False, "Membership Autopay is disabled by an administrator.", "OFF"
    except Exception:
        pass
    if sslcommerz_supports_recurring():
        return True, "", "GATEWAY"

    from donations.credential_service import resolve_sslcommerz_credentials

    if resolve_sslcommerz_credentials().is_sandbox:
        return True, "", "MOCK"
    return (
        False,
        "Automatic recurring payments are not available. "
        "Official gateway recurring is not configured in this system. "
        "Please pay manually or use sandbox mock mode.",
        "MOCK",
    )


def hosted_card_channels():
    """Visa/Mastercard represented as hosted via SSLCommerz (not direct adapters)."""
    return [
        {
            "code": "VISA_MC_HOSTED",
            "label": "Visa / Mastercard (via SSLCommerz hosted checkout)",
            "hosted_via": PaymentMethod.SSLCOMMERZ,
            "implemented_direct": False,
            "available_when": "SSLCommerz online checkout enabled and merchant store allows cards",
        }
    ]
