"""Resolution drafting, signing, versioning, and finalization."""

import io
import re
from unittest.mock import MagicMock

from django.core.files.base import ContentFile
from django.test import TestCase
from django.utils import timezone
from PIL import Image

from governance.models import ParticipantStatus, ResolutionStatus, ResolutionSignature
from governance.sequences import generate_resolution_id
from governance.services.participants import (
    add_participants_from_members,
    mark_attendance,
)
from governance.services.resolutions import (
    create_new_version,
    create_resolution,
    finalize_resolution,
    prepare_for_signing,
    select_signers,
    sign_resolution,
    update_draft_resolution,
)
from governance.tests.helpers import (
    create_approved_member,
    create_meeting,
    create_staff_with_permission,
    png_upload,
)


class ResolutionLifecycleTests(TestCase):
    def setUp(self):
        self.meeting = create_meeting()
        self.staff = create_staff_with_permission(
            "res-staff@example.com", "resolutions.manage_signers"
        )

        self.signers_users = []
        self.signers = []
        for i in range(3):
            sig_file = png_upload(f"sig-{i}.png")
            user, member = create_approved_member(100 + i, signature_image=sig_file)
            participant = add_participants_from_members(self.meeting, [member])[0]
            mark_attendance(
                participant,
                ParticipantStatus.ATTENDED,
                actor=self.staff,
            )
            self.signers_users.append(user)
            self.signers.append(member)

        self.absent_user, self.absent_member = create_approved_member(
            200, signature_image=png_upload("absent.png")
        )
        absent_participant = add_participants_from_members(
            self.meeting, [self.absent_member]
        )[0]
        mark_attendance(
            absent_participant,
            ParticipantStatus.ABSENT,
            actor=self.staff,
        )

    def _draft(self, *, title_bn="খসড়া"):
        return create_resolution(
            self.meeting,
            title_bn=title_bn,
            content_bn="<p>Resolution body</p>",
            actor=self.staff,
        )

    def test_resolution_id_sequential_format(self):
        when = timezone.localdate()
        r1 = create_resolution(
            self.meeting,
            title_bn="One",
            content_bn="<p>One</p>",
        )
        r2 = create_resolution(
            self.meeting,
            title_bn="Two",
            content_bn="<p>Two</p>",
        )
        pattern = re.compile(rf"^ZF-{when.year}-{when.month:02d}-\d{{3}}$")
        self.assertRegex(r1.resolution_id, pattern)
        self.assertRegex(r2.resolution_id, pattern)
        self.assertNotEqual(r1.resolution_id, r2.resolution_id)

        seq1 = int(r1.resolution_id.rsplit("-", 1)[-1])
        seq2 = int(r2.resolution_id.rsplit("-", 1)[-1])
        self.assertEqual(seq2, seq1 + 1)

    def test_generate_resolution_id_matches_format(self):
        rid = generate_resolution_id()
        when = timezone.localdate()
        self.assertEqual(rid, f"ZF-{when.year}-{when.month:02d}-{int(rid[-3:]):03d}")

    def test_draft_edit_before_freeze(self):
        resolution = self._draft()
        update_draft_resolution(
            resolution,
            title_bn="Updated title",
            content_bn="<p>Updated content</p>",
            actor=self.staff,
        )
        resolution.refresh_from_db()
        self.assertEqual(resolution.title_bn, "Updated title")
        self.assertEqual(
            resolution.current_version.content_bn,
            "<p>Updated content</p>",
        )

    def test_prepare_for_signing_freezes_version(self):
        resolution = self._draft()
        prepare_for_signing(resolution, actor=self.staff)
        resolution.refresh_from_db()
        self.assertTrue(resolution.current_version.is_frozen)
        self.assertEqual(resolution.status, ResolutionStatus.READY_FOR_SIGNING)

        with self.assertRaises(ValueError):
            update_draft_resolution(resolution, title_bn="Too late")

    def test_select_signers_only_present(self):
        resolution = self._draft()
        prepare_for_signing(resolution, actor=self.staff)

        selected = select_signers(
            resolution,
            [self.signers[0].pk, self.signers[1].pk],
            actor=self.staff,
        )
        self.assertEqual(len(selected), 2)

        with self.assertRaises(ValueError) as ctx:
            select_signers(
                resolution,
                [self.absent_member.pk],
                actor=self.staff,
            )
        self.assertIn("PRESENT", str(ctx.exception))

    def test_sign_with_confirmation_and_status_progression(self):
        resolution = self._draft()
        prepare_for_signing(resolution, actor=self.staff)
        select_signers(
            resolution,
            [self.signers[0].pk, self.signers[1].pk],
            actor=self.staff,
        )

        request = MagicMock()
        request.META = {"HTTP_USER_AGENT": "TestAgent/1.0", "REMOTE_ADDR": "127.0.0.1"}

        with self.assertRaises(ValueError):
            sign_resolution(
                resolution,
                self.signers[0],
                user=self.signers_users[0],
                confirmation=False,
            )

        sign_resolution(
            resolution,
            self.signers[0],
            user=self.signers_users[0],
            request=request,
            confirmation=True,
        )
        resolution.refresh_from_db()
        self.assertEqual(resolution.status, ResolutionStatus.PARTIALLY_SIGNED)

        sign_resolution(
            resolution,
            self.signers[1],
            user=self.signers_users[1],
            request=request,
            confirmation=True,
        )
        resolution.refresh_from_db()
        self.assertEqual(resolution.status, ResolutionStatus.FULLY_SIGNED)

    def test_signature_snapshot_immutable_when_member_image_changes(self):
        resolution = self._draft()
        prepare_for_signing(resolution, actor=self.staff)
        select_signers(resolution, [self.signers[0].pk], actor=self.staff)

        sign_resolution(
            resolution,
            self.signers[0],
            user=self.signers_users[0],
            confirmation=True,
        )
        signature = ResolutionSignature.objects.get(member=self.signers[0])
        original_name = signature.signature_image.name
        signature.signature_image.open("rb")
        original_bytes = signature.signature_image.read()
        signature.signature_image.close()

        buf = io.BytesIO()
        Image.new("RGB", (60, 30), color=(255, 0, 0)).save(buf, format="PNG")
        self.signers[0].signature_image.save(
            "changed.png",
            ContentFile(buf.getvalue()),
            save=True,
        )

        signature.refresh_from_db()
        signature.signature_image.open("rb")
        current_bytes = signature.signature_image.read()
        signature.signature_image.close()
        self.assertEqual(current_bytes, original_bytes)
        self.assertEqual(signature.signature_image.name, original_name)

        with self.assertRaises(ValueError):
            signature.signer_name = "Tampered"
            signature.save()

    def test_create_new_version_resets_to_draft(self):
        resolution = self._draft()
        prepare_for_signing(resolution, actor=self.staff)
        select_signers(resolution, [self.signers[0].pk], actor=self.staff)

        new_version = create_new_version(
            resolution,
            reason="Typo correction",
            content_bn="<p>Revised body</p>",
            actor=self.staff,
        )
        resolution.refresh_from_db()
        self.assertEqual(resolution.status, ResolutionStatus.DRAFT)
        self.assertEqual(new_version.version_number, 2)
        self.assertFalse(new_version.is_frozen)
        self.assertEqual(new_version.content_bn, "<p>Revised body</p>")

    def test_finalize_only_when_fully_signed(self):
        resolution = self._draft()
        prepare_for_signing(resolution, actor=self.staff)
        select_signers(resolution, [self.signers[0].pk], actor=self.staff)

        with self.assertRaises(ValueError):
            finalize_resolution(resolution, actor=self.staff)

        sign_resolution(
            resolution,
            self.signers[0],
            user=self.signers_users[0],
            confirmation=True,
        )
        finalized = finalize_resolution(resolution, actor=self.staff)
        self.assertEqual(finalized.status, ResolutionStatus.FINALIZED)
        self.assertIsNotNone(finalized.finalized_at)

    def test_block_non_selected_signer(self):
        resolution = self._draft()
        prepare_for_signing(resolution, actor=self.staff)
        select_signers(resolution, [self.signers[0].pk], actor=self.staff)

        with self.assertRaises(ValueError) as ctx:
            sign_resolution(
                resolution,
                self.signers[1],
                user=self.signers_users[1],
                confirmation=True,
            )
        self.assertIn("required signer", str(ctx.exception).lower())

    def test_block_duplicate_sign(self):
        resolution = self._draft()
        prepare_for_signing(resolution, actor=self.staff)
        select_signers(
            resolution,
            [self.signers[0].pk, self.signers[1].pk],
            actor=self.staff,
        )

        sign_resolution(
            resolution,
            self.signers[0],
            user=self.signers_users[0],
            confirmation=True,
        )
        with self.assertRaises(ValueError) as ctx:
            sign_resolution(
                resolution,
                self.signers[0],
                user=self.signers_users[0],
                confirmation=True,
            )
        self.assertIn("already signed", str(ctx.exception).lower())

    def test_block_sign_as_another_user(self):
        resolution = self._draft()
        prepare_for_signing(resolution, actor=self.staff)
        select_signers(resolution, [self.signers[0].pk], actor=self.staff)

        with self.assertRaises(ValueError) as ctx:
            sign_resolution(
                resolution,
                self.signers[0],
                user=self.signers_users[1],
                confirmation=True,
            )
        self.assertIn("yourself", str(ctx.exception).lower())

    def test_block_sign_without_signature_image(self):
        user, member = create_approved_member(300)
        participant = add_participants_from_members(self.meeting, [member])[0]
        mark_attendance(participant, ParticipantStatus.ATTENDED, actor=self.staff)

        resolution = self._draft()
        prepare_for_signing(resolution, actor=self.staff)
        select_signers(resolution, [member.pk], actor=self.staff)

        with self.assertRaises(ValueError) as ctx:
            sign_resolution(
                resolution,
                member,
                user=user,
                confirmation=True,
            )
        self.assertIn("signature image", str(ctx.exception).lower())

    def test_cannot_create_version_from_finalized(self):
        resolution = self._draft()
        prepare_for_signing(resolution, actor=self.staff)
        select_signers(resolution, [self.signers[0].pk], actor=self.staff)
        sign_resolution(
            resolution,
            self.signers[0],
            user=self.signers_users[0],
            confirmation=True,
        )
        finalize_resolution(resolution, actor=self.staff)

        with self.assertRaises(ValueError):
            create_new_version(resolution, reason="Too late")
