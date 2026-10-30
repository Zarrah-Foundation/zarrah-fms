"""Digital resolution drafting, signing, versioning, and finalization."""

from __future__ import annotations

import logging
import os
from typing import Any, Iterable, Optional

from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from core.html_sanitize import sanitize_html
from governance.models import (
    MeetingParticipant,
    ParticipantStatus,
    Resolution,
    ResolutionSignature,
    ResolutionSigner,
    ResolutionStatus,
    ResolutionVersion,
)
from governance.sequences import generate_resolution_id
from governance.services.audit import log_governance
from members.models import Member

logger = logging.getLogger(__name__)

_HTML_FIELDS = ("content_bn", "content_en", "decision_bn", "decision_en")
_DRAFT_EDITABLE = {
    "title_bn",
    "title_en",
    "content_bn",
    "content_en",
    "decision_bn",
    "decision_en",
    "notes",
}
_REVERSION_FROM = {
    ResolutionStatus.READY_FOR_SIGNING,
    ResolutionStatus.PARTIALLY_SIGNED,
    ResolutionStatus.FULLY_SIGNED,
}


def _member_display_name(member: Member) -> str:
    return f"{member.first_name} {member.last_name}".strip() or member.member_id


def _member_designation(member: Member) -> str:
    """Snapshot organizational identity at signing (position — council)."""
    from members.positions import member_position_snapshot

    return member_position_snapshot(member)

def _request_meta(request) -> tuple[Optional[str], str]:
    if request is None:
        return None, ""
    from accounts.signals import get_client_ip

    ip = get_client_ip(request)
    ua = (request.META.get("HTTP_USER_AGENT") or "")[:300]
    return ip, ua


def _sanitize_fields(data: dict[str, Any]) -> dict[str, Any]:
    out = dict(data)
    for key in _HTML_FIELDS:
        if key in out and out[key] is not None:
            out[key] = sanitize_html(out[key] or "")
    return out


@transaction.atomic
def create_resolution(
    meeting,
    *,
    title_bn: str,
    title_en: str = "",
    content_bn: str,
    content_en: str = "",
    decision_bn: str = "",
    decision_en: str = "",
    agenda_item=None,
    actor=None,
) -> Resolution:
    """Create a DRAFT resolution with version 1 as current."""
    title_bn = (title_bn or "").strip()
    if not title_bn:
        raise ValueError("title_bn is required.")
    content_bn = sanitize_html(content_bn or "")
    if not content_bn.strip():
        raise ValueError("content_bn is required.")

    resolution_id = generate_resolution_id()
    resolution = Resolution.objects.create(
        resolution_id=resolution_id,
        meeting=meeting,
        agenda_item=agenda_item,
        title_bn=title_bn,
        title_en=title_en or "",
        status=ResolutionStatus.DRAFT,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
    )
    version = ResolutionVersion.objects.create(
        resolution=resolution,
        version_number=1,
        title_bn=title_bn,
        title_en=title_en or "",
        content_bn=content_bn,
        content_en=sanitize_html(content_en or ""),
        decision_bn=sanitize_html(decision_bn or ""),
        decision_en=sanitize_html(decision_en or ""),
        is_frozen=False,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
    )
    resolution.current_version = version
    resolution.save(update_fields=["current_version", "updated_at"])

    log_governance(
        actor,
        "RESOLUTION_CREATE",
        "Resolution",
        resolution.pk,
        f"Created resolution {resolution.resolution_id}",
        new={"resolution_id": resolution.resolution_id, "meeting_id": str(meeting.pk)},
    )
    return resolution


