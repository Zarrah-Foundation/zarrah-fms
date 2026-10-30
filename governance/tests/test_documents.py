"""Resolution PDF/DOCX document generation, downloads, and signature UX."""

import io
import re
import unittest
import zipfile
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from governance.documents import (
    assert_no_protected_media_urls,
    generate_resolution_docx,
    generate_resolution_pdf,
    resolution_document_filename,
)
from governance.models import ParticipantStatus
from governance.services.participants import (
    add_participants_from_members,
    mark_attendance,
)
from governance.services.public_share import enable_public_share, revoke_public_share
from governance.services.resolutions import (
    create_new_version,
    create_resolution,
    prepare_for_signing,
    select_signers,
    sign_resolution,
)
from governance.tests.helpers import (
    create_approved_member,
    create_meeting,
    create_staff_with_permission,
    png_upload,
)


def _fonts_available() -> bool:
    base = Path(settings.BASE_DIR) / "static" / "fonts"
    return (base / "NotoSansBengali-Regular.ttf").is_file()


def _docx_xml_text(payload: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        xml = zf.read("word/document.xml").decode("utf-8")
    return re.sub(r"<[^>]+>", " ", xml)


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }
)
class ResolutionDocumentTests(TestCase):
    def setUp(self):
        cache.clear()
        self.meeting = create_meeting(title_bn="ডকুমেন্ট সভা")
        self.staff = create_staff_with_permission(
            "doc-staff@example.com", "resolutions.manage_signers"
        )
        self.downloader = create_staff_with_permission(
            "doc-dl@example.com", "resolution_documents.download"
        )
        self.user_a, self.member_a = create_approved_member(
            501, signature_image=png_upload("sig-a.png")
        )
        self.user_b, self.member_b = create_approved_member(
            502, signature_image=png_upload("sig-b.png")
        )
        for member in (self.member_a, self.member_b):
            participant = add_participants_from_members(self.meeting, [member])[0]
            mark_attendance(
                participant,
                ParticipantStatus.ATTENDED,
                actor=self.staff,
            )

        self.resolution = create_resolution(
            self.meeting,
            title_bn="সিদ্ধান্ত",
            title_en="Decision",
            content_bn=(
                "<p>বাংলা সিদ্ধান্তের পাঠ্য — কার্যনির্বাহী পরিষদ "
                "রেজুলেশন অনুমোদন</p>"
            ),
            content_en="<p>English resolution text — Decision No. 8</p>",
            decision_bn="<p>সিদ্ধান্ত গৃহীত</p>",
            actor=self.staff,
        )
        prepare_for_signing(self.resolution, actor=self.staff)
        select_signers(
            self.resolution,
            [self.member_a.pk, self.member_b.pk],
            actor=self.staff,
        )
        sign_resolution(
            self.resolution,
            self.member_a,
            user=self.user_a,
            confirmation=True,
        )
        self.client = Client()

    @unittest.skipUnless(
        _fonts_available(), "Noto Sans Bengali fonts missing under static/fonts/"
    )
    def test_pdf_generates_bytes_and_embeds_noto(self):
        pdf = generate_resolution_pdf(self.resolution, actor=self.staff)
        self.assertIsInstance(pdf, bytes)
        self.assertGreater(len(pdf), 1000)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertIn(b"NotoSansBengali", pdf)
        fonts = re.findall(rb"/BaseFont\s*/([^\s/]+)", pdf)
        self.assertTrue(any(b"NotoSansBengali" in f for f in fonts))
        assert_no_protected_media_urls(pdf)
        self.assertIn(self.resolution.resolution_id.encode("latin-1"), pdf)

    @unittest.skipUnless(_fonts_available(), "Noto Sans Bengali fonts missing")
    def test_pdf_mixed_language_and_signature_blocks(self):
        from governance.documents import build_resolution_document_context

        ctx = build_resolution_document_context(self.resolution)
        self.assertTrue(ctx["content_paragraphs_bn"])
        self.assertTrue(ctx["content_paragraphs_en"])
        self.assertIn("Decision No. 8", " ".join(ctx["content_paragraphs_en"]))
        self.assertTrue(any("বাংলা" in p for p in ctx["content_paragraphs_bn"]))
        signed = [s for s in ctx["signatures"] if s["is_signed"]]
        self.assertEqual(len(signed), 1)
        self.assertEqual(signed[0]["member_id"], self.member_a.member_id)
        self.assertTrue(signed[0]["image_path"])
        self.assertEqual(ctx["version_number"], 1)
        self.assertEqual(ctx["resolution_id"], self.resolution.resolution_id)

        pdf = generate_resolution_pdf(self.resolution)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 2000)
        # Metadata title/subject embed resolution ID uncompressed.
        self.assertIn(self.resolution.resolution_id.encode("latin-1"), pdf)
        self.assertIn(b"NotoSansBengali", pdf)
        assert_no_protected_media_urls(pdf)

    def test_docx_generates_valid_bytes_with_bangla(self):
        try:
            docx = generate_resolution_docx(self.resolution, actor=self.staff)
        except ImportError:
            self.skipTest("python-docx not installed")
        self.assertIsInstance(docx, bytes)
        self.assertGreater(len(docx), 500)
        self.assertTrue(docx.startswith(b"PK"))
        text = _docx_xml_text(docx)
        self.assertIn("বাংলা", text)
        self.assertIn(self.resolution.resolution_id, text)
        self.assertIn(self.member_a.member_id, text)
        self.assertIn("Approved", text)
        assert_no_protected_media_urls(docx)

    def test_document_filename_includes_version(self):
        name = resolution_document_filename(self.resolution, ext="pdf")
        self.assertEqual(
            name,
            f"{self.resolution.resolution_id}-v1.pdf",
        )
        name_docx = resolution_document_filename(self.resolution, ext="docx")
        self.assertTrue(name_docx.endswith("-v1.docx"))

    def test_versioned_documents_remain_distinct(self):
        v1 = self.resolution.current_version
        v1_id = v1.pk
        create_new_version(
            self.resolution,
            actor=self.staff,
            reason="Clarify wording",
            content_bn="<p>নতুন সংস্করণের পাঠ্য</p>",
        )
        self.resolution.refresh_from_db()
        self.assertEqual(self.resolution.current_version.version_number, 2)
        self.assertTrue(
            self.resolution.versions.filter(pk=v1_id, is_frozen=True).exists()
        )
        name_v2 = resolution_document_filename(self.resolution, ext="pdf")
        self.assertTrue(name_v2.endswith("-v2.pdf"))
        v1.refresh_from_db()
        self.assertIn("বাংলা সিদ্ধান্তের", v1.content_bn)

    def test_admin_download_requires_permission(self):
        url = reverse("dashboard-resolution-pdf", kwargs={"pk": self.resolution.pk})
        anon = self.client.get(url)
        self.assertIn(anon.status_code, (302, 403))

        self.client.force_login(self.user_b)
        denied = self.client.get(url)
        self.assertEqual(denied.status_code, 302)

        self.client.force_login(self.downloader)
        ok = self.client.get(url)
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok["Content-Type"], "application/pdf")
        self.assertIn(
            f"{self.resolution.resolution_id}-v1.pdf",
            ok["Content-Disposition"],
        )
        assert_no_protected_media_urls(ok.content)

    def test_member_idor_cannot_download_other_resolution(self):
        other = create_resolution(
            self.meeting,
            title_bn="অন্যান্য",
            content_bn="<p>private</p>",
            actor=self.staff,
        )
        prepare_for_signing(other, actor=self.staff)
        select_signers(other, [self.member_a.pk], actor=self.staff)

        url = reverse("my-resolution-pdf", kwargs={"pk": other.pk})
        self.client.force_login(self.user_b)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)

        self.client.force_login(self.user_a)
        ok = self.client.get(url)
        self.assertEqual(ok.status_code, 200)

    def test_public_share_download_security(self):
        share = enable_public_share(
            self.resolution,
            actor=self.staff,
            password="secret99",
            expires_at=timezone.now() + timedelta(days=1),
        )
        pdf_url = reverse("public-resolution-pdf", kwargs={"token": share.token})

        blocked = self.client.get(pdf_url)
        self.assertEqual(blocked.status_code, 302)

        pwd_url = reverse(
            "public-resolution-password", kwargs={"token": share.token}
        )
        wrong = self.client.post(pwd_url, {"password": "nope"})
        self.assertEqual(wrong.status_code, 200)

        ok_pwd = self.client.post(pwd_url, {"password": "secret99"})
        self.assertEqual(ok_pwd.status_code, 302)

        pdf = self.client.get(pdf_url)
        self.assertEqual(pdf.status_code, 200)
        self.assertIn(
            f"{self.resolution.resolution_id}-v1.pdf",
            pdf["Content-Disposition"],
        )
        assert_no_protected_media_urls(pdf.content)
        self.assertNotIn(b"protected-media", pdf.content)

        revoke_public_share(self.resolution, actor=self.staff)
        revoked = self.client.get(pdf_url)
        self.assertEqual(revoked.status_code, 404)

    def test_expired_public_share_cannot_download(self):
        share = enable_public_share(
            self.resolution,
            actor=self.staff,
            expires_at=timezone.now() - timedelta(minutes=5),
        )
        url = reverse("public-resolution-pdf", kwargs={"token": share.token})
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_signature_profile_upload_and_immutability(self):
        url = reverse("my-signature")
        self.client.force_login(self.user_a)
        page = self.client.get(url)
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Digital Signature")

        sig = self.resolution.current_version.signatures.get(member=self.member_a)
        original_name = sig.signature_image.name
        sig.signature_image.open("rb")
        original_bytes = sig.signature_image.read()
        sig.signature_image.close()

        buf = io.BytesIO()
        Image.new("RGB", (64, 32), color=(200, 40, 40)).save(buf, format="PNG")
        upload = SimpleUploadedFile(
            "new-sig.png", buf.getvalue(), content_type="image/png"
        )
        resp = self.client.post(
            url, {"action": "upload", "signature_image": upload}, follow=True
        )
        self.assertEqual(resp.status_code, 200)
        self.member_a.refresh_from_db()
        self.assertTrue(self.member_a.signature_image)

        sig.refresh_from_db()
        self.assertEqual(sig.signature_image.name, original_name)
        sig.signature_image.open("rb")
        self.assertEqual(sig.signature_image.read(), original_bytes)
        sig.signature_image.close()

    def test_anonymous_cannot_access_signature_page(self):
        resp = self.client.get(reverse("my-signature"))
        self.assertEqual(resp.status_code, 302)
