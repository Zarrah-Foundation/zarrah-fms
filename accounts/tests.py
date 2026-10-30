from datetime import timedelta

from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from accounts.verification import (
    can_resend_verification,
    issue_email_verify_token,
    mark_resend_attempt,
)


class EmailVerificationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()

    def test_register_issues_token_and_unverified(self):
        response = self.client.post(
            reverse("register"),
            {
                "email": "new@example.com",
                "name": "New User",
                "password1": "Str0ngPass!23",
                "password2": "Str0ngPass!23",
            },
        )
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email="new@example.com")
        self.assertIsNone(user.email_verified)
        self.assertTrue(user.email_verify_token)

    def test_unverified_cannot_login(self):
        user = User.objects.create_user(email="u@example.com", password="Str0ngPass!23")
        issue_email_verify_token(user)
        response = self.client.post(
            reverse("login"),
            {"username": "u@example.com", "password": "Str0ngPass!23"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_verify_link_activates_account(self):
        user = User.objects.create_user(email="v@example.com", password="Str0ngPass!23")
        token = issue_email_verify_token(user)
        response = self.client.get(reverse("verify-email", kwargs={"token": token}))
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertIsNotNone(user.email_verified)
        self.assertIsNone(user.email_verify_token)

    def test_expired_token_rejected(self):
        user = User.objects.create_user(email="e@example.com", password="Str0ngPass!23")
        token = issue_email_verify_token(user)
        user.email_verify_token_expiry = timezone.now() - timedelta(hours=1)
        user.save(update_fields=["email_verify_token_expiry"])
        response = self.client.get(reverse("verify-email", kwargs={"token": token}))
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertIsNone(user.email_verified)

    def test_resend_rate_limit(self):
        email = "r@example.com"
        User.objects.create_user(email=email, password="Str0ngPass!23")
        allowed, _, _ = can_resend_verification(email)
        self.assertTrue(allowed)
        mark_resend_attempt(email)
        allowed, wait, reason = can_resend_verification(email)
        self.assertFalse(allowed)
        self.assertEqual(reason, "cooldown")
        self.assertGreater(wait, 0)

    def test_verified_user_can_login(self):
        user = User.objects.create_user(email="ok@example.com", password="Str0ngPass!23")
        user.email_verified = timezone.now()
        user.save(update_fields=["email_verified"])
        logged_in = self.client.login(username="ok@example.com", password="Str0ngPass!23")
        self.assertTrue(logged_in)


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "accounts-tests",
        }
    }
)
class EmailVerificationMiddlewareTests(TestCase):
    def test_unverified_session_blocked_from_dashboard(self):
        user = User.objects.create_user(email="mid@example.com", password="Str0ngPass!23")
        # Bypass login form gate by forcing login in test client
        self.client.force_login(user)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/verify-pending/", response.url)