@transaction.atomic
def update_draft_resolution(resolution: Resolution, *, actor=None, **fields) -> Resolution:
    """Update an unfrozen DRAFT resolution's current version."""
    resolution = (
        Resolution.objects.select_for_update(of=("self",))
        .select_related("current_version")
        .get(pk=resolution.pk)
    )
    if resolution.status != ResolutionStatus.DRAFT:
        raise ValueError("Only DRAFT resolutions can be edited.")

    version = resolution.current_version
    if version is None:
        raise ValueError("Resolution has no current version.")
    if version.is_frozen:
        raise ValueError("Current version is frozen and cannot be edited.")

    unknown = set(fields) - _DRAFT_EDITABLE
    if unknown:
        raise ValueError(f"Unsupported fields: {', '.join(sorted(unknown))}")

    cleaned = _sanitize_fields(fields)
    version_updates: list[str] = []
    for key, value in cleaned.items():
        setattr(version, key, value if value is not None else "")
        version_updates.append(key)
    if version_updates:
        version.save(update_fields=version_updates)

    res_updates: list[str] = []
    if "title_bn" in cleaned:
        resolution.title_bn = cleaned["title_bn"] or resolution.title_bn
        res_updates.append("title_bn")
    if "title_en" in cleaned:
        resolution.title_en = cleaned["title_en"] or ""
        res_updates.append("title_en")
    if res_updates:
        res_updates.append("updated_at")
        resolution.save(update_fields=res_updates)
    else:
        resolution.save(update_fields=["updated_at"])

    log_governance(
        actor,
        "RESOLUTION_UPDATE",
        "Resolution",
        resolution.pk,
        f"Updated draft {resolution.resolution_id}",
        new={k: cleaned[k] for k in cleaned},
    )
    return resolution


@transaction.atomic
def prepare_for_signing(resolution: Resolution, *, actor=None) -> Resolution:
    """Freeze the current version and mark READY_FOR_SIGNING."""
    resolution = (
        Resolution.objects.select_for_update(of=("self",))
        .select_related("current_version")
        .get(pk=resolution.pk)
    )
    if resolution.status != ResolutionStatus.DRAFT:
        raise ValueError("Only DRAFT resolutions can be prepared for signing.")

    version = resolution.current_version
    if version is None:
        raise ValueError("Resolution has no current version.")
    if not (version.content_bn or "").strip():
        raise ValueError("Resolution content is required before signing.")

    if not version.is_frozen:
        version.is_frozen = True
        version.save(update_fields=["is_frozen"])

    old = resolution.status
    resolution.status = ResolutionStatus.READY_FOR_SIGNING
    resolution.save(update_fields=["status", "updated_at"])

    log_governance(
        actor,
        "RESOLUTION_READY",
        "Resolution",
        resolution.pk,
        f"Prepared {resolution.resolution_id} for signing",
        old={"status": old},
        new={"status": resolution.status, "version": version.version_number},
    )
    return resolution


@transaction.atomic
def select_signers(
    resolution: Resolution,
    member_ids: Iterable,
    *,
    actor=None,
) -> list[ResolutionSigner]:
    """
    Select required signers from PRESENT (ATTENDED) meeting participants.

    Clears previous unsigned selections for the current version, then creates
    ResolutionSigner rows for the given members.
    """
    resolution = (
        Resolution.objects.select_for_update(of=("self",))
        .select_related("current_version", "meeting")
        .get(pk=resolution.pk)
    )
    version = resolution.current_version
    if version is None:
        raise ValueError("Resolution has no current version.")
    if resolution.status not in {
        ResolutionStatus.READY_FOR_SIGNING,
        ResolutionStatus.PARTIALLY_SIGNED,
    }:
        raise ValueError(
            "Signers can only be selected while the resolution is ready for signing "
            "or partially signed."
        )

    ids = list(member_ids)
    if not ids:
        raise ValueError("At least one signer is required.")

    present_ids = {
        str(pk)
        for pk in MeetingParticipant.objects.filter(
            meeting=resolution.meeting,
            status=ParticipantStatus.ATTENDED,
            member_id__in=ids,
        ).values_list("member_id", flat=True)
    }
    missing = [str(mid) for mid in ids if str(mid) not in present_ids]
    if missing:
        raise ValueError(
            "Only PRESENT (ATTENDED) participants may be selected as signers. "
            f"Not present: {', '.join(missing)}"
        )

    # Clear unsigned prior selections for this version.
    ResolutionSigner.objects.filter(version=version, signed_at__isnull=True).delete()

    already_signed = {
        str(pk)
        for pk in ResolutionSigner.objects.filter(
            version=version, signed_at__isnull=False
        ).values_list("member_id", flat=True)
    }

    created: list[ResolutionSigner] = []
    for mid in ids:
        if str(mid) in already_signed:
            continue
        signer, was_created = ResolutionSigner.objects.get_or_create(
            version=version,
            member_id=mid,
            defaults={
                "resolution": resolution,
                "selected_by": actor if getattr(actor, "is_authenticated", False) else None,
                "is_required": True,
            },
        )
        if was_created:
            created.append(signer)

    log_governance(
        actor,
        "RESOLUTION_SIGNERS",
        "Resolution",
        resolution.pk,
        f"Selected {len(ids)} signer(s) for {resolution.resolution_id} v{version.version_number}",
        new={"member_ids": [str(i) for i in ids], "created": len(created)},
    )
    return list(
        ResolutionSigner.objects.filter(version=version).select_related("member")
    )


