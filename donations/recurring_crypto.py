"""AES helpers for SSLCommerz EasyCheckout recurring ``schedule`` payload.

Encryption matches the common SSLCommerz merchant documentation pattern
(AES-128-CBC, PKCS7 padding, base64 ciphertext). The SALT/key is never logged.
"""

from __future__ import annotations

import base64
import json
import os

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def _normalize_aes128_key(salt_key: str) -> bytes:
    raw = (salt_key or "").encode("utf-8")
    if len(raw) >= 16:
        return raw[:16]
    return raw.ljust(16, b"\0")


def encrypt_schedule_payload(payload: dict, salt_key: str) -> str:
    """Return base64(iv + ciphertext) for SSLCommerz ``schedule`` field."""
    if not salt_key:
        raise ValueError("SSLCommerz SALT key is not configured.")
    plaintext = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    key = _normalize_aes128_key(salt_key)
    iv = os.urandom(16)
    padder = padding.PKCS7(128).padder()
    padded = padder.update(plaintext) + padder.finalize()
    encryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    ciphertext = encryptor.update(padded) + encryptor.finalize()
    return base64.b64encode(iv + ciphertext).decode("ascii")
