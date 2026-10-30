"""Public resolution sharing — tokens, passwords, expiry, revoke, rate limits."""

from datetime import timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from governance.services.public_share import (
    enable_public_share,
    get_valid_share,
    password_attempts_blocked,
    record_password_failure,
    revoke_public_share,
    verify_share_password,
)
from governance.services.resolutions import create_resolution
from governance.tests.helpers import create_meeting, create_staff_with_permission


class PublicShareTests(TestCase):
    def setUp(self):
        cache.clear()
        self.meeting = create_meeting()
        self.staff = create_staff_with_permission(
            "share-staff@example.com", "resolution_public_sharing.manage"
        )
        self.resolution = create_resolution(
            self.meeting,
            title_bn="Shared resolution",
            content_bn="<p>Public content</p>",
            actor=self.staff,
        )
        self.client = Client()

    def test_token_is_not_resolution_id(self):
        share = enable_public_share(self.resolution, actor=self.staff)
        self.assertNotEqual(share.token, self.resolution.resolution_id)
        self.assertNotEqual(share.token, str(self.resolution.pk))
        self.assertGreater(len(share.token), 20)

    def test_get_valid_share_by_token(self):
        share = enable_public_share(self.resolution, actor=self.staff, password="secret")
        found = get_valid_share(share.token)
        self.assertIsNotNone(found)
        self.assertEqual(found.resolution_id, self.resolution.pk)

    def test_password_required_and_verified(self):
        share = enable_public_share(
            self.resolution,
            actor=self.staff,
            password="hunter2",
        )
        self.assertTrue(share.requires_password)
        self.assertFalse(verify_share_password(share, "wrong", ip="1.2.3.4"))
        self.assertTrue(verify_share_password(share, "hunter2", ip="1.2.3.4"))

    def test_expired_share_not_accessible(self):
        share = enable_public_share(
            self.resolution,
            actor=self.staff,
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        self.assertFalse(share.is_accessible())
        self.assertIsNone(get_valid_share(share.token))

    def test_revoked_share_not_accessible(self):
        share = enable_public_share(self.resolution, actor=self.staff)
        revoke_public_share(self.resolution, actor=self.staff)
        share.refresh_from_db()
        self.assertFalse(share.is_accessible())
        self.assertIsNotNone(share.revoked_at)
        self.assertIsNone(get_valid_share(share.token))

    def test_password_rate_limit_helper(self):
        token = "test-token-abc"
        ip = "10.0.0.1"
        self.assertFalse(password_attempts_blocked(ip, token, limit=3))
        for _ in range(3):
            record_password_failure(ip, token)
        self.assertTrue(password_attempts_blocked(ip, token, limit=3))

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            }
        }
    )
    def test_public_view_uses_token_not_uuid(self):
        share = enable_public_share(self.resolution, actor=self.staff)
        url = reverse("public-resolution", kwargs={"token": share.token})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.resolution.resolution_id)

        bad = reverse("public-resolution", kwargs={"token": str(self.resolution.pk)})
        resp_bad = self.client.get(bad)
        self.assertEqual(resp_bad.status_code, 404)

    @patch("governance.views_public.password_attempts_blocked", return_value=True)
    def test_password_page_shows_blocked_state(self, _mock_blocked):
        share = enable_public_share(
            self.resolution,
            actor=self.staff,
            password="secret",
        )
        url = reverse("public-resolution-password", kwargs={"token": share.token})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["blocked"])
