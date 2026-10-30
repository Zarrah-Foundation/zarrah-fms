from datetime import date
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role
from core.choices import DonationStatus, PaymentMethod
from donations.models import ChannelKind, PaymentMethodConfig, Transaction, TransactionPurpose
from members.billing import (
    MEMBERSHIP_MONTHLY_FEE_BDT,
    activate_autopay,
    add_months,
    complete_fee_payment,
    current_year_month,
    deactivate_autopay,
    ensure_ledger_months,
    initiate_fee_checkout,
    is_prepaid_beyond_current,
    mark_fee_months_paid,
    mock_charge_due_autopay,
    paid_through,
    record_admin_fee_payment,
    seed_ledger_for_new_member,
)
from members.models import (
    AutoPayMode,
    Member,
    MemberStatus,
    MembershipAutoPay,
    MembershipFee,
    MembershipFeePayment,
)

User = get_user_model()


def _verified_user(email, role=Role.MEMBER):
    user = User.objects.create_user(email=email, password="Str0ngPass!23", role=role)
    user.email_verified = timezone.now()
    user.save(update_fields=["email_verified"])
    return user


def _member(email="m@example.com", phone="01710000001"):
    user = _verified_user(email)
    return Member.objects.create(
        member_id=f"ZF-TEST-{phone[-4:]}",
        user=user,
        first_name="Test",
        last_name="Member",
        phone=phone,
        present_address="Dhaka",
        district="Dhaka",
        status=MemberStatus.APPROVED,
        joined_at=timezone.now(),
    )


