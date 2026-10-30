"""SMS service: provider selection, send, and cache-backed verification codes."""

from __future__ import annotations

import logging
import secrets
from typing import Optional

from django.conf import settings
from django.core.cache import cache
from django.utils.translation import gettext as _

from core.models import SmsSettings
from core.sms.base import SmsProvider
from core.sms.console import ConsoleSmsProvider
from core.sms.http_generic import HttpGenericSmsProvider

logger = logging.getLogger("core.sms")


def _normalize_phone(phone: str) -> str:
    return "".join(ch for ch in (phone or "").strip() if ch.isdigit() or ch == "+")


def _code_key(phone: str) -> str:
    return f"sms:verify:code:{phone}"


def _attempts_key(phone: str) -> str:
    return f"sms:verify:attempts:{phone}"


def _cooldown_key(phone: str) -> str:
    return f"sms:send:cd:{phone}"


def _hourly_key(phone: str) -> str:
    return f"sms:send:hr:{phone}"


class SMSService:
    """Facade for outbound SMS and phone verification codes."""

    @staticmethod
    def get_settings() -> SmsSettings:
        return SmsSettings.load()

    @classmethod
    def get_provider(cls) -> SmsProvider:
        cfg = cls.get_settings()
        # DEBUG-safe: never fire real HTTP when provider is CONSOLE, or when disabled.
        if settings.DEBUG and (
            not cfg.enabled or cfg.provider == SmsSettings.Provider.CONSOLE
        ):
            return ConsoleSmsProvider()
        if (
            cfg.enabled
            and cfg.provider == SmsSettings.Provider.HTTP_GENERIC
            and cfg.api_url
        ):
            return HttpGenericSmsProvider(
                api_url=cfg.api_url,
                api_key=cfg.api_key,
                sender_id=cfg.sender_id,
            )
        return ConsoleSmsProvider()

    @classmethod
    def send_sms(cls, to: str, message: str) -> bool:
        phone = _normalize_phone(to)
        if not phone or not message:
            return False
        provider = cls.get_provider()
        return bool(provider.send(phone, message))

    @classmethod
    def can_send_verification(cls, phone: str) -> tuple[bool, int, Optional[str]]:
        """Return (allowed, wait_seconds, reason)."""
        phone = _normalize_phone(phone)
        if not phone:
            return False, 0, "invalid"
        cfg = cls.get_settings()
        wait = cache.get(_cooldown_key(phone))
        if wait:
            return False, int(wait), "cooldown"
        count = cache.get(_hourly_key(phone)) or 0
        if count >= cfg.max_sends_per_hour:
            return False, 3600, "hourly_limit"
        return True, 0, None

    @classmethod
    def send_verification_code(cls, phone: str) -> tuple[bool, str]:
        """
        Generate and send a verification code.

        Returns ``(ok, detail)`` where detail is a user-facing message or the
        code itself only when using the console provider in DEBUG (for tests).
        """
        phone = _normalize_phone(phone)
        if not phone:
            return False, _("Invalid phone number.")

        allowed, wait, reason = cls.can_send_verification(phone)
        if not allowed:
            if reason == "cooldown":
                return False, _("Please wait %(seconds)s seconds before resending.") % {
                    "seconds": wait
                }
            if reason == "hourly_limit":
                return False, _("Too many SMS sends. Try again later.")
            return False, _("Unable to send verification code.")

        cfg = cls.get_settings()
        code = f"{secrets.randbelow(1_000_000):06d}"
        timeout = cfg.verification_timeout_seconds or 300
        cache.set(_code_key(phone), code, timeout=timeout)
        cache.set(_attempts_key(phone), 0, timeout=timeout)

        message = _("Your verification code is %(code)s") % {"code": code}
        ok = cls.send_sms(phone, message)
        if not ok:
            cache.delete(_code_key(phone))
            cache.delete(_attempts_key(phone))
            return False, _("Failed to send SMS.")

        cache.set(_cooldown_key(phone), cfg.resend_cooldown_seconds, cfg.resend_cooldown_seconds)
        hourly = cache.get(_hourly_key(phone)) or 0
        cache.set(_hourly_key(phone), hourly + 1, 3600)
        return True, _("Verification code sent.")

    @classmethod
    def verify_code(cls, phone: str, code: str) -> tuple[bool, str]:
        phone = _normalize_phone(phone)
        code = (code or "").strip()
        if not phone or not code:
            return False, _("Invalid code.")

        cfg = cls.get_settings()
        stored = cache.get(_code_key(phone))
        if not stored:
            return False, _("Code expired or not found.")

        attempts = cache.get(_attempts_key(phone)) or 0
        if attempts >= cfg.max_attempts:
            cache.delete(_code_key(phone))
            cache.delete(_attempts_key(phone))
            return False, _("Too many attempts. Request a new code.")

        if secrets.compare_digest(str(stored), code):
            cache.delete(_code_key(phone))
            cache.delete(_attempts_key(phone))
            return True, _("Phone verified.")

        cache.set(_attempts_key(phone), attempts + 1, cfg.verification_timeout_seconds or 300)
        remaining = max(0, cfg.max_attempts - (attempts + 1))
        return False, _("Incorrect code. %(count)s attempts remaining.") % {
            "count": remaining
        }
