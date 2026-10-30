"""Organizational position assignment, primary, effective dates, signature snapshot."""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from governance.models import ParticipantStatus
from governance.services.participants import add_participants_from_members, mark_attendance
from governance.services.resolutions import (
    create_resolution,
    prepare_for_signing,
    select_signers,
    sign_resolution,
)
from governance.tests.helpers import (
    create_approved_member,
    create_meeting,
    create_staff_with_permission,
    png_upload,
)
from members.models import CouncilBody, OrganizationalPosition
from members.positions import (
    assign_position,
    effective_assignments,
    end_position,
    member_position_snapshot,
    primary_assignment,
    set_primary_assignment,
)


class PositionAssignmentTests(TestCase):
    def setUp(self):
        self.user, self.member = create_approved_member(
            701, signature_image=png_upload("sig-pos.png")
        )
        self.chair = OrganizationalPosition.objects.create(
            name_en="Chairman",
            name_bn="চেয়ারম্যান",
            council_body=CouncilBody.EXECUTIVE,
            is_primary_eligible=True,
            display_order=1,
        )
        self.secretary = OrganizationalPosition.objects.create(
            name_en="Secretary",
            name_bn="সচিব",
            council_body=CouncilBody.EXECUTIVE,
            is_primary_eligible=True,
            display_order=2,
        )
        self.staff = create_staff_with_permission(
            "pos-staff@example.com", "members.manage_positions"
        )

    def test_multiple_positions_and_primary(self):
        today = timezone.localdate()
        a1 = assign_position(
            self.member,
            self.chair,
            start_date=today - timedelta(days=30),
            is_primary=True,
            actor=self.staff,
        )
        a2 = assign_position(
            self.member,
            self.secretary,
            start_date=today - timedelta(days=10),
            is_primary=False,
            actor=self.staff,
        )
        effective = list(effective_assignments(self.member))
        self.assertEqual(len(effective), 2)
        self.assertEqual(primary_assignment(self.member).pk, a1.pk)

        set_primary_assignment(a2, actor=self.staff)
        a1.refresh_from_db()
        a2.refresh_from_db()
        self.assertFalse(a1.is_primary)
        self.assertTrue(a2.is_primary)
        self.assertEqual(primary_assignment(self.member).pk, a2.pk)

    def test_date_effectiveness(self):
        today = timezone.localdate()
        assign_position(
            self.member,
            self.chair,
            start_date=today + timedelta(days=5),
            actor=self.staff,
        )
        self.assertEqual(effective_assignments(self.member).count(), 0)
        self.assertEqual(
            effective_assignments(self.member, on_date=today + timedelta(days=6)).count(),
            1,
        )

    def test_end_position_removes_from_effective(self):
        today = timezone.localdate()
        assignment = assign_position(
            self.member,
            self.chair,
            start_date=today - timedelta(days=1),
            is_primary=True,
            actor=self.staff,
        )
        end_position(assignment, end_date=today, actor=self.staff)
        self.assertEqual(effective_assignments(self.member).count(), 0)

    def test_signature_snapshot_uses_position(self):
        today = timezone.localdate()
        assign_position(
            self.member,
            self.chair,
            start_date=today - timedelta(days=1),
            is_primary=True,
            actor=self.staff,
        )
        snap = member_position_snapshot(self.member, lang="en")
        self.assertIn("Chairman", snap)
        self.assertIn("Executive", snap)

        meeting = create_meeting()
        staff = create_staff_with_permission(
            "pos-gov@example.com", "resolutions.manage_signers"
        )
        participant = add_participants_from_members(meeting, [self.member])[0]
        mark_attendance(participant, ParticipantStatus.ATTENDED, actor=staff)
        resolution = create_resolution(
            meeting,
            title_bn="পদবী পরীক্ষা",
            title_en="Position test",
            content_bn="বিষয়বস্তু",
            actor=staff,
        )
        prepare_for_signing(resolution, actor=staff)
        select_signers(resolution, [self.member.pk], actor=staff)
        sign_resolution(resolution, member=self.member, user=self.user)
        signature = resolution.current_version.signatures.get(member=self.member)
        self.assertTrue(
            "Chairman" in signature.signer_designation
            or "চেয়ারম্যান" in signature.signer_designation
        )