@transaction.atomic
def sign_resolution(
    resolution: Resolution,
    member: Member,
    *,
    user,
    request=None,
    confirmation: bool = True,
) -> ResolutionSignature:
    """
    Apply the member's digital signature to the current frozen version.

    Verifies ownership, required-signer status, and that the member has not
    already signed. Snapshots ``member.signature_image`` into resolutions/signatures/.
    """
    if not confirmation:
        raise ValueError("Explicit confirmation is required to sign.")

    if user is None or not getattr(user, "is_authenticated", False):
        raise ValueError("Authentication required.")

    if member.user_id != getattr(user, "pk", None):
        raise ValueError("You may only sign as yourself.")

    if not member.signature_image:
        raise ValueError("Member has no signature image on file.")

    resolution = (
        Resolution.objects.select_for_update(of=("self",))
        .select_related("current_version")
        .get(pk=resolution.pk)
    )
    version = resolution.current_version
    if version is None or not version.is_frozen:
        raise ValueError("Current version must be frozen before signing.")

    if resolution.status not in {
        ResolutionStatus.READY_FOR_SIGNING,
        ResolutionStatus.PARTIALLY_SIGNED,
    }:
        raise ValueError(
            f"Cannot sign resolution in status {resolution.status}."
        )

    try:
        signer = ResolutionSigner.objects.select_for_update().get(
            version=version, member=member, is_required=True
        )
    except ResolutionSigner.DoesNotExist as exc:
        raise ValueError("Member is not a required signer for the current version.") from exc

    if signer.signed_at is not None or ResolutionSignature.objects.filter(
        signer=signer
    ).exists():
        raise ValueError("Member has already signed this version.")

    ip, ua = _request_meta(request)
    now = timezone.now()

    # Snapshot signature bytes into a separate media path.
    member.signature_image.open("rb")
    try:
        raw = member.signature_image.read()
    finally:
        member.signature_image.close()

    filename = os.path.basename(member.signature_image.name) or f"{member.member_id}.png"
    snapshot = ContentFile(raw, name=filename)

    signature = ResolutionSignature(
        signer=signer,
        version=version,
        member=member,
        signer_name=_member_display_name(member),
        signer_designation=_member_designation(member),
        member_id_snapshot=member.member_id,
        signed_at=now,
        ip_address=ip,
        user_agent=ua,
        confirmation_text="I confirm this digital signature on the resolution.",
    )
    signature.signature_image.save(filename, snapshot, save=False)
    signature.save()

    signer.signed_at = now
    signer.save(update_fields=["signed_at"])

    required = ResolutionSigner.objects.filter(version=version, is_required=True)
    signed_count = required.filter(signed_at__isnull=False).count()
    total_required = required.count()

    old_status = resolution.status
    if total_required > 0 and signed_count >= total_required:
        resolution.status = ResolutionStatus.FULLY_SIGNED
    else:
        resolution.status = ResolutionStatus.PARTIALLY_SIGNED
    resolution.save(update_fields=["status", "updated_at"])

    log_governance(
        user,
        "RESOLUTION_SIGN",
        "Resolution",
        resolution.pk,
        f"{member.member_id} signed {resolution.resolution_id} v{version.version_number}",
        old={"status": old_status},
        new={
            "status": resolution.status,
            "signed_count": signed_count,
            "required": total_required,
        },
    )
    logger.info(
        "Resolution %s signed by %s (%s/%s)",
        resolution.resolution_id,
        member.member_id,
        signed_count,
        total_required,
    )
    return signature


