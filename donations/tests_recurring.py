"""PAY-WP3 recurring donation tests."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from core.choices import DonationStatus, PaymentMethod
from donations.models import (
    Donation,
    DonationCategory,
    DonationRecurringCharge,
    DonationSubscription,
    GatewayWebhookEvent,
    RecurringChargeKind,
    RecurringChargeStatus,
    SubscriptionFrequency,
    SubscriptionStatus,
    Transaction,
    WebhookProcessingStatus,
)
from donations.recurring_services import (
    RecurringDonationError,
    cancel_subscription,
    claim_subscription_for_reconciliation,
    complete_authorization_from_gateway,
    create_recurring_subscription,
    get_subscription_by_management_token,
    record_webhook_event,
    settle_recurring_ipn,
)
from finance.models import Income

User = get_user_model()


def _make_user(email, password="pass12345", **kwargs):
    from django.utils import timezone

    kwargs.setdefault("email_verified", timezone.now())
    return User.objects.create_user(email=email, password=password, **kwargs)


def _category(**kwargs):
    defaults = {
        "name_en": "General",
        "name_bn": "সাধারণ",
        "slug": kwargs.pop("slug", "general-wp3"),
        "is_active": True,
        "is_default": True,
    }
    defaults.update(kwargs)
    return DonationCategory.objects.create(**defaults)


RECURRING_ENV = dict(
    SSLCOMMERZ_STORE_ID="store",
    SSLCOMMERZ_STORE_PASSWORD="pass",
    SSLCOMMERZ_IS_SANDBOX=True,
    SSLCOMMERZ_SALT_KEY="0123456789abcdef",
    SSLCOMMERZ_RECURRING_PLAN_REFER="plan-refer-test",
    RECURRING_DONATION_FAILURE_THRESHOLD=3,
)


@override_settings(**RECURRING_ENV)
class RecurringSubscriptionCreateTests(TestCase):
    def setUp(self):
        self.cat = _category()

    def test_create_subscription_guest(self):
        sub = create_recurring_subscription(
            amount=500,
            category=self.cat,
            donor_name="Guest Donor",
            donor_email="guest@example.com",
        )
        self.assertEqual(sub.status, SubscriptionStatus.DRAFT)
        self.assertEqual(sub.frequency, SubscriptionFrequency.MONTHLY)
        self.assertEqual(sub.currency, "BDT")
        self.assertTrue(sub.management_token)
        self.assertIsNone(sub.user)

    def test_create_subscription_authenticated(self):
        user = _make_user("d1@example.com")
        sub = create_recurring_subscription(
            amount=200,
            category=self.cat,
            donor_name="Auth Donor",
            donor_email="d1@example.com",
            user=user,
        )
        self.assertEqual(sub.user_id, user.pk)

    def test_monthly_frequency_enforced(self):
        with self.assertRaises(RecurringDonationError):
            create_recurring_subscription(
                amount=100,
                category=self.cat,
                donor_name="A",
                donor_email="a@example.com",
                frequency=SubscriptionFrequency.DAILY,
            )

    def test_amount_tampering_rejected(self):
        with self.assertRaises(RecurringDonationError):
            create_recurring_subscription(
                amount=0,
                category=self.cat,
                donor_name="A",
                donor_email="a@example.com",
            )

    def test_unsupported_provider(self):
        with self.assertRaises(RecurringDonationError):
            create_recurring_subscription(
                amount=100,
                category=self.cat,
                donor_name="A",
                donor_email="a@example.com",
                gateway=PaymentMethod.BKASH,
            )


@override_settings(
    SSLCOMMERZ_STORE_ID="store",
    SSLCOMMERZ_STORE_PASSWORD="pass",
    SSLCOMMERZ_IS_SANDBOX=True,
    SSLCOMMERZ_SALT_KEY="",
    SSLCOMMERZ_RECURRING_PLAN_REFER="",
)
class RecurringNotConfiguredTests(TestCase):
    def setUp(self):
        self.cat = _category(slug="general-nc")

    def test_create_blocked_when_not_configured(self):
        with self.assertRaises(RecurringDonationError) as ctx:
            create_recurring_subscription(
                amount=100,
                category=self.cat,
                donor_name="A",
                donor_email="a@example.com",
            )
        self.assertEqual(ctx.exception.code, "not_configured")

    def test_public_page_shows_not_configured(self):
        r = self.client.get(reverse("donation-recurring"))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.context["recurring_configured"])


@override_settings(**RECURRING_ENV)
class RecurringFormTamperTests(TestCase):
    def setUp(self):
        self.cat = _category(slug="general-form")

    def test_frequency_provider_purpose_currency_tamper(self):
        resp = self.client.post(
            reverse("donation-recurring"),
            {
                "category": str(self.cat.pk),
                "amount": "100",
                "donor_name": "Tamper",
                "contact": "tamper@example.com",
                "frequency": "YEARLY",
                "payment_provider": "BKASH",
                "currency": "USD",
                "purpose": "MEMBERSHIP_FEE",
            },
        )
        # Form rejects non-monthly / non-SSLCommerz
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(DonationSubscription.objects.exists())


@override_settings(**RECURRING_ENV)
class RecurringAuthorizationTests(TestCase):
    def setUp(self):
        self.cat = _category(slug="general-auth")
        self.sub = create_recurring_subscription(
            amount=250,
            category=self.cat,
            donor_name="Auth",
            donor_email="auth@example.com",
        )

    def _pending_auth_charge(self):
        from donations.services import generate_tran_id
        import uuid

        txn = Transaction.objects.create(
            session_id=str(uuid.uuid4()),
            tran_id=generate_tran_id(),
            amount=250,
            currency="BDT",
            status=DonationStatus.PENDING,
            gateway=PaymentMethod.SSLCOMMERZ,
            cus_name="Auth",
            cus_email="auth@example.com",
        )
        charge = DonationRecurringCharge.objects.create(
            subscription=self.sub,
            kind=RecurringChargeKind.AUTHORIZATION,
            amount=250,
            currency="BDT",
            status=RecurringChargeStatus.PENDING,
            idempotency_key=f"auth:{self.sub.pk}:{txn.tran_id}",
            transaction=txn,
        )
        self.sub.status = SubscriptionStatus.PENDING_AUTHORIZATION
        self.sub.save(update_fields=["status"])
        return charge

    def test_invalid_authorization(self):
        charge = self._pending_auth_charge()
        with self.assertRaises(RecurringDonationError):
            complete_authorization_from_gateway(
                tran_id=charge.transaction.tran_id,
                val_id="bad",
                validation_data={"status": "FAILED", "tran_id": charge.transaction.tran_id},
            )
        self.sub.refresh_from_db()
        self.assertNotEqual(self.sub.status, SubscriptionStatus.ACTIVE)

    def test_successful_authorization(self):
        charge = self._pending_auth_charge()
        data = {
            "status": "VALID",
            "tran_id": charge.transaction.tran_id,
            "amount": "250.00",
            "currency": "BDT",
            "val_id": "VAL1",
            "bank_tran_id": "BANK1",
            "subscription_id": "gw-sub-1",
        }
        complete_authorization_from_gateway(
            tran_id=charge.transaction.tran_id,
            val_id="VAL1",
            validation_data=data,
        )
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, SubscriptionStatus.ACTIVE)
        self.assertEqual(self.sub.gateway_subscription_ref, "gw-sub-1")
        self.assertEqual(Donation.objects.filter(subscription=self.sub).count(), 1)
        self.assertEqual(Income.objects.count(), 1)

    def test_browser_success_without_gateway_validation(self):
        charge = self._pending_auth_charge()
        # Hitting success URL without mocked validate_transaction must not activate.
        with patch("donations.recurring_views.validate_transaction", return_value=None):
            r = self.client.get(
                reverse("donation-recurring-success"),
                {"val_id": "X", "tran_id": charge.transaction.tran_id},
            )
        self.assertEqual(r.status_code, 302)
        self.sub.refresh_from_db()
        self.assertNotEqual(self.sub.status, SubscriptionStatus.ACTIVE)

    def test_duplicate_authorization_callback(self):
        charge = self._pending_auth_charge()
        data = {
            "status": "VALID",
            "tran_id": charge.transaction.tran_id,
            "amount": "250.00",
            "currency": "BDT",
            "val_id": "VAL1",
            "bank_tran_id": "BANK1",
            "subscription_id": "gw-sub-1",
        }
        complete_authorization_from_gateway(
            tran_id=charge.transaction.tran_id,
            val_id="VAL1",
            validation_data=data,
        )
        complete_authorization_from_gateway(
            tran_id=charge.transaction.tran_id,
            val_id="VAL1",
            validation_data=data,
        )
        self.assertEqual(Donation.objects.filter(subscription=self.sub).count(), 1)
        self.assertEqual(Income.objects.count(), 1)


@override_settings(**RECURRING_ENV)
class RecurringSettleIPNTests(TestCase):
    def setUp(self):
        self.cat = _category(slug="general-ipn")
        self.sub = create_recurring_subscription(
            amount=100,
            category=self.cat,
            donor_name="IPN",
            donor_email="ipn@example.com",
        )
        self.sub.status = SubscriptionStatus.ACTIVE
        self.sub.gateway_subscription_ref = "gw-active"
        self.sub.save()

    def _event(self, payload):
        event, _ = record_webhook_event(PaymentMethod.SSLCOMMERZ, payload)
        return event

    def test_successful_recurring_charge(self):
        payload = {
            "status": "VALID",
            "tran_id": "RTRAN1",
            "val_id": "RVAL1",
            "amount": "100.00",
            "currency": "BDT",
            "bank_tran_id": "RBANK1",
            "value_a": str(self.sub.pk),
            "subscription_id": "gw-active",
        }
        event = self._event(payload)
        settle_recurring_ipn(validation_data=payload, event=event)
        self.assertEqual(
            DonationRecurringCharge.objects.filter(
                subscription=self.sub, kind=RecurringChargeKind.RECURRING
            ).count(),
            1,
        )
        self.assertEqual(Donation.objects.filter(subscription=self.sub).count(), 1)
        self.assertEqual(Income.objects.count(), 1)

    def test_duplicate_recurring_ipn(self):
        payload = {
            "status": "VALID",
            "tran_id": "RTRAN2",
            "val_id": "RVAL2",
            "amount": "100.00",
            "currency": "BDT",
            "bank_tran_id": "RBANK2",
            "value_a": str(self.sub.pk),
        }
        event1 = self._event(payload)
        settle_recurring_ipn(validation_data=payload, event=event1)
        event2, created = record_webhook_event(PaymentMethod.SSLCOMMERZ, payload)
        self.assertFalse(created)
        # Replay settlement on already-processed event
        event2.processing_status = WebhookProcessingStatus.RECEIVED
        event2.save(update_fields=["processing_status"])
        settle_recurring_ipn(validation_data=payload, event=event2)
        self.assertEqual(
            DonationRecurringCharge.objects.filter(
                subscription=self.sub, kind=RecurringChargeKind.RECURRING
            ).count(),
            1,
        )
        self.assertEqual(Donation.objects.filter(subscription=self.sub).count(), 1)
        self.assertEqual(Income.objects.count(), 1)

    def test_forged_ipn_no_matching_subscription(self):
        payload = {
            "status": "VALID",
            "tran_id": "FORGE1",
            "val_id": "FORGEV",
            "amount": "100.00",
            "currency": "BDT",
            "value_a": "00000000-0000-0000-0000-000000000000",
        }
        event = self._event(payload)
        settle_recurring_ipn(validation_data=payload, event=event)
        self.assertEqual(Donation.objects.count(), 0)
        self.assertEqual(Income.objects.count(), 0)
        event.refresh_from_db()
        self.assertEqual(event.processing_status, WebhookProcessingStatus.IGNORED)

    def test_amount_mismatch(self):
        payload = {
            "status": "VALID",
            "tran_id": "AM1",
            "val_id": "AMV",
            "amount": "999.00",
            "currency": "BDT",
            "value_a": str(self.sub.pk),
        }
        event = self._event(payload)
        result = settle_recurring_ipn(validation_data=payload, event=event)
        self.assertIsNone(result)
        self.assertEqual(Income.objects.count(), 0)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, SubscriptionStatus.PAYMENT_FAILED)

    def test_currency_mismatch(self):
        payload = {
            "status": "VALID",
            "tran_id": "CM1",
            "val_id": "CMV",
            "amount": "100.00",
            "currency": "USD",
            "value_a": str(self.sub.pk),
        }
        event = self._event(payload)
        result = settle_recurring_ipn(validation_data=payload, event=event)
        self.assertIsNone(result)
        self.assertEqual(Income.objects.count(), 0)

    def test_failed_charge_suspends_after_threshold(self):
        from donations.recurring_services import _record_failure

        _record_failure(self.sub, reason="fail1")
        _record_failure(self.sub, reason="fail2")
        _record_failure(self.sub, reason="fail3")
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, SubscriptionStatus.SUSPENDED)
        self.assertEqual(self.sub.consecutive_failures, 3)


@override_settings(**RECURRING_ENV)
class RecurringCancelAndGuestTests(TestCase):
    def setUp(self):
        self.cat = _category(slug="general-cancel")
        self.sub = create_recurring_subscription(
            amount=150,
            category=self.cat,
            donor_name="Cancel Me",
            donor_email="c@example.com",
        )
        self.sub.status = SubscriptionStatus.ACTIVE
        self.sub.save()
        self.user = _make_user("owner@example.com")
        self.other = _make_user("other@example.com")
        self.sub.user = self.user
        self.sub.save(update_fields=["user"])

    def test_cancellation_idempotent(self):
        cancel_subscription(self.sub, actor=self.user, reason="test")
        cancel_subscription(self.sub, actor=self.user, reason="again")
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, SubscriptionStatus.CANCELLED)

    def test_guest_token_security(self):
        self.assertIsNone(get_subscription_by_management_token("not-a-real-token"))
        found = get_subscription_by_management_token(self.sub.management_token)
        self.assertEqual(found.pk, self.sub.pk)

    def test_guest_idor(self):
        other_sub = create_recurring_subscription(
            amount=10,
            category=self.cat,
            donor_name="Other Guest Donor",
            donor_email="o2@example.com",
        )
        r = self.client.get(
            reverse("donation-recurring-manage", args=[other_sub.management_token])
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["subscription"].pk, other_sub.pk)
        self.assertContains(r, "৳10")
        # Wrong token must not reveal this subscription
        r2 = self.client.get(reverse("donation-recurring-manage", args=["wrongtoken"]))
        self.assertEqual(r2.status_code, 302)

    def test_member_idor(self):
        self.client.force_login(self.other)
        r = self.client.get(
            reverse("dashboard-my-recurring-detail", args=[self.sub.pk])
        )
        self.assertEqual(r.status_code, 404)

    def test_owner_can_view(self):
        self.client.force_login(self.user)
        r = self.client.get(
            reverse("dashboard-my-recurring-detail", args=[self.sub.pk])
        )
        self.assertEqual(r.status_code, 200)


@override_settings(**RECURRING_ENV)
class RecurringAdminRbacTests(TestCase):
    def setUp(self):
        self.cat = _category(slug="general-rbac")
        self.sub = create_recurring_subscription(
            amount=50,
            category=self.cat,
            donor_name="RBAC",
            donor_email="r@example.com",
        )
        self.member = _make_user("m@example.com")

    def test_member_cannot_admin_list(self):
        self.client.force_login(self.member)
        r = self.client.get(reverse("dashboard-recurring"))
        self.assertIn(r.status_code, (302, 403))


@override_settings(**RECURRING_ENV)
class RecurringWebhookReplayTests(TestCase):
    def test_webhook_event_idempotent(self):
        payload = {"val_id": "W1", "tran_id": "T1", "amount": "10"}
        e1, c1 = record_webhook_event(PaymentMethod.SSLCOMMERZ, payload)
        e2, c2 = record_webhook_event(PaymentMethod.SSLCOMMERZ, payload)
        self.assertTrue(c1)
        self.assertFalse(c2)
        self.assertEqual(e1.pk, e2.pk)
        self.assertEqual(GatewayWebhookEvent.objects.count(), 1)


@override_settings(**RECURRING_ENV)
class RecurringConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.cat = _category(slug="general-conc")
        self.sub = create_recurring_subscription(
            amount=300,
            category=self.cat,
            donor_name="Conc",
            donor_email="conc@example.com",
        )
        self.sub.status = SubscriptionStatus.ACTIVE
        self.sub.save()

    def test_concurrent_workers_one_charge(self):
        payload = {
            "status": "VALID",
            "tran_id": "CONCTRAN",
            "val_id": "CONCVAL",
            "amount": "300.00",
            "currency": "BDT",
            "bank_tran_id": "CONCBANK",
            "value_a": str(self.sub.pk),
        }
        barrier = threading.Barrier(2)
        errors = []

        def worker(tag):
            try:
                connection.close()
                barrier.wait(timeout=5)
                # Distinct webhook rows (different bank_tran_id suffix) but same charge identity
                local = {
                    **payload,
                    "bank_tran_id": f"CONCBANK-{tag}",
                    # Keep val_id identical so settlement idempotency key matches
                }
                # Force distinct external event ids via unique val_id while same settlement key
                local["val_id"] = f"CONCVAL-{tag}"
                event, _ = record_webhook_event(PaymentMethod.SSLCOMMERZ, local)
                # Settlement uses shared provider_ref from bank_tran_id in settle — align refs
                settle_payload = {
                    **payload,
                    "val_id": "CONCVAL-SHARED",
                    "bank_tran_id": "CONCBANK-SHARED",
                }
                settle_recurring_ipn(validation_data=settle_payload, event=event)
            except Exception as exc:
                errors.append(exc)

        with ThreadPoolExecutor(max_workers=2) as pool:
            f1 = pool.submit(worker, "a")
            f2 = pool.submit(worker, "b")
            f1.result(timeout=30)
            f2.result(timeout=30)

        charges = DonationRecurringCharge.objects.filter(
            subscription=self.sub,
            kind=RecurringChargeKind.RECURRING,
            status=RecurringChargeStatus.COMPLETED,
        )
        self.assertEqual(charges.count(), 1, errors)
        self.assertEqual(Donation.objects.filter(subscription=self.sub).count(), 1)
        self.assertEqual(
            Transaction.objects.filter(status=DonationStatus.COMPLETED).count(), 1
        )
        self.assertEqual(Income.objects.count(), 1)

    def test_claim_lock_exclusive(self):
        ok_a = claim_subscription_for_reconciliation(self.sub, lock_token="aaa")
        ok_b = claim_subscription_for_reconciliation(self.sub, lock_token="bbb")
        self.assertTrue(ok_a)
        self.assertFalse(ok_b)


@override_settings(**RECURRING_ENV)
class RecurringCapabilityMatrixTests(TestCase):
    def test_ssl_configured_supports_recurring(self):
        from donations.gateway_capabilities import (
            method_capabilities,
            sslcommerz_supports_recurring,
        )

        self.assertTrue(sslcommerz_supports_recurring())
        caps = method_capabilities(PaymentMethod.SSLCOMMERZ)
        self.assertTrue(caps["supports_recurring"])
        for method in (PaymentMethod.BKASH, PaymentMethod.NAGAD):
            self.assertFalse(method_capabilities(method)["supports_recurring"])


@override_settings(
    SSLCOMMERZ_STORE_ID="store",
    SSLCOMMERZ_STORE_PASSWORD="pass",
    SSLCOMMERZ_IS_SANDBOX=True,
)
class OneTimeDonationRegressionSmoke(TestCase):
    def setUp(self):
        self.cat = _category(slug="onetime-reg")

    def test_one_time_donation_page_ok(self):
        r = self.client.get(reverse("donation"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "donation-form")
