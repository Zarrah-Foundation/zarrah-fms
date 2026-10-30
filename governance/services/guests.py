"""External meeting guests — never members, never signers, never quorum."""

from __future__ import annotations

import logging

from django.db import transaction

from governance.models import GuestStatus, Meeting, MeetingGuest
from governance.services.audit import log_governance

logger = logging.getLogger(__name__)

_GUEST_STATUSES = {c.value for c in GuestStatus}
_ATTENDANCE_STATUSES = {GuestStatus.PRESENT, GuestStatus.ABSENT}
_RESPONSE_STATUSES = {GuestStatus.ACCEPTED, GuestStatus.DECLINED}


@transaction.atomic
def add_guest(
    meeting: Meeting,
    *,
    full_name: str,
    organization: str = "",
    designation: str = "",
    email: str = "",
    phone: str = "",
    notes: str = "",
    status: str = GuestStatus.INVITED,
    actor=None,
) -> MeetingGuest:
    """Invite an external guest on ``meeting``."""
    meeting = Meeting.objects.select_for_update().get(pk=meeting.pk)
    full_name = (full_name or "").strip()
    if not full_name:
        raise ValueError("Guest full_name is required.")

    status = str(status or GuestStatus.INVITED)
    if status not in _GUEST_STATUSES:
        raise ValueError(f"Invalid guest status: {status}")

    guest = MeetingGuest.objects.create(
        meeting=meeting,
        full_name=full_name,
        organization=(organization or "").strip(),
        designation=(designation or "").strip(),
        email=(email or "").strip(),
        phone=(phone or "").strip(),
        notes=notes or "",
        status=status,
    )
    log_governance(
        actor,
        "GUEST_ADD",
        "MeetingGuest",
        guest.pk,
        f"Added guest {full_name} to {meeting.reference_id}",
        new={"status": status},
    )
    return guest


@transaction.atomic
def update_guest(
    guest: MeetingGuest,
    *,
    actor=None,
    **fields,
) -> MeetingGuest:
    """Update guest profile fields. Guests remain non-members."""
    guest = MeetingGuest.objects.select_for_update().select_related("meeting").get(
        pk=guest.pk
    )
    allowed = {
        "full_name",
        "organization",
        "designation",
        "email",
        "phone",
        "notes",
    }
    updates = []
    old = {}
    new = {}
    for key, value in fields.items():
        if key not in allowed:
            raise ValueError(f"Field '{key}' cannot be updated on guests.")
        if key == "full_name":
            value = (value or "").strip()
            if not value:
                raise ValueError("Guest full_name is required.")
        elif key in ("organization", "designation", "email", "phone") and value is not None:
            value = str(value).strip()
        old[key] = getattr(guest, key)
        setattr(guest, key, value)
        new[key] = value
        updates.append(key)

    if updates:
        updates.append("updated_at")
        guest.save(update_fields=updates)
        log_governance(
            actor,
            "GUEST_UPDATE",
            "MeetingGuest",
            guest.pk,
            f"Updated guest on {guest.meeting.reference_id}",
            old=old,
            new=new,
        )
    return guest


@transaction.atomic
def set_guest_status(
    guest: MeetingGuest,
    status: str,
    *,
    actor=None,
) -> MeetingGuest:
    """Set guest status within the migration-defined GuestStatus set."""
    guest = MeetingGuest.objects.select_for_update().select_related("meeting").get(
        pk=guest.pk
    )
    status = str(status)
    if status not in _GUEST_STATUSES:
        raise ValueError(f"Invalid guest status: {status}")

    old = guest.status
    if old == status:
        return guest

    guest.status = status
    guest.save(update_fields=["status", "updated_at"])
    log_governance(
        actor,
        "GUEST_STATUS",
        "MeetingGuest",
        guest.pk,
        f"Guest status {old} → {status} on {guest.meeting.reference_id}",
        old={"status": old},
        new={"status": status},
    )
    return guest


@transaction.atomic
def mark_guest_attendance(
    guest: MeetingGuest,
    status: str,
    *,
    actor=None,
) -> MeetingGuest:
    """Record guest PRESENT or ABSENT (never counts toward quorum)."""
    status = str(status)
    if status not in _ATTENDANCE_STATUSES:
        raise ValueError("Guest attendance must be PRESENT or ABSENT.")
    return set_guest_status(guest, status, actor=actor)


@transaction.atomic
def set_guest_response(
    guest: MeetingGuest,
    status: str,
    *,
    actor=None,
) -> MeetingGuest:
    """Record guest ACCEPTED or DECLINED RSVP."""
    status = str(status)
    if status not in _RESPONSE_STATUSES:
        raise ValueError("Guest response must be ACCEPTED or DECLINED.")
    return set_guest_status(guest, status, actor=actor)


@transaction.atomic
def delete_guest(guest: MeetingGuest, *, actor=None) -> None:
    guest = MeetingGuest.objects.select_for_update().select_related("meeting").get(
        pk=guest.pk
    )
    pk = guest.pk
    meeting_ref = guest.meeting.reference_id
    guest.delete()
    log_governance(
        actor,
        "GUEST_DELETE",
        "MeetingGuest",
        pk,
        f"Removed guest from {meeting_ref}",
    )


def assert_guest_cannot_sign(guest: MeetingGuest) -> None:
    """Hard guard — guests are never resolution signers."""
    raise ValueError(
        f"Guests cannot sign resolutions (guest={guest.pk}). "
        "Only PRESENT (ATTENDED) selected members may sign."
    )
