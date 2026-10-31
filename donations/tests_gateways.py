from django.test import TestCase, override_settings

from core.choices import PaymentMethod
from donations.gateway_capabilities import (
    autopay_activation_allowed,
    hosted_card_channels,
    method_capabilities,
    online_checkout_allowed,
    sslcommerz_supports_recurring,
)
from donations.models import ChannelKind, PaymentMethodConfig, TransactionPurpose


@override_settings(
    SSLCOMMERZ_STORE_ID="store",
    SSLCOMMERZ_STORE_PASSWORD="pass",
    SSLCOMMERZ_IS_SANDBOX=True,
)
class GatewayCapabilityTests(TestCase):
    def test_sslcommerz_one_time_true_recurring_false(self):
        caps = method_capabilities(PaymentMethod.SSLCOMMERZ)
        self.assertTrue(caps["implemented"])
        self.assertTrue(caps["supports_one_time"])
        self.assertFalse(caps["supports_recurring"])
        self.assertFalse(sslcommerz_supports_recurring())
        self.assertEqual(caps["credentials"]["status"], "sandbox")
        # Never expose secrets in the capabilities map
        blob = str(caps["credentials"])
        self.assertNotIn("envsecret", blob)
        self.assertNotIn("testpass", blob)
        self.assertNotIn("store_passwd", blob)
        self.assertNotIn("store_password", blob)

    def test_bkash_sandbox_one_time_and_nagad_not_implemented(self):
        nagad = method_capabilities(PaymentMethod.NAGAD)
        self.assertFalse(nagad["implemented"])
        self.assertFalse(nagad["supports_recurring"])
        self.assertIn("not implemented", nagad["label_note"].lower())

        bkash = method_capabilities(PaymentMethod.BKASH)
        self.assertTrue(bkash["implemented"])
        self.assertFalse(bkash["supports_one_time"])
        self.assertFalse(bkash["supports_recurring"])
        self.assertIn("not implemented", bkash["label_note"].lower())
        self.assertIn("sandbox", bkash["label_note"].lower())

    def test_visa_mc_hosted_not_direct(self):
        channels = hosted_card_channels()
        self.assertEqual(channels[0]["hosted_via"], PaymentMethod.SSLCOMMERZ)
        self.assertFalse(channels[0]["implemented_direct"])

    def test_disabled_ssl_blocks_checkout(self):
        PaymentMethodConfig.objects.update_or_create(
            method=PaymentMethod.SSLCOMMERZ,
            defaults={"is_enabled": False, "channel_kind": ChannelKind.ONLINE_HOSTED},
        )
        ok, err = online_checkout_allowed(PaymentMethod.SSLCOMMERZ)
        self.assertFalse(ok)
        self.assertIn("disabled", err.lower())

    def test_purpose_toggles_are_independent(self):
        PaymentMethodConfig.objects.update_or_create(
            method=PaymentMethod.SSLCOMMERZ,
            defaults={
                "is_enabled": True,
                "channel_kind": ChannelKind.ONLINE_HOSTED,
                "enabled_for_donation": False,
                "enabled_for_membership_fee": True,
            },
        )
        ok_d, _ = online_checkout_allowed(
            purpose=TransactionPurpose.DONATION
        )
        ok_m, _ = online_checkout_allowed(
            purpose=TransactionPurpose.MEMBERSHIP_FEE
        )
        self.assertFalse(ok_d)
        self.assertTrue(ok_m)

    def test_autopay_mock_allowed_in_sandbox(self):
        allowed, _msg, mode = autopay_activation_allowed()
        self.assertTrue(allowed)
        self.assertEqual(mode, "MOCK")


@override_settings(
    SSLCOMMERZ_STORE_ID="",
    SSLCOMMERZ_STORE_PASSWORD="",
    SSLCOMMERZ_IS_SANDBOX=False,
)
class GatewayMissingCredentialsTests(TestCase):
    def test_missing_credentials(self):
        caps = method_capabilities(PaymentMethod.SSLCOMMERZ)
        self.assertEqual(caps["credentials"]["status"], "missing")
        ok, _err = online_checkout_allowed()
        self.assertFalse(ok)
