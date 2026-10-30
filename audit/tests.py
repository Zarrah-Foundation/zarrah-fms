from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role
from audit.models import NotificationRead
from audit.notifications import (
    mark_all_read_for_user,
    mark_read_for_user,
    notify,
    notify_roles,
    unread_count_for_user,
)

User = get_user_model()


def _verified_user(**kwargs):
    user = User.objects.create_user(**kwargs)
    user.email_verified = timezone.now()
    user.save(update_fields=["email_verified"])
    return user


class NotificationReadTests(TestCase):
    def setUp(self):
        self.admin_a = _verified_user(
            email="admin.a@example.com",
            password="Str0ngPass!23",
            role=Role.SUPER_ADMIN,
        )
        self.admin_b = _verified_user(
            email="admin.b@example.com",
            password="Str0ngPass!23",
            role=Role.SUPER_ADMIN,
        )
        self.member = _verified_user(
            email="member@example.com",
            password="Str0ngPass!23",
            role=Role.MEMBER,
        )
        self.personal = notify(
            title="Personal",
            message="Hello",
            user=self.admin_a,
        )
        self.role_notices = notify_roles(
            ["SUPER_ADMIN"],
            title="Role broadcast",
            message="New application",
        )
        self.role = self.role_notices[0]

    def test_mark_read_role_broadcast_uses_receipt(self):
        self.assertEqual(unread_count_for_user(self.admin_a), 2)
        self.assertTrue(mark_read_for_user(self.role, self.admin_a))
        self.assertTrue(
            NotificationRead.objects.filter(notification=self.role, user=self.admin_a).exists()
        )
        self.role.refresh_from_db()
        self.assertFalse(self.role.is_read)
        self.assertEqual(unread_count_for_user(self.admin_a), 1)
        # Other admin still sees unread role notice
        self.assertGreaterEqual(unread_count_for_user(self.admin_b), 1)

    def test_mark_all_read_clears_badge_for_current_user_only(self):
        mark_all_read_for_user(self.admin_a)
        self.assertEqual(unread_count_for_user(self.admin_a), 0)
        self.assertGreaterEqual(unread_count_for_user(self.admin_b), 1)

    def test_cannot_mark_another_users_personal_notification(self):
        self.assertFalse(mark_read_for_user(self.personal, self.admin_b))
        self.personal.refresh_from_db()
        self.assertFalse(self.personal.is_read)

    def test_mark_read_endpoint_for_role_broadcast(self):
        client = Client()
        client.force_login(self.admin_a)
        url = reverse("dashboard-notification-read", kwargs={"pk": self.role.pk})
        response = client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertTrue(
            NotificationRead.objects.filter(notification=self.role, user=self.admin_a).exists()
        )

    def test_cannot_mark_other_personal_via_http(self):
        client = Client()
        client.force_login(self.admin_b)
        url = reverse("dashboard-notification-read", kwargs={"pk": self.personal.pk})
        response = client.post(url)
        self.assertEqual(response.status_code, 404)