@transaction.atomic
def create_new_version(
    resolution: Resolution,
    *,
    reason: str,
    actor=None,
    **content,
) -> ResolutionVersion:
    """
    Open a new DRAFT version after READY / PARTIAL / FULLY (not FINALIZED).

    Signers are not carried forward — selections apply per version.
    """
    reason = (reason or "").strip()
    if not reason:
        raise ValueError("A change reason is required.")

    resolution = (
        Resolution.objects.select_for_update(of=("self",))
        .select_related("current_version")
        .get(pk=resolution.pk)
    )
    if resolution.status == ResolutionStatus.FINALIZED:
        raise ValueError("Finalized resolutions cannot receive new versions.")
    if resolution.status == ResolutionStatus.WITHDRAWN:
        raise ValueError("Withdrawn resolutions cannot receive new versions.")
    if resolution.status not in _REVERSION_FROM:
        raise ValueError(
            f"Cannot create a new version from status {resolution.status}."
        )

    previous = resolution.current_version
    if previous is None:
        raise ValueError("Resolution has no current version.")

    agg = resolution.versions.aggregate(m=Max("version_number"))
    next_number = int(agg["m"] or 0) + 1

    base = {
        "title_bn": previous.title_bn,
        "title_en": previous.title_en,
        "content_bn": previous.content_bn,
        "content_en": previous.content_en,
        "decision_bn": previous.decision_bn,
        "decision_en": previous.decision_en,
        "notes": previous.notes,
    }
    overrides = _sanitize_fields({k: v for k, v in content.items() if k in _DRAFT_EDITABLE})
    base.update(overrides)

    version = ResolutionVersion.objects.create(
        resolution=resolution,
        version_number=next_number,
        title_bn=base["title_bn"],
        title_en=base.get("title_en") or "",
        content_bn=base["content_bn"],
        content_en=base.get("content_en") or "",
        decision_bn=base.get("decision_bn") or "",
        decision_en=base.get("decision_en") or "",
        notes=base.get("notes") or "",
        previous_version=previous,
        change_reason=reason[:300],
        is_frozen=False,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
    )

    old_status = resolution.status
    resolution.current_version = version
    resolution.status = ResolutionStatus.DRAFT
    resolution.title_bn = version.title_bn
    resolution.title_en = version.title_en
    resolution.save(
        update_fields=[
            "current_version",
            "status",
            "title_bn",
            "title_en",
            "updated_at",
        ]
    )

    log_governance(
        actor,
        "RESOLUTION_VERSION",
        "Resolution",
        resolution.pk,
        f"New version v{next_number} for {resolution.resolution_id}: {reason}",
        old={"status": old_status, "version": previous.version_number},
        new={"status": resolution.status, "version": next_number, "reason": reason},
    )
    return version


@transaction.atomic
def finalize_resolution(resolution: Resolution, *, actor=None) -> Resolution:
    """Finalize a FULLY_SIGNED resolution."""
    resolution = Resolution.objects.select_for_update().get(pk=resolution.pk)
    if resolution.status != ResolutionStatus.FULLY_SIGNED:
        raise ValueError("Resolution must be FULLY_SIGNED before finalization.")

    old = resolution.status
    now = timezone.now()
    resolution.status = ResolutionStatus.FINALIZED
    resolution.finalized_at = now
    resolution.finalized_by = (
        actor if getattr(actor, "is_authenticated", False) else None
    )
    resolution.save(
        update_fields=["status", "finalized_at", "finalized_by", "updated_at"]
    )

    log_governance(
        actor,
        "RESOLUTION_FINALIZE",
        "Resolution",
        resolution.pk,
        f"Finalized {resolution.resolution_id}",
        old={"status": old},
        new={"status": resolution.status, "finalized_at": now.isoformat()},
    )
    return resolution
