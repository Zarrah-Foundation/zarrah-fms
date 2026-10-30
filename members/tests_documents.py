"""Member/application PDF generation and permission gates."""

import unittest
from datetime import date
from pathlib import Path

from django.conf import settings
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from governance.tests.helpers import (
    create_approved_member,
    create_staff_with_permission,
    ensure_rbac_seeded,
)
from members.documents import (
    generate_application_pdf,
    generate_bulk_applications_pdf,
    generate_bulk_members_pdf,
    generate_member_pdf,
)
from members.models import (
    ApplicationStatus,
    CouncilBody,
    Gender,
    IdentityType,
    MemberApplication,
    OrganizationalPosition,
)
from members.positions import assign_position


def _fonts_available() -> bool:
    base = Path(settings.BASE_DIR) / "static" / "fonts"
    return (base / "NotoSansBengali-Regular.ttf").is_file()


@unittest.skipUnless(_fonts_available(), "Bengali PDF fonts not installed")
class MemberDocumentGenerationTests(TestCase):
    def setUp(self):
        self.user, self.member = create_approved_member(901)
        pos = OrganizationalPosition.objects.create(
            name_en="Treasurer",
            council_body=CouncilBody.EXECUTIVE,
        )
        assign_position(
            self.member,
            pos,
            start_date=timezone.localdate(),
            is_primary=True,
        )

    def test_generate_member_pdf_bytes(self):
        payload = generate_member_pdf(self.member)
        self.assertTrue(payload.startswith(b"%PDF"))
        self.assertGreater(len(payload), 500)

    def test_bulk_members_has_page_breaks(self):
        _, member_b = create_approved_member(902)
        payload = generate_bulk_members_pdf([self.member, member_b])
        self.assertTrue(payload.startswith(b"%PDF"))
        # Multiple pages implied by larger size than single
        single = generate_member_pdf(self.member)
        self.assertGreater(len(payload), len(single))


@unittest.skipUnless(_fonts_available(), "Bengali PDF fonts not installed")
class ApplicationDocumentGenerationTests(TestCase):
    def setUp(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        photo = SimpleUploadedFile("p.jpg", b"\xff\xd8\xff\xd9", content_type="image/jpeg")
        ident = SimpleUploadedFile("id.pdf", b"%PDF-1.4", content_type="application/pdf")
        self.application = MemberApplication.objects.create(
            bangla_name="পরীক্ষা",
            english_name="Test Applicant",
            father_name="Father",
            mother_name="Mother",
            phone="01719999001",
            email="app-pdf@example.com",
            gender=Gender.MALE,
            date_of_birth=date(1990, 1, 15),
            identity_type=IdentityType.NID,
            identity_number="1234567890",
            photo=photo,
            identity_document=ident,
            status=ApplicationStatus.PENDING,
        )

    def test_generate_application_pdf_bytes(self):
        payload = generate_application_pdf(self.application)
        self.assertTrue(payload.startswith(b"%PDF"))

    def test_bulk_applications_pdf(self):
        payload = generate_bulk_applications_pdf([self.application])
        self.assertTrue(payload.startswith(b"%PDF"))


class MemberDocumentPermissionTests(TestCase):
    def setUp(self):
        ensure_rbac_seeded()
        self.client = Client()
        self.user, self.member = create_approved_member(911)
        self.denied = create_staff_with_permission(
            "doc-deny@example.com", "members.view"
        )
        self.allowed = create_staff_with_permission(
            "doc-allow@example.com", "members.profile_download"
        )

    def test_pdf_denied_without_permission(self):
        self.client.force_login(self.denied)
        url = reverse("dashboard-member-pdf", args=[self.member.pk])
        response = self.client.get(url)
        self.assertIn(response.status_code, (302, 403))

    def test_bulk_report_denied_without_permission(self):
        self.client.force_login(self.denied)
        url = reverse("dashboard-members-bulk-report")
        response = self.client.get(url)
        self.assertIn(response.status_code, (302, 403))

    @unittest.skipUnless(_fonts_available(), "Bengali PDF fonts not installed")
    def test_pdf_allowed_with_permission(self):
        # profile_download alone — also need view for redirect targets; grant both
        from rbac.models import Permission, RolePermission, UserRole
        from rbac.permissions import clear_cache

        module, action = "members", "view"
        perm, _ = Permission.objects.get_or_create(
            module=module, action=action, defaults={"label": "members.view"}
        )
        role = UserRole.objects.filter(user=self.allowed).select_related("role").first().role
        RolePermission.objects.get_or_create(role=role, permission=perm)
        clear_cache(self.allowed)

        self.client.force_login(self.allowed)
        url = reverse("dashboard-member-pdf", args=[self.member.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
