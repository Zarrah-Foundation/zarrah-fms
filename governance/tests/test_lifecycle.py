"""Meeting status lifecycle transitions."""

from django.test import TestCase

from governance.models import MeetingStatus
from governance.services.lifecycle import (
    ALLOWED_TRANSITIONS,
    assert_meeting_transition_allowed,
    transition_meeting,
)
from governance.tests.helpers import create_meeting


class MeetingLifecycleTests(TestCase):
    def setUp(self):
        self.meeting = create_meeting()

    def test_happy_path_transitions(self):
        path = [
            MeetingStatus.SCHEDULED,
            MeetingStatus.INVITATIONS_SENT,
            MeetingStatus.IN_PROGRESS,
            MeetingStatus.COMPLETED,
            MeetingStatus.FINALIZED,
            MeetingStatus.ARCHIVED,
        ]
        for status in path:
            transition_meeting(self.meeting, status)
            self.meeting.refresh_from_db()
            self.assertEqual(self.meeting.status, status)

    def test_cancel_from_draft(self):
        transition_meeting(self.meeting, MeetingStatus.CANCELLED)
        self.meeting.refresh_from_db()
        self.assertEqual(self.meeting.status, MeetingStatus.CANCELLED)

    def test_cancel_from_scheduled(self):
        transition_meeting(self.meeting, MeetingStatus.SCHEDULED)
        transition_meeting(self.meeting, MeetingStatus.CANCELLED)
        self.meeting.refresh_from_db()
        self.assertEqual(self.meeting.status, MeetingStatus.CANCELLED)

    def test_idempotent_same_status(self):
        transition_meeting(self.meeting, MeetingStatus.SCHEDULED)
        transition_meeting(self.meeting, MeetingStatus.SCHEDULED)
        self.meeting.refresh_from_db()
        self.assertEqual(self.meeting.status, MeetingStatus.SCHEDULED)

    def test_illegal_skip_forward(self):
        with self.assertRaises(ValueError) as ctx:
            transition_meeting(self.meeting, MeetingStatus.IN_PROGRESS)
        self.assertIn("Illegal meeting status transition", str(ctx.exception))

    def test_illegal_backward(self):
        transition_meeting(self.meeting, MeetingStatus.SCHEDULED)
        transition_meeting(self.meeting, MeetingStatus.INVITATIONS_SENT)
        transition_meeting(self.meeting, MeetingStatus.IN_PROGRESS)
        with self.assertRaises(ValueError):
            transition_meeting(self.meeting, MeetingStatus.SCHEDULED)

    def test_illegal_from_terminal_states(self):
        transition_meeting(self.meeting, MeetingStatus.SCHEDULED)
        transition_meeting(self.meeting, MeetingStatus.CANCELLED)
        with self.assertRaises(ValueError):
            transition_meeting(self.meeting, MeetingStatus.IN_PROGRESS)

        archived = create_meeting(title_en="Archived meeting")
        for status in (
            MeetingStatus.SCHEDULED,
            MeetingStatus.INVITATIONS_SENT,
            MeetingStatus.IN_PROGRESS,
            MeetingStatus.COMPLETED,
            MeetingStatus.FINALIZED,
            MeetingStatus.ARCHIVED,
        ):
            transition_meeting(archived, status)
        with self.assertRaises(ValueError):
            transition_meeting(archived, MeetingStatus.COMPLETED)

    def test_allowed_transitions_map(self):
        self.assertEqual(
            ALLOWED_TRANSITIONS[MeetingStatus.DRAFT],
            {MeetingStatus.SCHEDULED, MeetingStatus.CANCELLED},
        )
        self.assertEqual(
            ALLOWED_TRANSITIONS[MeetingStatus.INVITATIONS_SENT],
            {MeetingStatus.IN_PROGRESS},
        )

    def test_assert_helper_matches_service(self):
        assert_meeting_transition_allowed(MeetingStatus.DRAFT, MeetingStatus.SCHEDULED)
        with self.assertRaises(ValueError):
            assert_meeting_transition_allowed(MeetingStatus.DRAFT, MeetingStatus.COMPLETED)
