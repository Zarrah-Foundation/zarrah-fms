"""Present ↔ Absent attendance corrections and signed-block integrity."""

from django.test import TestCase

from governance.models import ParticipantStatus
from governance.services.participants import (
    add_participants_from_members,
    mark_attendance,
)
from governance.services.quorum import quorum_snapshot
from governance.services.resolutions import (
    create_resolution,
    prepare_for_signing,
    select_signers,
    sign_resolution,
)
from governance.tests.helpers import (
    create_approved_member,
    create_meeting,
    create_meeting_type,
    create_member_group,
    create_staff_with_permission,
    png_upload,
)
from members.models import MemberGroupMembership


class AttendanceReversalTests(TestCase):
    def setUp(self):
        self.group = create_member_group("Attendance Council")
        self.meeting_type = create_meeting_type(
            quorum_numerator=1,
            quorum_denominator=2,
            groups=[self.group],
        )
        self.meeting = create_meeting(meeting_type=self.meeting_type)
        self.staff = create_staff_with_permission(
            "att-staff@example.com", "meetings.manage_attendance"
        )
        self.user, self.member = create_approved_member(
            801, signature_image=png_upload("att-sig.png")
        )
        MemberGroupMembership.objects.create(group=self.group, member=self.member)
        self.participant = add_participants_from_members(
            self.meeting, [self.member]
        )[0]

    def test_present_absent_toggle(self):
        mark_attendance(
            self.participant, ParticipantStatus.ATTENDED, actor=self.staff
        )
        self.participant.refresh_from_db()
        self.assertEqual(self.participant.status, ParticipantStatus.ATTENDED)

        mark_attendance(self.participant, ParticipantStatus.ABSENT, actor=self.staff)
        self.participant.refresh_from_db()
        self.assertEqual(self.participant.status, ParticipantStatus.ABSENT)

        mark_attendance(
            self.participant, ParticipantStatus.ATTENDED, actor=self.staff
        )
        self.participant.refresh_from_db()
        self.assertEqual(self.participant.status, ParticipantStatus.ATTENDED)

    def test_quorum_updates_with_reversal(self):
        from governance.services.participants import freeze_eligible_roster

        freeze_eligible_roster(self.meeting)
        mark_attendance(
            self.participant, ParticipantStatus.ATTENDED, actor=self.staff
        )
        snap = quorum_snapshot(self.meeting)
        self.assertTrue(snap["achieved"])

        mark_attendance(self.participant, ParticipantStatus.ABSENT, actor=self.staff)
        snap = quorum_snapshot(self.meeting)
        self.assertFalse(snap["achieved"])

    def test_signed_blocks_present_to_absent(self):
        staff = create_staff_with_permission(
            "att-sign@example.com", "resolutions.manage_signers"
        )
        mark_attendance(
            self.participant, ParticipantStatus.ATTENDED, actor=self.staff
        )
        resolution = create_resolution(
            self.meeting,
            title_bn="স্বাক্ষর পরীক্ষা",
            content_bn="<p>Body</p>",
            actor=staff,
        )
        prepare_for_signing(resolution, actor=staff)
        select_signers(resolution, [self.member.pk], actor=staff)
        sign_resolution(resolution, member=self.member, user=self.user)

        with self.assertRaises(ValueError) as ctx:
            mark_attendance(
                self.participant, ParticipantStatus.ABSENT, actor=self.staff
            )
        self.assertIn("signed", str(ctx.exception).lower())
        self.participant.refresh_from_db()
        self.assertEqual(self.participant.status, ParticipantStatus.ATTENDED)
