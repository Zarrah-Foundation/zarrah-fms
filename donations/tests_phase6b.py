"""Phase 6B — donation income, completion security, decimal validation, admin."""

from decimal import Decimal
from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone

from accounts.models import Role
from core.choices import DonationStatus, PaymentMethod
from donations.admin import DonationAdmin, TransactionAdmin
from donations.gateways.sslcommerz import SSLCommerzGateway
from donations.models import Donation, DonationCategory, Transaction, TransactionPurpose
from donations.money import amounts_equal, to_money
from donations.services import (
    DonationCompletionError,
    complete_donation,
    create_manual_donation,
)
from finance.donation_income import ensure_income_for_donation, income_key_for_donation
from finance.models import Income
from members.admin import MembershipAutoPayAdmin, MembershipFeeAdmin
from members.billing import deactivate_autopay
from members.models import AutoPayMode, Member, MembershipAutoPay, MemberStatus

User = get_user_model()


def _category():
    import uuid

    slug = f"general-p6b-{uuid.uuid4().hex[:8]}"
    return DonationCategory.objects.create(
        name_en="General", name_bn="সাধারণ", slug=slug
    )


def _pending_gateway_donation(*, amount=100.0, tran_id="ZF-P6B-1", currency="BDT"):
    cat = _category()
    txn = Transaction.objects.create(
        session_id=f"sess-{tran_id}",
        tran_id=tran_id,
        amount=amount,
        currency=currency,
        status=DonationStatus.PENDING,
        purpose=TransactionPurpose.DONATION,
        gateway=PaymentMethod.SSLCOMMERZ,
        cus_name="Donor",
        cus_email="donor@example.com",
    )
    donation = Donation.objects.create(
        donor_name="Donor",
        donor_email="donor@example.com",
        amount=amount,
        currency=currency,
        category=cat,
        payment_method=PaymentMethod.SSLCOMMERZ,
        status=DonationStatus.PENDING,
        transaction=txn,
    )
    return donation


def _valid_payload(donation, **overrides):
    data = {
        "status": "VALID",
        "tran_id": donation.transaction.tran_id,
        "amount": f"{float(donation.amount):.2f}",
        "currency": donation.currency or "BDT",
        "bank_tran_id": "BANK1",
        "val_id": "VAL1",
    }
    data.update(overrides)
    return data


class MoneyHelperTests(TestCase):
    def test_decimal_equality(self):
        self.assertTrue(amounts_equal("100.00", 100))
        self.assertTrue(amounts_equal(Decimal("100.0"), "100.00"))
        self.assertFalse(amounts_equal("100.00", "100.01"))
        self.assertEqual(to_money("10.999"), Decimal("11.00"))


