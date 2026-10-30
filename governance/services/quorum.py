"""Quorum calculation for meetings."""

from __future__ import annotations

from governance.models import Meeting, MeetingParticipant, ParticipantStatus
from governance.services.participants import live_eligible_members_qs


def _eligible_count(meeting: Meeting) -> int:
    """Frozen eligible roster is authoritative once freeze has occurred."""
    if meeting.eligible_frozen_at:
        return meeting.eligible_members.count()
    return live_eligible_members_qs(meeting).count()


def _present_member_count(meeting: Meeting) -> int:
    """
    Count ATTENDED member participants only.

    Guests never count. When the eligible roster is frozen, only attended
    members who appear on that frozen roster count toward quorum.
    """
    qs = MeetingParticipant.objects.filter(
        meeting=meeting,
        status=ParticipantStatus.ATTENDED,
    )
    if meeting.eligible_frozen_at:
        eligible_ids = meeting.eligible_members.values_list("member_id", flat=True)
        qs = qs.filter(member_id__in=eligible_ids)
    return qs.count()


def quorum_snapshot(meeting: Meeting) -> dict:
    """
    Return quorum metrics for ``meeting``.

    Keys: eligible_count, required, present_count, achieved.
    required = ceil(eligible * numerator / denominator) via MeetingType.required_quorum.
    Guests never count. Frozen eligible roster is authoritative after freeze.
    """
    eligible_count = _eligible_count(meeting)
    required = meeting.meeting_type.required_quorum(eligible_count)
    present_count = _present_member_count(meeting)
    achieved = bool(required > 0 and present_count >= required)

    return {
        "eligible_count": eligible_count,
        "required": required,
        "present_count": present_count,
        "achieved": achieved,
        "status": "ACHIEVED" if achieved else "NOT ACHIEVED",
    }
