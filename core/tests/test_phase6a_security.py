"""Phase 6A — production settings, private media, MOCK autopay guard."""

from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import Client, RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role
from core.media_access import (
    is_private_media_path,
    is_public_media_path,
    normalize_media_path,
    user_can_access_private_media,
)
from core.storage import SecureMediaStorage
from members.billing import mock_autopay_permitted, mock_charge_due_autopay
from members.models import (
    AutoPayMode,
    Member,
    MemberApplication,
    MemberDocument,
    MembershipAutoPay,
    MemberStatus,
)
from members.views import STATUS_SESSION_KEY
from rbac.management.commands.seed_rbac import Command as SeedRbac

User = get_user_model()


class MediaClassificationTests(SimpleTestCase):
    def test_private_and_public_prefixes(self):
        self.assertTrue(is_private_media_path("members/identity/a.pdf"))
        self.assertTrue(is_private_media_path("members/documents/x.pdf"))
        self.assertTrue(is_private_media_path("members/signatures/sig.png"))
        self.assertTrue(is_private_media_path("resolutions/signatures/snap.png"))
        self.assertTrue(is_private_media_path("meetings/agenda/a.pdf"))
        self.assertFalse(is_public_media_path("members/photos/a.jpg"))
        self.assertTrue(is_public_media_path("brand/logo/a.png"))
        self.assertTrue(is_public_media_path("reports/annual.pdf"))
        self.assertEqual(normalize_media_path("../etc/passwd"), "")
        self.assertEqual(normalize_media_path("members/../secret"), "")


class StorageUrlTests(SimpleTestCase):
    def test_private_url_uses_protected_prefix(self):
        storage = SecureMediaStorage()
        url = storage.url("members/identity/abc.pdf")
        self.assertTrue(url.startswith("/protected-media/"))
        self.assertIn("members/identity/abc.pdf", url)

    def test_public_url_uses_media_prefix(self):
        storage = SecureMediaStorage()
        url = storage.url("brand/logo/logo.png")
        self.assertTrue(url.startswith("/media/"))


class SecretKeySettingsTests(SimpleTestCase):
    def test_unsafe_secret_rejected_when_not_debug(self):
        from zarrah_foundation import settings as settings_module

        with patch.object(settings_module, "DEBUG", False):
            self.assertTrue(
                settings_module._is_unsafe_secret("django-insecure-xxx")
            )
            self.assertTrue(settings_module._is_unsafe_secret(""))
            self.assertTrue(settings_module._is_unsafe_secret("short"))

    def test_strong_secret_accepted(self):
        from zarrah_foundation import settings as settings_module

        strong = "a" * 50 + "-production-grade-key"
        with patch.object(settings_module, "DEBUG", False):
            self.assertFalse(settings_module._is_unsafe_secret(strong))


class MockAutopayGuardTests(TestCase):
    @override_settings(DEBUG=False, ALLOW_MOCK_AUTOPAY_WHEN_DEBUG_FALSE=False)
    def test_mock_refused_in_production(self):
        self.assertFalse(mock_autopay_permitted())
        user = User.objects.create_user(
            email="mockprod@example.com", password="pass12345"
        )
        user.email_verified = timezone.now()
        user.save(update_fields=["email_verified"])
        member = Member.objects.create(
            member_id="MPROD1",
            user=user,
            first_name="M",
            last_name="P",
            phone="01700000991",
            present_address="Dhaka",
            district="Dhaka",
            status=MemberStatus.APPROVED,
        )
        profile = MembershipAutoPay.objects.create(
            member=member,
            is_enabled=True,
            mode=AutoPayMode.MOCK,
            next_charge_on=timezone.localdate(),
        )
        self.assertIsNone(mock_charge_due_autopay(profile))

    @override_settings(DEBUG=True, ALLOW_MOCK_AUTOPAY_WHEN_DEBUG_FALSE=False)
    def test_mock_allowed_in_debug(self):
        self.assertTrue(mock_autopay_permitted())

    @override_settings(DEBUG=False, ALLOW_MOCK_AUTOPAY_WHEN_DEBUG_FALSE=True)
    def test_mock_allowed_with_explicit_override(self):
        self.assertTrue(mock_autopay_permitted())


