"""PAY-WP2: public current-month membership fee payment tests."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import signing
from django.core.cache import cache
from django.test import Client, RequestFactory, TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role
from core.choices import DonationStatus, PaymentMethod
from donations.models import ChannelKind, PaymentMethodConfig, TransactionPurpose
from finance.membership_income import income_key_for_fee_payment
from finance.models import Income
from members.billing import (
    current_year_month,
    ensure_ledger_months,
    mark_fee_months_paid,
)
from members.models import (
    Member,
    MemberStatus,
    MembershipFee,
    MembershipFeePayment,
)
from members.public_fee_payment import (
    TOKEN_SALT,
    PublicFeeError,
    build_public_current_month_snapshot,
    initiate_public_current_month_checkout,
    issue_public_fee_checkout_token,
    load_public_fee_checkout_token,
)

User = get_user_model()


def _csrf_ready_client():
    from django.conf import settings as dj_settings

    client = Client(enforce_csrf_checks=True)
    client.cookies[dj_settings.LANGUAGE_COOKIE_NAME] = "en"
    client.get(reverse("public-membership-fee-payment"))
    return client


def _csrf_post(client, url, data=None):
    data = dict(data or {})
    data["csrfmiddlewaretoken"] = client.cookies["csrftoken"].value
    return client.post(url, data)


def _verified_user(email, role=Role.MEMBER):
    user = User.objects.create_user(email=email, password="Str0ngPass!23", role=role)
    user.email_verified = timezone.now()
    user.save(update_fields=["email_verified"])
    return user


def _member(
    *,
    email="pubfee@example.com",
    phone="01719990001",
    member_id="ZF-2026-00025",
    status=MemberStatus.APPROVED,
    first_name="Md.",
    last_name="Example",
):
    user = _verified_user(email)
    return Member.objects.create(
        member_id=member_id,
        user=user,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        present_address="Secret Address Line",
        district="Dhaka",
        status=status,
        joined_at=timezone.now(),
        approved_at=timezone.now(),
    )


def _enable_ssl():
    PaymentMethodConfig.objects.update_or_create(
        method=PaymentMethod.SSLCOMMERZ,
        defaults={
            "is_enabled": True,
            "channel_kind": ChannelKind.ONLINE_HOSTED,
            "enabled_for_donation": True,
            "enabled_for_membership_fee": True,
            "display_name": "SSLCommerz",
        },
    )


@override_settings(
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
    SSLCOMMERZ_STORE_ID="teststore",
    SSLCOMMERZ_STORE_PASSWORD="testpass",
    SSLCOMMERZ_IS_SANDBOX=True,
)
class PublicFeeVerifyTests(TestCase):
    def setUp(self):
        from django.conf import settings as dj_settings

        cache.clear()
        _enable_ssl()
        self.client = Client(enforce_csrf_checks=True)
        self.client.cookies[dj_settings.LANGUAGE_COOKIE_NAME] = "en"
        self.member = _member()
        cy, cm = current_year_month()
        ensure_ledger_months(self.member, cy, cm)

    def test_start_page_ok(self):
        r = self.client.get(reverse("public-membership-fee-payment"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Membership Fee Payment")
        self.assertContains(r, "without logging in")

    def test_verify_requires_csrf(self):
        r = self.client.post(
            reverse("public-membership-fee-verify"),
            {"member_id": self.member.member_id},
        )
        self.assertEqual(r.status_code, 403)

    def test_valid_membership_id_shows_minimal_fields(self):
        c = _csrf_ready_client()
        r = _csrf_post(
            c,
            reverse("public-membership-fee-verify"),
            {"member_id": self.member.member_id},
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Md. Example")
        self.assertContains(r, self.member.member_id)
        self.assertContains(r, "Pay Now")
        self.assertNotContains(r, "Secret Address")
        self.assertNotContains(r, self.member.phone)
        self.assertNotContains(r, "pubfee@example.com")

    def test_invalid_membership_id_generic(self):
        c = _csrf_ready_client()
        r = _csrf_post(
            c,
            reverse("public-membership-fee-verify"),
            {"member_id": "ZF-NOPE-99999"},
        )
        self.assertEqual(r.status_code, 400)
        self.assertContains(r, "could not verify", status_code=400)

    def test_unapproved_member_generic(self):
        pending = _member(
            email="pending@example.com",
            phone="01719990002",
            member_id="ZF-2026-00099",
            status=MemberStatus.PENDING,
        )
        c = _csrf_ready_client()
        r = _csrf_post(
            c,
            reverse("public-membership-fee-verify"),
            {"member_id": pending.member_id},
        )
        self.assertEqual(r.status_code, 400)
        self.assertContains(r, "could not verify", status_code=400)

    def test_already_paid_current_month(self):
        cy, cm = current_year_month()
        mark_fee_months_paid(
            self.member,
            [{"year": cy, "month": cm}],
            payment_method=PaymentMethod.CASH,
            source="ADMIN",
        )
        c = _csrf_ready_client()
        r = _csrf_post(
            c,
            reverse("public-membership-fee-verify"),
            {"member_id": self.member.member_id},
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "already been paid")
        self.assertContains(r, "Login to your account")

    def test_verify_rejects_previous_month_crafted(self):
        cy, cm = current_year_month()
        prev_y, prev_m = (cy - 1, 12) if cm == 1 else (cy, cm - 1)
        c = _csrf_ready_client()
        r = _csrf_post(
            c,
            reverse("public-membership-fee-verify"),
            {
                "member_id": self.member.member_id,
                "year": prev_y,
                "month": prev_m,
            },
        )
        self.assertEqual(r.status_code, 400)
        self.assertContains(r, "log in to your account", status_code=400)

    def test_rate_limiting(self):
        c = _csrf_ready_client()
        with patch("members.public_fee_payment.VERIFY_MAX_PER_HOUR", 2), patch(
            "members.public_fee_payment.VERIFY_COOLDOWN_SECONDS", 0
        ):
            for _ in range(2):
                cache.delete("public_fee_verify_cd:127.0.0.1")
                r = _csrf_post(
                    c,
                    reverse("public-membership-fee-verify"),
                    {"member_id": "ZF-NOPE-0000"},
                )
                self.assertEqual(r.status_code, 400)
            cache.delete("public_fee_verify_cd:127.0.0.1")
            r = _csrf_post(
                c,
                reverse("public-membership-fee-verify"),
                {"member_id": "ZF-NOPE-0000"},
            )
            self.assertContains(r, "Too many attempts", status_code=400)


@override_settings(
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
    SSLCOMMERZ_STORE_ID="teststore",
    SSLCOMMERZ_STORE_PASSWORD="testpass",
    SSLCOMMERZ_IS_SANDBOX=True,
)
class PublicFeeTokenSecurityTests(TestCase):
    def setUp(self):
        cache.clear()
        _enable_ssl()
        self.member = _member()
        cy, cm = current_year_month()
        ensure_ledger_months(self.member, cy, cm)
        self.snapshot = build_public_current_month_snapshot(self.member)
        self.token = issue_public_fee_checkout_token(self.snapshot)

    def test_pay_requires_csrf(self):
        c = Client(enforce_csrf_checks=True)
        r = c.post(
            reverse("public-membership-fee-pay"),
            {"checkout_token": self.token},
        )
        self.assertEqual(r.status_code, 403)

    def test_amount_tampering_ignored_server_amount_used(self):
        c = _csrf_ready_client()
        with patch(
            "donations.gateways.sslcommerz.SSLCommerzGateway.init_payment",
            return_value="https://gateway.example/pay",
        ):
            r = _csrf_post(
                c,
                reverse("public-membership-fee-pay"),
                {
                    "checkout_token": self.token,
                    "amount": "999999",
                    "purpose": "DONATION",
                    "member_id": "ZF-OTHER",
                },
            )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], "https://gateway.example/pay")
        payment = MembershipFeePayment.objects.get(member=self.member)
        self.assertEqual(payment.amount, self.snapshot.amount)
        self.assertEqual(payment.transaction.purpose, TransactionPurpose.MEMBERSHIP_FEE)
        self.assertNotEqual(float(payment.amount), 999999.0)

    def test_period_tampering_rejected(self):
        c = _csrf_ready_client()
        cy, cm = current_year_month()
        prev_y, prev_m = (cy - 1, 12) if cm == 1 else (cy, cm - 1)
        r = _csrf_post(
            c,
            reverse("public-membership-fee-pay"),
            {
                "checkout_token": self.token,
                "year": prev_y,
                "month": prev_m,
            },
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, reverse("public-membership-fee-payment"))

    def test_future_month_rejected(self):
        c = _csrf_ready_client()
        cy, cm = current_year_month()
        fy, fm = (cy + 1, 1) if cm == 12 else (cy, cm + 1)
        r = _csrf_post(
            c,
            reverse("public-membership-fee-pay"),
            {
                "checkout_token": self.token,
                "period_key": f"{fy}-{fm:02d}",
            },
        )
        self.assertEqual(r.status_code, 302)

    def test_bad_token_rejected(self):
        c = _csrf_ready_client()
        r = _csrf_post(
            c,
            reverse("public-membership-fee-pay"),
            {"checkout_token": "not.a.valid.token"},
        )
        self.assertEqual(r.status_code, 302)

    def test_expired_token_rejected(self):
        with patch(
            "members.public_fee_payment.signing.loads",
            side_effect=signing.SignatureExpired("expired"),
        ):
            with self.assertRaises(PublicFeeError) as ctx:
                load_public_fee_checkout_token(self.token)
            self.assertEqual(ctx.exception.code, "expired")

    def test_token_for_another_member_rejected(self):
        other = _member(
            email="other@example.com",
            phone="01719990003",
            member_id="ZF-2026-00026",
        )
        cy, cm = current_year_month()
        ensure_ledger_months(other, cy, cm)
        payload = signing.loads(self.token, salt=TOKEN_SALT)
        payload["mid"] = str(other.pk)
        forged = signing.dumps(payload, salt=TOKEN_SALT)
        c = _csrf_ready_client()
        with patch("members.public_fee_payment.initiate_fee_checkout") as mock_init:
            r = _csrf_post(
                c,
                reverse("public-membership-fee-pay"),
                {"checkout_token": forged},
            )
        self.assertEqual(r.status_code, 302)
        mock_init.assert_not_called()

    def test_token_amount_tamper_rejected(self):
        payload = signing.loads(self.token, salt=TOKEN_SALT)
        payload["amount"] = "99999.00"
        forged = signing.dumps(payload, salt=TOKEN_SALT)
        c = _csrf_ready_client()
        with patch("members.public_fee_payment.initiate_fee_checkout") as mock_init:
            r = _csrf_post(
                c,
                reverse("public-membership-fee-pay"),
                {"checkout_token": forged},
            )
        self.assertEqual(r.status_code, 302)
        mock_init.assert_not_called()

    def test_token_period_tamper_rejected(self):
        payload = signing.loads(self.token, salt=TOKEN_SALT)
        cy, cm = current_year_month()
        payload["y"], payload["m"] = (cy - 1, 12) if cm == 1 else (cy, cm - 1)
        forged = signing.dumps(payload, salt=TOKEN_SALT)
        c = _csrf_ready_client()
        with patch("members.public_fee_payment.initiate_fee_checkout") as mock_init:
            r = _csrf_post(
                c,
                reverse("public-membership-fee-pay"),
                {"checkout_token": forged},
            )
        self.assertEqual(r.status_code, 302)
        mock_init.assert_not_called()


@override_settings(
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
    SSLCOMMERZ_STORE_ID="teststore",
    SSLCOMMERZ_STORE_PASSWORD="testpass",
    SSLCOMMERZ_IS_SANDBOX=True,
)
class PublicFeeCheckoutFlowTests(TestCase):
    def setUp(self):
        cache.clear()
        _enable_ssl()
        self.member = _member()
        cy, cm = current_year_month()
        ensure_ledger_months(self.member, cy, cm)

    def test_sslcommerz_init_correct_amount_purpose(self):
        snap = build_public_current_month_snapshot(self.member)
        token = issue_public_fee_checkout_token(snap)
        c = _csrf_ready_client()

        def fake_init(payment, request):
            self.assertEqual(payment.amount, snap.amount)
            self.assertEqual(
                payment.transaction.purpose, TransactionPurpose.MEMBERSHIP_FEE
            )
            self.assertEqual(len(payment.months), 1)
            cy, cm = current_year_month()
            self.assertEqual(payment.months[0], {"year": cy, "month": cm})
            return "https://sandbox.sslcommerz.com/EasyCheckOut/test"

        with patch(
            "donations.gateways.sslcommerz.SSLCommerzGateway.init_payment",
            side_effect=fake_init,
        ):
            r = _csrf_post(
                c,
                reverse("public-membership-fee-pay"),
                {"checkout_token": token},
            )
        self.assertEqual(r.status_code, 302)
        self.assertIn("sslcommerz", r["Location"])
        payment = MembershipFeePayment.objects.get(member=self.member)
        self.assertTrue(payment.notes.startswith("public_checkout:"))
        self.assertEqual(payment.transaction.purpose, TransactionPurpose.MEMBERSHIP_FEE)
        self.assertNotEqual(
            payment.transaction.purpose, TransactionPurpose.MEMBERSHIP_REGISTRATION
        )
        self.assertNotEqual(payment.transaction.purpose, TransactionPurpose.DONATION)

    def _valid_payload(self, payment, val_id="VAL-PUB-1"):
        return {
            "status": "VALID",
            "tran_id": payment.transaction.tran_id,
            "val_id": val_id,
            "amount": str(payment.amount),
            "currency": "BDT",
            "bank_tran_id": "BANK-PUB-1",
            "card_type": "VISA",
            "card_no": "411111****1111",
        }

    def test_success_completes_and_income_once(self):
        snap = build_public_current_month_snapshot(self.member)
        token = issue_public_fee_checkout_token(snap)
        c = _csrf_ready_client()
        with patch(
            "donations.gateways.sslcommerz.SSLCommerzGateway.init_payment",
            return_value="https://gateway.example/pay",
        ):
            _csrf_post(
                c,
                reverse("public-membership-fee-pay"),
                {"checkout_token": token},
            )
        payment = MembershipFeePayment.objects.get(member=self.member)
        payload = self._valid_payload(payment)
        with patch("donations.services.validate_transaction", return_value=payload):
            r = c.post(
                reverse("membership-fee-pay-success"),
                {"val_id": "VAL-PUB-1", "tran_id": payment.transaction.tran_id},
            )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Payment Successful")
        payment.refresh_from_db()
        self.assertEqual(payment.status, DonationStatus.COMPLETED)
        cy, cm = current_year_month()
        fee = MembershipFee.objects.get(member=self.member, year=cy, month=cm)
        self.assertEqual(fee.status, DonationStatus.COMPLETED)
        key = income_key_for_fee_payment(payment)
        self.assertEqual(Income.objects.filter(idempotency_key=key).count(), 1)

        with patch("donations.services.validate_transaction", return_value=payload):
            c.post(
                reverse("membership-fee-pay-success"),
                {"val_id": "VAL-PUB-1", "tran_id": payment.transaction.tran_id},
            )
        self.assertEqual(Income.objects.filter(idempotency_key=key).count(), 1)

    def test_ipn_duplicate_safe(self):
        snap = build_public_current_month_snapshot(self.member)
        token = issue_public_fee_checkout_token(snap)
        c = _csrf_ready_client()
        with patch(
            "donations.gateways.sslcommerz.SSLCommerzGateway.init_payment",
            return_value="https://gateway.example/pay",
        ):
            _csrf_post(
                c,
                reverse("public-membership-fee-pay"),
                {"checkout_token": token},
            )
        payment = MembershipFeePayment.objects.get(member=self.member)
        payload = self._valid_payload(payment, val_id="VAL-IPN-1")
        with patch("donations.services.validate_transaction", return_value=payload):
            r1 = c.post(
                reverse("membership-fee-pay-ipn"),
                {"val_id": "VAL-IPN-1", "tran_id": payment.transaction.tran_id},
            )
            r2 = c.post(
                reverse("membership-fee-pay-ipn"),
                {"val_id": "VAL-IPN-1", "tran_id": payment.transaction.tran_id},
            )
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)
        key = income_key_for_fee_payment(payment)
        self.assertEqual(Income.objects.filter(idempotency_key=key).count(), 1)

    def test_fail_and_cancel_guest_redirect(self):
        snap = build_public_current_month_snapshot(self.member)
        token = issue_public_fee_checkout_token(snap)
        c = _csrf_ready_client()
        with patch(
            "donations.gateways.sslcommerz.SSLCommerzGateway.init_payment",
            return_value="https://gateway.example/pay",
        ):
            _csrf_post(
                c,
                reverse("public-membership-fee-pay"),
                {"checkout_token": token},
            )
        payment = MembershipFeePayment.objects.get(member=self.member)
        r = c.post(
            reverse("membership-fee-pay-fail"),
            {"tran_id": payment.transaction.tran_id},
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, reverse("public-membership-fee-payment"))

        cache.clear()
        token2 = issue_public_fee_checkout_token(
            build_public_current_month_snapshot(self.member)
        )
        with patch(
            "donations.gateways.sslcommerz.SSLCommerzGateway.init_payment",
            return_value="https://gateway.example/pay",
        ):
            _csrf_post(
                c,
                reverse("public-membership-fee-pay"),
                {"checkout_token": token2},
            )
        payment2 = (
            MembershipFeePayment.objects.filter(member=self.member)
            .order_by("-created_at")
            .first()
        )
        r = c.post(
            reverse("membership-fee-pay-cancel"),
            {"tran_id": payment2.transaction.tran_id},
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, reverse("public-membership-fee-payment"))

    def test_validation_failure_does_not_complete(self):
        snap = build_public_current_month_snapshot(self.member)
        token = issue_public_fee_checkout_token(snap)
        c = _csrf_ready_client()
        with patch(
            "donations.gateways.sslcommerz.SSLCommerzGateway.init_payment",
            return_value="https://gateway.example/pay",
        ):
            _csrf_post(
                c,
                reverse("public-membership-fee-pay"),
                {"checkout_token": token},
            )
        payment = MembershipFeePayment.objects.get(member=self.member)
        with patch("donations.services.validate_transaction", return_value=None):
            r = c.post(
                reverse("membership-fee-pay-success"),
                {"val_id": "BAD", "tran_id": payment.transaction.tran_id},
            )
        self.assertEqual(r.status_code, 302)
        payment.refresh_from_db()
        self.assertEqual(payment.status, DonationStatus.PENDING)
        self.assertEqual(Income.objects.count(), 0)


@override_settings(
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
    SSLCOMMERZ_STORE_ID="teststore",
    SSLCOMMERZ_STORE_PASSWORD="testpass",
    SSLCOMMERZ_IS_SANDBOX=True,
)
class PublicFeeRaceTests(TransactionTestCase):
    def setUp(self):
        cache.clear()
        _enable_ssl()
        self.member = _member(email="race@example.com", phone="01719990009")
        cy, cm = current_year_month()
        ensure_ledger_months(self.member, cy, cm)

    def test_callback_ipn_race_income_once(self):
        snap = build_public_current_month_snapshot(self.member)
        token = issue_public_fee_checkout_token(snap)
        rf = RequestFactory()
        req = rf.post("/membership-fee-payment/pay/")
        req.session = {}
        with patch(
            "donations.gateways.sslcommerz.SSLCommerzGateway.init_payment",
            return_value="https://gateway.example/pay",
        ):
            payment, _url, _ = initiate_public_current_month_checkout(
                token=token, request=req
            )

        payload = {
            "status": "VALID",
            "tran_id": payment.transaction.tran_id,
            "val_id": "VAL-RACE",
            "amount": str(payment.amount),
            "currency": "BDT",
        }

        def hit_success():
            from django.db import close_old_connections

            close_old_connections()
            try:
                client = Client()
                with patch(
                    "donations.services.validate_transaction", return_value=payload
                ):
                    return client.post(
                        reverse("membership-fee-pay-success"),
                        {
                            "val_id": "VAL-RACE",
                            "tran_id": payment.transaction.tran_id,
                        },
                    )
            finally:
                close_old_connections()

        def hit_ipn():
            from django.db import close_old_connections

            close_old_connections()
            try:
                client = Client()
                with patch(
                    "donations.services.validate_transaction", return_value=payload
                ):
                    return client.post(
                        reverse("membership-fee-pay-ipn"),
                        {
                            "val_id": "VAL-RACE",
                            "tran_id": payment.transaction.tran_id,
                        },
                    )
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            f1 = pool.submit(hit_success)
            f2 = pool.submit(hit_ipn)
            f1.result()
            f2.result()

        key = income_key_for_fee_payment(payment)
        self.assertEqual(Income.objects.filter(idempotency_key=key).count(), 1)
        payment.refresh_from_db()
        self.assertEqual(payment.status, DonationStatus.COMPLETED)
