"""Integration-hardening batch tests (notifications, fees, finance, paid-through, purposes)."""

from io import BytesIO
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from accounts.models import Role
from audit.models import Notification, NotificationRead, NotificationType
from audit.notifications import (
    mark_read_for_user,
    notify,
    notify_roles,
    recent_for_user,
    unread_count_for_user,
)
from core.choices import DonationStatus, PaymentMethod
from donations.models import ChannelKind, DonationCategory, PaymentMethodConfig, TransactionPurpose
from finance.membership_income import ensure_income_for_fee_payment, income_key_for_fee_payment
from finance.models import Income
from members.billing import (
    add_months,
    complete_fee_payment,
    current_year_month,
    ensure_ledger_months,
    initiate_fee_checkout,
    is_due_for_current_month,
    is_prepaid_beyond_current,
    mark_fee_months_paid,
    paid_through,
    record_admin_fee_payment,
)
from members.fee_notifications import notify_fee_due, notify_fee_paid
from members.models import (
    ApplicationEvent,
    ApplicationStatus,
    Member,
    MemberStatus,
    MembershipFee,
    MembershipFeePayment,
)
from members.services import create_application_as_admin
from members.tests import application_payload

User = get_user_model()


def _png():
    buf = BytesIO()
    Image.new("RGB", (8, 8), color="red").save(buf, format="PNG")
    return SimpleUploadedFile("photo.png", buf.getvalue(), content_type="image/png")


def _pdf():
    return SimpleUploadedFile(
        "id.pdf", b"%PDF-1.4 test", content_type="application/pdf"
    )


def _verified_user(email, role=Role.MEMBER):
    user = User.objects.create_user(email=email, password="Str0ngPass!23", role=role)
    user.email_verified = timezone.now()
    user.save(update_fields=["email_verified"])
    return user


def _admin(email="ih-admin@example.com"):
    u = _verified_user(email, role=Role.SUPER_ADMIN)
    u.is_superuser = True
    u.save(update_fields=["is_superuser"])
    return u


def _member(email="ih-m@example.com", phone="01720000001"):
    user = _verified_user(email)
    return Member.objects.create(
        member_id=f"ZF-IH-{phone[-4:]}",
        user=user,
        first_name="Hard",
        last_name="Member",
        phone=phone,
        present_address="Dhaka",
        district="Dhaka",
        status=MemberStatus.APPROVED,
        joined_at=timezone.now().replace(day=1),
    )


class DashboardUnreadUsesNotificationServiceTests(TestCase):
    def setUp(self):
        self.admin = _admin()
        self.client = Client()
        self.client.force_login(self.admin)

    def test_dashboard_home_unread_respects_notification_read(self):
        personal = notify(title="P", message="p", user=self.admin)
        roles = notify_roles(["SUPER_ADMIN"], title="R", message="role")
        role = roles[0]
        mark_read_for_user(role, self.admin)
        role.refresh_from_db()
        self.assertFalse(role.is_read)
        self.assertTrue(
            NotificationRead.objects.filter(notification=role, user=self.admin).exists()
        )
        expected = unread_count_for_user(self.admin)
        self.assertEqual(expected, 1)

        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["notifications_unread_count"], expected)
        unread_ids = {n.pk for n in response.context["notifications"]}
        self.assertIn(personal.pk, unread_ids)
        self.assertNotIn(role.pk, unread_ids)

    def test_role_broadcast_read_state_consistent_everywhere(self):
        roles = notify_roles(["SUPER_ADMIN"], title="Broadcast", message="x")
        role = roles[0]
        self.assertEqual(unread_count_for_user(self.admin), 1)
        recent = recent_for_user(self.admin, limit=5)
        self.assertTrue(any(n.pk == role.pk and n.viewer_is_unread for n in recent))
        mark_read_for_user(role, self.admin)
        self.assertEqual(unread_count_for_user(self.admin), 0)
        recent2 = recent_for_user(self.admin, limit=5)
        match = next(n for n in recent2 if n.pk == role.pk)
        self.assertFalse(match.viewer_is_unread)


class FeeNotificationIdempotencyTests(TestCase):
    def test_fee_due_once_per_member_month(self):
        member = _member(phone="01720000002")
        cy, cm = current_year_month()
        ensure_ledger_months(member, cy, cm)
        fee = MembershipFee.objects.get(member=member, year=cy, month=cm)
        ensure_ledger_months(member, cy, cm)
        ensure_ledger_months(member, cy, cm)
        notify_fee_due(fee)
        notify_fee_due(fee)
        self.assertEqual(
            Notification.objects.filter(
                type=NotificationType.FEE_DUE, object_id=str(fee.pk)
            ).count(),
            1,
        )

    def test_fee_paid_notification_once(self):
        member = _member(phone="01720000003")
        cy, cm = current_year_month()
        payment = record_admin_fee_payment(
            member,
            [{"year": cy, "month": cm}],
            payment_method=PaymentMethod.CASH,
            actor=_admin("ih-admin-fee@example.com"),
        )
        notify_fee_paid(payment)
        notify_fee_paid(payment)
        self.assertEqual(
            Notification.objects.filter(
                type=NotificationType.FEE_PAID, object_id=str(payment.pk)
            ).count(),
            1,
        )


