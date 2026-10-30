"""WP3 — governance RBAC grants, notification types, private media privacy."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.utils import timezone

from accounts.models import Role as LegacyRole
from audit.models import Notification, NotificationType
from audit.notifications import (
    TYPE_ICONS,
    for_user_qs,
    mark_read_for_user,
    notify,
    unread_count_for_user,
)
from core.media_access import (
    is_private_media_path,
    is_public_media_path,
    user_can_access_private_media,
)
from core.storage import SecureMediaStorage
from governance.tests.helpers import (
    create_approved_member,
    create_user,
    ensure_rbac_seeded,
    png_upload,
)
from rbac.models import Permission, Role, UserRole
from rbac.permissions import clear_cache, has_action

User = get_user_model()

GOVERNANCE_CODENAMES = {
    "meetings.view",
    "meetings.create",
    "meetings.edit",
    "meetings.delete",
    "meetings.manage",
    "meetings.manage_participants",
    "meetings.manage_attendance",
    "meetings.manage_agenda",
    "meetings.finalize",
    "resolutions.view",
    "resolutions.create",
    "resolutions.edit",
    "resolutions.delete",
    "resolutions.manage",
    "resolutions.sign",
    "resolutions.manage_signers",
    "resolutions.finalize",
    "resolutions.publish",
    "resolution_documents.download",
    "resolution_public_sharing.manage",
}


class GovernanceRBACSeedTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_rbac_seeded()

    def test_governance_permissions_registered(self):
        existing = set(
            Permission.objects.filter(
                codename__in=GOVERNANCE_CODENAMES
            ).values_list("codename", flat=True)
        )
        self.assertEqual(existing, GOVERNANCE_CODENAMES)

    def test_super_admin_and_president_have_full_governance(self):
        super_user = create_user(
            "gov-super@example.com",
            role=LegacyRole.SUPER_ADMIN,
            is_staff=True,
        )
        self.assertTrue(has_action(super_user, "meetings", "manage"))
        self.assertTrue(has_action(super_user, "resolutions", "manage_signers"))
        self.assertTrue(has_action(super_user, "resolution_public_sharing", "manage"))

        president_role = Role.objects.get(name="President")
        president = create_user("gov-president@example.com", is_staff=True)
        UserRole.objects.create(user=president, role=president_role)
        clear_cache(president)
        self.assertTrue(has_action(president, "meetings", "finalize"))
        self.assertTrue(has_action(president, "resolutions", "publish"))

    def test_executive_admin_and_secretary_have_governance(self):
        exec_user = create_user(
            "gov-exec@example.com",
            role=LegacyRole.EXECUTIVE_ADMIN,
            is_staff=True,
        )
        self.assertTrue(has_action(exec_user, "meetings", "create"))
        self.assertTrue(has_action(exec_user, "resolutions", "sign"))
        self.assertTrue(has_action(exec_user, "resolution_documents", "download"))

        secretary_role = Role.objects.get(name="Secretary")
        secretary = create_user("gov-secretary@example.com", is_staff=True)
        UserRole.objects.create(user=secretary, role=secretary_role)
        clear_cache(secretary)
        self.assertTrue(has_action(secretary, "meetings", "manage_attendance"))
        self.assertTrue(has_action(secretary, "resolutions", "manage_signers"))
        self.assertTrue(has_action(secretary, "resolution_public_sharing", "manage"))

    def test_non_governance_roles_denied(self):
        denied_roles = [
            (LegacyRole.MEMBER, "member"),
            (LegacyRole.DONOR, "donor"),
            (LegacyRole.FINANCE_OFFICER, "finance"),
            (LegacyRole.VOLUNTEER_COORDINATOR, "volunteer"),
        ]
        for legacy, label in denied_roles:
            user = create_user(f"gov-deny-{label}@example.com", role=legacy)
            self.assertFalse(
                has_action(user, "meetings", "view"),
                msg=f"{label} must not have meetings.view",
            )
            self.assertFalse(
                has_action(user, "resolutions", "manage"),
                msg=f"{label} must not have resolutions.manage",
            )

        membership_mgr = create_user("gov-deny-mm@example.com", is_staff=True)
        UserRole.objects.create(
            user=membership_mgr,
            role=Role.objects.get(name="Membership Manager"),
        )
        clear_cache(membership_mgr)
        self.assertFalse(has_action(membership_mgr, "meetings", "edit"))
        self.assertFalse(has_action(membership_mgr, "resolutions", "create"))

    def test_ordinary_user_without_role_denied(self):
        user = User.objects.create_user(
            email="gov-ordinary@example.com",
            password="pass12345",
        )
        user.email_verified = timezone.now()
        user.save(update_fields=["email_verified"])
        clear_cache(user)
        self.assertFalse(has_action(user, "meetings", "view"))
        self.assertFalse(has_action(user, "resolutions", "view"))


class GovernanceNotificationTypeTests(TestCase):
    def test_governance_notification_types_registered(self):
        required = {
            "MEETING_INVITATION",
            "MEETING_UPDATED",
            "MEETING_CANCELLED",
            "MEETING_REMINDER",
            "RESOLUTION_AWAITING_SIGNATURE",
            "RESOLUTION_FULLY_SIGNED",
            "RESOLUTION_FINALIZED",
            "RESOLUTION_NEW_VERSION",
        }
        values = {c.value for c in NotificationType}
        self.assertTrue(required.issubset(values))
        for code in required:
            self.assertIn(code, TYPE_ICONS)

    def test_notification_read_state_compatible(self):
        user = create_user("gov-notif-read@example.com")
        n = notify(
            title="Meeting invitation",
            message="Please attend.",
            ntype=NotificationType.MEETING_INVITATION,
            user=user,
        )
        self.assertEqual(unread_count_for_user(user), 1)
        self.assertTrue(for_user_qs(user).filter(pk=n.pk).exists())
        mark_read_for_user(n, user)
        self.assertEqual(unread_count_for_user(user), 0)
        self.assertTrue(Notification.objects.filter(pk=n.pk, is_read=True).exists())


class GovernancePrivateMediaTests(TestCase):
    def setUp(self):
        ensure_rbac_seeded()
        self.factory = RequestFactory()
        self.user_a, self.member_a = create_approved_member(
            401, signature_image=png_upload("sig-a.png")
        )
        self.user_b, self.member_b = create_approved_member(
            402, signature_image=png_upload("sig-b.png")
        )
        self.sig_a = self.member_a.signature_image.name
        self.sig_b = self.member_b.signature_image.name

    def _request(self, user=None):
        from django.contrib.auth.models import AnonymousUser

        req = self.factory.get("/protected-media/test")
        req.session = {}
        req.user = user if user is not None else AnonymousUser()
        return req

    def test_signature_and_meeting_prefixes_are_private(self):
        self.assertTrue(is_private_media_path("members/signatures/x.png"))
        self.assertTrue(is_private_media_path("resolutions/signatures/y.png"))
        self.assertTrue(is_private_media_path("meetings/agenda/z.pdf"))
        self.assertFalse(is_public_media_path("members/signatures/x.png"))
        self.assertTrue(is_public_media_path("cms/hero.jpg"))
        self.assertTrue(is_public_media_path("reports/annual.pdf"))

    def test_storage_rewrites_signature_urls_to_protected(self):
        storage = SecureMediaStorage()
        url = storage.url("members/signatures/abc.png")
        self.assertTrue(url.startswith("/protected-media/"))
        self.assertIn("members/signatures/abc.png", url)

    def test_anonymous_and_cross_member_denied(self):
        anon = self._request(None)
        self.assertFalse(user_can_access_private_media(anon, self.sig_a))

        other = self._request(self.user_b)
        self.assertFalse(user_can_access_private_media(other, self.sig_a))

    def test_owner_can_access_own_signature(self):
        own = self._request(self.user_a)
        self.assertTrue(user_can_access_private_media(own, self.sig_a))

    def test_governance_staff_can_access_signatures(self):
        from governance.tests.helpers import create_staff_with_permission

        staff = create_staff_with_permission(
            "gov-media-staff@example.com", "resolutions.view"
        )
        req = self._request(staff)
        self.assertTrue(user_can_access_private_media(req, self.sig_a))
        self.assertTrue(
            user_can_access_private_media(req, "meetings/agenda/doc.pdf")
            or is_private_media_path("meetings/agenda/doc.pdf")
        )
        # Path may not exist on disk; authorization still allows staff for prefix.
        self.assertTrue(user_can_access_private_media(req, "meetings/agenda/doc.pdf"))

    def test_member_cannot_access_meeting_private_files(self):
        req = self._request(self.user_a)
        self.assertFalse(user_can_access_private_media(req, "meetings/agenda/secret.pdf"))

    def test_existing_private_application_media_still_private(self):
        self.assertTrue(is_private_media_path("members/identity/nid.pdf"))
        self.assertTrue(is_private_media_path("members/documents/x.pdf"))
