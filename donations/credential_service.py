"""Resolve SSLCommerz credentials and safe gateway diagnostics.

Resolution order (never silently replace production env unless admin opts in):

1. If PaymentMethodConfig.use_database_credentials is True and DB store id +
   encrypted password exist → use database credentials.
2. Else if environment SSLCOMMERZ_STORE_ID / SSLCOMMERZ_STORE_PASSWORD set → env.
3. Else if DB credentials exist even without the use_database flag → DB fallback.
4. Else → not configured.

Sandbox mode: config.is_sandbox when set and DB/env path allows; otherwise
settings.SSLCOMMERZ_IS_SANDBOX. Production activation requires confirm_production.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Tuple

import requests
from django.conf import settings
from django.utils import timezone

from core.choices import PaymentMethod
from donations.credential_crypto import decrypt_secret, has_encrypted_password, mask_store_id

logger = logging.getLogger(__name__)

TEST_STATUS_SUCCESS = "SUCCESS"
TEST_STATUS_FAILED = "FAILED"
TEST_STATUS_NOT_CONFIGURED = "NOT_CONFIGURED"


@dataclass(frozen=True)
class ResolvedCredentials:
    store_id: str
    store_password: str
    is_sandbox: bool
    source: str  # "environment" | "database" | ""
    configured: bool

    def as_public_status(self) -> dict:
        """Safe for templates/JSON — never includes password."""
        return {
            "configured": self.configured,
            "source": self.source or None,
            "store_id_masked": mask_store_id(self.store_id) if self.store_id else "",
            "environment": "Sandbox" if self.is_sandbox else "Production",
            "is_sandbox": self.is_sandbox,
            "status": (
                "sandbox"
                if self.configured and self.is_sandbox
                else "configured"
                if self.configured
                else "missing"
            ),
        }


def _env_credentials() -> Tuple[str, str]:
    return (
        (getattr(settings, "SSLCOMMERZ_STORE_ID", "") or "").strip(),
        (getattr(settings, "SSLCOMMERZ_STORE_PASSWORD", "") or "").strip(),
    )


def _env_sandbox() -> bool:
    return bool(getattr(settings, "SSLCOMMERZ_IS_SANDBOX", True))


def get_sslcommerz_config():
    from donations.models import PaymentMethodConfig

    return PaymentMethodConfig.objects.filter(method=PaymentMethod.SSLCOMMERZ).first()


def resolve_sslcommerz_credentials() -> ResolvedCredentials:
    """Return decrypted credentials for outbound API use only (never log password)."""
    cfg = get_sslcommerz_config()
    env_id, env_pass = _env_credentials()
    env_sandbox = _env_sandbox()

    db_id = ""
    db_pass = ""
    if cfg:
        db_id = (cfg.store_id or "").strip()
        if has_encrypted_password(cfg.encrypted_store_password):
            try:
                db_pass = decrypt_secret(cfg.encrypted_store_password)
            except Exception:
                logger.exception("Failed to decrypt SSLCommerz store password")
                db_pass = ""

    use_db = bool(cfg and cfg.use_database_credentials and db_id and db_pass)
    if use_db:
        sandbox = cfg.is_sandbox if cfg.is_sandbox is not None else True
        return ResolvedCredentials(
            store_id=db_id,
            store_password=db_pass,
            is_sandbox=bool(sandbox),
            source="database",
            configured=True,
        )

    if env_id and env_pass:
        # Admin may toggle sandbox overlay when credentials come from env.
        sandbox = env_sandbox
        if cfg is not None and cfg.is_sandbox is not None:
            sandbox = bool(cfg.is_sandbox)
        return ResolvedCredentials(
            store_id=env_id,
            store_password=env_pass,
            is_sandbox=sandbox,
            source="environment",
            configured=True,
        )

    if db_id and db_pass:
        sandbox = cfg.is_sandbox if cfg is not None and cfg.is_sandbox is not None else True
        return ResolvedCredentials(
            store_id=db_id,
            store_password=db_pass,
            is_sandbox=bool(sandbox),
            source="database",
            configured=True,
        )

    return ResolvedCredentials(
        store_id=env_id or db_id,
        store_password="",
        is_sandbox=env_sandbox,
        source="",
        configured=False,
    )


def gateway_urls(is_sandbox: bool) -> Tuple[str, str]:
    if is_sandbox:
        return (
            "https://sandbox.sslcommerz.com/gwprocess/v4/api.php",
            "https://sandbox.sslcommerz.com/validator/api/validationserverAPI.php",
        )
    return (
        "https://securepay.sslcommerz.com/gwprocess/v4/api.php",
        "https://securepay.sslcommerz.com/validator/api/validationserverAPI.php",
    )


def public_credential_status(cfg=None) -> dict:
    """Admin/UI status map without secrets."""
    creds = resolve_sslcommerz_credentials()
    public = creds.as_public_status()
    if cfg is None:
        cfg = get_sslcommerz_config()
    public.update(
        {
            "gateway_enabled": bool(cfg.is_enabled) if cfg else True,
            "enabled_for_donation": bool(cfg.enabled_for_donation) if cfg else True,
            "enabled_for_membership_fee": bool(cfg.enabled_for_membership_fee) if cfg else True,
            "use_database_credentials": bool(cfg.use_database_credentials) if cfg else False,
            "has_saved_secret": bool(cfg and has_encrypted_password(cfg.encrypted_store_password)),
            "last_tested_at": cfg.last_tested_at if cfg else None,
            "last_test_status": (cfg.last_test_status if cfg else "") or "",
            "last_test_message": (cfg.last_test_message if cfg else "") or "",
            "admin_notes": (cfg.admin_notes if cfg else "") or "",
            "production_confirmed": bool(cfg and cfg.production_confirmed_at),
        }
    )
    return public


def test_sslcommerz_connection(*, actor=None) -> Tuple[str, str]:
    """Validate credentials without creating local payments/donations/income.

    Uses the validation API with a dummy val_id — never charges and never
    creates a checkout session in our database.
    """
    cfg = get_sslcommerz_config()
    creds = resolve_sslcommerz_credentials()
    if not creds.configured:
        status, message = TEST_STATUS_NOT_CONFIGURED, "SSLCommerz credentials are not configured."
        _record_test_result(cfg, status, message)
        return status, message

    _gateway_url, validation_url = gateway_urls(creds.is_sandbox)
    try:
        response = requests.get(
            validation_url,
            params={
                "val_id": "ZARRAH_CREDENTIAL_TEST",
                "store_id": creds.store_id,
                "store_passwd": creds.store_password,
                "format": "json",
            },
            timeout=12,
        )
        # Never log password or raw body if it might echo secrets.
        logger.info(
            "SSLCommerz test connection status_code=%s sandbox=%s source=%s actor=%s",
            response.status_code,
            creds.is_sandbox,
            creds.source,
            getattr(actor, "pk", None),
        )
        try:
            data = response.json()
        except ValueError:
            status, message = TEST_STATUS_FAILED, "Gateway returned a non-JSON response."
            _record_test_result(cfg, status, message)
            return status, message

        api_status = (data.get("status") or "").upper()
        # Authenticated merchant + unknown val_id → typically INVALID_TRANSACTION / FAILED.
        # Wrong credentials often → FAILEDREASON mentioning store id/password or HTTP auth.
        reason = (
            data.get("errorReason")
            or data.get("failedreason")
            or data.get("failed_reason")
            or data.get("status")
            or ""
        )
        reason_l = str(reason).lower()
        if any(
            token in reason_l
            for token in (
                "store password",
                "store_passwd",
                "invalid store",
                "authentication",
                "unauthorized",
                "credential",
            )
        ):
            status, message = TEST_STATUS_FAILED, "Gateway rejected credentials."
        elif response.status_code in (401, 403):
            status, message = TEST_STATUS_FAILED, "Gateway rejected credentials."
        elif api_status in ("VALID", "VALIDATED", "INVALID_TRANSACTION", "FAILED", "UNATTEMPTED", ""):
            # Reachable + accepted store handshake (dummy val_id expected to fail validation).
            status, message = TEST_STATUS_SUCCESS, "Credentials accepted by gateway validation endpoint."
        elif response.ok:
            status, message = TEST_STATUS_SUCCESS, "Gateway responded successfully."
        else:
            status, message = TEST_STATUS_FAILED, f"Gateway HTTP {response.status_code}."
    except requests.Timeout:
        status, message = TEST_STATUS_FAILED, "Connection timed out."
        logger.warning("SSLCommerz test connection timeout")
    except requests.RequestException as exc:
        status, message = TEST_STATUS_FAILED, "Network error contacting gateway."
        logger.warning("SSLCommerz test connection error: %s", type(exc).__name__)

    # Strip anything that looks like a secret in message.
    message = _sanitize_public_message(message)
    _record_test_result(cfg, status, message)
    return status, message


def _sanitize_public_message(message: str) -> str:
    msg = (message or "")[:200]
    # Defensive: never echo credential field names with values.
    return msg.replace("store_passwd", "[redacted]").replace("store_password", "[redacted]")


def _record_test_result(cfg, status: str, message: str) -> None:
    if cfg is None:
        return
    cfg.last_tested_at = timezone.now()
    cfg.last_test_status = status[:20]
    cfg.last_test_message = (message or "")[:300]
    cfg.save(update_fields=["last_tested_at", "last_test_status", "last_test_message", "updated_at"])
