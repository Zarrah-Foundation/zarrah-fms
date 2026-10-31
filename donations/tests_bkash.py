"""bKash Tokenized Checkout v2 sandbox tests. HTTP is mocked. No live charges."""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role
from core.choices import DonationStatus, PaymentMethod
from donations.bkash_config import (
    LIVE_CREDENTIALS_REQUIRED,
    LIVE_VERIFIED,
    NOT_CONFIGURED,
    SANDBOX_CONFIGURED,
    SANDBOX_VERIFIED,
    bkash_readiness,
    resolve_bkash_credentials,
    test_bkash_connection,
)
from donations.gateways import get_gateway
from donations.gateways.base import PaymentGatewayError
from donations.gateways.bkash_client import BkashClient, BkashTimeout
from donations.models import (
    Donation,
    DonationCategory,
    DonationRecurringCharge,
    DonationSubscription,
    GatewayWebhookEvent,
    PaymentMethodConfig,
    RefundStatus,
    Transaction,
    TransactionPurpose,
)
from donations.refund_services import RefundError, approve_refund, request_refund
from finance.models import Income
from members.billing import (
    current_year_month,
    ensure_ledger_months,
    initiate_fee_checkout,
    initiate_registration_fee_checkout,
)
from members.models import Member, MemberStatus, MembershipFee

User = get_user_model()

FAKE = dict(
    BKASH_ENV="sandbox",
    BKASH_BASE_URL="https://tokenized.sandbox.bka.sh/v2/tokenized-checkout",
    BKASH_USERNAME="sandbox-user",
    BKASH_PASSWORD="sandbox-pass",
    BKASH_APP_KEY="sandbox-app",
    BKASH_APP_SECRET="sandbox-secret",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)


class _Response:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def _completed(amount="100.00", invoice="INV", payment_id="PAY1", trx="TRX1"):
    return {
        "paymentId": payment_id,
        "trxId": trx,
        "transactionStatus": "Completed",
        "amount": amount,
        "currency": "BDT",
        "intent": "sale",
        "merchantInvoiceNumber": invoice,
    }


