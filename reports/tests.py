from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from finance.models import FinancialSummary
from reports.models import Report, ReportType


class TransparencyDocumentTests(TestCase):
    def test_public_documents_grouped_on_transparency_page(self):
        Report.objects.create(
            title="Audit 2026",
            title_en="Audit 2026",
            type=ReportType.AUDIT,
            year=2026,
            file=SimpleUploadedFile("audit.pdf", b"%PDF-1.4", content_type="application/pdf"),
            is_public=True,
            show_on_transparency=True,
            show_on_reports=False,
        )
        Report.objects.create(
            title="Secret",
            type=ReportType.POLICY,
            file=SimpleUploadedFile("secret.pdf", b"%PDF-1.4", content_type="application/pdf"),
            is_public=False,
            show_on_transparency=True,
        )
        FinancialSummary.objects.create(
            year=2026, total_income=1000, total_expense=400, net_balance=600, is_published=True
        )
        FinancialSummary.objects.create(
            year=2025, total_income=1, total_expense=1, net_balance=0, is_published=False
        )
        response = self.client.get(reverse("transparency"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Audit 2026")
        self.assertNotContains(response, "Secret")
        self.assertContains(response, "2026")
        self.assertNotContains(response, ">2025<")


class NewsSanitizeTests(TestCase):
    def test_news_form_strips_script_tags(self):
        from dashboard.forms import NewsForm
        from accounts.models import User

        author = User.objects.create_user(email="ed@example.com", password="x")
        form = NewsForm(
            data={
                "title": "Hello",
                "slug": "hello",
                "excerpt": "",
                "content": '<p>Hi</p><script>alert(1)</script><a href="https://example.com">link</a>',
                "is_published": True,
            }
        )
        form.instance.author = author
        self.assertTrue(form.is_valid(), form.errors)
        self.assertNotIn("<script>", form.cleaned_data["content"])
        self.assertIn("<p>Hi</p>", form.cleaned_data["content"])