@override_settings(
    SSLCOMMERZ_STORE_ID="store",
    SSLCOMMERZ_STORE_PASSWORD="pass",
    SSLCOMMERZ_IS_SANDBOX=True,
)
class SSLCommerzDecimalValidationTests(TestCase):
    @patch("donations.gateways.sslcommerz.requests.get")
    def test_exact_amount_and_currency(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "status": "VALID",
            "tran_id": "T1",
            "amount": "50.00",
            "currency": "BDT",
        }
        mock_get.return_value.raise_for_status = lambda: None
        gw = SSLCommerzGateway()
        data = gw.validate_transaction("v", "T1", 50, currency="BDT")
        self.assertIsNotNone(data)

    @patch("donations.gateways.sslcommerz.requests.get")
    def test_tampered_amount_rejected(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "status": "VALID",
            "tran_id": "T1",
            "amount": "51.00",
            "currency": "BDT",
        }
        mock_get.return_value.raise_for_status = lambda: None
        gw = SSLCommerzGateway()
        self.assertIsNone(gw.validate_transaction("v", "T1", 50, currency="BDT"))

    @patch("donations.gateways.sslcommerz.requests.get")
    def test_tampered_currency_rejected(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "status": "VALID",
            "tran_id": "T1",
            "amount": "50.00",
            "currency": "USD",
        }
        mock_get.return_value.raise_for_status = lambda: None
        gw = SSLCommerzGateway()
        self.assertIsNone(gw.validate_transaction("v", "T1", 50, currency="BDT"))

    @patch("donations.gateways.sslcommerz.requests.get")
    def test_store_amount_net_may_differ_from_charged_amount(self, mock_get):
        """store_amount is merchant net (fees/discounts); charged amount must match."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "status": "VALIDATED",
            "tran_id": "T1",
            "amount": "50.00",
            "store_amount": "48.75",
            "currency": "BDT",
        }
        mock_get.return_value.raise_for_status = lambda: None
        gw = SSLCommerzGateway()
        data = gw.validate_transaction("v", "T1", 50, currency="BDT")
        self.assertIsNotNone(data)
        self.assertEqual(data["store_amount"], "48.75")


class DonationCompletionSecurityTests(TestCase):
    def test_complete_without_validation_rejected(self):
        donation = _pending_gateway_donation()
        with self.assertRaises(DonationCompletionError):
            complete_donation(donation)
        donation.refresh_from_db()
        self.assertEqual(donation.status, DonationStatus.PENDING)
        self.assertEqual(Income.objects.count(), 0)

    def test_complete_with_invalid_status_rejected(self):
        donation = _pending_gateway_donation()
        with self.assertRaises(DonationCompletionError):
            complete_donation(
                donation,
                val_id="v",
                validation_data=_valid_payload(donation, status="FAILED"),
            )
        donation.refresh_from_db()
        self.assertEqual(donation.status, DonationStatus.PENDING)

    def test_tampered_amount_rejected_at_service(self):
        donation = _pending_gateway_donation(amount=100)
        with self.assertRaises(DonationCompletionError):
            complete_donation(
                donation,
                val_id="v",
                validation_data=_valid_payload(donation, amount="999.00"),
            )

    def test_wrong_tran_id_rejected(self):
        donation = _pending_gateway_donation(tran_id="ZF-RIGHT")
        with self.assertRaises(DonationCompletionError):
            complete_donation(
                donation,
                val_id="v",
                validation_data=_valid_payload(donation, tran_id="ZF-WRONG"),
            )


class DonationIncomeTests(TestCase):
    def test_completed_donation_creates_one_income(self):
        donation = _pending_gateway_donation(amount=250)
        complete_donation(
            donation, val_id="v1", validation_data=_valid_payload(donation)
        )
        key = income_key_for_donation(donation)
        self.assertEqual(Income.objects.filter(idempotency_key=key).count(), 1)
        income = Income.objects.get(idempotency_key=key)
        self.assertEqual(income.amount, 250)

    def test_duplicate_completion_no_second_income(self):
        donation = _pending_gateway_donation(tran_id="ZF-DUP")
        payload = _valid_payload(donation)
        complete_donation(donation, val_id="v1", validation_data=payload)
        complete_donation(donation, val_id="v1", validation_data=payload)
        ensure_income_for_donation(donation)
        self.assertEqual(
            Income.objects.filter(idempotency_key=income_key_for_donation(donation)).count(),
            1,
        )

    def test_failed_donation_no_income(self):
        donation = _pending_gateway_donation(tran_id="ZF-FAIL")
        donation.status = DonationStatus.FAILED
        donation.save(update_fields=["status"])
        ensure_income_for_donation(donation)
        self.assertEqual(Income.objects.count(), 0)

    def test_cancelled_donation_no_income(self):
        donation = _pending_gateway_donation(tran_id="ZF-CAN")
        donation.status = DonationStatus.CANCELLED
        donation.save(update_fields=["status"])
        ensure_income_for_donation(donation)
        self.assertEqual(Income.objects.count(), 0)

    def test_manual_donation_creates_income_once(self):
        cat = _category()
        d1 = create_manual_donation(
            amount=75,
            category=cat,
            donor_name="Cash Donor",
            payment_method=PaymentMethod.CASH,
        )
        self.assertEqual(d1.status, DonationStatus.COMPLETED)
        key = income_key_for_donation(d1)
        self.assertEqual(Income.objects.filter(idempotency_key=key).count(), 1)
        ensure_income_for_donation(d1)
        self.assertEqual(Income.objects.filter(idempotency_key=key).count(), 1)

    def test_manual_cannot_use_sslcommerz(self):
        cat = _category()
        with self.assertRaises(DonationCompletionError):
            create_manual_donation(
                amount=10,
                category=cat,
                payment_method=PaymentMethod.SSLCOMMERZ,
            )


class AdminHardeningTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin_user = User.objects.create_superuser(
            email="p6b-admin@example.com", password="pass12345"
        )
        self.site = AdminSite()

    def test_donation_status_readonly(self):
        ma = DonationAdmin(Donation, self.site)
        self.assertIn("status", ma.readonly_fields)
        self.assertIn("amount", ma.readonly_fields)
        self.assertFalse(ma.has_add_permission(self.factory.get("/")))

    def test_transaction_not_mutable_via_post(self):
        ta = TransactionAdmin(Transaction, self.site)
        req = self.factory.post("/admin/")
        req.user = self.admin_user
        self.assertFalse(ta.has_change_permission(req))

    def test_membership_fee_not_mutable_via_post(self):
        from members.models import MembershipFee

        fa = MembershipFeeAdmin(MembershipFee, self.site)
        req = self.factory.post("/admin/")
        req.user = self.admin_user
        self.assertFalse(fa.has_change_permission(req))

    def test_autopay_cannot_be_enabled_via_admin_save(self):
        user = User.objects.create_user(email="ap@example.com", password="x")
        user.email_verified = timezone.now()
        user.save()
        member = Member.objects.create(
            member_id="AP6B1",
            user=user,
            first_name="A",
            last_name="P",
            phone="01700008881",
            present_address="Dhaka",
            district="Dhaka",
            status=MemberStatus.APPROVED,
        )
        profile = MembershipAutoPay.objects.create(
            member=member, is_enabled=False, mode=AutoPayMode.MOCK
        )
        ma = MembershipAutoPayAdmin(MembershipAutoPay, self.site)
        req = self.factory.get("/admin/")
        req.user = self.admin_user
        # Simulate attempted enable
        profile.is_enabled = True
        ma.save_model(req, profile, form=None, change=True)
        profile.refresh_from_db()
        self.assertFalse(profile.is_enabled)

    def test_autopay_deactivate_service_still_works(self):
        user = User.objects.create_user(email="ap2@example.com", password="x")
        user.email_verified = timezone.now()
        user.save()
        member = Member.objects.create(
            member_id="AP6B2",
            user=user,
            first_name="A",
            last_name="P",
            phone="01700008882",
            present_address="Dhaka",
            district="Dhaka",
            status=MemberStatus.APPROVED,
        )
        MembershipAutoPay.objects.create(
            member=member, is_enabled=True, mode=AutoPayMode.MOCK
        )
        deactivate_autopay(member, actor=self.admin_user)
        member.auto_pay.refresh_from_db()
        self.assertFalse(member.auto_pay.is_enabled)


class PurposeFlagRegressionTests(TestCase):
    @override_settings(
        SSLCOMMERZ_STORE_ID="store",
        SSLCOMMERZ_STORE_PASSWORD="pass",
        SSLCOMMERZ_IS_SANDBOX=True,
    )
    def test_purpose_toggles_independent(self):
        from donations.gateway_capabilities import online_checkout_allowed
        from donations.models import ChannelKind, PaymentMethodConfig

        PaymentMethodConfig.objects.update_or_create(
            method=PaymentMethod.SSLCOMMERZ,
            defaults={
                "is_enabled": True,
                "channel_kind": ChannelKind.ONLINE_HOSTED,
                "enabled_for_donation": True,
                "enabled_for_membership_fee": False,
            },
        )
        ok_d, _ = online_checkout_allowed(purpose=TransactionPurpose.DONATION)
        ok_m, _ = online_checkout_allowed(purpose=TransactionPurpose.MEMBERSHIP_FEE)
        self.assertTrue(ok_d)
        self.assertFalse(ok_m)


@override_settings(
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
    SSLCOMMERZ_STORE_ID="store",
    SSLCOMMERZ_STORE_PASSWORD="pass",
    SSLCOMMERZ_IS_SANDBOX=True,
)
class GatewayReturnCallbackTests(TestCase):
    """SSLCommerz browser return uses POST without CSRF cookies."""

    def test_success_post_csrf_exempt_completes_and_income_once(self):
        from django.test import Client

        donation = _pending_gateway_donation(amount=50, tran_id="ZF-RET-1")
        payload = _valid_payload(donation, val_id="VAL-RET-1")
        client = Client(enforce_csrf_checks=True)
        with patch("donations.views.validate_transaction", return_value=payload):
            response = client.post(
                "/donation/success/",
                {"val_id": "VAL-RET-1", "tran_id": "ZF-RET-1"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.status_code, 403)
        donation.refresh_from_db()
        self.assertEqual(donation.status, DonationStatus.COMPLETED)
        key = income_key_for_donation(donation)
        self.assertEqual(Income.objects.filter(idempotency_key=key).count(), 1)

        with patch("donations.views.validate_transaction", return_value=payload):
            client.post(
                "/donation/success/",
                {"val_id": "VAL-RET-1", "tran_id": "ZF-RET-1"},
            )
        self.assertEqual(Income.objects.filter(idempotency_key=key).count(), 1)

    def test_fail_post_marks_failed(self):
        from django.test import Client

        donation = _pending_gateway_donation(tran_id="ZF-FAIL-POST")
        client = Client(enforce_csrf_checks=True)
        response = client.post("/donation/fail/", {"tran_id": "ZF-FAIL-POST"})
        self.assertEqual(response.status_code, 200)
        donation.refresh_from_db()
        self.assertEqual(donation.status, DonationStatus.FAILED)

    def test_cancel_post_marks_cancelled(self):
        from django.test import Client

        donation = _pending_gateway_donation(tran_id="ZF-CAN-POST")
        client = Client(enforce_csrf_checks=True)
        response = client.post("/donation/cancel/", {"tran_id": "ZF-CAN-POST"})
        self.assertEqual(response.status_code, 200)
        donation.refresh_from_db()
        self.assertEqual(donation.status, DonationStatus.CANCELLED)