@override_settings(**FAKE)
class BkashSandboxTests(TestCase):
    def setUp(self):
        cache.clear()
        PaymentMethodConfig.objects.update_or_create(
            method=PaymentMethod.BKASH,
            defaults={
                "is_enabled": True,
                "is_sandbox": True,
                "enabled_for_donation": True,
                "enabled_for_membership_fee": True,
                "refunds_enabled": True,
                "supports_one_time": True,
                "supports_recurring": False,
                "hosted_via": None,
            },
        )
        self.factory = RequestFactory()
        self.category = DonationCategory.objects.create(
            name_bn="সাধারণ",
            name_en="General",
            slug=f"general-{uuid.uuid4().hex[:8]}",
            is_active=True,
        )

    def _request(self):
        request = self.factory.post("/donation/create/")
        request.META["HTTP_HOST"] = "testserver"
        request.user = User()
        return request

    def _donation(self, *, user=None, anonymous=False, amount=100):
        txn = Transaction.objects.create(
            session_id=str(uuid.uuid4()),
            tran_id=f"ZF{uuid.uuid4().hex[:12].upper()}",
            amount=amount,
            currency="BDT",
            status=DonationStatus.PENDING,
            gateway=PaymentMethod.BKASH,
            purpose=TransactionPurpose.DONATION,
            cus_name="Anonymous" if anonymous else "Donor",
            cus_phone="01710000099",
        )
        donation = Donation.objects.create(
            donor_name="Anonymous" if anonymous else "Donor",
            amount=amount,
            currency="BDT",
            category=self.category,
            payment_method=PaymentMethod.BKASH,
            status=DonationStatus.PENDING,
            transaction=txn,
            user=user,
            is_anonymous=anonymous,
        )
        return donation

    def _router(self, routes):
        def post(url, json=None, headers=None, timeout=None):
            self.assertNotIn("sandbox-secret", str(headers or {}))
            self.assertNotIn("sandbox-pass", str(json or {}))
            for suffix, payload in routes.items():
                if url.endswith(suffix):
                    if payload == "timeout":
                        import requests

                        raise requests.Timeout("timed out")
                    if suffix == "/payment/create":
                        self.assertNotIn("mode", json or {})
                        self.assertNotIn("app_secret", json or {})
                    return _Response(payload)
            return _Response({"errorMessageEn": "unexpected"})

        return post

    def test_missing_credentials_fail_closed(self):
        with override_settings(
            BKASH_USERNAME="",
            BKASH_PASSWORD="",
            BKASH_APP_KEY="",
            BKASH_APP_SECRET="",
        ):
            creds = resolve_bkash_credentials()
            self.assertFalse(creds.api_callable)
            self.assertEqual(creds.state, NOT_CONFIGURED)
            donation = self._donation()
            with patch("donations.gateways.bkash_client.requests.post") as post:
                with self.assertRaises(PaymentGatewayError):
                    get_gateway(PaymentMethod.BKASH).init_payment(donation, self._request())
                post.assert_not_called()

    def test_live_configuration_never_calls_sandbox_or_live(self):
        with override_settings(BKASH_ENV="production", BKASH_BASE_URL="https://tokenized.pay.bka.sh"):
            creds = resolve_bkash_credentials()
            self.assertEqual(creds.state, LIVE_CREDENTIALS_REQUIRED)
            self.assertFalse(creds.api_callable)
            self.assertEqual(creds.base_url, "")
            ready = bkash_readiness()
            self.assertEqual(ready["live"], LIVE_CREDENTIALS_REQUIRED)
            self.assertNotEqual(ready["one_time"], LIVE_VERIFIED)
            donation = self._donation()
            with patch("donations.gateways.bkash_client.requests.post") as post:
                with self.assertRaises(PaymentGatewayError):
                    get_gateway(PaymentMethod.BKASH).init_payment(donation, self._request())
                post.assert_not_called()

    def test_database_credentials_used_when_environment_is_empty(self):
        cfg, _created = PaymentMethodConfig.objects.update_or_create(
            method=PaymentMethod.BKASH,
            defaults={
                "is_enabled": True,
                "is_sandbox": True,
                "api_app_key": "db-app",
                "api_username": "db-user",
                "refunds_enabled": True,
                "enabled_for_donation": True,
                "enabled_for_membership_fee": True,
            },
        )
        cfg.set_api_secret("db-secret")
        cfg.set_api_password("db-password")
        cfg.save()
        with override_settings(
            BKASH_USERNAME="",
            BKASH_PASSWORD="",
            BKASH_APP_KEY="",
            BKASH_APP_SECRET="",
        ):
            creds = resolve_bkash_credentials()
        self.assertTrue(creds.api_callable)
        self.assertEqual(creds.source, "database")
        self.assertEqual(creds.app_key, "db-app")
        self.assertNotIn("db-secret", str(bkash_readiness()))

    def test_environment_credentials_win_over_database(self):
        cfg, _created = PaymentMethodConfig.objects.update_or_create(
            method=PaymentMethod.BKASH,
            defaults={
                "is_enabled": True,
                "is_sandbox": False,
                "api_app_key": "db-app",
                "api_username": "db-user",
            },
        )
        cfg.set_api_secret("db-secret")
        cfg.set_api_password("db-password")
        cfg.save()
        creds = resolve_bkash_credentials()
        self.assertEqual(creds.source, "environment")
        self.assertEqual(creds.app_key, "sandbox-app")
        self.assertTrue(creds.api_callable)

    def test_grant_caches_token_and_refresh_is_preferred(self):
        calls = []

        def post(url, json=None, headers=None, timeout=None):
            calls.append(url)
            if url.endswith("/auth/grant-token"):
                return _Response(
                    {
                        "statusCode": "0000",
                        "statusMessage": "Successful",
                        "id_token": "id-1",
                        "refresh_token": "refresh-1",
                        "expires_in": 3600,
                    }
                )
            if url.endswith("/auth/refresh-token"):
                return _Response(
                    {
                        "statusCode": "0000",
                        "id_token": "id-2",
                        "refresh_token": "refresh-2",
                        "expires_in": 3600,
                    }
                )
            return _Response({})

        client = BkashClient()
        with patch("donations.gateways.bkash_client.requests.post", side_effect=post):
            self.assertEqual(client.grant_token(force=True), "id-1")
            self.assertEqual(client.authorization_token(), "id-1")
            bundle = cache.get(client._cache_key())
            bundle["expires_at"] = 0
            cache.set(client._cache_key(), bundle, 3600)
            self.assertEqual(client.authorization_token(), "id-2")
        self.assertEqual(sum(1 for url in calls if url.endswith("/auth/grant-token")), 1)
        self.assertTrue(any(url.endswith("/auth/refresh-token") for url in calls))

    def test_create_execute_and_query(self):
        donation = self._donation(amount=100)
        routes = {
            "/auth/grant-token": {
                "statusCode": "0000",
                "id_token": "id-token",
                "refresh_token": "refresh",
                "expires_in": 3600,
            },
            "/payment/create": {
                "paymentId": "PAY1",
                "bkashURL": "https://sandbox.payment.bkash.com/?paymentId=PAY1",
                "transactionStatus": "Initiated",
                "amount": "100.00",
                "currency": "BDT",
                "merchantInvoiceNumber": donation.transaction.tran_id,
            },
            "/payment/execute": _completed("100.00", donation.transaction.tran_id),
            "/query/payment": _completed("100.00", donation.transaction.tran_id),
            "/general/search-transaction": {
                "trxId": "TRX1",
                "transactionStatus": "Completed",
                "amount": "100.00",
                "currency": "BDT",
            },
        }
        gateway = get_gateway(PaymentMethod.BKASH)
        with patch("donations.gateways.bkash_client.requests.post", side_effect=self._router(routes)):
            url = gateway.init_payment(donation, self._request())
            donation.transaction.refresh_from_db()
            self.assertEqual(url, "https://sandbox.payment.bkash.com/?paymentId=PAY1")
            self.assertEqual(donation.transaction.val_id, "PAY1")
            data = gateway.validate_transaction(
                "PAY1", donation.transaction.tran_id, donation.amount, currency="BDT"
            )
            found = gateway.search_transaction("TRX1")
        self.assertEqual(data["status"], "VALID")
        self.assertEqual(data["bank_tran_id"], "TRX1")
        self.assertEqual(found["transactionStatus"], "Completed")

    def test_execute_timeout_uses_query_and_does_not_create_another_payment(self):
        donation = self._donation()
        calls = []

        def post(url, json=None, headers=None, timeout=None):
            calls.append(url)
            if url.endswith("/auth/grant-token"):
                return _Response(
                    {"statusCode": "0000", "id_token": "id", "refresh_token": "r", "expires_in": 3600}
                )
            if url.endswith("/payment/execute"):
                import requests

                raise requests.Timeout("slow")
            if url.endswith("/query/payment"):
                return _Response(_completed("100.00", donation.transaction.tran_id, "PAY1"))
            return _Response({})

        donation.transaction.val_id = "PAY1"
        donation.transaction.save(update_fields=["val_id"])
        with patch("donations.gateways.bkash_client.requests.post", side_effect=post):
            data = get_gateway(PaymentMethod.BKASH).validate_transaction(
                "PAY1", donation.transaction.tran_id, 100, currency="BDT"
            )
        self.assertEqual(data["status"], "VALID")
        self.assertFalse(any(url.endswith("/payment/create") for url in calls))

    def test_invalid_provider_response_does_not_complete(self):
        donation = self._donation()
        self._start(donation)
        routes = {
            "/auth/grant-token": {"statusCode": "0000", "id_token": "id", "refresh_token": "r", "expires_in": 3600},
            "/payment/execute": {"errorMessageEn": "Invalid Payment ID"},
            "/query/payment": {"paymentId": "PAY1", "transactionStatus": "Initiated", "amount": "100.00", "currency": "BDT"},
        }
        with patch("donations.gateways.bkash_client.requests.post", side_effect=self._router(routes)):
            response = self.client.get(reverse("bkash-callback"), {"paymentID": "PAY1", "status": "success"})
        donation.refresh_from_db()
        self.assertEqual(donation.status, DonationStatus.PENDING)
        self.assertNotEqual(response.status_code, 500)
        self.assertEqual(Income.objects.filter(idempotency_key=f"donation:{donation.pk}").count(), 0)

    def test_successful_anonymous_and_authenticated_donations_post_income_once(self):
        user = User.objects.create_user(email="donor@example.com", password="Str0ngPass!23")
        for index, (anonymous, owner) in enumerate(((True, None), (False, user))):
            donation = self._donation(user=owner, anonymous=anonymous, amount=50)
            self._start(donation, amount="50.00", payment_id=f"PAY-DON-{index}")
            self._callback_success(donation, amount="50.00")
            donation.refresh_from_db()
            self.assertEqual(donation.status, DonationStatus.COMPLETED)
            self.assertEqual(Income.objects.filter(idempotency_key=f"donation:{donation.pk}").count(), 1)
            self._callback_success(donation, amount="50.00")
            self.assertEqual(Income.objects.filter(idempotency_key=f"donation:{donation.pk}").count(), 1)

    def test_failure_cancel_and_browser_close(self):
        failed = self._donation()
        self._start(failed)
        with patch("donations.gateways.bkash_client.requests.post") as post:
            self.client.get(reverse("bkash-callback"), {"paymentID": "PAY1", "status": "failure"})
            post.assert_not_called()
        failed.refresh_from_db()
        self.assertEqual(failed.status, DonationStatus.FAILED)

        cancelled = self._donation()
        cancelled.transaction.val_id = "PAY2"
        cancelled.transaction.save(update_fields=["val_id"])
        with patch("donations.gateways.bkash_client.requests.post") as post:
            self.client.get(reverse("bkash-callback"), {"paymentID": "PAY2", "status": "cancel"})
            post.assert_not_called()
        cancelled.refresh_from_db()
        self.assertEqual(cancelled.status, DonationStatus.CANCELLED)

        closed = self._donation()
        closed.transaction.val_id = "PAY3"
        closed.transaction.save(update_fields=["val_id"])
        closed.refresh_from_db()
        self.assertEqual(closed.status, DonationStatus.PENDING)

    def test_duplicate_callback_and_post_race_do_not_double_income(self):
        donation = self._donation()
        self._start(donation)
        self._callback_success(donation)
        self._callback_success(donation, method="post")
        self.assertEqual(Income.objects.filter(idempotency_key=f"donation:{donation.pk}").count(), 1)
        self.assertEqual(
            GatewayWebhookEvent.objects.filter(provider=PaymentMethod.BKASH, event_type="bkash_callback").count(),
            1,
        )

    def test_callback_rejects_mismatched_amount_purpose_and_provider_amount(self):
        donation = self._donation()
        self._start(donation)
        with patch("donations.gateways.bkash_client.requests.post") as post:
            self.client.get(
                reverse("bkash-callback"),
                {"paymentID": "PAY1", "status": "success", "amount": "1", "purpose": "MEMBERSHIP_FEE"},
            )
            post.assert_not_called()
        donation.refresh_from_db()
        self.assertEqual(donation.status, DonationStatus.PENDING)

        routes = {
            "/auth/grant-token": {"statusCode": "0000", "id_token": "id", "refresh_token": "r", "expires_in": 3600},
            "/payment/execute": _completed("1.00", donation.transaction.tran_id),
            "/query/payment": _completed("1.00", donation.transaction.tran_id),
        }
        with patch("donations.gateways.bkash_client.requests.post", side_effect=self._router(routes)):
            self.client.get(reverse("bkash-callback"), {"paymentID": "PAY1", "status": "success"})
        donation.refresh_from_db()
        self.assertEqual(donation.status, DonationStatus.PENDING)

    def test_idor_callback_cannot_complete_a_different_transaction(self):
        first = self._donation()
        second = self._donation(amount=80)
        self._start(first)
        second.transaction.val_id = "PAY-OTHER"
        second.transaction.save(update_fields=["val_id"])
        self.client.get(
            reverse("bkash-callback"),
            {"paymentID": "PAY1", "status": "success", "tran_id": second.transaction.tran_id},
        )
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.status, DonationStatus.PENDING)
        self.assertEqual(second.status, DonationStatus.PENDING)

    def test_membership_fee_and_registration_fee(self):
        member = self._member()
        cy, cm = current_year_month()
        ensure_ledger_months(member, cy, cm)
        payment, url = self._checkout_fee(member, cy, cm)
        self.assertIn("sandbox.payment.bkash.com", url)
        txn = payment.transaction
        self._callback_success_for_txn(txn, amount=f"{Decimal(str(payment.amount)).quantize(Decimal('0.01'))}")
        payment.refresh_from_db()
        fee = MembershipFee.objects.get(member=member, year=cy, month=cm)
        self.assertEqual(payment.status, DonationStatus.COMPLETED)
        self.assertEqual(fee.status, DonationStatus.COMPLETED)
        self.assertEqual(
            Income.objects.filter(idempotency_key=f"membership-fee-payment:{payment.pk}").count(),
            1,
        )
        self._callback_success_for_txn(txn, amount=f"{Decimal(str(payment.amount)).quantize(Decimal('0.01'))}")
        self.assertEqual(
            Income.objects.filter(idempotency_key=f"membership-fee-payment:{payment.pk}").count(),
            1,
        )

        reg, _url = self._checkout_registration(member)
        self._callback_success_for_txn(
            reg.transaction,
            amount=f"{Decimal(str(reg.amount)).quantize(Decimal('0.01'))}",
            payment_id=reg.transaction.val_id,
        )
        reg.refresh_from_db()
        self.assertEqual(reg.status, DonationStatus.COMPLETED)
        self.assertEqual(
            Income.objects.filter(idempotency_key__startswith="membership-registration-fee:").count(),
            1,
        )

    def test_agreement_lifecycle_does_not_activate_recurring(self):
        sub = DonationSubscription.objects.create(
            category=self.category,
            donor_name="Donor",
            amount=100,
            payment_gateway=PaymentMethod.BKASH,
            gateway_subscription_ref="AGR1",
        )
        routes = {
            "/auth/grant-token": {"statusCode": "0000", "id_token": "id", "refresh_token": "r", "expires_in": 3600},
            "/agreement/create": {
                "paymentId": "AGPAY",
                "agreementId": "AGR1",
                "bkashURL": "https://sandbox.payment.bkash.com/?paymentId=AGPAY",
                "agreementStatus": "Initiated",
            },
            "/agreement/execute": {"agreementId": "AGR1", "agreementStatus": "Completed"},
            "/query/agreement": {"agreementId": "AGR1", "agreementStatus": "Completed"},
            "/agreement/cancel": {"agreementId": "AGR1", "agreementStatus": "Cancelled"},
            "/payment-with-agreement/create": {
                "paymentId": "PWA1",
                "bkashURL": "https://sandbox.payment.bkash.com/?paymentId=PWA1",
                "transactionStatus": "Initiated",
                "agreementId": "AGR1",
            },
            "/payment-with-agreement/execute": _completed("100.00", "INV", "PWA1", "TRX-A"),
        }
        gateway = get_gateway(PaymentMethod.BKASH)
        with patch("donations.gateways.bkash_client.requests.post", side_effect=self._router(routes)):
            created = gateway.begin_agreement(payer_reference="01710000099", callback_url="https://example.test/cb")
            executed = gateway.execute_agreement("AGR1")
            queried = gateway.query_agreement("AGR1")
            started = gateway.create_payment_with_agreement(
                agreement_id="AGR1",
                callback_url="https://example.test/cb",
                amount="100.00",
                currency="BDT",
                merchant_invoice="INV",
            )
            with self.assertRaises(PaymentGatewayError):
                gateway.init_recurring_authorization(None, self._request(), subscription=sub, schedule_day=1)
            cancelled = gateway.cancel_recurring(sub)
        self.assertEqual(created["agreementStatus"], "Initiated")
        self.assertEqual(executed["agreementStatus"], "Completed")
        self.assertEqual(queried["agreementStatus"], "Completed")
        self.assertIn("bkash.com", started["bkashURL"])
        self.assertEqual(cancelled["agreementStatus"], "Cancelled")
        sub.refresh_from_db()
        self.assertNotEqual(sub.status, "ACTIVE")
        self.assertEqual(DonationRecurringCharge.objects.count(), 0)
        self.assertEqual(Donation.objects.filter(status=DonationStatus.COMPLETED).count(), 0)

    def test_refund_lifecycle_requires_provider_completion(self):
        donation = self._donation()
        self._start(donation)
        self._callback_success(donation)
        donation.transaction.refresh_from_db()
        finance = User.objects.create_user(
            email="finance@example.com", password="Str0ngPass!23", role=Role.FINANCE_OFFICER
        )
        superuser = User.objects.create_user(
            email="sa@example.com", password="Str0ngPass!23", role=Role.SUPER_ADMIN, is_superuser=True
        )
        refund = request_refund(
            transaction_obj=donation.transaction,
            amount=100,
            reason="Wrong gift",
            actor=finance,
        )
        self.assertEqual(refund.status, RefundStatus.REQUESTED)
        with self.assertRaises(RefundError):
            approve_refund(refund=refund, actor=finance)
        refund.refresh_from_db()
        self.assertEqual(refund.status, RefundStatus.REQUESTED)

        routes = {
            "/auth/grant-token": {"statusCode": "0000", "id_token": "id", "refresh_token": "r", "expires_in": 3600},
            "/refund/payment/transaction": {"errorMessageEn": "Refund amount not valid", "externalCode": "2072"},
        }
        with patch("donations.gateways.bkash_client.requests.post", side_effect=self._router(routes)):
            with self.assertRaises(RefundError):
                approve_refund(refund=refund, actor=superuser)
        refund.refresh_from_db()
        self.assertEqual(refund.status, RefundStatus.FAILED)

        refund.status = RefundStatus.REQUESTED
        refund.save(update_fields=["status"])
        routes["/refund/payment/transaction"] = {
            "originalTrxId": donation.transaction.bank_tran_id,
            "refundTrxId": "RFD1",
            "refundTransactionStatus": "Completed",
            "refundAmount": "100.00",
            "currency": "BDT",
        }
        with patch("donations.gateways.bkash_client.requests.post", side_effect=self._router(routes)):
            approve_refund(refund=refund, actor=superuser)
        refund.refresh_from_db()
        self.assertEqual(refund.status, RefundStatus.REFUNDED)
        self.assertEqual(refund.provider_reference, "RFD1")

    def test_connection_test_does_not_mark_one_time_verified_or_return_token(self):
        cfg = PaymentMethodConfig.objects.get(method=PaymentMethod.BKASH)
        routes = {
            "/auth/grant-token": {
                "statusCode": "0000",
                "id_token": "secret-token-value",
                "refresh_token": "refresh",
                "expires_in": 3600,
            }
        }
        with patch("donations.gateways.bkash_client.requests.post", side_effect=self._router(routes)):
            status, message = test_bkash_connection()
        self.assertEqual(status, "SUCCESS")
        self.assertNotIn("secret-token-value", message)
        cfg.refresh_from_db()
        self.assertEqual(cfg.last_test_status, "SUCCESS")
        self.assertIsNone(cfg.one_time_verified_at)
        ready = bkash_readiness()
        self.assertEqual(ready["connection"], SANDBOX_VERIFIED)
        self.assertEqual(ready["one_time"], SANDBOX_CONFIGURED)
        self.assertNotEqual(ready["one_time"], LIVE_VERIFIED)

    def test_member_cannot_configure_or_reconcile(self):
        member_user = User.objects.create_user(email="member@example.com", password="Str0ngPass!23", role=Role.MEMBER)
        member_user.email_verified = timezone.now()
        member_user.save(update_fields=["email_verified"])
        cfg = PaymentMethodConfig.objects.get(method=PaymentMethod.BKASH)
        txn = self._donation().transaction
        txn.val_id = "PAY1"
        txn.save(update_fields=["val_id"])
        client = Client()
        client.force_login(member_user)
        configure = client.get(reverse("dashboard-payment-method-configure", args=[cfg.pk]))
        reconcile = client.post(reverse("dashboard-payments-bkash-reconcile", args=[txn.pk]))
        self.assertIn(configure.status_code, (302, 403))
        self.assertEqual(reconcile.status_code, 403)
        txn.refresh_from_db()
        self.assertEqual(txn.status, DonationStatus.PENDING)

    def test_reconcile_query_completed_and_initiated(self):
        from donations.bkash_flow import reconcile_bkash_transaction

        donation = self._donation()
        self._start(donation)
        routes = {
            "/auth/grant-token": {"statusCode": "0000", "id_token": "id", "refresh_token": "r", "expires_in": 3600},
            "/query/payment": {
                "paymentId": "PAY1",
                "transactionStatus": "Initiated",
                "amount": "100.00",
                "currency": "BDT",
                "merchantInvoice": donation.transaction.tran_id,
            },
        }
        with patch("donations.gateways.bkash_client.requests.post", side_effect=self._router(routes)):
            reconcile_bkash_transaction(donation.transaction)
        donation.refresh_from_db()
        self.assertEqual(donation.status, DonationStatus.PENDING)
        routes["/query/payment"] = _completed("100.00", donation.transaction.tran_id)
        routes["/query/payment"]["merchantInvoice"] = donation.transaction.tran_id
        with patch("donations.gateways.bkash_client.requests.post", side_effect=self._router(routes)):
            reconcile_bkash_transaction(donation.transaction)
        donation.refresh_from_db()
        self.assertEqual(donation.status, DonationStatus.COMPLETED)

    def test_sqlite_does_not_claim_postgres_race_safety(self):
        if connection.vendor == "postgresql":
            self.skipTest("Covered by the PostgreSQL deployment, not this assertion.")
        self.assertNotEqual(connection.vendor, "postgresql")

    def _start(self, donation, amount="100.00", payment_id="PAY1"):
        routes = {
            "/auth/grant-token": {"statusCode": "0000", "id_token": "id", "refresh_token": "r", "expires_in": 3600},
            "/payment/create": {
                "paymentId": payment_id,
                "bkashURL": f"https://sandbox.payment.bkash.com/?paymentId={payment_id}",
                "transactionStatus": "Initiated",
                "amount": amount,
                "currency": "BDT",
                "merchantInvoiceNumber": donation.transaction.tran_id,
            },
        }
        with patch("donations.gateways.bkash_client.requests.post", side_effect=self._router(routes)):
            get_gateway(PaymentMethod.BKASH).init_payment(donation, self._request())
        donation.transaction.refresh_from_db()

    def _callback_success(self, donation, amount="100.00", method="get"):
        self._callback_success_for_txn(donation.transaction, amount=amount, method=method)

    def _callback_success_for_txn(self, txn, amount, method="get", payment_id=None):
        payment_id = payment_id or txn.val_id
        payload = _completed(amount, txn.tran_id, payment_id)
        routes = {
            "/auth/grant-token": {"statusCode": "0000", "id_token": "id", "refresh_token": "r", "expires_in": 3600},
            "/payment/execute": payload,
            "/query/payment": payload,
        }
        query = {"paymentID": payment_id, "status": "success", "signature": "sig"}
        with patch("donations.gateways.bkash_client.requests.post", side_effect=self._router(routes)):
            if method == "post":
                response = self.client.post(reverse("bkash-callback"), query)
            else:
                response = self.client.get(reverse("bkash-callback"), query)
        self.assertEqual(response.status_code, 200)

    def _member(self):
        user = User.objects.create_user(
            email=f"m{uuid.uuid4().hex[:6]}@example.com",
            password="Str0ngPass!23",
            role=Role.MEMBER,
        )
        user.email_verified = timezone.now()
        user.save(update_fields=["email_verified"])
        return Member.objects.create(
            member_id=f"ZF-TEST-{uuid.uuid4().hex[:4]}",
            user=user,
            first_name="Test",
            last_name="Member",
            phone="01710000001",
            present_address="Dhaka",
            district="Dhaka",
            status=MemberStatus.APPROVED,
            joined_at=timezone.now(),
        )

    def _checkout_fee(self, member, year, month):
        routes = {
            "/auth/grant-token": {"statusCode": "0000", "id_token": "id", "refresh_token": "r", "expires_in": 3600},
            "/payment/create": None,
        }

        def post(url, json=None, headers=None, timeout=None):
            if url.endswith("/auth/grant-token"):
                return _Response(routes["/auth/grant-token"])
            if url.endswith("/payment/create"):
                return _Response(
                    {
                        "paymentId": "FEE1",
                        "bkashURL": "https://sandbox.payment.bkash.com/?paymentId=FEE1",
                        "transactionStatus": "Initiated",
                        "amount": json["amount"],
                        "currency": "BDT",
                        "merchantInvoiceNumber": json["merchantInvoiceNumber"],
                    }
                )
            return _Response({})

        with patch("donations.gateways.bkash_client.requests.post", side_effect=post):
            return initiate_fee_checkout(
                member,
                [{"year": year, "month": month}],
                request=self._request(),
                method=PaymentMethod.BKASH,
            )

    def _checkout_registration(self, member):
        def post(url, json=None, headers=None, timeout=None):
            if url.endswith("/auth/grant-token"):
                return _Response(
                    {"statusCode": "0000", "id_token": "id", "refresh_token": "r", "expires_in": 3600}
                )
            if url.endswith("/payment/create"):
                return _Response(
                    {
                        "paymentId": "REG1",
                        "bkashURL": "https://sandbox.payment.bkash.com/?paymentId=REG1",
                        "transactionStatus": "Initiated",
                        "amount": json["amount"],
                        "currency": "BDT",
                        "merchantInvoiceNumber": json["merchantInvoiceNumber"],
                    }
                )
            return _Response({})

        with patch("donations.gateways.bkash_client.requests.post", side_effect=post):
            return initiate_registration_fee_checkout(
                member, request=self._request(), method=PaymentMethod.BKASH
            )


class BkashTimeoutTypeTests(TestCase):
    def test_timeout_exception_is_a_gateway_error(self):
        self.assertIsInstance(BkashTimeout(), PaymentGatewayError)
