"""Meeting participant roster, eligibility freeze, RSVP, and attendance."""

from __future__ import annotations

import logging
from typing import Iterable

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from governance.models import (
    EligibilityMode,
    Meeting,
    MeetingEligibleMember,
    MeetingParticipant,
    ParticipantStatus,
)
from governance.services.audit import log_governance
from members.models import Member, MemberGroup, MemberStatus

logger = logging.getLogger(__name__)

_RESPONSE_STATUSES = {ParticipantStatus.ACCEPTED, ParticipantStatus.DECLINED}
_ATTENDANCE_STATUSES = {ParticipantStatus.ATTENDED, ParticipantStatus.ABSENT}
_ATTENDANCE_FROM = {
    ParticipantStatus.ACCEPTED,
    ParticipantStatus.INVITED,
    ParticipantStatus.ATTENDED,
    ParticipantStatus.ABSENT,
}


def _as_member_list(members: Iterable[Member]) -> list[Member]:
    if isinstance(members, QuerySet):
        return list(members)
    return list(members)


def approved_members_in_group(group: MemberGroup) -> QuerySet[Member]:
    return Member.objects.filter(
        status=MemberStatus.APPROVED,
        group_memberships__group=group,
    ).distinct()


def live_eligible_members_qs(meeting: Meeting) -> QuerySet[Member]:
    """Eligible population before freeze (does not write)."""
    mt = meeting.meeting_type
    qs = Member.objects.filter(status=MemberStatus.APPROVED)
    mode = mt.eligibility_mode or EligibilityMode.LINKED_GROUPS

    if mode == EligibilityMode.ALL_APPROVED:
        return qs

    group_ids = list(mt.eligibility_groups.values_list("pk", flat=True))
    if not group_ids:
        return qs.none()
    return qs.filter(group_memberships__group_id__in=group_ids).distinct()


def _ensure_participants_mutable(meeting: Meeting) -> None:
    if meeting.participants_frozen_at:
        raise ValueError("Meeting participants are frozen and cannot be changed.")


@transaction.atomic
def add_participants_from_members(
    meeting: Meeting,
    members,
    *,
    actor=None,
    source_group: MemberGroup | None = None,
) -> list[MeetingParticipant]:
    """Add or refresh participants for the given members (idempotent per member)."""
    meeting = Meeting.objects.select_for_update().get(pk=meeting.pk)
    _ensure_participants_mutable(meeting)

    created: list[MeetingParticipant] = []
    now = timezone.now()
    for member in _as_member_list(members):
        participant, was_created = MeetingParticipant.objects.get_or_create(
            meeting=meeting,
            member=member,
            defaults={
                "status": ParticipantStatus.INVITED,
                "source_group": source_group,
                "invited_at": now,
            },
        )
        if was_created:
            created.append(participant)
        elif source_group and participant.source_group_id is None:
            participant.source_group = source_group
            participant.save(update_fields=["source_group", "updated_at"])

    if created:
        log_governance(
            actor,
            "PARTICIPANTS_ADD",
            "Meeting",
            meeting.pk,
            f"Added {len(created)} participant(s) to {meeting.reference_id}",
            new={"added": len(created), "source_group_id": str(source_group.pk) if source_group else None},
        )
    return created


@transaction.atomic
def add_participants_from_group(
    meeting: Meeting,
    group: MemberGroup,
    *,
    actor=None,
) -> list[MeetingParticipant]:
    """Resolve APPROVED members in ``group`` and add them as participants."""
    members = approved_members_in_group(group)
    return add_participants_from_members(
        meeting, members, actor=actor, source_group=group
    )


@transaction.atomic
def freeze_eligible_roster(meeting: Meeting, *, actor=None) -> int:
    """
    Snapshot quorum-eligible members into MeetingEligibleMember rows.

    Idempotent when ``eligible_frozen_at`` is already set.
    """
    meeting = Meeting.objects.select_for_update().get(pk=meeting.pk)
    if meeting.eligible_frozen_at:
        return meeting.eligible_members.count()

    now = timezone.now()
    members = list(live_eligible_members_qs(meeting))
    MeetingEligibleMember.objects.bulk_create(
        [
            MeetingEligibleMember(meeting=meeting, member=m, frozen_at=now)
            for m in members
        ],
        ignore_conflicts=True,
    )
    meeting.eligible_frozen_at = now
    meeting.save(update_fields=["eligible_frozen_at", "updated_at"])

    count = meeting.eligible_members.count()
    log_governance(
        actor,
        "ELIGIBLE_FREEZE",
        "Meeting",
        meeting.pk,
        f"Froze eligible roster for {meeting.reference_id} ({count} members)",
        new={"eligible_count": count, "frozen_at": now.isoformat()},
    )
    logger.info("Froze eligible roster for %s: %s", meeting.reference_id, count)
    return count


