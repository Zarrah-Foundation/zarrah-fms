from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from core.choices import DonationStatus, PaymentMethod
from donations.models import Donation, DonationCategory, Transaction
from donations.ownership import donations_for_user, user_can_access_donation

User = get_user_model()


class DonationOwnershipTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="donor@example.com", password="Str0ngPass!23")
        self.user.email_verified = timezone.now()
        self.user.save(update_fields=["email_verified"])
        self.category = DonationCategory.objects.create(
            name_en="General", name_bn="সাধারণ", slug="general", is_active=True
        )
        self.tx1 = Transaction.objects.create(
            tran_id="T1", session_id="S1", amount=100, currency="BDT"
        )
        self.linked = Donation.objects.create(
            donor_name="Linked",
            donor_email="donor@example.com",
            user=self.user,
            amount=100,
            category=self.category,
            payment_method=PaymentMethod.SSLCOMMERZ,
            status=DonationStatus.COMPLETED,
            transaction=self.tx1,
            receipt_number="ZFR-TEST-1",
        )
        self.tx2 = Transaction.objects.create(
            tran_id="T2", session_id="S2", amount=50, currency="BDT"
        )
        self.by_email = Donation.objects.create(
            donor_name="Guest",
            donor_email="donor@example.com",
            user=None,
            amount=50,
            category=self.category,
            payment_method=PaymentMethod.CASH,
            status=DonationStatus.COMPLETED,
            transaction=self.tx2,
            receipt_number="ZFR-TEST-2",
        )
        self.tx3 = Transaction.objects.create(
            tran_id="T3", session_id="S3", amount=10, currency="BDT"
        )
        self.other = Donation.objects.create(
            donor_name="Other",
            donor_email="other@example.com",
            amount=10,
            category=self.category,
            payment_method=PaymentMethod.CASH,
            status=DonationStatus.COMPLETED,
            transaction=self.tx3,
            receipt_number="ZFR-TEST-3",
        )

    def test_queryset_includes_user_and_email_matches(self):
        qs = donations_for_user(self.user)
        ids = set(qs.values_list("id", flat=True))
        self.assertIn(self.linked.id, ids)
        self.assertIn(self.by_email.id, ids)
        self.assertNotIn(self.other.id, ids)

    def test_cannot_access_other_donors_receipt(self):
        self.assertFalse(user_can_access_donation(self.user, self.other))
        self.assertTrue(user_can_access_donation(self.user, self.linked))

    def test_my_donations_page(self):
        client = Client()
        client.force_login(self.user)
        response = client.get(reverse("dashboard-my-donations"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ZFR-TEST-1")
        self.assertContains(response, "ZFR-TEST-2")
        self.assertNotContains(response, "ZFR-TEST-3")

    def test_receipt_denied_without_ownership(self):
        client = Client()
        client.force_login(self.user)
        response = client.get(reverse("donation-receipt", kwargs={"pk": self.other.pk}))
        self.assertEqual(response.status_code, 302)
