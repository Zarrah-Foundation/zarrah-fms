"""bKash Tokenized Checkout v2 configuration.

Sandbox and live settings stay separate. This release never calls a live host
and never returns saved secrets.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from django.conf import settings
from django.utils import timezone

from core.choices import PaymentMethod

NOT_CONFIGURED = "NOT_CONFIGURED"
SANDBOX_CONFIGURED = "SANDBOX_CONFIGURED"
SANDBOX_VERIFIED = "SANDBOX_VERIFIED"
LIVE_CREDENTIALS_REQUIRED = "LIVE_CREDENTIALS_REQUIRED"
LIVE_VERIFIED = "LIVE_VERIFIED"
NOT_IMPLEMENTED = "NOT_IMPLEMENTED"

_LIVE_ENVS = {"live", "production", "prod"}
_DEFAULT_BASE = "https://tokenized.sandbox.bka.sh/v2/tokenized-checkout"
_V2_SUFFIX = "/v2/tokenized-checkout"


@dataclass(frozen=True)
class BkashCredentials:
    """Resolved credentials. Empty strings when the API must not be called."""

    configured: bool
    environment: str
    base_url: str
    username: str
    password: str
    app_key: str
    app_secret: str
    source: str
    state: str
    api_callable: bool
    reason: str


def _clean(value) -> str:
    return (value or "").strip()


def normalize_sandbox_base_url(raw: str) -> str:
    """Accept the official sandbox host. Reject every other host."""
    text = _clean(raw) or _DEFAULT_BASE
    parsed = urlparse(text)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host.endswith(".sandbox.bka.sh"):
        raise ValueError("BKASH_BASE_URL must be an https *.sandbox.bka.sh host.")
    path = (parsed.path or "").rstrip("/")
    if path in ("", "/"):
        path = _V2_SUFFIX
    if path != _V2_SUFFIX and not path.endswith(_V2_SUFFIX):
        raise ValueError("BKASH_BASE_URL must use the Tokenized Checkout v2 path.")
    return f"https://{host}{path}"


def _env_name() -> str:
    return _clean(getattr(settings, "BKASH_ENV", "sandbox")).lower() or "sandbox"


def _env_secrets() -> dict | None:
    username = _clean(getattr(settings, "BKASH_USERNAME", ""))
    password = _clean(getattr(settings, "BKASH_PASSWORD", ""))
    app_key = _clean(getattr(settings, "BKASH_APP_KEY", ""))
    app_secret = _clean(getattr(settings, "BKASH_APP_SECRET", ""))
    if not (username and password and app_key and app_secret):
        return None
    return {
        "username": username,
        "password": password,
        "app_key": app_key,
        "app_secret": app_secret,
        "source": "environment",
    }


def _db_secrets(cfg) -> dict | None:
    if cfg is None:
        return None
    if not (cfg.api_app_key and cfg.api_username and cfg.encrypted_api_secret and cfg.encrypted_api_password):
        return None
    from donations.credential_crypto import decrypt_secret

    try:
        app_secret = decrypt_secret(cfg.encrypted_api_secret)
        password = decrypt_secret(cfg.encrypted_api_password)
    except Exception:
        return None
    if not app_secret or not password:
        return None
    return {
        "username": _clean(cfg.api_username),
        "password": password,
        "app_key": _clean(cfg.api_app_key),
        "app_secret": app_secret,
        "source": "database",
    }


def _config_row():
    from donations.models import PaymentMethodConfig

    return PaymentMethodConfig.objects.filter(method=PaymentMethod.BKASH).first()


def resolve_bkash_credentials() -> BkashCredentials:
    """Environment credentials win when all four are set. Live mode never calls out."""
    env_name = _env_name()
    cfg = _config_row()
    secrets = _env_secrets()
    source = "environment" if secrets else ""
    if secrets is None:
        if cfg is not None and cfg.is_sandbox is False:
            return BkashCredentials(
                False, "live", "", "", "", "", "", "database",
                LIVE_CREDENTIALS_REQUIRED, False,
                "Live bKash credentials cannot be used in this release.",
            )
        secrets = _db_secrets(cfg)
        source = secrets["source"] if secrets else ""

    if env_name in _LIVE_ENVS:
        return BkashCredentials(
            bool(secrets), "live", "", "", "", "", "", source or "environment",
            LIVE_CREDENTIALS_REQUIRED, False,
            "Live bKash checkout is disabled. Sandbox credentials are required.",
        )

    if not secrets:
        return BkashCredentials(
            False, "sandbox", "", "", "", "", "", "missing",
            NOT_CONFIGURED, False,
            "bKash sandbox credentials are not configured.",
        )

    try:
        base_url = normalize_sandbox_base_url(getattr(settings, "BKASH_BASE_URL", ""))
    except ValueError as exc:
        return BkashCredentials(
            False, "sandbox", "", "", "", "", "", source,
            NOT_CONFIGURED, False, str(exc),
        )

    return BkashCredentials(
        True, "sandbox", base_url,
        secrets["username"], secrets["password"], secrets["app_key"], secrets["app_secret"],
        source, SANDBOX_CONFIGURED, True, "",
    )


def bkash_checkout_allowed(purpose: str) -> tuple[bool, str]:
    """Sandbox one-time checkout only. Purpose flags stay server-side."""
    creds = resolve_bkash_credentials()
    if not creds.api_callable:
        return False, creds.reason or "bKash sandbox checkout is not available."
    cfg = _config_row()
    if cfg is not None:
        if not cfg.is_enabled:
            return False, "bKash is temporarily disabled by an administrator."
        from donations.models import TransactionPurpose

        if purpose == TransactionPurpose.DONATION and not cfg.enabled_for_donation:
            return False, "Online donation payment is temporarily disabled."
        if purpose in (
            TransactionPurpose.MEMBERSHIP_FEE,
            TransactionPurpose.MEMBERSHIP_REGISTRATION,
        ) and not cfg.enabled_for_membership_fee:
            return False, "Online membership fee payment is temporarily disabled."
    return True, ""


def bkash_readiness() -> dict:
    """Public capability states. Contains no secrets."""
    creds = resolve_bkash_credentials()
    cfg = _config_row()
    connection = creds.state if creds.state != SANDBOX_CONFIGURED else SANDBOX_CONFIGURED
    one_time = connection
    refund = NOT_CONFIGURED if not creds.api_callable else SANDBOX_CONFIGURED
    if creds.api_callable and cfg is not None:
        if cfg.last_test_status == "SUCCESS":
            connection = SANDBOX_VERIFIED
        if cfg.one_time_verified_at:
            one_time = SANDBOX_VERIFIED
        if cfg.refund_verified_at:
            refund = SANDBOX_VERIFIED
        elif not cfg.refunds_enabled:
            refund = NOT_CONFIGURED
    if creds.state == LIVE_CREDENTIALS_REQUIRED:
        connection = LIVE_CREDENTIALS_REQUIRED
        one_time = LIVE_CREDENTIALS_REQUIRED
        refund = LIVE_CREDENTIALS_REQUIRED
    return {
        "connection": connection,
        "one_time": one_time,
        "recurring": NOT_IMPLEMENTED,
        "refund": refund,
        "cancel": NOT_IMPLEMENTED,
        "live": LIVE_CREDENTIALS_REQUIRED,
        "environment": creds.environment,
        "api_callable": creds.api_callable,
        "checkout_allowed": creds.api_callable and bkash_checkout_allowed("DONATION")[0],
        "source": creds.source,
        "reason": creds.reason,
        "last_test_status": (cfg.last_test_status if cfg else "") or "",
        "last_test_message": ((cfg.last_test_message if cfg else "") or "")[:200],
    }


def redact_provider_text(text: str, creds: BkashCredentials | None = None) -> str:
    """Strip credentials and bearer-looking tokens from provider text."""
    import re

    out = str(text or "")
    secrets = []
    if creds is not None:
        secrets.extend([creds.password, creds.app_secret, creds.username, creds.app_key])
    for secret in secrets:
        if secret and len(secret) >= 4:
            out = out.replace(secret, "[redacted]")
    out = re.sub(r"eyJ[A-Za-z0-9_\-]{8,}", "[redacted]", out)
    return out[:300]


def record_bkash_test(status: str, message: str) -> None:
    cfg = _config_row()
    if cfg is None:
        return
    cfg.last_tested_at = timezone.now()
    cfg.last_test_status = (status or "")[:20]
    cfg.last_test_message = redact_provider_text(message)[:300]
    cfg.save(update_fields=["last_tested_at", "last_test_status", "last_test_message", "updated_at"])


def test_bkash_connection() -> tuple[str, str]:
    """Grant a sandbox token. Does not create a payment or reveal the token."""
    creds = resolve_bkash_credentials()
    if creds.state == LIVE_CREDENTIALS_REQUIRED or creds.environment == "live":
        message = "Live bKash checkout is disabled. No request was sent."
        record_bkash_test("FAILED", message)
        return "FAILED", message
    if not creds.api_callable:
        message = creds.reason or "bKash sandbox credentials are not configured."
        record_bkash_test("NOT_CONFIGURED", message)
        return "NOT_CONFIGURED", message
    from donations.gateways.bkash_client import BkashClient
    from donations.gateways.base import PaymentGatewayError

    try:
        BkashClient(creds).grant_token(force=True)
    except PaymentGatewayError as exc:
        message = redact_provider_text(str(exc), creds)
        record_bkash_test("FAILED", message)
        return "FAILED", message
    message = "Sandbox token granted. No payment was created. Live payments stay disabled."
    record_bkash_test("SUCCESS", message)
    return "SUCCESS", message
