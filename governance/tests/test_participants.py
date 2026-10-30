"""Participant roster, freeze, and eligibility snapshot tests."""

from django.test import TestCase

from governance.models import ParticipantStatus
from governance.services.participants import (
    add_participants_from_group,
    add_participants_from_members,
    freeze_eligible_roster,
    freeze_participants,
    live_eligible_members_qs,
    set_participant_response,
)
from governance.tests.helpers import (
    create_approved_member,
    create_meeting,
    create_meeting_type,
    create_member_group,
)
from members.models import MemberGroupMembership, MemberStatus


class ParticipantRosterTests(TestCase):
    def setUp(self):
        self.group = create_member_group("Executive")
        self.meeting_type = create_meeting_type(groups=[self.group])
        self.meeting = create_meeting(meeting_type=self.meeting_type)

        self.users = []
        self.members = []
        for i in range(4):
            user, member = create_approved_member(i)
            self.users.append(user)
            self.members.append(member)

        MemberGroupMembership.objects.create(group=self.group, member=self.members[0])
        MemberGroupMembership.objects.create(group=self.group, member=self.members[1])

    def test_add_individual_members(self):
        created = add_participants_from_members(self.meeting, [self.members[2]])
        self.assertEqual(len(created), 1)
        self.assertEqual(self.meeting.participants.count(), 1)
        participant = self.meeting.participants.get()
        self.assertEqual(participant.status, ParticipantStatus.INVITED)

    def test_add_from_group(self):
        created = add_participants_from_group(self.meeting, self.group)
        self.assertEqual(len(created), 2)
        self.assertEqual(self.meeting.participants.count(), 2)
        member_ids = set(
            self.meeting.participants.values_list("member_id", flat=True)
        )
        self.assertEqual(
            member_ids,
            {self.members[0].pk, self.members[1].pk},
        )

    def test_add_idempotent_for_same_member(self):
        add_participants_from_members(self.meeting, [self.members[0]])
        again = add_participants_from_members(self.meeting, [self.members[0]])
        self.assertEqual(again, [])
        self.assertEqual(self.meeting.participants.count(), 1)

    def test_freeze_participants_and_eligible_roster(self):
        add_participants_from_group(self.meeting, self.group)
        eligible_count = freeze_eligible_roster(self.meeting)
        self.meeting.refresh_from_db()
        self.assertEqual(eligible_count, 2)
        self.assertIsNotNone(self.meeting.eligible_frozen_at)

        freeze_participants(self.meeting)
        self.meeting.refresh_from_db()
        self.assertIsNotNone(self.meeting.participants_frozen_at)

    def test_eligible_freeze_idempotent(self):
        add_participants_from_group(self.meeting, self.group)
        first = freeze_eligible_roster(self.meeting)
        second = freeze_eligible_roster(self.meeting)
        self.assertEqual(first, second)
        self.assertEqual(self.meeting.eligible_members.count(), 2)

    def test_group_membership_change_after_freeze_does_not_change_eligible(self):
        add_participants_from_group(self.meeting, self.group)
        freeze_eligible_roster(self.meeting)
        frozen_ids = set(
            self.meeting.eligible_members.values_list("member_id", flat=True)
        )
        self.assertEqual(len(frozen_ids), 2)

        MemberGroupMembership.objects.create(group=self.group, member=self.members[2])
        self.assertEqual(live_eligible_members_qs(self.meeting).count(), 3)
        self.assertEqual(self.meeting.eligible_members.count(), 2)
        self.assertEqual(
            set(self.meeting.eligible_members.values_list("member_id", flat=True)),
            frozen_ids,
        )

    def test_cannot_add_participants_after_freeze(self):
        add_participants_from_members(self.meeting, [self.members[0]])
        freeze_participants(self.meeting)
        with self.assertRaises(ValueError) as ctx:
            add_participants_from_members(self.meeting, [self.members[1]])
        self.assertIn("frozen", str(ctx.exception).lower())

    def test_member_rsvp_accept(self):
        participant = add_participants_from_members(
            self.meeting, [self.members[0]]
        )[0]
        set_participant_response(
            participant,
            ParticipantStatus.ACCEPTED,
            user=self.users[0],
        )
        participant.refresh_from_db()
        self.assertEqual(participant.status, ParticipantStatus.ACCEPTED)
        self.assertIsNotNone(participant.responded_at)

    def test_non_invited_member_excluded_from_live_eligibility(self):
        _, pending = create_approved_member(99, status=MemberStatus.PENDING)
        self.assertNotIn(pending, live_eligible_members_qs(self.meeting))
