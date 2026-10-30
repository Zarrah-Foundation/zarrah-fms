"""Webhook/IPN persistence hardening — one-time donation + shared event model."""

from __future__ import annotations

import uuid
from unittest.mock import patch

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from core.choices import DonationStatus, PaymentMethod
from donations.models import (
    Donation,
    DonationCategory,
    GatewayWebhookEvent,
    Transaction,
    WebhookProcessingStatus,
)
from donations.webhook_services import record_webhook_event
from finance.models import Income


def _category():
    return DonationCategory.objects.create(
        name_en="General",
        name_bn="সাধারণ",
        slug=f"g-{uuid.uuid4().hex[:8]}",
        is_active=True,
        is_default=True,
    )


def _pending_donation(*, amount=100.0):
    cat = _category()
    txn = Transaction.objects.create(
        session_id=str(uuid.uuid4()),
        tran_id=f"ZF{uuid.uuid4().hex[:12].upper()}",
        amount=amount,
        currency="BDT",
        status=DonationStatus.PENDING,
        gateway=PaymentMethod.SSLCOMMERZ,
        cus_name="Donor",
        cus_email="d@example.com",
    )
    donation = Donation.objects.create(
        donor_name="Donor",
        donor_email="d@example.com",
        amount=amount,
        currency="BDT",
        category=cat,
        payment_method=PaymentMethod.SSLCOMMERZ,
        status=DonationStatus.PENDING,
        transaction=txn,
    )
    return donation


@override_settings(
    SSLCOMMERZ_STORE_ID="store",
    SSLCOMMERZ_STORE_PASSWORD="pass",
    SSLCOMMERZ_IS_SANDBOX=True,
)
class DonationIPNWebhookPersistenceTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.donation = _pending_donation()
        self.payload = {
            "status": "VALID",
            "tran_id": self.donation.transaction.tran_id,
            "val_id": "VAL-HARDEN-1",
            "amount": "100.00",
            "currency": "BDT",
            "bank_tran_id": "BANK-H1",
        }

    def test_ipn_persists_webhook_and_completes_once(self):
        with patch(
            "donations.views.validate_transaction", return_value=self.payload
        ):
            r = self.client.post(reverse("donation-ipn"), self.payload)
        self.assertEqual(r.status_code, 200)
        self.donation.refresh_from_db()
        self.assertEqual(self.donation.status, DonationStatus.COMPLETED)
        self.assertEqual(GatewayWebhookEvent.objects.count(), 1)
        event = GatewayWebhookEvent.objects.get()
        self.assertEqual(event.event_type, "donation_ipn")
        self.assertEqual(event.processing_status, WebhookProcessingStatus.PROCESSED)
        self.assertEqual(Income.objects.count(), 1)

    def test_duplicate_ipn_no_second_income(self):
        with patch(
            "donations.views.validate_transaction", return_value=self.payload
        ):
            self.client.post(reverse("donation-ipn"), self.payload)
            self.client.post(reverse("donation-ipn"), self.payload)
        self.assertEqual(GatewayWebhookEvent.objects.count(), 1)
        self.assertEqual(Income.objects.count(), 1)
        self.assertEqual(
            Donation.objects.filter(status=DonationStatus.COMPLETED).count(), 1
        )

    def test_invalid_validation_marks_failed_event(self):
        with patch("donations.views.validate_transaction", return_value=None):
            r = self.client.post(reverse("donation-ipn"), self.payload)
        self.assertEqual(r.status_code, 400)
        event = GatewayWebhookEvent.objects.get()
        self.assertEqual(event.processing_status, WebhookProcessingStatus.FAILED)
        self.assertEqual(Income.objects.count(), 0)

    def test_browser_success_without_validation_does_not_complete(self):
        with patch("donations.views.validate_transaction", return_value=None):
            r = self.client.get(
                reverse("donation-success"),
                {
                    "val_id": self.payload["val_id"],
                    "tran_id": self.payload["tran_id"],
                },
            )
        self.assertEqual(r.status_code, 302)
        self.donation.refresh_from_db()
        self.assertNotEqual(self.donation.status, DonationStatus.COMPLETED)
        event = GatewayWebhookEvent.objects.get()
        self.assertEqual(event.processing_status, WebhookProcessingStatus.FAILED)

    def test_record_webhook_idempotent(self):
        e1, c1 = record_webhook_event(PaymentMethod.SSLCOMMERZ, self.payload)
        e2, c2 = record_webhook_event(PaymentMethod.SSLCOMMERZ, self.payload)
        self.assertTrue(c1)
        self.assertFalse(c2)
        self.assertEqual(e1.pk, e2.pk)
