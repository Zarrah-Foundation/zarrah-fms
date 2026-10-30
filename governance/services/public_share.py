"""Public resolution sharing — tokens, passwords, expiry, revoke."""

from __future__ import annotations

import logging
import secrets
from typing import Optional

from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from governance.models import Resolution, ResolutionPublicShare
from governance.services.audit import log_governance

logger = logging.getLogger(__name__)

_PASSWORD_ATTEMPT_PREFIX = "gov:share:pwfail:"
_PASSWORD_ATTEMPT_TTL = 900  # 15 minutes
_DEFAULT_ATTEMPT_LIMIT = 5


def _new_token() -> str:
    # urlsafe ~43 chars for 32 bytes — never use resolution_id / UUID as credential.
    return secrets.token_urlsafe(32)


def _attempt_cache_key(ip: str, token: str) -> str:
    return f"{_PASSWORD_ATTEMPT_PREFIX}{ip or 'unknown'}:{token}"


def password_attempts_blocked(
    ip: str,
    token: str,
    *,
    limit: int = _DEFAULT_ATTEMPT_LIMIT,
) -> bool:
    key = _attempt_cache_key(ip, token)
    count = cache.get(key) or 0
    return int(count) >= int(limit)


def record_password_failure(ip: str, token: str) -> int:
    key = _attempt_cache_key(ip, token)
    count = int(cache.get(key) or 0) + 1
    cache.set(key, count, _PASSWORD_ATTEMPT_TTL)
    return count


def clear_password_failures(ip: str, token: str) -> None:
    cache.delete(_attempt_cache_key(ip, token))


def get_valid_share(token: str) -> Optional[ResolutionPublicShare]:
    """Return an enabled, non-revoked, non-expired share for ``token``, else None."""
    token = (token or "").strip()
    if not token:
        return None
    try:
        share = ResolutionPublicShare.objects.select_related(
            "resolution",
            "resolution__meeting",
            "resolution__current_version",
        ).get(token=token)
    except ResolutionPublicShare.DoesNotExist:
        return None
    if not share.is_accessible():
        return None
    return share


def verify_share_password(
    share: ResolutionPublicShare,
    password: str,
    *,
    ip: str = "",
) -> bool:
    """
    Verify optional share password.

    Records failures for rate limiting. Does not reveal whether the share
    exists beyond the caller already holding a share instance.
    """
    if password_attempts_blocked(ip, share.token):
        return False

    if not share.requires_password:
        clear_password_failures(ip, share.token)
        return True

    ok = check_password(password or "", share.password_hash)
    if ok:
        clear_password_failures(ip, share.token)
        return True

    record_password_failure(ip, share.token)
    return False


@transaction.atomic
def enable_public_share(
    resolution: Resolution,
    *,
    actor=None,
    password: str | None = None,
    expires_at=None,
    show_signer_details: bool = True,
) -> ResolutionPublicShare:
    """
    Enable (or re-enable) a public share with a secure random token.

    Password is hashed with Django's password hasher; plaintext is never stored.
    """
    resolution = Resolution.objects.select_for_update().get(pk=resolution.pk)
    share, created = ResolutionPublicShare.objects.select_for_update().get_or_create(
        resolution=resolution,
        defaults={
            "token": _new_token(),
            "is_enabled": True,
            "show_signer_details": bool(show_signer_details),
            "created_by": actor if getattr(actor, "is_authenticated", False) else None,
        },
    )

    updates = ["is_enabled", "revoked_at", "expires_at", "show_signer_details", "updated_at"]
    share.is_enabled = True
    share.revoked_at = None
    share.expires_at = expires_at
    share.show_signer_details = bool(show_signer_details)

    if password:
        share.password_hash = make_password(password)
        updates.append("password_hash")
    elif created:
        share.password_hash = ""
        updates.append("password_hash")

    if not share.token:
        share.token = _new_token()
        updates.append("token")

    if getattr(actor, "is_authenticated", False) and share.created_by_id is None:
        share.created_by = actor
        updates.append("created_by")

    share.save(update_fields=list(dict.fromkeys(updates)))

    log_governance(
        actor,
        "PUBLIC_SHARE_ENABLE",
        "Resolution",
        resolution.pk,
        f"Enabled public share for {resolution.resolution_id}",
        new={
            "expires_at": expires_at.isoformat() if expires_at else None,
            "password_protected": bool(share.password_hash),
            "show_signer_details": share.show_signer_details,
        },
    )
    return share


@transaction.atomic
def revoke_public_share(resolution: Resolution, *, actor=None) -> ResolutionPublicShare:
    """Revoke public access immediately (idempotent)."""
    resolution = Resolution.objects.select_for_update().get(pk=resolution.pk)
    try:
        share = ResolutionPublicShare.objects.select_for_update().get(
            resolution=resolution
        )
    except ResolutionPublicShare.DoesNotExist as exc:
        raise ValueError("Resolution has no public share to revoke.") from exc

    now = timezone.now()
    share.is_enabled = False
    share.revoked_at = now
    share.save(update_fields=["is_enabled", "revoked_at", "updated_at"])

    log_governance(
        actor,
        "PUBLIC_SHARE_REVOKE",
        "Resolution",
        resolution.pk,
        f"Revoked public share for {resolution.resolution_id}",
        new={"revoked_at": now.isoformat()},
    )
    return share


@transaction.atomic
def set_share_password(
    resolution: Resolution,
    password: str | None,
    *,
    actor=None,
) -> ResolutionPublicShare:
    """Set or clear the public-share password (hashed)."""
    share = (
        ResolutionPublicShare.objects.select_for_update()
        .select_related("resolution")
        .get(resolution=resolution)
    )
    if password:
        share.password_hash = make_password(password)
    else:
        share.password_hash = ""
    share.save(update_fields=["password_hash", "updated_at"])
    log_governance(
        actor,
        "PUBLIC_SHARE_PASSWORD",
        "Resolution",
        resolution.pk,
        f"Updated public share password for {resolution.resolution_id}",
        new={"password_protected": bool(share.password_hash)},
    )
    return share
