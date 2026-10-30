"""RBAC and IDOR protections for member meeting/resolution views."""

from django.test import Client, TestCase
from django.urls import reverse

from governance.models import ParticipantStatus, ResolutionStatus
from governance.services.participants import (
    add_participants_from_members,
    set_participant_response,
)
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
    ensure_rbac_seeded,
    png_upload,
)
from rbac.permissions import has_action


class GovernanceRBACAndIDORTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_rbac_seeded()

    def setUp(self):
        self.client = Client()
        self.meeting = create_meeting()

        self.user_a, self.member_a = create_approved_member(1)
        self.user_b, self.member_b = create_approved_member(2, signature_image=png_upload())
        self.participant_a = add_participants_from_members(
            self.meeting, [self.member_a]
        )[0]
        add_participants_from_members(self.meeting, [self.member_b])

    def test_member_cannot_rsvp_for_another_member(self):
        with self.assertRaises(ValueError) as ctx:
            set_participant_response(
                self.participant_a,
                ParticipantStatus.ACCEPTED,
                user=self.user_b,
            )
        self.assertIn("your own", str(ctx.exception).lower())

    def test_member_cannot_sign_as_another_via_service(self):
        staff = create_staff_with_permission(
            "idor-staff@example.com", "resolutions.manage_signers"
        )
        from governance.services.participants import mark_attendance

        resolution = create_resolution(
            self.meeting,
            title_bn="IDOR test",
            content_bn="<p>Body</p>",
            actor=staff,
        )
        prepare_for_signing(resolution, actor=staff)
        participant_b = self.meeting.participants.get(member=self.member_b)
        mark_attendance(
            participant_b,
            ParticipantStatus.ATTENDED,
            actor=create_staff_with_permission(
                "idor-attendance2@example.com", "meetings.manage_attendance"
            ),
        )
        select_signers(resolution, [self.member_b.pk], actor=staff)

        with self.assertRaises(ValueError):
            sign_resolution(
                resolution,
                self.member_b,
                user=self.user_a,
                confirmation=True,
            )

    def test_admin_with_meetings_view_can_list(self):
        admin = create_staff_with_permission("meetings-view@example.com", "meetings.view")
        self.assertTrue(has_action(admin, "meetings", "view"))

        self.client.force_login(admin)
        resp = self.client.get(reverse("dashboard-meetings"))
        self.assertEqual(resp.status_code, 200)

    def test_member_without_meetings_view_redirected_from_admin_list(self):
        self.client.force_login(self.user_a)
        resp = self.client.get(reverse("dashboard-meetings"))
        self.assertEqual(resp.status_code, 302)

    def test_member_can_rsvp_own_invite_via_view(self):
        self.client.force_login(self.user_a)
        url = reverse("my-meeting-detail", kwargs={"pk": self.meeting.pk})
        resp = self.client.post(
            url,
            {"response": ParticipantStatus.ACCEPTED},
        )
        self.assertEqual(resp.status_code, 302)
        self.participant_a.refresh_from_db()
        self.assertEqual(self.participant_a.status, ParticipantStatus.ACCEPTED)

    def test_member_cannot_access_resolution_they_do_not_sign(self):
        staff = create_staff_with_permission(
            "idor-staff2@example.com", "resolutions.manage_signers"
        )
        from governance.services.participants import mark_attendance

        resolution = create_resolution(
            self.meeting,
            title_bn="Private resolution",
            content_bn="<p>Body</p>",
            actor=staff,
        )
        prepare_for_signing(resolution, actor=staff)
        participant_b = self.meeting.participants.get(member=self.member_b)
        mark_attendance(
            participant_b,
            ParticipantStatus.ATTENDED,
            actor=create_staff_with_permission(
                "idor-attendance@example.com", "meetings.manage_attendance"
            ),
        )
        select_signers(resolution, [self.member_b.pk], actor=staff)

        self.client.force_login(self.user_a)
        url = reverse("my-resolution-detail", kwargs={"pk": resolution.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        resolution.refresh_from_db()
        self.assertEqual(resolution.status, ResolutionStatus.READY_FOR_SIGNING)
