"""Email verification helpers (token issue, resend rate limiting)."""

import secrets
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.email import send_email
from core.models import SiteSettings

RESEND_COOLDOWN_SECONDS = 60
RESEND_MAX_PER_HOUR = 5


def issue_email_verify_token(user, save=True):
    user.email_verify_token = secrets.token_urlsafe(32)
    user.email_verify_token_expiry = timezone.now() + timedelta(
        seconds=getattr(settings, "EMAIL_VERIFY_TIMEOUT", 86400)
    )
    if save:
        user.save(
            update_fields=["email_verify_token", "email_verify_token_expiry", "updated_at"]
        )
    return user.email_verify_token


def send_verification_email(user, absolute_verify_url):
    foundation = SiteSettings.load().localized_name()
    send_email(
        subject=_("Verify your email - %(name)s") % {"name": foundation},
        message=_("Please verify your email by visiting: %(url)s") % {"url": absolute_verify_url},
        recipient_list=[user.email],
        fail_silently=True,
    )


def is_email_verified(user) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser or user.is_staff:
        return True
    return bool(user.email_verified)


def _cooldown_key(email):
    return f"email_verify_resend_cd:{email.lower()}"


def _hourly_key(email):
    return f"email_verify_resend_hr:{email.lower()}"


def can_resend_verification(email):
    """Return (allowed: bool, wait_seconds: int, reason: str|None)."""
    email = (email or "").strip().lower()
    if not email:
        return False, 0, "invalid"
    wait = cache.get(_cooldown_key(email))
    if wait:
        return False, int(wait), "cooldown"
    count = cache.get(_hourly_key(email)) or 0
    if count >= RESEND_MAX_PER_HOUR:
        return False, 3600, "hourly_limit"
    return True, 0, None


def mark_resend_attempt(email):
    email = (email or "").strip().lower()
    cache.set(_cooldown_key(email), RESEND_COOLDOWN_SECONDS, RESEND_COOLDOWN_SECONDS)
    hourly = cache.get(_hourly_key(email)) or 0
    cache.set(_hourly_key(email), hourly + 1, 3600)


def user_owns_donation(user, donation) -> bool:
    if not user or not user.is_authenticated:
        return False
    if donation.user_id and donation.user_id == user.id:
        return True
    if not is_email_verified(user):
        return False
    donor_email = (donation.donor_email or "").strip().lower()
    return bool(donor_email and donor_email == user.email.lower())
