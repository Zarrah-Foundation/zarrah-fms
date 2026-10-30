"""Phase 4.5 — payment credentials, transparency destinations, homepage wiring."""

from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role
from community.models import Partner, Testimonial
from core.choices import PaymentMethod
from donations.credential_crypto import decrypt_secret, encrypt_secret, mask_store_id
from donations.credential_service import (
    TEST_STATUS_NOT_CONFIGURED,
    resolve_sslcommerz_credentials,
    test_sslcommerz_connection,
)
from donations.models import ChannelKind, PaymentMethodConfig, Transaction, TransactionPurpose
from donations.models import Donation
from finance.models import Income
from reports.models import Report, ReportType

User = get_user_model()


def _admin():
    u = User.objects.create_user(
        email="pay-admin@example.com", password="Str0ngPass!23", role=Role.SUPER_ADMIN
    )
    u.is_superuser = True
    u.email_verified = timezone.now()
    u.save()
    return u


def _ssl_config(**kwargs):
    defaults = {
        "method": PaymentMethod.SSLCOMMERZ,
        "display_name": "SSLCommerz",
        "channel_kind": ChannelKind.ONLINE_HOSTED,
        "is_enabled": True,
        "enabled_for_donation": True,
        "enabled_for_membership_fee": True,
    }
    defaults.update(kwargs)
    cfg, _ = PaymentMethodConfig.objects.update_or_create(
        method=PaymentMethod.SSLCOMMERZ, defaults=defaults
    )
    return cfg


class CredentialCryptoTests(TestCase):
    def test_encrypt_decrypt_roundtrip(self):
        token = encrypt_secret("super-secret-pass")
        self.assertNotIn("super-secret-pass", token)
        self.assertEqual(decrypt_secret(token), "super-secret-pass")

    def test_mask_store_id(self):
        masked = mask_store_id("mystore12345")
        self.assertNotEqual(masked, "mystore12345")
        self.assertTrue(masked.startswith("my"))