class AdminAutoApproveNotificationTests(TestCase):
    def setUp(self):
        self.admin = _admin("ih-admin-app@example.com")

    def _form(self, auto_approve, email, phone):
        from members.forms import AdminMemberApplicationForm

        payload = application_payload(
            email=email,
            phone=phone,
            auto_approve=auto_approve,
        )
        return AdminMemberApplicationForm(
            data=payload,
            files={"photo": _png(), "identity_document": _pdf()},
        )

    def test_auto_approve_skips_new_application_review_notification(self):
        form = self._form(True, "auto-ih@example.com", "01720000004")
        self.assertTrue(form.is_valid(), form.errors)
        before = Notification.objects.filter(type=NotificationType.NEW_APPLICATION).count()
        application, member = create_application_as_admin(
            form, creator=self.admin, auto_approve=True
        )
        self.assertIsNotNone(member)
        after = Notification.objects.filter(type=NotificationType.NEW_APPLICATION).count()
        self.assertEqual(before, after)
        self.assertTrue(
            application.events.filter(action=ApplicationEvent.Action.ADMIN_CREATED).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                type=NotificationType.USER_CREATED,
                message__contains=member.member_id,
            ).exists()
        )

    def test_normal_admin_application_creates_review_notification(self):
        form = self._form(False, "pending-ih@example.com", "01720000005")
        self.assertTrue(form.is_valid(), form.errors)
        before = Notification.objects.filter(type=NotificationType.NEW_APPLICATION).count()
        application, member = create_application_as_admin(
            form, creator=self.admin, auto_approve=False
        )
        self.assertIsNone(member)
        self.assertEqual(application.status, ApplicationStatus.PENDING)
        after = Notification.objects.filter(type=NotificationType.NEW_APPLICATION).count()
        self.assertGreater(after, before)


class MembershipFinanceIncomeTests(TestCase):
    def test_membership_payment_creates_one_income(self):
        member = _member(phone="01720000006")
        admin = _admin("ih-admin-fin@example.com")
        cy, cm = current_year_month()
        payment = record_admin_fee_payment(
            member,
            [{"year": cy, "month": cm}],
            payment_method=PaymentMethod.BANK_TRANSFER,
            actor=admin,
        )
        key = income_key_for_fee_payment(payment)
        self.assertEqual(Income.objects.filter(idempotency_key=key).count(), 1)
        income = Income.objects.get(idempotency_key=key)
        self.assertEqual(income.amount, payment.amount)
        self.assertIn(member.member_id, income.source)

    def test_duplicate_callback_does_not_duplicate_income(self):
        member = _member(phone="01720000007")
        cy, cm = current_year_month()
        from donations.models import Transaction

        txn = Transaction.objects.create(
            session_id="s-ih-1",
            tran_id="T-IH-1",
            amount=50,
            status=DonationStatus.PENDING,
            purpose=TransactionPurpose.MEMBERSHIP_FEE,
            gateway=PaymentMethod.SSLCOMMERZ,
            cus_name="Test",
        )
        payment = MembershipFeePayment.objects.create(
            member=member,
            transaction=txn,
            amount=50,
            months=[{"year": cy, "month": cm}],
            status=DonationStatus.PENDING,
            payment_method=PaymentMethod.SSLCOMMERZ,
        )
        data = {
            "status": "VALID",
            "tran_id": "T-IH-1",
            "amount": "50.00",
            "currency": "BDT",
            "bank_tran_id": "B",
        }
        complete_fee_payment(payment, val_id="v1", validation_data=data)
        complete_fee_payment(payment, val_id="v1", validation_data=data)
        ensure_income_for_fee_payment(payment)
        key = income_key_for_fee_payment(payment)
        self.assertEqual(Income.objects.filter(idempotency_key=key).count(), 1)