@override_settings(
    SSLCOMMERZ_STORE_ID="teststore",
    SSLCOMMERZ_STORE_PASSWORD="testpass",
    SSLCOMMERZ_IS_SANDBOX=True,
)
class LedgerAndPaymentTests(TestCase):
    def test_ensure_ledger_creates_fifty_taka_months(self):
        member = _member()
        cy, cm = current_year_month()
        ensure_ledger_months(member, cy, cm)
        fee = MembershipFee.objects.get(member=member, year=cy, month=cm)
        self.assertEqual(fee.amount, MEMBERSHIP_MONTHLY_FEE_BDT)
        self.assertEqual(fee.status, DonationStatus.PENDING)

    def test_multi_month_pay_and_paid_through(self):
        member = _member(phone="01710000002")
        cy, cm = current_year_month()
        ny, nm = add_months(cy, cm, 1)
        months = [{"year": cy, "month": cm}, {"year": ny, "month": nm}]
        mark_fee_months_paid(
            member,
            months,
            payment_method=PaymentMethod.CASH,
            source="ADMIN",
        )
        self.assertEqual(paid_through(member), (ny, nm))
        self.assertTrue(is_prepaid_beyond_current(member))
        self.assertEqual(
            MembershipFee.objects.filter(member=member, status=DonationStatus.COMPLETED).count(),
            2,
        )

    def test_paid_through_contiguous_no_gaps(self):
        member = _member(phone="01710000022")
        cy, cm = current_year_month()
        # Force join to current month for predictable chain.
        member.joined_at = timezone.now().replace(day=1)
        member.save(update_fields=["joined_at"])
        m2y, m2m = add_months(cy, cm, 1)
        m3y, m3m = add_months(cy, cm, 2)
        mark_fee_months_paid(
            member,
            [
                {"year": cy, "month": cm},
                {"year": m2y, "month": m2m},
                {"year": m3y, "month": m3m},
            ],
            payment_method=PaymentMethod.CASH,
            source="ADMIN",
        )
        self.assertEqual(paid_through(member), (m3y, m3m))

    def test_paid_through_stops_at_gap(self):
        member = _member(phone="01710000023")
        member.joined_at = timezone.now().replace(day=1)
        member.save(update_fields=["joined_at"])
        cy, cm = current_year_month()
        m2y, m2m = add_months(cy, cm, 1)
        m3y, m3m = add_months(cy, cm, 2)
        ensure_ledger_months(member, m3y, m3m)
        mark_fee_months_paid(
            member,
            [{"year": cy, "month": cm}, {"year": m3y, "month": m3m}],
            payment_method=PaymentMethod.CASH,
            source="ADMIN",
        )
        # Gap in month+1 → paid_through is current only, not month+2.
        self.assertEqual(paid_through(member), (cy, cm))
        self.assertNotEqual(paid_through(member), (m3y, m3m))
        # Middle month still pending
        self.assertEqual(
            MembershipFee.objects.get(member=member, year=m2y, month=m2m).status,
            DonationStatus.PENDING,
        )

    def test_prepaid_forces_autopay_off(self):
        member = _member(phone="01710000003")
        cy, cm = current_year_month()
        y1, m1 = add_months(cy, cm, 1)
        y2, m2 = add_months(cy, cm, 2)
        profile = MembershipAutoPay.objects.create(
            member=member, is_enabled=True, mode=AutoPayMode.MOCK
        )
        # Contiguous prepaid months (gap would stop paid_through at current).
        mark_fee_months_paid(
            member,
            [
                {"year": cy, "month": cm},
                {"year": y1, "month": m1},
                {"year": y2, "month": m2},
            ],
            payment_method=PaymentMethod.CASH,
            source="ADMIN",
        )
        profile.refresh_from_db()
        self.assertFalse(profile.is_enabled)

    def test_activate_autopay_refused_when_prepaid(self):
        member = _member(phone="01710000004")
        cy, cm = current_year_month()
        ny, nm = add_months(cy, cm, 1)
        mark_fee_months_paid(
            member,
            [{"year": cy, "month": cm}, {"year": ny, "month": nm}],
            payment_method=PaymentMethod.CASH,
            source="ADMIN",
        )
        with self.assertRaises(ValueError):
            activate_autopay(member)

    def test_activate_when_due_and_deactivate(self):
        member = _member(phone="01710000005")
        seed_ledger_for_new_member(member)
        profile = activate_autopay(member, actor=member.user)
        self.assertTrue(profile.is_enabled)
        self.assertEqual(profile.mode, AutoPayMode.MOCK)
        self.assertIsNone(profile.payment_token)
        deactivate_autopay(member, actor=member.user)
        profile.refresh_from_db()
        self.assertFalse(profile.is_enabled)

    @override_settings(DEBUG=True, ALLOW_MOCK_AUTOPAY_WHEN_DEBUG_FALSE=False)
    def test_mock_charge_no_http(self):
        member = _member(phone="01710000006")
        seed_ledger_for_new_member(member)
        profile = activate_autopay(member)
        profile.next_charge_on = timezone.localdate()
        profile.save(update_fields=["next_charge_on"])
        with patch("requests.post") as post, patch("requests.get") as get:
            payment = mock_charge_due_autopay(profile)
            post.assert_not_called()
            get.assert_not_called()
        self.assertIsNotNone(payment)
        cy, cm = current_year_month()
        self.assertTrue(
            MembershipFee.objects.filter(
                member=member, year=cy, month=cm, status=DonationStatus.COMPLETED
            ).exists()
        )

    def test_admin_record_cash(self):
        admin = _verified_user("finance@example.com", role=Role.FINANCE_OFFICER)
        member = _member(phone="01710000007")
        cy, cm = current_year_month()
        payment = record_admin_fee_payment(
            member,
            [{"year": cy, "month": cm}],
            payment_method=PaymentMethod.CASH,
            actor=admin,
        )
        self.assertEqual(payment.status, DonationStatus.COMPLETED)
        # Admin must never silently enable autopay
        from members.billing import get_or_create_autopay

        self.assertFalse(get_or_create_autopay(member).is_enabled)

    def test_idempotent_complete_fee_payment(self):
        member = _member(phone="01710000008")
        cy, cm = current_year_month()
        ensure_ledger_months(member, cy, cm)
        txn = Transaction.objects.create(
            session_id="s1",
            tran_id="ZFTESTIDEM1",
            amount=50,
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
        )
        data = {
            "status": "VALID",
            "tran_id": "ZFTESTIDEM1",
            "amount": "50.00",
            "currency": "BDT",
            "bank_tran_id": "B1",
            "card_type": "VISA",
            "card_no": "411111******1111",
            "card_issuer": "Bank",
            "risk_level": "0",
        }
        complete_fee_payment(payment, val_id="v1", validation_data=data)
        complete_fee_payment(payment, val_id="v1", validation_data=data)
        self.assertEqual(
            MembershipFee.objects.filter(
                member=member, year=cy, month=cm, status=DonationStatus.COMPLETED
            ).count(),
            1,
        )

    @patch("donations.gateways.sslcommerz.SSLCommerzGateway.init_payment", return_value="https://pay.example/x")
    def test_checkout_blocked_when_ssl_disabled(self, _init):
        PaymentMethodConfig.objects.update_or_create(
            method=PaymentMethod.SSLCOMMERZ,
            defaults={
                "display_name": "SSLCommerz",
                "channel_kind": ChannelKind.ONLINE_HOSTED,
                "is_enabled": False,
            },
        )
        member = _member(phone="01710000009")
        cy, cm = current_year_month()
        ensure_ledger_months(member, cy, cm)
        request = MagicMock()
        with self.assertRaises(ValueError):
            initiate_fee_checkout(
                member, [{"year": cy, "month": cm}], request=request, actor=member.user
            )

    def test_member_cannot_access_other_fees_via_admin_record(self):
        member = _member(phone="01710000010")
        other = _member(email="o@example.com", phone="01710000011")
        client = Client()
        client.force_login(member.user)
        url = reverse("dashboard-member-fee-record", kwargs={"pk": other.pk})
        response = client.post(
            url,
            {"months": [f"{current_year_month()[0]}-{current_year_month()[1]}"], "payment_method": "CASH"},
        )
        # No membership_fees.create permission → redirect away, unpaid remains
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            MembershipFee.objects.filter(member=other, status=DonationStatus.COMPLETED).exists()
        )


@override_settings(SSLCOMMERZ_IS_SANDBOX=True)
class AutoPayAdminDeactivateTests(TestCase):
    def test_admin_cannot_enable_via_deactivate_endpoint(self):
        admin = _verified_user("sa@example.com", role=Role.SUPER_ADMIN)
        admin.is_superuser = True
        admin.save(update_fields=["is_superuser"])
        member = _member(phone="01710000012")
        seed_ledger_for_new_member(member)
        profile = MembershipAutoPay.objects.get(member=member)
        self.assertFalse(profile.is_enabled)
        client = Client()
        client.force_login(admin)
        # Even if somehow posted, deactivate endpoint only disables.
        client.post(reverse("dashboard-member-fee-autopay-deactivate", kwargs={"pk": member.pk}))
        profile.refresh_from_db()
        self.assertFalse(profile.is_enabled)
