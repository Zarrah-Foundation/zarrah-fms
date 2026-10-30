"""Guest quorum exclusion and ceiling quorum math."""

from django.test import TestCase

from governance.models import GuestStatus, ParticipantStatus
from governance.services.guests import add_guest
from governance.services.participants import (
    add_participants_from_members,
    freeze_eligible_roster,
    mark_attendance,
)
from governance.services.quorum import quorum_snapshot
from governance.tests.helpers import (
    create_approved_member,
    create_meeting,
    create_meeting_type,
    create_staff_with_permission,
)
from governance.models import EligibilityMode


class QuorumMathTests(TestCase):
    def test_meeting_type_required_quorum_ceil(self):
        mt_two_thirds = create_meeting_type(
            slug="two-thirds",
            quorum_numerator=2,
            quorum_denominator=3,
        )
        self.assertEqual(mt_two_thirds.required_quorum(10), 7)
        self.assertEqual(mt_two_thirds.required_quorum(0), 0)

        mt_one_third = create_meeting_type(
            slug="one-third",
            quorum_numerator=1,
            quorum_denominator=3,
        )
        self.assertEqual(mt_one_third.required_quorum(5), 2)

    def test_quorum_snapshot_uses_frozen_eligible_count(self):
        mt = create_meeting_type(
            slug="frozen-quorum",
            quorum_numerator=2,
            quorum_denominator=3,
            eligibility_mode=EligibilityMode.ALL_APPROVED,
        )
        meeting = create_meeting(meeting_type=mt)
        members = [create_approved_member(i)[1] for i in range(10)]
        add_participants_from_members(meeting, members)
        freeze_eligible_roster(meeting)

        snap = quorum_snapshot(meeting)
        self.assertEqual(snap["eligible_count"], 10)
        self.assertEqual(snap["required"], 7)
        self.assertEqual(snap["present_count"], 0)
        self.assertFalse(snap["achieved"])

    def test_guests_never_count_for_quorum(self):
        mt = create_meeting_type(
            slug="guest-quorum",
            quorum_numerator=1,
            quorum_denominator=1,
            eligibility_mode=EligibilityMode.ALL_APPROVED,
        )
        meeting = create_meeting(meeting_type=mt)
        user, member = create_approved_member(50)
        participant = add_participants_from_members(meeting, [member])[0]
        freeze_eligible_roster(meeting)

        staff = create_staff_with_permission(
            "staff-quorum@example.com", "meetings.manage_attendance"
        )
        mark_attendance(participant, ParticipantStatus.ATTENDED, actor=staff)

        add_guest(
            meeting,
            full_name="External Guest",
            status=GuestStatus.PRESENT,
        )
        add_guest(
            meeting,
            full_name="Another Guest",
            status=GuestStatus.PRESENT,
        )

        snap = quorum_snapshot(meeting)
        self.assertEqual(snap["present_count"], 1)
        self.assertTrue(snap["achieved"])

    def test_quorum_achieved_when_present_meets_required(self):
        mt = create_meeting_type(
            slug="achieve-quorum",
            quorum_numerator=1,
            quorum_denominator=3,
            eligibility_mode=EligibilityMode.ALL_APPROVED,
        )
        meeting = create_meeting(meeting_type=mt)
        members = [create_approved_member(60 + i)[1] for i in range(5)]
        participants = add_participants_from_members(meeting, members)
        freeze_eligible_roster(meeting)

        staff = create_staff_with_permission(
            "staff-q2@example.com", "meetings.manage_attendance"
        )
        for p in participants[:2]:
            mark_attendance(p, ParticipantStatus.ATTENDED, actor=staff)

        snap = quorum_snapshot(meeting)
        self.assertEqual(snap["required"], 2)
        self.assertEqual(snap["present_count"], 2)
        self.assertTrue(snap["achieved"])