@transaction.atomic
def freeze_participants(meeting: Meeting) -> Meeting:
    """Lock the participant list (sets ``participants_frozen_at``)."""
    meeting = Meeting.objects.select_for_update().get(pk=meeting.pk)
    if meeting.participants_frozen_at:
        return meeting
    meeting.participants_frozen_at = timezone.now()
    meeting.save(update_fields=["participants_frozen_at", "updated_at"])
    return meeting


@transaction.atomic
def set_participant_response(
    participant: MeetingParticipant,
    status: str,
    *,
    user,
) -> MeetingParticipant:
    """
    Member RSVP: ACCEPTED or DECLINED from INVITED only.

    Enforces ownership via ``participant.member.user == user``.
    """
    participant = (
        MeetingParticipant.objects.select_for_update()
        .select_related("member")
        .get(pk=participant.pk)
    )
    status = str(status)

    if status not in _RESPONSE_STATUSES:
        raise ValueError("Response status must be ACCEPTED or DECLINED.")

    if user is None or not getattr(user, "is_authenticated", False):
        raise ValueError("Authentication required.")

    if participant.member.user_id != getattr(user, "pk", None):
        raise ValueError("You may only respond for your own invitation.")

    if participant.status != ParticipantStatus.INVITED:
        raise ValueError(
            f"Cannot respond from status {participant.status}; expected INVITED."
        )

    old = participant.status
    participant.status = status
    participant.responded_at = timezone.now()
    participant.save(update_fields=["status", "responded_at", "updated_at"])

    log_governance(
        user,
        "PARTICIPANT_RESPONSE",
        "MeetingParticipant",
        participant.pk,
        f"RSVP {old} → {status}",
        old={"status": old},
        new={"status": status},
    )
    return participant


def present_participants_qs(meeting: Meeting) -> QuerySet[MeetingParticipant]:
    """Participants marked PRESENT (ATTENDED) — candidates for resolution signing."""
    return MeetingParticipant.objects.filter(
        meeting=meeting,
        status=ParticipantStatus.ATTENDED,
    ).select_related("member")


def present_member_ids(meeting: Meeting) -> list:
    """Member PKs eligible to be selected as resolution signers."""
    return list(present_participants_qs(meeting).values_list("member_id", flat=True))


def _actor_is_staff(actor) -> bool:
    if actor is None:
        return False
    return bool(getattr(actor, "is_staff", False) or getattr(actor, "is_superuser", False))


def member_has_signed_meeting_resolution(meeting: Meeting, member: Member) -> bool:
    """True if member has an immutable signature on any resolution for this meeting."""
    from governance.models import ResolutionSignature

    return ResolutionSignature.objects.filter(
        member=member,
        version__resolution__meeting=meeting,
    ).exists()


@transaction.atomic
def mark_attendance(
    participant: MeetingParticipant,
    status: str,
    *,
    actor,
) -> MeetingParticipant:
    """
    Staff attendance: ATTENDED or ABSENT.

    Supports Present ↔ Absent correction from INVITED/ACCEPTED/ATTENDED/ABSENT.
    Hard-blocks changes that would remove present status when the member has
    already signed a resolution for this meeting (historical integrity).
    """
    participant = MeetingParticipant.objects.select_for_update().select_related(
        "member", "meeting"
    ).get(pk=participant.pk)
    status = str(status)

    if not _actor_is_staff(actor):
        raise ValueError("Only staff may mark attendance.")

    if status not in _ATTENDANCE_STATUSES:
        raise ValueError("Attendance status must be ATTENDED or ABSENT.")

    if participant.status not in _ATTENDANCE_FROM:
        raise ValueError(
            f"Cannot mark attendance from status {participant.status}; "
            "expected INVITED, ACCEPTED, ATTENDED, or ABSENT."
        )

    old = participant.status
    if old == status:
        return participant

    # Protect signed records: do not strip Present after an official signature.
    if (
        old == ParticipantStatus.ATTENDED
        and status == ParticipantStatus.ABSENT
        and member_has_signed_meeting_resolution(participant.meeting, participant.member)
    ):
        log_governance(
            actor,
            "ATTENDANCE_BLOCKED",
            "MeetingParticipant",
            participant.pk,
            "Blocked Present→Absent: member has signed a resolution for this meeting",
            old={"status": old},
            new={"status": status, "blocked": True},
        )
        raise ValueError(
            "Cannot mark Absent: this member has already signed an official "
            "resolution for this meeting. Historical signatures remain immutable."
        )

    now = timezone.now()
    participant.status = status
    participant.attendance_marked_at = now
    participant.attendance_marked_by = actor
    participant.save(
        update_fields=[
            "status",
            "attendance_marked_at",
            "attendance_marked_by",
            "updated_at",
        ]
    )

    log_governance(
        actor,
        "ATTENDANCE",
        "MeetingParticipant",
        participant.pk,
        f"Attendance {old} → {status}",
        old={"status": old},
        new={"status": status},
    )
    return participant
