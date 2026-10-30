from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.utils.translation import activate, deactivate

from reports.models import Report, ReportType


def _pdf(name="doc.pdf"):
    return SimpleUploadedFile(name, b"%PDF-1.4 test", content_type="application/pdf")


class DocumentDestinationTests(TestCase):
    def test_transparency_only_not_on_reports(self):
        Report.objects.create(
            title="Governance Charter",
            title_en="Governance Charter",
            type=ReportType.GOVERNANCE,
            year=2026,
            file=_pdf("gov.pdf"),
            is_public=True,
            show_on_transparency=True,
            show_on_reports=False,
        )
        self.assertContains(Client().get(reverse("transparency")), "Governance Charter")
        self.assertNotContains(Client().get(reverse("reports")), "Governance Charter")

    def test_reports_only_not_on_transparency(self):
        Report.objects.create(
            title="Activity Report 2026",
            title_en="Activity Report 2026",
            type=ReportType.ACTIVITY,
            year=2026,
            file=_pdf("act.pdf"),
            is_public=True,
            show_on_transparency=False,
            show_on_reports=True,
        )
        self.assertContains(Client().get(reverse("reports")), "Activity Report 2026")
        self.assertNotContains(Client().get(reverse("transparency")), "Activity Report 2026")

    def test_dual_destination(self):
        Report.objects.create(
            title="Shared Public Doc",
            title_en="Shared Public Doc",
            type=ReportType.ANNUAL,
            year=2026,
            file=_pdf("shared.pdf"),
            is_public=True,
            show_on_transparency=True,
            show_on_reports=True,
        )
        self.assertContains(Client().get(reverse("transparency")), "Shared Public Doc")
        self.assertContains(Client().get(reverse("reports")), "Shared Public Doc")

    def test_private_document_not_exposed(self):
        Report.objects.create(
            title="Internal Only",
            title_en="Internal Only",
            type=ReportType.POLICY,
            file=_pdf("priv.pdf"),
            is_public=False,
            show_on_transparency=True,
            show_on_reports=True,
        )
        self.assertNotContains(Client().get(reverse("transparency")), "Internal Only")
        self.assertNotContains(Client().get(reverse("reports")), "Internal Only")
        resp = Client().get(
            reverse("report-download", kwargs={"pk": Report.objects.get().pk})
        )
        self.assertEqual(resp.status_code, 404)

    def test_bilingual_fallback_and_long_title_wrap_classes(self):
        Report.objects.create(
            title="EN title",
            title_en="",
            title_bn="বাংলা শিরোনাম খুব দীর্ঘ নথি যা কার্ডের ভিতরে মুড়িয়ে যেতে হবে নিরাপদে",
            description_bn="বিবরণ",
            description_en="",
            type=ReportType.LEGAL,
            year=2026,
            file=_pdf("bn.pdf"),
            is_public=True,
            show_on_transparency=True,
            show_on_reports=True,
        )
        activate("en")
        try:
            # EN missing → BN fallback
            r = Client().get(reverse("reports"))
            self.assertContains(r, "বাংলা শিরোনাম")
            self.assertContains(r, "break-words")
            self.assertContains(r, "zf-doc-card")
        finally:
            deactivate()
