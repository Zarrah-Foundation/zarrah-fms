"""Bengali PDF rendering — font embed + generation smoke tests."""

from io import BytesIO
import re

from django.test import SimpleTestCase, override_settings
from django.utils import translation

from core.pdf_fonts import FONT_FAMILY, ensure_pdf_fonts, pdf_paragraph_styles, shaping_available


BN_SAMPLES = [
    "বাংলাদেশ",
    "জাররাহ ফাউন্ডেশন",
    "আমাদের লক্ষ্য",
    "আমাদের অভিলক্ষ্য",
    "স্বচ্ছতা ও জবাবদিহিতা",
    "সদস্যপদ আবেদন",
    "সদস্যপদ ফি",
    "ডিসেম্বর ২০২৬",
    "Membership Fee — ডিসেম্বর ২০২৬",
]


class BanglaPdfFontTests(SimpleTestCase):
    def test_fonts_register_and_shaping_available(self):
        name = ensure_pdf_fonts()
        self.assertEqual(name, FONT_FAMILY)
        self.assertTrue(shaping_available())
        styles = pdf_paragraph_styles()
        self.assertTrue(styles["body"].shaping)
        self.assertTrue(styles["heading"].shaping)

    def test_paragraph_pdf_embeds_noto_and_survives_bengali(self):
        from reportlab.platypus import Paragraph, SimpleDocTemplate

        from core.pdf_fonts import escape_pdf_text

        styles = pdf_paragraph_styles()
        buf = BytesIO()
        doc = SimpleDocTemplate(buf)
        story = [Paragraph(escape_pdf_text(s), styles["body"]) for s in BN_SAMPLES]
        story.append(Paragraph(escape_pdf_text(("বাংলাদেশ " * 80).strip()), styles["body"]))
        doc.build(story)
        pdf = buf.getvalue()
        self.assertGreater(len(pdf), 1000)
        self.assertIn(b"NotoSansBengali", pdf)
        fonts = re.findall(rb"/BaseFont\s*/([^\s/]+)", pdf)
        self.assertTrue(any(b"NotoSansBengali" in f for f in fonts))
        # Mixed EN/BN uses Helvetica for Latin + Noto for Bengali.
        mixed = BytesIO()
        SimpleDocTemplate(mixed).build(
            [Paragraph(escape_pdf_text("Membership Fee — ডিসেম্বর ২০২৬"), styles["body"])]
        )
        mixed_pdf = mixed.getvalue()
        self.assertIn(b"NotoSansBengali", mixed_pdf)
        self.assertTrue(b"Helvetica" in mixed_pdf or b"Helv" in mixed_pdf)

    def test_export_helper_path_with_bengali_title(self):
        from dashboard.views_content import _pdf_response

        response = _pdf_response(
            "test.pdf",
            "জাররাহ ফাউন্ডেশন — স্বচ্ছতা ও জবাবদিহিতা",
            ["নাম", "বিবরণ"],
            [["সদস্যপদ ফি", "Membership Fee — ডিসেম্বর ২০২৬"]],
        )
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn(b"NotoSansBengali", response.content)

    def test_receipt_pdf_with_bangla_foundation_name(self):
        from unittest.mock import MagicMock

        from donations.receipts import generate_receipt_pdf

        donation = MagicMock()
        donation.receipt_number = "R-BN-1"
        donation.transaction_id = "TX-BN-1"
        donation.display_name = "টেস্ট দাতা"
        donation.on_behalf_of = ""
        donation.amount = 100
        donation.currency = "BDT"
        donation.get_payment_method_display.return_value = "Cash"
        donation.get_status_display.return_value = "Completed"
        donation.created_at = __import__("django.utils.timezone", fromlist=["now"]).now()
        category = MagicMock()
        category.name_en = "General"
        category.name_bn = "সাধারণ"
        donation.category = category

        site = MagicMock()
        site.foundation_name_en = "Zarrah Foundation"
        site.foundation_name_bn = "জাররাহ ফাউন্ডেশন"
        site.short_name = "জাররাহ"
        site.site_title = "Zarrah Foundation"
        site.site_logo = None
        site.primary_email = "info@example.com"
        site.primary_phone = "01700000000"
        site.address_en = "Dhaka"
        site.address_bn = "ঢাকা"

        with override_settings(LANGUAGE_CODE="bn"):
            with translation.override("bn"):
                from unittest.mock import patch

                with patch("donations.receipts.SiteSettings.load", return_value=site):
                    pdf = generate_receipt_pdf(donation)
        self.assertIn(b"%PDF", pdf[:8])
        self.assertIn(b"NotoSansBengali", pdf)
