from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import translation

from community.models import FAQ, LeadershipPerson, LeadershipRole, Partner, Testimonial
from core.models import SiteSettings


@override_settings(LANGUAGE_CODE="en")
class FAQFrontendTests(TestCase):
    def test_faq_page_shows_active_entries(self):
        FAQ.objects.create(
            question_en="How to join?",
            question_bn="কিভাবে যোগ দেব?",
            answer_en="Apply online.",
            answer_bn="অনলাইনে আবেদন করুন।",
            is_active=True,
            display_order=1,
        )
        FAQ.objects.create(
            question_en="Hidden",
            answer_en="Nope",
            is_active=False,
        )
        with translation.override("en"):
            response = self.client.get(reverse("faq"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "How to join?")
        self.assertNotContains(response, "Hidden")

    def test_faq_empty_state(self):
        with translation.override("en"):
            response = self.client.get(reverse("faq"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No FAQs have been published yet")


class ContactPageTests(TestCase):
    def test_contact_form_is_stored(self):
        from community.models import ContactMessage

        response = self.client.post(
            reverse("contact"),
            {
                "name": "Rina",
                "email": "rina@example.com",
                "subject": "Hello",
                "message": "I would like to help.",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            ContactMessage.objects.filter(email="rina@example.com", subject="Hello").exists()
        )

    def test_contact_shows_registration_and_safe_map(self):
        settings = SiteSettings.load()
        settings.registration_number = "S-15000/2026"
        settings.primary_email = "info@zarrah.org"
        settings.google_maps_embed_url = "https://www.google.com/maps/embed?pb=test"
        settings.save()
        response = self.client.get(reverse("contact"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "S-15000/2026")
        self.assertContains(response, "info@zarrah.org")
        self.assertContains(response, "maps/embed")

    def test_unsafe_iframe_html_not_used_as_embed(self):
        settings = SiteSettings.load()
        settings.google_maps_embed_url = "javascript:alert(1)"
        settings.save()
        response = self.client.get(reverse("contact"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "javascript:alert")


class TermsPageTests(TestCase):
    def test_terms_has_structured_sections(self):
        with translation.override("en"):
            response = self.client.get(reverse("terms"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="acceptance"')
        self.assertContains(response, 'id="donations"')
        self.assertContains(response, 'id="membership"')


class AboutLeadershipTests(TestCase):
    def test_leadership_photo_from_model(self):
        LeadershipPerson.objects.create(
            role=LeadershipRole.CHAIRMAN,
            name="Test Chair",
            role_label_en="Chairman",
            role_label_bn="চেয়ারম্যান",
            is_published=True,
        )
        response = self.client.get(reverse("about"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Chair")


class HomeCommunitySectionsTests(TestCase):
    def test_home_context_includes_published_testimonials_and_partners(self):
        Testimonial.objects.create(
            author_name="Donor One",
            content_en="Great work",
            is_published=True,
        )
        Partner.objects.create(name="Partner Org", is_active=True)
        # No CMS sections required — HomeView synthetic sections cover this.
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Donor One")
        self.assertContains(response, "Partner Org")

    def test_unpublished_testimonial_and_inactive_partner_hidden(self):
        Testimonial.objects.create(
            author_name="Hidden T",
            content_en="secret",
            is_published=False,
        )
        Partner.objects.create(name="Hidden P", is_active=False)
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, "Hidden T")
        self.assertNotContains(response, "Hidden P")

    def test_empty_quote_testimonial_not_rendered(self):
        Testimonial.objects.create(
            author_name="No Quote Author",
            designation="Volunteer",
            content_en="",
            content_bn="",
            is_published=True,
        )
        Testimonial.objects.create(
            author_name="Has Quote",
            content_bn="ভালো কাজ",
            content_en="",
            is_published=True,
        )
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "No Quote Author")
        self.assertContains(response, "Has Quote")
        self.assertContains(response, "ভালো কাজ")


class AboutSectionRedirectTests(TestCase):
    def test_mission_vision_objectives_leadership_routes(self):
        cases = (
            ("mission-vision", "/about/#mission-vision", 302),
            ("objectives", None, 200),
            ("leadership", "/about/#leadership", 302),
        )
        for name, location, status in cases:
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, status)
                if location:
                    self.assertEqual(response["Location"], location)

    def test_about_page_has_section_fragment_ids(self):
        response = self.client.get(reverse("about"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="mission-vision"')
        self.assertContains(response, 'id="objectives"')
        self.assertContains(response, 'id="leadership"')
        self.assertContains(response, 'id="zarrah-skills"')
        self.assertContains(response, "Zarrah Foundation")
        self.assertContains(response, "https://skills.zarrah.org/")
        self.assertNotContains(response, "Lives Impacted")
        self.assertNotContains(response, "Vision 2030")

    def test_objectives_page_uses_memorandum_objectives(self):
        from django.conf import settings
        from django.utils import translation

        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "en"
        self.client.post(reverse("set_language"), {"language": "en", "next": "/objectives/"})
        with translation.override("en"):
            response = self.client.get(reverse("objectives"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Humanitarian Assistance")
        self.assertContains(response, "Humanitarian Support")
        self.assertContains(response, "Assisting helpless")
        self.assertContains(response, "zf-objective-card")
        self.assertNotContains(response, "Lives Impacted")

    def test_objectives_page_bangla_title(self):
        from django.conf import settings

        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "bn"
        self.client.post(reverse("set_language"), {"language": "bn", "next": "/objectives/"})
        response = self.client.get(reverse("objectives"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "উদ্দেশ্যসমূহ")
        self.assertContains(response, "মানবিক সহায়তা")
        self.assertContains(response, "কর্মক্ষেত্রসমূহ")
        self.assertNotContains(response, "Areas of Work")
        self.assertNotContains(response, "Contact page")

    def test_privacy_and_terms_language_labels(self):
        from django.conf import settings

        en = self.client.get(reverse("privacy"))
        self.assertContains(en, "Privacy")
        self.client.post(reverse("set_language"), {"language": "bn", "next": "/privacy/"})
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "bn"
        bn = self.client.get(reverse("privacy"))
        self.assertContains(bn, "গোপনীয়তা")
        terms = self.client.get(reverse("terms"))
        self.assertContains(terms, "legal-page")
        self.assertContains(terms, "legal-section")

    def test_about_objectives_cta_follows_language(self):
        from django.conf import settings

        self.client.post(reverse("set_language"), {"language": "en", "next": "/about/"})
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "en"
        en = self.client.get(reverse("about"))
        self.assertContains(en, "Objectives")
        self.client.post(reverse("set_language"), {"language": "bn", "next": "/about/"})
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "bn"
        bn = self.client.get(reverse("about"))
        self.assertContains(bn, "উদ্দেশ্যসমূহ")

    def test_about_bangla_labels_and_quorum(self):
        from django.conf import settings

        self.client.post(reverse("set_language"), {"language": "en", "next": "/about/"})
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "en"
        en = self.client.get(reverse("about"))
        self.assertContains(en, "Organizational Nature")
        self.assertContains(en, "Areas of Work")
        self.assertContains(en, "Financial Principles")
        self.assertContains(en, "View Transparency")
        self.assertContains(en, "Governance &amp; Accountability")
        self.assertContains(en, "Meeting Quorum")
        self.assertContains(en, "zf-quorum-card")
        self.assertContains(en, "2/3")
        self.assertContains(en, "1/3")
        self.assertContains(en, "Become a Member")
        self.assertContains(en, "Contact Us")
        self.assertNotContains(en, "Contact page")

        self.client.post(reverse("set_language"), {"language": "bn", "next": "/about/"})
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "bn"
        bn = self.client.get(reverse("about"))
        self.assertContains(bn, "সাংগঠনিক পরিচিতি")
        self.assertContains(bn, "কর্মক্ষেত্রসমূহ")
        self.assertContains(bn, "আর্থিক নীতিমালা")
        self.assertContains(bn, "স্বচ্ছতা দেখুন")
        self.assertContains(bn, "সুশাসন ও জবাবদিহিতা")
        self.assertContains(bn, "সভায় কোরাম")
        self.assertContains(bn, "কার্যনির্বাহী পরিষদ")
        self.assertContains(bn, "উপদেষ্টা পরিষদ")
        self.assertContains(bn, "সদস্য হোন")
        self.assertContains(bn, "যোগাযোগ করুন")
        self.assertNotContains(bn, "Contact page")
        self.assertNotContains(bn, "Organizational Nature")
        self.assertNotContains(bn, "Financial Principles")
        self.assertNotContains(bn, "Meeting Quorum")
        self.assertNotContains(bn, "(opens in a new tab)")
        self.assertContains(bn, "উপরে যান")
        self.assertContains(bn, "শাসন ও নীতিমালার নথি দেখুন")
        self.assertContains(bn, "মোট সদস্যের ২/৩")
        self.assertContains(bn, "তালিকাভুক্ত মোট সদস্যের ১/৩")
        self.assertContains(bn, "সাধারণ পরিষদ / AGM")

    def test_transparency_and_reports_bangla_chrome(self):
        from django.conf import settings
        from django.core.files.uploadedfile import SimpleUploadedFile

        from reports.models import Report, ReportType

        Report.objects.create(
            title="Memorandum",
            title_en="Memorandum",
            type=ReportType.CONSTITUTION,
            year=2026,
            file=SimpleUploadedFile("moa.pdf", b"%PDF-1.4", content_type="application/pdf"),
            is_public=True,
            show_on_transparency=True,
            show_on_reports=True,
        )
        self.client.post(reverse("set_language"), {"language": "en", "next": "/transparency/"})
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "en"
        en_t = self.client.get(reverse("transparency"))
        self.assertContains(en_t, "Transparency &amp; Accountability")
        self.assertContains(en_t, "Financial Principles")
        self.assertContains(en_t, "View Reports &amp; publications")
        self.assertContains(en_t, "Language")
        self.assertContains(en_t, "Download")
        self.assertContains(en_t, "zf-transparency-nav")
        self.assertContains(en_t, "Category")

        self.client.post(reverse("set_language"), {"language": "bn", "next": "/transparency/"})
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "bn"
        bn_t = self.client.get(reverse("transparency"))
        self.assertContains(bn_t, "স্বচ্ছতা ও জবাবদিহিতা")
        self.assertContains(bn_t, "আর্থিক নীতিমালা")
        self.assertContains(bn_t, "প্রতিবেদন ও প্রকাশনা দেখুন")
        self.assertContains(bn_t, "স্মারকলিপি")
        self.assertContains(bn_t, "ভাষা")
        self.assertContains(bn_t, "শ্রেণি")
        self.assertContains(bn_t, "ডাউনলোড")
        self.assertNotContains(bn_t, "Financial Principles")
        self.assertNotContains(bn_t, "View Reports &amp; publications")
        self.assertContains(bn_t, "তারিখ")
        self.assertNotContains(bn_t, ">Language<")
        self.assertNotContains(bn_t, ">Category<")
        self.assertNotContains(bn_t, ">Download<")

        bn_r = self.client.get(reverse("reports"))
        self.assertContains(bn_r, "প্রতিবেদন ও প্রকাশনা")
        self.assertContains(bn_r, "স্বচ্ছতার নথি দেখুন")
        self.assertContains(bn_r, "ভাষা")
        self.assertContains(bn_r, "zf-doc-card")


class FooterRegistrationTests(TestCase):
    def test_footer_shows_registration_from_settings(self):
        settings = SiteSettings.load()
        settings.registration_number = "S-999/2026"
        settings.save()
        response = self.client.get(reverse("home"))
        self.assertContains(response, "S-999/2026")


class PublicChromeFinalTests(TestCase):
    def test_objectives_mobile_hero_structure(self):
        from pathlib import Path

        from django.conf import settings

        css = Path(settings.BASE_DIR, "static", "css", "pages-polish.css").read_text(
            encoding="utf-8"
        )
        self.assertIn("overflow-x: clip", css)
        self.assertNotIn("max-width: 20ch", css)
        self.assertIn(".legal-hero__title", css)
        self.assertIn("padding-inline: 1rem", css)
        self.assertIn("padding-inline: 1.25rem", css)
        self.assertIn("padding-block:", css)
        self.assertNotIn("padding: 1.65rem 0", css)
        self.assertNotIn("overflow-wrap: anywhere", css)

        self.client.post(reverse("set_language"), {"language": "en", "next": "/objectives/"})
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "en"
        en = self.client.get(reverse("objectives"))
        self.assertEqual(en.status_code, 200)
        self.assertContains(en, "legal-hero")
        self.assertContains(en, "legal-hero__title")
        self.assertContains(en, "legal-hero__inner")
        self.assertContains(en, "legal-breadcrumb")
        self.assertContains(en, "Objectives")

        self.client.post(reverse("set_language"), {"language": "bn", "next": "/objectives/"})
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "bn"
        bn = self.client.get(reverse("objectives"))
        self.assertContains(bn, "উদ্দেশ্যসমূহ")
        self.assertContains(bn, "legal-hero__title")

    def test_membership_bangla_public_chrome(self):
        from django.conf import settings

        self.client.post(reverse("set_language"), {"language": "en", "next": "/membership/"})
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "en"
        en = self.client.get(reverse("membership"))
        self.assertContains(en, "Become a Member")
        self.assertContains(en, "Check Application Status")
        self.assertContains(en, "Pay Membership Fee")
        self.assertContains(en, "Membership Requirements")
        self.assertContains(en, "Contact Admin")

        self.client.post(reverse("set_language"), {"language": "bn", "next": "/membership/"})
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "bn"
        bn = self.client.get(reverse("membership"))
        self.assertContains(bn, "সদস্যপদ")
        self.assertContains(bn, "সদস্য হোন")
        self.assertContains(bn, "আবেদনের অবস্থা দেখুন")
        self.assertContains(bn, "সদস্যপদ ফি পরিশোধ করুন")
        self.assertContains(bn, "সদস্যপদের যোগ্যতা")
        self.assertContains(bn, "প্রশাসনের সাথে যোগাযোগ করুন")
        self.assertNotContains(bn, "Become a Member")
        self.assertNotContains(bn, "Check Application Status")
        self.assertNotContains(bn, "Pay Membership Fee")
        self.assertNotContains(bn, "Membership Requirements")
        self.assertNotContains(bn, "Contact Admin")

    def test_contact_bangla_public_chrome(self):
        from django.conf import settings

        site = SiteSettings.load()
        site.primary_phone = "01711111111"
        site.primary_email = "info@zarrah.org"
        site.save()

        self.client.post(reverse("set_language"), {"language": "en", "next": "/contact/"})
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "en"
        en = self.client.get(reverse("contact"))
        self.assertContains(en, "Contact Us")
        self.assertContains(en, "Office Address")
        self.assertContains(en, "Holding No. NA-134")
        self.assertContains(en, "Send Message")
        self.assertContains(en, "Submit")
        self.assertNotContains(en, "হোল্ডিং নং এনএ-১৩৪")

        self.client.post(reverse("set_language"), {"language": "bn", "next": "/contact/"})
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "bn"
        bn = self.client.get(reverse("contact"))
        self.assertContains(bn, "যোগাযোগ")
        self.assertContains(bn, "যোগাযোগ করুন")
        self.assertContains(bn, "অফিসের ঠিকানা")
        self.assertContains(bn, "ফোন")
        self.assertContains(bn, "ইমেইল")
        self.assertContains(bn, "বার্তা পাঠান")
        self.assertContains(bn, "জমা দিন")
        self.assertContains(bn, "হোল্ডিং নং এনএ-১৩৪")
        self.assertNotContains(bn, "Office Address")
        self.assertNotContains(bn, "Send Message")
        self.assertNotContains(bn, "Contact Us")
        self.assertNotContains(bn, "Holding No. NA-134")