def _make_application(**overrides):
    """Minimal valid MemberApplication with private files."""
    defaults = dict(
        bangla_name="টেস্ট",
        english_name="Test User",
        father_name="F",
        mother_name="M",
        email="appowner@example.com",
        phone="01700000992",
        gender="MALE",
        date_of_birth="1990-01-01",
        identity_type="NID",
        identity_number="1234567890",
        present_district="Dhaka",
        present_address="Dhaka",
        occupation="Teacher",
        is_student=False,
    )
    defaults.update(overrides)
    application = MemberApplication(**defaults)
    application.photo.save("owner_photo.jpg", ContentFile(b"fakeimg"), save=False)
    application.identity_document.save(
        "owner_id.pdf", ContentFile(b"%PDF-1.4"), save=False
    )
    application.save()
    return application


class PrivateMediaAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        SeedRbac().handle()

    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        self.owner = User.objects.create_user(
            email="owner@example.com", password="pass12345", role=Role.MEMBER
        )
        self.owner.email_verified = timezone.now()
        self.owner.save(update_fields=["email_verified"])
        self.other = User.objects.create_user(
            email="other@example.com", password="pass12345", role=Role.MEMBER
        )
        self.other.email_verified = timezone.now()
        self.other.save(update_fields=["email_verified"])
        self.admin = User.objects.create_superuser(
            email="adminmedia@example.com",
            password="pass12345",
        )
        self.admin.email_verified = timezone.now()
        self.admin.save(update_fields=["email_verified"])

        self.application = _make_application(email="owner@example.com", phone="01700000994")
        self.member = Member.objects.create(
            member_id="MOWN1",
            user=self.owner,
            first_name="Test",
            last_name="User",
            phone="01700000993",
            present_address="Dhaka",
            district="Dhaka",
            status=MemberStatus.APPROVED,
        )
        self.doc = MemberDocument(member=self.member, title="Note", uploaded_by=self.admin)
        self.doc.file.save("member_doc.pdf", ContentFile(b"%PDF-doc"), save=True)

        self.private_id_path = self.application.identity_document.name
        self.private_doc_path = self.doc.file.name

    def test_unauthenticated_denied(self):
        url = reverse("protected-media", kwargs={"path": self.private_id_path})
        resp = self.client.get(url)
        self.assertIn(resp.status_code, (403, 404))

    def test_other_member_denied(self):
        self.client.force_login(self.other)
        url = reverse("protected-media", kwargs={"path": self.private_id_path})
        resp = self.client.get(url)
        self.assertIn(resp.status_code, (403, 404))

    def test_admin_allowed(self):
        self.client.force_login(self.admin)
        url = reverse("protected-media", kwargs={"path": self.private_id_path})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_owner_member_document_allowed(self):
        self.client.force_login(self.owner)
        url = reverse("protected-media", kwargs={"path": self.private_doc_path})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_applicant_session_allowed(self):
        session = self.client.session
        session[STATUS_SESSION_KEY] = str(self.application.pk)
        session.save()
        url = reverse("protected-media", kwargs={"path": self.private_id_path})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_direct_media_private_path_404(self):
        url = reverse("public-media", kwargs={"path": self.private_id_path})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)

    def test_public_media_ok(self):
        from django.conf import settings

        rel = "brand/logo/test_public.png"
        full = Path(settings.MEDIA_ROOT) / rel
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(b"png")
        url = reverse("public-media", kwargs={"path": rel})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_user_can_access_helper_cross_member(self):
        req = self.factory.get("/")
        req.user = self.other
        req.session = {}
        self.assertFalse(user_can_access_private_media(req, self.private_id_path))
