"""Membership fee settings, start-month rules, registration fee, approval notice."""

from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role
from audit.models import Notification, NotificationType
from core.choices import DonationStatus, PaymentMethod
from members.billing import (
    ensure_ledger_months,
    mark_fee_months_paid,
    member_join_period,
    seed_ledger_for_new_member,
)
from members.fee_settings import (
    clear_fee_settings_cache,
    get_monthly_fee_amount,
    get_registration_fee_amount,
)
from members.models import (
    Member,
    MemberStatus,
    MembershipFee,
    MembershipFeeSettings,
    MembershipRegistrationFee,
)
from members.fee_notifications import notify_membership_approved_payment_due
from rbac.management.commands.seed_rbac import Command as SeedRbac

User = get_user_model()


def _verified_user(email, role=Role.MEMBER):
    user = User.objects.create_user(email=email, password="Str0ngPass!23", role=role)
    user.email_verified = timezone.now()
    user.save(update_fields=["email_verified"])
    return user


def _member(*, email="m@example.com", phone="01710000991", approved_at=None):
    user = _verified_user(email)
    stamp = approved_at or timezone.now()
    return Member.objects.create(
        member_id=f"ZF-FS-{phone[-4:]}",
        user=user,
        first_name="Fee",
        last_name="Tester",
        phone=phone,
        present_address="Dhaka",
        district="Dhaka",
        status=MemberStatus.APPROVED,
        joined_at=stamp,
        approved_at=stamp,
    )


def _set_fee_settings(*, monthly=50, registration=100, year=1, month=1):
    settings = MembershipFeeSettings.load()
    settings.monthly_fee_amount = Decimal(str(monthly))
    settings.registration_fee_amount = Decimal(str(registration))
    settings.fee_start_year = year
    settings.fee_start_month = month
    settings.save()
    return settings


