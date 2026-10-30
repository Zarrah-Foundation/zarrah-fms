"""Phase 6C — SiteSettings registration consistency, finance pagination, membership ops."""

import io
from datetime import date

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from accounts.models import Role as LegacyRole
from core.models import SiteSettings
from finance.models import Expense, Income
from members.models import (
    ApplicationStatus,
    MemberApplication,
    MembershipType,
    MemberStatus,
)
from members.services import approve_application, reject_application
from pages import about_data, constitution_data
from pages.about_data import resolve_registration_info
from pages.constitution_data import resolve_registration

User = get_user_model()


def _png(name="photo.png"):
    buf = io.BytesIO()
    Image.new("RGB", (24, 24), color=(20, 120, 80)).save(buf, format="PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


def _pdf(name="id.pdf"):
    return SimpleUploadedFile(name, b"%PDF-1.4 test", content_type="application/pdf")


class SiteSettingsRegistrationConsistencyTests(TestCase):
    def test_about_and_constitution_use_sitesettings(self):
        settings = SiteSettings.load()
        settings.registration_number = "S-99999/2026"
        settings.registration_date = date(2026, 3, 15)
        settings.save()

        about_reg = resolve_registration_info()
        const_reg = resolve_registration()
        self.assertEqual(about_reg["number"], "S-99999/2026")
        self.assertEqual(const_reg["number"], "S-99999/2026")

        about_rows = {r["label_en"]: r for r in about_reg["rows"]}
        self.assertEqual(about_rows["Registration No."]["value_en"], "S-99999/2026")
        self.assertIn("15", about_rows["Registered On"]["value_en"])
        self.assertIn("2026", about_rows["Registered On"]["value_en"])

        ctx_about = about_data.get_context()
        ctx_const = constitution_data.get_context()
        self.assertEqual(
            ctx_about["about_registration"]["number"], "S-99999/2026"
        )
        self.assertEqual(
            ctx_const["constitution_registration"]["number"], "S-99999/2026"
        )

    def test_public_pages_render_sitesettings_registration(self):
        settings = SiteSettings.load()
        settings.registration_number = "S-88888/2026"
        settings.registration_date = date(2026, 1, 10)
        settings.save()
        client = Client()
        about = client.get(reverse("about"))
        contact = client.get(reverse("contact"))
        self.assertEqual(about.status_code, 200)
        self.assertEqual(contact.status_code, 200)
        self.assertContains(about, "S-88888/2026")
        self.assertContains(contact, "S-88888/2026")
        footer_home = client.get(reverse("home"))
        self.assertContains(footer_home, "S-88888/2026")


class FinanceCashBookPaginationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="fin-p6c@example.com",
            password="pass12345",
            role=LegacyRole.FINANCE_OFFICER,
            is_staff=True,
        )
        self.user.email_verified = timezone.now()
        self.user.save()
        # Grant finance.view via superuser for simplicity in pagination check
        self.user.is_superuser = True
        self.user.save()
        for i in range(30):
            Income.objects.create(
                title=f"Inc {i}",
                amount=10,
                received_date=timezone.now(),
                source="test",
            )
            Expense.objects.create(
                title=f"Exp {i}",
                amount=5,
                expense_date=timezone.now(),
                category="ops",
            )

    def test_cash_book_paginated(self):
        client = Client()
        client.force_login(self.user)
        resp = client.get(reverse("dashboard-finance-cashbook"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("page_obj", resp.context)
        self.assertEqual(resp.context["page_obj"].paginator.per_page, 25)
        self.assertLessEqual(len(resp.context["entries"]), 25)
        # Full closing balance still computed across all rows
        self.assertEqual(resp.context["closing_balance"], 30 * 10 - 30 * 5)


class MembershipRejectNotifyAndLedgerTests(TestCase):
    def setUp(self):
        self.reviewer = User.objects.create_user(
            email="rev-p6c@example.com",
            password="pass12345",
            role=LegacyRole.EXECUTIVE_ADMIN,
            is_staff=True,
        )
        self.mtype = MembershipType.objects.create(
            name_en="General", name_bn="সাধারণ", slug="gen-p6c-m", fee_amount=50
        )

    def _application(self, email="app-p6c@example.com", phone="01711112222"):
        return MemberApplication.objects.create(
            bangla_name="আবেদনকারী",
            english_name="Applicant SixC",
            father_name="Father",
            mother_name="Mother",
            phone=phone,
            email=email,
            gender="MALE",
            date_of_birth=date(1995, 5, 15),
            photo=_png(),
            identity_type="NID",
            identity_number="1234567890999",
            identity_document=_pdf(),
            present_address="Dhaka",
            present_district="Dhaka",
            status=ApplicationStatus.PENDING,
        )

    def test_approve_seeds_fee_ledger(self):
        from members.models import MembershipFee

        app = self._application()
        member = approve_application(app, self.reviewer, membership_type=self.mtype)
        self.assertEqual(member.status, MemberStatus.APPROVED)
        self.assertTrue(MembershipFee.objects.filter(member=member).exists())

    def test_reject_notifies_existing_user(self):
        from audit.models import Notification, NotificationType

        user = User.objects.create_user(
            email="app-p6c@example.com", password="pass12345"
        )
        app = self._application(email=user.email)
        reject_application(app, self.reviewer, reason="Incomplete docs")
        self.assertTrue(
            Notification.objects.filter(
                user=user, type=NotificationType.MEMBERSHIP_REJECTED
            ).exists()
        )
