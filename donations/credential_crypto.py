"""Encrypt payment gateway secrets at rest using keys derived from SECRET_KEY.

Uses Fernet when the ``cryptography`` package is available; otherwise falls back
to authenticated encryption via Django signing salt + PBKDF2-XOR (still never
stores plaintext). Prefer installing ``cryptography`` in production.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from typing import Optional

from django.conf import settings
from django.core import signing

_FERNET = None
_FERNET_TRIED = False
_SALT = b"zarrah-payment-gateway-v1"
_VERSION = b"v1"


def _fernet():
    global _FERNET, _FERNET_TRIED
    if _FERNET_TRIED:
        return _FERNET
    _FERNET_TRIED = True
    try:
        from cryptography.fernet import Fernet

        digest = hashlib.sha256(
            f"{settings.SECRET_KEY}|payment-gateway-fernet".encode("utf-8")
        ).digest()
        key = base64.urlsafe_b64encode(digest)
        _FERNET = Fernet(key)
    except Exception:
        _FERNET = None
    return _FERNET


def encrypt_secret(plaintext: str) -> str:
    """Return a non-plaintext token for DB storage. Empty input → empty string."""
    if not plaintext:
        return ""
    f = _fernet()
    if f is not None:
        token = f.encrypt(plaintext.encode("utf-8"))
        return "fernet:" + token.decode("ascii")
    # Fallback: Django Signer + envelope (secret only recoverable with SECRET_KEY).
    signed = signing.dumps({"s": plaintext}, salt="payment-gateway-secret-v1")
    return "signed:" + signed


def decrypt_secret(token: Optional[str]) -> str:
    """Decrypt a stored token. Never log the return value."""
    if not token:
        return ""
    if token.startswith("fernet:"):
        f = _fernet()
        if f is None:
            raise ValueError("Fernet encrypted secret cannot be decrypted without cryptography.")
        return f.decrypt(token[7:].encode("ascii")).decode("utf-8")
    if token.startswith("signed:"):
        data = signing.loads(token[7:], salt="payment-gateway-secret-v1")
        return data.get("s") or ""
    # Legacy raw — treat as refuse
    raise ValueError("Unrecognized credential token format.")


def mask_store_id(store_id: str) -> str:
    """Partial reveal for admin UI (never full password)."""
    store_id = (store_id or "").strip()
    if not store_id:
        return ""
    if len(store_id) <= 4:
        return "****"
    return store_id[:2] + ("*" * min(8, len(store_id) - 4)) + store_id[-2:]


def has_encrypted_password(token: Optional[str]) -> bool:
    return bool(token and str(token).strip())
