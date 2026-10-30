"""Public recurring-donation visibility: CMS switch AND provider capability."""

from __future__ import annotations

from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.choices import PaymentMethod
from donations.gateway_capabilities import (
    CMS_RECURRING_DISABLED_MSG,
    cms_new_recurring_enabled,
    public_recurring_option_visible,
    recurring_checkout_allowed,
)
from donations.models import DonationSubscription, PaymentSystemSettings, SubscriptionStatus
from donations.recurring_services import RecurringDonationError, create_recurring_subscription
from donations.tests_recurring import RECURRING_ENV, _category


def _force_en(client):
    from django.conf import settings as dj_settings

    client.post(reverse("set_language"), {"language": "en", "next": "/"})
    client.cookies[dj_settings.LANGUAGE_COOKIE_NAME] = "en"


@override_settings(
    SSLCOMMERZ_STORE_ID="store",
    SSLCOMMERZ_STORE_PASSWORD="pass",
    SSLCOMMERZ_IS_SANDBOX=True,
    SSLCOMMERZ_SALT_KEY="",
    SSLCOMMERZ_RECURRING_PLAN_REFER="",
)
class RecurringHiddenWithoutProviderTests(TestCase):
    def setUp(self):
        self.cat = _category(slug="vis-noprov")
        s = PaymentSystemSettings.load()
        s.recurring_donation_enabled = True
        s.save()

    def test_cms_on_provider_unavailable_hides_public_option(self):
        _force_en(self.client)
        self.assertTrue(cms_new_recurring_enabled())
        self.assertFalse(public_recurring_option_visible())
        r = self.client.get(reverse("donation"))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.context["show_recurring_option"])
        self.assertContains(r, "donation-form")
        self.assertContains(r, "One-time Donation")
        self.assertNotContains(r, 'href="/donation/recurring/"')
        self.assertNotContains(r, "Recurring Donation")


@override_settings(**RECURRING_ENV)
class RecurringCmsVisibilityTests(TestCase):
    def setUp(self):
        self.cat = _category(slug="vis-cms")
        self.settings = PaymentSystemSettings.load()
        self.settings.recurring_donation_enabled = True
        self.settings.save()

    def test_recurring_visible_when_cms_on_and_provider_ready(self):
        _force_en(self.client)
        ok, _err = recurring_checkout_allowed(PaymentMethod.SSLCOMMERZ)
        self.assertTrue(ok)
        r = self.client.get(reverse("donation"))
        self.assertTrue(r.context["show_recurring_option"])
        self.assertContains(r, "One-time Donation")
        self.assertContains(r, "Recurring Donation")
        self.assertContains(r, "donation-form")
        self.assertContains(r, 'href="/donation/recurring/"')

    def test_recurring_hidden_when_cms_disabled(self):
        _force_en(self.client)
        self.settings.recurring_donation_enabled = False
        self.settings.save()
        self.assertFalse(cms_new_recurring_enabled())
        r = self.client.get(reverse("donation"))
        self.assertFalse(r.context["show_recurring_option"])
        self.assertContains(r, "donation-form")
        self.assertContains(r, "One-time Donation")
        self.assertNotContains(r, "Recurring Donation")
        self.assertNotContains(r, 'href="/donation/recurring/"')

        signup = self.client.get(reverse("donation-recurring"))
        self.assertEqual(signup.status_code, 302)
        self.assertIn("/donation/", signup.url)

    def test_server_rejects_new_recurring_when_cms_disabled(self):
        self.settings.recurring_donation_enabled = False
        self.settings.save()
        with self.assertRaises(RecurringDonationError) as ctx:
            create_recurring_subscription(
                amount=200,
                category=self.cat,
                donor_name="Blocked",
                donor_email="blocked@example.com",
            )
        self.assertEqual(ctx.exception.code, "cms_disabled")
        self.assertEqual(str(ctx.exception), CMS_RECURRING_DISABLED_MSG)
        self.assertFalse(DonationSubscription.objects.exists())

        posted = self.client.post(
            reverse("donation-recurring"),
            {
                "category": str(self.cat.pk),
                "amount": "200",
                "donor_name": "Blocked",
                "contact": "blocked@example.com",
            },
        )
        self.assertEqual(posted.status_code, 302)
        self.assertFalse(DonationSubscription.objects.exists())

    def test_existing_subscription_unaffected_when_cms_disabled(self):
        sub = create_recurring_subscription(
            amount=300,
            category=self.cat,
            donor_name="Existing Donor",
            donor_email="existing@example.com",
        )
        next_billing = timezone.now() + timedelta(days=28)
        sub.status = SubscriptionStatus.ACTIVE
        sub.next_billing = next_billing
        sub.gateway_subscription_ref = "sub-keep-1"
        sub.save()
        token = sub.management_token
        status_before = sub.status
        ref_before = sub.gateway_subscription_ref

        self.settings.recurring_donation_enabled = False
        self.settings.save()

        sub.refresh_from_db()
        self.assertEqual(sub.status, status_before)
        self.assertEqual(sub.status, SubscriptionStatus.ACTIVE)
        self.assertEqual(sub.next_billing, next_billing)
        self.assertEqual(sub.gateway_subscription_ref, ref_before)

        manage = self.client.get(reverse("donation-recurring-manage", args=[token]))
        self.assertEqual(manage.status_code, 200)
        self.assertContains(manage, "৳300")

    def test_donation_bangla_labels_and_hidden_recurring(self):
        from django.conf import settings as dj_settings

        self.settings.recurring_donation_enabled = False
        self.settings.save()
        self.client.post(reverse("set_language"), {"language": "bn", "next": "/donation/"})
        self.client.cookies[dj_settings.LANGUAGE_COOKIE_NAME] = "bn"
        bn = self.client.get(reverse("donation"))
        self.assertContains(bn, "অনুদান")
        self.assertContains(bn, "এখনই অনুদান দিন")
        self.assertContains(bn, "অনুদানের পরিমাণ")
        self.assertContains(bn, "নিজস্ব পরিমাণ")
        self.assertContains(bn, "এককালীন অনুদান")
        self.assertContains(bn, "দাতার তথ্য")
        self.assertNotContains(bn, "Recurring Donation")
        self.assertNotContains(bn, "Make a Donation")
        self.assertNotContains(bn, "Donate Now")
        self.assertNotContains(bn, "পুনরাবৃত্ত অনুদান")

    def test_donation_bangla_recurring_label_when_enabled(self):
        from django.conf import settings as dj_settings

        self.client.post(reverse("set_language"), {"language": "bn", "next": "/donation/"})
        self.client.cookies[dj_settings.LANGUAGE_COOKIE_NAME] = "bn"
        bn = self.client.get(reverse("donation"))
        self.assertContains(bn, "নিয়মিত অনুদান")
        self.assertContains(bn, "এককালীন অনুদান")
        self.assertNotContains(bn, "Recurring Donation")
        self.assertNotContains(bn, "পুনরাবৃত্ত অনুদান")
