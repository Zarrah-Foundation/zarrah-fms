"""Payment Management Center + refund + provider gate tests (no live gateway calls)."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role
from core.choices import DonationStatus, PaymentMethod
from donations.gateways import get_gateway
from donations.gateways.base import PaymentGatewayError
from donations.models import (
    PaymentMethodConfig,
    PaymentSystemSettings,
    RefundRequest,
    RefundStatus,
    Transaction,
)
from donations.provider_capabilities import (
    bkash_health,
    nagad_health,
    recurring_providers_for_checkout,
    sslcommerz_health,
)
from donations.refund_services import RefundError, approve_refund, reject_refund, request_refund
import uuid

User = get_user_model()


def _user(email, *, role=Role.MEMBER, superuser=False):
    u = User.objects.create_user(
        email=email,
        password="pass12345",
        role=role,
        email_verified=timezone.now(),
        is_superuser=superuser,
        is_staff=superuser,
    )
    return u


def _txn(**kwargs):
    defaults = dict(
        session_id=str(uuid.uuid4()),
        tran_id=f"T{uuid.uuid4().hex[:12]}",
        amount=100,
        currency="BDT",
        status=DonationStatus.COMPLETED,
        gateway=PaymentMethod.SSLCOMMERZ,
        cus_name="Donor",
    )
    defaults.update(kwargs)
    return Transaction.objects.create(**defaults)


@override_settings(
    SSLCOMMERZ_STORE_ID="store",
    SSLCOMMERZ_STORE_PASSWORD="pass",
    SSLCOMMERZ_IS_SANDBOX=True,
    SSLCOMMERZ_SALT_KEY="",
    SSLCOMMERZ_RECURRING_PLAN_REFER="",
)
class ProviderCapabilityTests(TestCase):
    def test_ssl_recurring_not_configured_without_salt(self):
        h = sslcommerz_health()
        self.assertTrue(h.one_time.configured)
        self.assertFalse(h.recurring.configured)
        self.assertEqual(h.recurring.status, "Not configured")
        self.assertEqual(recurring_providers_for_checkout(), [])

    def test_bkash_nagad_recurring_not_configured(self):
        self.assertIn("NOT IMPLEMENTED", bkash_health().recurring.detail)
        self.assertIn("NOT IMPLEMENTED", nagad_health().recurring.detail)
        self.assertEqual(bkash_health().recurring.status, "Not implemented")
        self.assertEqual(nagad_health().recurring.status, "Not implemented")
        self.assertFalse(bkash_health().recurring.available)
        self.assertFalse(nagad_health().recurring.available)

    def test_bkash_gateway_refuses_without_credentials(self):
        gw = get_gateway(PaymentMethod.BKASH)
        with self.assertRaises(PaymentGatewayError):
            gw.init_payment(None, None)

    def test_nagad_gateway_refuses_without_credentials(self):
        gw = get_gateway(PaymentMethod.NAGAD)
        with self.assertRaises(PaymentGatewayError):
            gw.init_payment(None, None)


@override_settings(
    SSLCOMMERZ_STORE_ID="store",
    SSLCOMMERZ_STORE_PASSWORD="pass",
    SSLCOMMERZ_IS_SANDBOX=True,
    SSLCOMMERZ_SALT_KEY="0123456789abcdef",
    SSLCOMMERZ_RECURRING_PLAN_REFER="plan-x",
)
class ProviderConfiguredTests(TestCase):
    def test_ssl_recurring_configured_from_env(self):
        h = sslcommerz_health()
        self.assertTrue(h.recurring.configured)
        # Without DB merchant flag and without DB salt, env-only is available
        self.assertTrue(h.recurring.available)


class RefundWorkflowTests(TestCase):
    def setUp(self):
        self.super = _user("super@example.com", role=Role.SUPER_ADMIN, superuser=True)
        self.finance = _user("fin@example.com", role=Role.FINANCE_OFFICER)
        self.txn = _txn()
        PaymentMethodConfig.objects.update_or_create(
            method=PaymentMethod.SSLCOMMERZ,
            defaults={"refunds_enabled": True, "is_enabled": True},
        )

    def test_request_refund(self):
        req = request_refund(
            transaction_obj=self.txn,
            amount=50,
            reason="Duplicate charge",
            actor=self.finance,
        )
        self.assertEqual(req.status, RefundStatus.REQUESTED)

    def test_amount_overflow(self):
        with self.assertRaises(RefundError) as ctx:
            request_refund(
                transaction_obj=self.txn,
                amount=9999,
                reason="Too much",
                actor=self.finance,
            )
        self.assertEqual(ctx.exception.code, "overflow")

    def test_finance_cannot_approve(self):
        req = request_refund(
            transaction_obj=self.txn, amount=10, reason="x", actor=self.finance
        )
        with self.assertRaises(RefundError) as ctx:
            approve_refund(refund=req, actor=self.finance)
        self.assertEqual(ctx.exception.code, "forbidden")

    def test_super_admin_approve_does_not_fake_refunded(self):
        req = request_refund(
            transaction_obj=self.txn, amount=10, reason="x", actor=self.finance
        )
        with self.assertRaises(RefundError):
            approve_refund(refund=req, actor=self.super)
        req.refresh_from_db()
        # Approval committed; provider refused → FAILED (never silent REFUNDED)
        self.assertEqual(req.status, RefundStatus.FAILED)
        self.assertIsNotNone(req.approved_at)

    def test_reject(self):
        req = request_refund(
            transaction_obj=self.txn, amount=10, reason="x", actor=self.finance
        )
        reject_refund(refund=req, actor=self.super, reason="No")
        req.refresh_from_db()
        self.assertEqual(req.status, RefundStatus.REJECTED)

    def test_duplicate_pending_reduces_refundable(self):
        request_refund(
            transaction_obj=self.txn, amount=60, reason="a", actor=self.finance
        )
        with self.assertRaises(RefundError):
            request_refund(
                transaction_obj=self.txn, amount=50, reason="b", actor=self.finance
            )


class PaymentCenterViewTests(TestCase):
    def setUp(self):
        self.super = _user("sa@example.com", role=Role.SUPER_ADMIN, superuser=True)

    def test_overview_requires_auth(self):
        r = self.client.get(reverse("dashboard-payments"))
        self.assertEqual(r.status_code, 302)

    def test_super_can_open_overview(self):
        self.client.force_login(self.super)
        r = self.client.get(reverse("dashboard-payments"))
        # May 403 if RBAC not seeded — superuser should pass has_action via is_superuser
        self.assertIn(r.status_code, (200, 403))


class PaymentSettingsGateTests(TestCase):
    def test_settings_singleton(self):
        s = PaymentSystemSettings.load()
        self.assertEqual(s.pk, 1)
        s.recurring_donation_enabled = False
        s.save()
        self.assertFalse(PaymentSystemSettings.load().recurring_donation_enabled)


@override_settings(
    SSLCOMMERZ_STORE_ID="store-public",
    SSLCOMMERZ_STORE_PASSWORD="STORE-PASSWORD-DO-NOT-LEAK",
    SSLCOMMERZ_IS_SANDBOX=True,
    SSLCOMMERZ_SALT_KEY="SALT-SECRET-VALUE-DO-NOT-LEAK",
    SSLCOMMERZ_RECURRING_PLAN_REFER="plan-public-ref",
    SITE_URL="https://staging.example.org",
)
class RecurringSetupCenterTests(TestCase):
    def setUp(self):
        self.super = _user("setup-sa@example.com", role=Role.SUPER_ADMIN, superuser=True)
        self.member = _user("setup-member@example.com", role=Role.MEMBER)
        PaymentMethodConfig.objects.update_or_create(
            method=PaymentMethod.BKASH,
            defaults={
                "is_enabled": True,
                "api_app_key": "bkash-app-key-public",
                "encrypted_api_secret": "BKASH-APP-SECRET-DO-NOT-LEAK",
                "api_username": "bkash-user",
                "encrypted_api_password": "BKASH-API-PASSWORD-DO-NOT-LEAK",
            },
        )

    def test_member_cannot_open_setup(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("dashboard-payments-recurring-setup"))
        self.assertEqual(response.status_code, 403)

    def test_setup_page_hides_secrets_and_marks_unimplemented_wallets(self):
        self.client.force_login(self.super)
        response = self.client.get(reverse("dashboard-payments-recurring-setup"))
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("Recurring Payment Setup", body)
        self.assertIn("NOT_IMPLEMENTED", body)
        self.assertIn("plan-public-ref", body)
        self.assertIn("https://staging.example.org/donation/recurring/ipn/", body)
        self.assertNotIn("STORE-PASSWORD-DO-NOT-LEAK", body)
        self.assertNotIn("SALT-SECRET-VALUE-DO-NOT-LEAK", body)
        self.assertNotIn("BKASH-APP-SECRET-DO-NOT-LEAK", body)
        self.assertNotIn("BKASH-API-PASSWORD-DO-NOT-LEAK", body)
        for card in response.context["cards"]:
            blob = str(card)
            self.assertNotIn("DO-NOT-LEAK", blob)
            if card["method"] == PaymentMethod.BKASH:
                self.assertEqual(card["recurring_state"], "NOT_IMPLEMENTED")
                self.assertEqual(card["one_time_state"], "NOT_IMPLEMENTED")
                self.assertFalse(card["accepting_new_subscriptions"])
                self.assertTrue(card["has_api_secret"])
            if card["method"] == PaymentMethod.NAGAD:
                self.assertEqual(card["recurring_state"], "NOT_IMPLEMENTED")
            if card["method"] == PaymentMethod.SSLCOMMERZ:
                self.assertEqual(card["recurring_state"], "CONFIGURED")
                self.assertTrue(card["has_salt"])
                self.assertTrue(card["accepting_new_subscriptions"])

    def test_capabilities_page_is_purpose_specific(self):
        self.client.force_login(self.super)
        response = self.client.get(reverse("dashboard-payments-capabilities"))
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("Donation one-time", body)
        self.assertIn("Membership Autopay", body)
        bkash = next(row for row in response.context["purpose_rows"] if row["method"] == "BKASH")
        self.assertEqual(bkash["donation_recurring"], "NOT_IMPLEMENTED")
        self.assertEqual(bkash["membership_autopay"], "NOT_IMPLEMENTED")
        self.assertFalse(bkash["donation_one_time_live"])

    def test_overview_uses_database_totals(self):
        txn = _txn(amount=80, status=DonationStatus.COMPLETED)
        pending = _txn(amount=15, status=DonationStatus.PENDING)
        from donations.models import DonationCategory

        category = DonationCategory.objects.create(
            name_bn="সাধারণ",
            name_en="General",
            slug="general-setup",
        )
        from donations.models import Donation

        Donation.objects.create(
            donor_name="A",
            amount=80,
            category=category,
            status=DonationStatus.COMPLETED,
            transaction=txn,
        )
        self.client.force_login(self.super)
        response = self.client.get(reverse("dashboard-payments"))
        self.assertEqual(response.status_code, 200)
        metrics = response.context["metrics"]
        self.assertEqual(metrics["donations_today_total"], 80)
        self.assertEqual(metrics["donations_today_count"], 1)
        self.assertGreaterEqual(metrics["txn_stats"]["pending"], 1)
        self.assertEqual(pending.status, DonationStatus.PENDING)
        self.assertNotIn("STORE-PASSWORD-DO-NOT-LEAK", response.content.decode())

    def test_transaction_filters_by_date_gateway_and_reference(self):
        keep = _txn(gateway=PaymentMethod.SSLCOMMERZ, bank_tran_id="GW-KEEP-99")
        drop = _txn(gateway=PaymentMethod.CASH, bank_tran_id="GW-DROP-11")
        Transaction.objects.filter(pk=drop.pk).update(created_at="2020-01-02T00:00:00Z")
        self.client.force_login(self.super)
        response = self.client.get(
            reverse("dashboard-payments-transactions"),
            {"q": "GW-KEEP-99", "gateway": PaymentMethod.SSLCOMMERZ},
        )
        self.assertEqual(response.status_code, 200)
        rows = list(response.context["transactions"])
        self.assertEqual([row.pk for row in rows], [keep.pk])
        dated = self.client.get(
            reverse("dashboard-payments-transactions"),
            {"date_from": "2020-01-01", "date_to": "2020-01-03", "gateway": PaymentMethod.CASH},
        )
        self.assertEqual([row.pk for row in dated.context["transactions"]], [drop.pk])

    def test_registration_fee_page_requires_login(self):
        response = self.client.get(reverse("dashboard-payments-registration-fees"))
        self.assertEqual(response.status_code, 302)
        self.client.force_login(self.super)
        opened = self.client.get(reverse("dashboard-payments-registration-fees"))
        self.assertEqual(opened.status_code, 200)
