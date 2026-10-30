"""Meeting status lifecycle transitions."""

from __future__ import annotations

import logging

from django.db import transaction

from governance.models import Meeting, MeetingStatus
from governance.services.audit import log_governance

logger = logging.getLogger(__name__)

# Linear happy-path plus cancel from early states.
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    MeetingStatus.DRAFT: {MeetingStatus.SCHEDULED, MeetingStatus.CANCELLED},
    MeetingStatus.SCHEDULED: {
        MeetingStatus.INVITATIONS_SENT,
        MeetingStatus.CANCELLED,
    },
    MeetingStatus.INVITATIONS_SENT: {MeetingStatus.IN_PROGRESS},
    MeetingStatus.IN_PROGRESS: {MeetingStatus.COMPLETED},
    MeetingStatus.COMPLETED: {MeetingStatus.FINALIZED},
    MeetingStatus.FINALIZED: {MeetingStatus.ARCHIVED},
    MeetingStatus.ARCHIVED: set(),
    MeetingStatus.CANCELLED: set(),
}


def assert_meeting_transition_allowed(current: str, new_status: str) -> None:
    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        raise ValueError(
            f"Illegal meeting status transition: {current} → {new_status}."
        )


@transaction.atomic
def transition_meeting(meeting: Meeting, new_status: str, *, actor=None) -> Meeting:
    """
    Move ``meeting`` to ``new_status`` if the transition is allowed.

    Raises ``ValueError`` on illegal transitions.
    """
    meeting = Meeting.objects.select_for_update().get(pk=meeting.pk)
    old_status = meeting.status
    new_status = str(new_status)

    if old_status == new_status:
        return meeting

    assert_meeting_transition_allowed(old_status, new_status)

    meeting.status = new_status
    meeting.save(update_fields=["status", "updated_at"])

    log_governance(
        actor,
        "MEETING_STATUS",
        "Meeting",
        meeting.pk,
        f"Meeting {meeting.reference_id}: {old_status} → {new_status}",
        old={"status": old_status},
        new={"status": new_status},
    )
    logger.info(
        "Meeting %s transitioned %s → %s",
        meeting.reference_id,
        old_status,
        new_status,
    )
    return meeting