class MembershipFeeSettingsTests(TestCase):
    def setUp(self):
        _set_fee_settings(monthly=50, registration=100, year=1, month=1)
        clear_fee_settings_cache()

    def test_defaults(self):
        settings = MembershipFeeSettings.load()
        self.assertEqual(float(settings.monthly_fee_amount), 50.0)
        self.assertEqual(float(settings.registration_fee_amount), 100.0)
        self.assertEqual(get_monthly_fee_amount(), 50.0)
        self.assertEqual(get_registration_fee_amount(), 100.0)

    def test_admin_can_change_amounts_and_start_month(self):
        SeedRbac().handle()
        admin = _verified_user("fees-admin@example.com", role=Role.SUPER_ADMIN)
        client = Client()
        self.assertTrue(client.login(email="fees-admin@example.com", password="Str0ngPass!23"))
        resp = client.post(
            reverse("dashboard-membership-fees-settings"),
            {
                "monthly_fee_amount": "75.00",
                "registration_fee_amount": "150.00",
                "fee_starting_month": "2026-12",
                "is_active": "on",
                "admin_note": "Policy update",
            },
        )
        self.assertEqual(resp.status_code, 302)
        settings = MembershipFeeSettings.load()
        self.assertEqual(float(settings.monthly_fee_amount), 75.0)
        self.assertEqual(float(settings.registration_fee_amount), 150.0)
        self.assertEqual(settings.fee_start_year, 2026)
        self.assertEqual(settings.fee_start_month, 12)

    def test_existing_member_starts_from_configured_month(self):
        _set_fee_settings(year=2026, month=12)
        approved = timezone.make_aware(datetime(2026, 3, 15, 12, 0, 0))
        member = _member(phone="01710000992", approved_at=approved)
        self.assertEqual(member_join_period(member), (2026, 12))
        ensure_ledger_months(member, 2026, 12)
        self.assertFalse(
            MembershipFee.objects.filter(member=member, year=2026, month=3).exists()
        )
        self.assertTrue(
            MembershipFee.objects.filter(member=member, year=2026, month=12).exists()
        )

    def test_new_member_starts_from_approval_month(self):
        _set_fee_settings(year=2026, month=12)
        approved = timezone.make_aware(datetime(2027, 1, 10, 12, 0, 0))
        member = _member(phone="01710000993", approved_at=approved, email="new@example.com")
        self.assertEqual(member_join_period(member), (2027, 1))
        ensure_ledger_months(member, 2027, 1)
        self.assertFalse(
            MembershipFee.objects.filter(member=member, year=2026, month=12).exists()
        )
        fee = MembershipFee.objects.get(member=member, year=2027, month=1)
        self.assertEqual(fee.status, DonationStatus.PENDING)

    def test_no_fees_before_applicable_start(self):
        _set_fee_settings(year=2026, month=12)
        approved = timezone.make_aware(datetime(2026, 1, 1, 12, 0, 0))
        member = _member(phone="01710000994", approved_at=approved, email="early@example.com")
        created = ensure_ledger_months(member, 2026, 11)
        self.assertEqual(created, [])
        self.assertFalse(MembershipFee.objects.filter(member=member).exists())

    def test_completed_historical_fees_not_rewritten_when_rate_changes(self):
        _set_fee_settings(monthly=50, year=1, month=1)
        member = _member(phone="01710000995", email="hist@example.com")
        seed_ledger_for_new_member(member)
        cy = timezone.localdate().year
        cm = timezone.localdate().month
        mark_fee_months_paid(
            member,
            [{"year": cy, "month": cm}],
            payment_method=PaymentMethod.CASH,
            source="ADMIN",
        )
        fee = MembershipFee.objects.get(member=member, year=cy, month=cm)
        self.assertEqual(fee.amount, 50.0)
        _set_fee_settings(monthly=75, year=1, month=1)
        mark_fee_months_paid(
            member,
            [{"year": cy, "month": cm}],
            payment_method=PaymentMethod.CASH,
            source="ADMIN",
        )
        fee.refresh_from_db()
        self.assertEqual(fee.amount, 50.0)
        self.assertEqual(fee.status, DonationStatus.COMPLETED)

    def test_registration_fee_separate_from_monthly(self):
        member = _member(phone="01710000996", email="reg@example.com")
        seed_ledger_for_new_member(member)
        reg = MembershipRegistrationFee.objects.get(member=member)
        self.assertEqual(reg.amount, 100.0)
        self.assertEqual(reg.status, DonationStatus.PENDING)
        self.assertTrue(MembershipFee.objects.filter(member=member).exists())
        self.assertNotEqual(reg.payment_purpose, "MEMBERSHIP_FEE")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_approval_notification_amounts_email_and_sms(self):
        _set_fee_settings(monthly=50, registration=100, year=1, month=1)
        approved = timezone.make_aware(datetime(2026, 12, 5, 12, 0, 0))
        member = _member(phone="01710000997", email="approve-notice@example.com", approved_at=approved)
        seed_ledger_for_new_member(member)
        with patch("core.sms.SMSService.send_sms", return_value=True) as sms:
            notify_membership_approved_payment_due(member, year=2026, month=12)
            self.assertTrue(sms.called)
        self.assertTrue(
            Notification.objects.filter(
                type=NotificationType.MEMBERSHIP_APPROVED, user=member.user
            ).exists()
        )
        self.assertTrue(mail.outbox)
        body = mail.outbox[-1].body
        self.assertIn("Registration Fee: ৳100", body)
        self.assertIn("৳50", body)
        self.assertIn("৳150", body)
        # Idempotent in-app notification
        notify_membership_approved_payment_due(member, year=2026, month=12)
        self.assertEqual(
            Notification.objects.filter(
                type=NotificationType.MEMBERSHIP_APPROVED, user=member.user
            ).count(),
            1,
        )

    def test_fees_list_one_row_per_member_and_registration_status(self):
        SeedRbac().handle()
        admin = _verified_user("fees-list@example.com", role=Role.SUPER_ADMIN)
        member = _member(phone="01710000998", email="listed@example.com")
        seed_ledger_for_new_member(member)
        client = Client()
        self.assertTrue(client.login(email="fees-list@example.com", password="Str0ngPass!23"))
        resp = client.get(reverse("dashboard-membership-fees"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, member.member_id)
        self.assertContains(resp, "Registration Fee Status")
        self.assertContains(resp, "View Details")
        detail = client.get(reverse("dashboard-membership-fee-detail", kwargs={"pk": member.pk}))
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "Fee Start Month")
        self.assertContains(detail, "Registration Fee")