@override_settings(
    SSLCOMMERZ_STORE_ID="envstore",
    SSLCOMMERZ_STORE_PASSWORD="envsecret",
    SSLCOMMERZ_IS_SANDBOX=True,
)
class PaymentCredentialAdminTests(TestCase):
    def setUp(self):
        self.admin = _admin()
        self.client = Client()
        self.client.force_login(self.admin)
        self.cfg = _ssl_config()

    def test_credentials_status_from_env(self):
        creds = resolve_sslcommerz_credentials()
        self.assertTrue(creds.configured)
        self.assertEqual(creds.source, "environment")
        self.assertEqual(creds.store_id, "envstore")

    def test_password_never_exposed_in_configure_page(self):
        self.cfg.set_store_password("db-secret-password")
        self.cfg.store_id = "dbstore"
        self.cfg.use_database_credentials = True
        self.cfg.is_sandbox = True
        self.cfg.save()
        url = reverse("dashboard-payment-method-configure", kwargs={"pk": self.cfg.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8")
        self.assertNotIn("db-secret-password", body)
        self.assertNotIn(self.cfg.encrypted_store_password, body)
        self.assertNotIn("envsecret", body)

    def test_production_requires_confirmation(self):
        url = reverse("dashboard-payment-method-configure", kwargs={"pk": self.cfg.pk})
        response = self.client.post(
            url,
            {
                "store_id": "s1",
                "store_password": "p1",
                "use_database_credentials": "on",
                "is_enabled": "on",
                "enabled_for_donation": "on",
                "enabled_for_membership_fee": "on",
                # is_sandbox unchecked = production without confirm
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Confirm Production")

    def test_permission_required(self):
        member = User.objects.create_user(
            email="member-pay@example.com", password="Str0ngPass!23", role=Role.MEMBER
        )
        member.email_verified = timezone.now()
        member.save()
        c = Client()
        c.force_login(member)
        url = reverse("dashboard-payment-method-configure", kwargs={"pk": self.cfg.pk})
        response = c.get(url)
        self.assertEqual(response.status_code, 302)

    @patch("donations.credential_service.requests.get")
    def test_connection_does_not_create_transactions(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "INVALID_TRANSACTION"}
        mock_get.return_value = mock_resp
        before_tx = Transaction.objects.count()
        before_don = Donation.objects.count()
        before_inc = Income.objects.count()
        status, _msg = test_sslcommerz_connection(actor=self.admin)
        self.assertEqual(status, "SUCCESS")
        self.assertEqual(Transaction.objects.count(), before_tx)
        self.assertEqual(Donation.objects.count(), before_don)
        self.assertEqual(Income.objects.count(), before_inc)

    def test_not_configured_status(self):
        with override_settings(SSLCOMMERZ_STORE_ID="", SSLCOMMERZ_STORE_PASSWORD=""):
            PaymentMethodConfig.objects.filter(method=PaymentMethod.SSLCOMMERZ).update(
                use_database_credentials=False,
                encrypted_store_password="",
                store_id="",
            )
            status, _ = test_sslcommerz_connection()
            self.assertEqual(status, TEST_STATUS_NOT_CONFIGURED)

    def test_donation_toggle_independent(self):
        from donations.gateway_capabilities import online_checkout_allowed

        _ssl_config(enabled_for_donation=False, enabled_for_membership_fee=True)
        ok_d, _ = online_checkout_allowed(purpose=TransactionPurpose.DONATION)
        ok_m, _ = online_checkout_allowed(purpose=TransactionPurpose.MEMBERSHIP_FEE)
        self.assertFalse(ok_d)
        self.assertTrue(ok_m)

    def test_membership_toggle_independent(self):
        from donations.gateway_capabilities import online_checkout_allowed

        _ssl_config(enabled_for_donation=True, enabled_for_membership_fee=False)
        ok_d, _ = online_checkout_allowed(purpose=TransactionPurpose.DONATION)
        ok_m, _ = online_checkout_allowed(purpose=TransactionPurpose.MEMBERSHIP_FEE)
        self.assertTrue(ok_d)
        self.assertFalse(ok_m)


class TransparencyReportsSeparationTests(TestCase):
    def _doc(self, title, **kwargs):
        defaults = {
            "title": title,
            "title_en": title,
            "type": ReportType.AUDIT,
            "year": 2026,
            "file": SimpleUploadedFile(f"{title}.pdf", b"%PDF-1.4", content_type="application/pdf"),
            "is_public": True,
            "show_on_transparency": False,
            "show_on_reports": False,
        }
        defaults.update(kwargs)
        return Report.objects.create(**defaults)

    def test_transparency_only(self):
        self._doc("Only Transparency", show_on_transparency=True, show_on_reports=False)
        t = self.client.get(reverse("transparency"))
        r = self.client.get(reverse("reports"))
        self.assertContains(t, "Only Transparency")
        self.assertNotContains(r, "Only Transparency")

    def test_reports_only(self):
        self._doc(
            "Only Reports",
            type=ReportType.ACTIVITY,
            show_on_transparency=False,
            show_on_reports=True,
        )
        t = self.client.get(reverse("transparency"))
        r = self.client.get(reverse("reports"))
        self.assertNotContains(t, "Only Reports")
        self.assertContains(r, "Only Reports")

    def test_dual_published(self):
        self._doc("Both Pages", show_on_transparency=True, show_on_reports=True)
        self.assertContains(self.client.get(reverse("transparency")), "Both Pages")
        self.assertContains(self.client.get(reverse("reports")), "Both Pages")

    def test_unpublished_nowhere(self):
        self._doc(
            "Hidden Doc",
            is_public=False,
            show_on_transparency=True,
            show_on_reports=True,
        )
        self.assertNotContains(self.client.get(reverse("transparency")), "Hidden Doc")
        self.assertNotContains(self.client.get(reverse("reports")), "Hidden Doc")

    def test_private_finance_not_listed_as_document(self):
        response = self.client.get(reverse("transparency"))
        self.assertNotContains(response, "cash book")
        self.assertNotContains(response, "Ledger expense")


class HomepageCommunityTests(TestCase):
    def test_published_testimonial_appears_without_cms_section(self):
        Testimonial.objects.create(
            author_name="Visible Donor",
            content_en="Excellent work",
            is_published=True,
            display_order=1,
        )
        Testimonial.objects.create(
            author_name="Hidden Donor",
            content_en="Nope",
            is_published=False,
        )
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Visible Donor")
        self.assertContains(response, "Excellent work")
        self.assertNotContains(response, "Hidden Donor")

    def test_active_partner_ordering(self):
        Partner.objects.create(name="Zed Partner", is_active=True, display_order=2)
        Partner.objects.create(name="Alpha Partner", is_active=True, display_order=1)
        Partner.objects.create(name="Inactive Co", is_active=False, display_order=0)
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Alpha Partner")
        self.assertContains(response, "Zed Partner")
        self.assertNotContains(response, "Inactive Co")
        body = response.content.decode()
        self.assertLess(body.index("Alpha Partner"), body.index("Zed Partner"))

    def test_empty_state_when_none(self):
        # No CMS sections either → fall back welcome hero, no error
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    def test_bn_en_content_rendering(self):
        Testimonial.objects.create(
            author_name="Bilingual",
            content_en="English quote",
            content_bn="বাংলা উক্তি",
            is_published=True,
        )
        from django.conf import settings as dj_settings

        self.client.cookies[dj_settings.LANGUAGE_COOKIE_NAME] = "en"
        r_en = self.client.get(reverse("home"))
        self.assertContains(r_en, "English quote")
        self.client.cookies[dj_settings.LANGUAGE_COOKIE_NAME] = "bn"
        r_bn = self.client.get(reverse("home"))
        self.assertContains(r_bn, "বাংলা উক্তি")