class PaidThroughSemanticsTests(TestCase):
    def test_paid_through_no_gaps(self):
        member = _member(phone="01720000008")
        cy, cm = current_year_month()
        y2, m2 = add_months(cy, cm, 1)
        mark_fee_months_paid(
            member,
            [{"year": cy, "month": cm}, {"year": y2, "month": m2}],
            payment_method=PaymentMethod.CASH,
            source="ADMIN",
        )
        self.assertEqual(paid_through(member), (y2, m2))

    def test_paid_through_with_gap(self):
        member = _member(phone="01720000009")
        cy, cm = current_year_month()
        y2, m2 = add_months(cy, cm, 1)
        y3, m3 = add_months(cy, cm, 2)
        ensure_ledger_months(member, y3, m3)
        mark_fee_months_paid(
            member,
            [{"year": cy, "month": cm}, {"year": y3, "month": m3}],
            payment_method=PaymentMethod.CASH,
            source="ADMIN",
        )
        self.assertEqual(paid_through(member), (cy, cm))
        self.assertNotEqual(paid_through(member), (y3, m3))
        self.assertEqual(
            MembershipFee.objects.get(member=member, year=y2, month=m2).status,
            DonationStatus.PENDING,
        )

    def test_future_prepaid_months(self):
        member = _member(phone="01720000010")
        cy, cm = current_year_month()
        y2, m2 = add_months(cy, cm, 1)
        y3, m3 = add_months(cy, cm, 2)
        mark_fee_months_paid(
            member,
            [
                {"year": cy, "month": cm},
                {"year": y2, "month": m2},
                {"year": y3, "month": m3},
            ],
            payment_method=PaymentMethod.CASH,
            source="ADMIN",
        )
        self.assertEqual(paid_through(member), (y3, m3))
        self.assertTrue(is_prepaid_beyond_current(member))
        self.assertFalse(is_due_for_current_month(member))


@override_settings(
    SSLCOMMERZ_STORE_ID="store",
    SSLCOMMERZ_STORE_PASSWORD="pass",
    SSLCOMMERZ_IS_SANDBOX=True,
)
class PaymentPurposeAvailabilityTests(TestCase):
    def _ssl_cfg(self, **kwargs):
        defaults = {
            "display_name": "SSLCommerz",
            "channel_kind": ChannelKind.ONLINE_HOSTED,
            "is_enabled": True,
            "enabled_for_donation": True,
            "enabled_for_membership_fee": True,
        }
        defaults.update(kwargs)
        return PaymentMethodConfig.objects.update_or_create(
            method=PaymentMethod.SSLCOMMERZ, defaults=defaults
        )[0]

    def test_disable_membership_keeps_donation_available(self):
        from donations.gateway_capabilities import online_checkout_allowed

        self._ssl_cfg(enabled_for_membership_fee=False, enabled_for_donation=True)
        ok_d, _ = online_checkout_allowed(
            PaymentMethod.SSLCOMMERZ, purpose=TransactionPurpose.DONATION
        )
        ok_m, err_m = online_checkout_allowed(
            PaymentMethod.SSLCOMMERZ, purpose=TransactionPurpose.MEMBERSHIP_FEE
        )
        self.assertTrue(ok_d)
        self.assertFalse(ok_m)
        self.assertIn("membership", err_m.lower())

    def test_disable_donation_keeps_membership_available(self):
        from donations.gateway_capabilities import online_checkout_allowed

        self._ssl_cfg(enabled_for_donation=False, enabled_for_membership_fee=True)
        ok_d, err_d = online_checkout_allowed(
            PaymentMethod.SSLCOMMERZ, purpose=TransactionPurpose.DONATION
        )
        ok_m, _ = online_checkout_allowed(
            PaymentMethod.SSLCOMMERZ, purpose=TransactionPurpose.MEMBERSHIP_FEE
        )
        self.assertFalse(ok_d)
        self.assertIn("donation", err_d.lower())
        self.assertTrue(ok_m)

    @patch(
        "donations.gateways.sslcommerz.SSLCommerzGateway.init_payment",
        return_value="https://pay.example/membership",
    )
    def test_membership_checkout_respects_purpose_flag(self, _init):
        self._ssl_cfg(enabled_for_membership_fee=False)
        member = _member(phone="01720000011")
        cy, cm = current_year_month()
        ensure_ledger_months(member, cy, cm)
        with self.assertRaises(ValueError):
            initiate_fee_checkout(
                member,
                [{"year": cy, "month": cm}],
                request=MagicMock(),
                actor=member.user,
            )

    @patch("donations.views.init_payment", return_value="https://pay.example/donation")
    def test_donation_checkout_remains_functional_when_membership_disabled(self, mock_init):
        self._ssl_cfg(enabled_for_membership_fee=False, enabled_for_donation=True)
        DonationCategory.objects.create(
            name_en="General",
            name_bn="সাধারণ",
            slug="general-ih",
            is_active=True,
            is_default=True,
        )
        client = Client()
        response = client.post(
            reverse("donation-create"),
            {
                "amount": "100",
                "donor_name": "Donor IH",
                "contact": "donor-ih@example.com",
                "category": str(DonationCategory.objects.get(slug="general-ih").pk),
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "https://pay.example/donation")
        mock_init.assert_called_once()
