"""Homepage experience tests — CMS architecture, visibility, bilingual, no empty blocks."""

from django.conf import settings
from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from accounts.models import User
from cms.homepage_defaults import DEFAULT_SECTIONS, seed_homepage_defaults
from cms.models import HomepageSection, SectionType
from community.models import LeadershipPerson, LeadershipRole, Partner, Testimonial
from news.models import News


class HomepageExperienceTests(TestCase):
    def setUp(self):
        seed_homepage_defaults()
        self.client = Client()

    def _set_lang(self, code):
        """LocaleMiddleware reads language from cookie/session — not translation.override()."""
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = code
        self.client.post(reverse("set_language"), {"language": code, "next": "/"})

    def test_homepage_200(self):
        r = self.client.get(reverse("home"))
        self.assertEqual(r.status_code, 200)

    def test_core_seeded_sections_render(self):
        self._set_lang("en")
        r = self.client.get(reverse("home"))
        self.assertContains(r, "zf-hero")
        self.assertContains(r, "zf-trust")
        self.assertContains(r, "home-mv-title")
        self.assertContains(r, "zf-approach")
        self.assertContains(r, "home-focus-title")
        self.assertContains(r, "home-transparency-title")
        self.assertContains(r, "Membership")
        self.assertContains(r, "Donate")

    def test_admin_edits_survive_reseed(self):
        hero = HomepageSection.objects.get(section_type=SectionType.HERO, order=10)
        hero.title_en = "Custom Hero Edit"
        hero.is_published = False
        hero.save()
        seed_homepage_defaults()
        hero.refresh_from_db()
        self.assertEqual(hero.title_en, "Custom Hero Edit")
        self.assertFalse(hero.is_published)

    def test_unpublished_section_not_rendered(self):
        HomepageSection.objects.filter(section_type=SectionType.APPROACH).update(
            is_published=False
        )
        r = self.client.get(reverse("home"))
        self.assertNotContains(r, "zf-approach")

    def test_empty_testimonials_hidden(self):
        Testimonial.objects.all().delete()
        r = self.client.get(reverse("home"))
        self.assertNotContains(r, "home-testimonials-title")

    def test_published_testimonials_render(self):
        Testimonial.objects.create(
            author_name="IMROZ AHMAD",
            designation="Secretary",
            content_en="A verified public statement.",
            is_published=True,
        )
        r = self.client.get(reverse("home"))
        self.assertContains(r, "IMROZ AHMAD")
        self.assertContains(r, "home-testimonials-title")

    def test_empty_quote_not_rendered(self):
        Testimonial.objects.all().delete()
        Testimonial.objects.create(
            author_name="Empty",
            content_en="   ",
            content_bn="",
            is_published=True,
        )
        r = self.client.get(reverse("home"))
        self.assertNotContains(r, "home-testimonials-title")
        self.assertNotContains(r, "Empty")

    def test_active_partners_render_inactive_hidden(self):
        Partner.objects.create(name="Active Partner Co", is_active=True, display_order=1)
        Partner.objects.create(name="Inactive Partner Co", is_active=False, display_order=2)
        r = self.client.get(reverse("home"))
        self.assertContains(r, "Active Partner Co")
        self.assertNotContains(r, "Inactive Partner Co")

    def test_no_partners_hides_section(self):
        Partner.objects.all().delete()
        r = self.client.get(reverse("home"))
        self.assertNotContains(r, "home-partners-title")

    def test_published_news_renders_and_empty_hides(self):
        author = User.objects.create_user(email="ed@example.com", password="x")
        News.objects.create(
            title="Foundation Update",
            slug="foundation-update",
            content="<p>Hello</p>",
            excerpt="Short excerpt",
            is_published=True,
            author=author,
        )
        r = self.client.get(reverse("home"))
        self.assertContains(r, "Foundation Update")
        self.assertContains(r, "home-news-title")
        News.objects.all().delete()
        r = self.client.get(reverse("home"))
        self.assertNotContains(r, "home-news-title")

    def test_leadership_section_requires_people(self):
        LeadershipPerson.objects.all().delete()
        r = self.client.get(reverse("home"))
        self.assertNotContains(r, "home-leadership-title")
        LeadershipPerson.objects.create(
            role=LeadershipRole.CHAIRMAN,
            name="MD. BABUL HOSSAIN",
            role_label_en="Chairman",
            role_label_bn="চেয়ারম্যান",
            bio_en="Strategic leadership.",
            is_published=True,
        )
        r = self.client.get(reverse("home"))
        self.assertContains(r, "home-leadership-title")
        self.assertContains(r, "MD. BABUL HOSSAIN")

    def test_transparency_membership_donation_ctas(self):
        r = self.client.get(reverse("home"))
        self.assertContains(r, reverse("transparency"))
        self.assertContains(r, reverse("membership-apply"))
        self.assertContains(r, reverse("membership-status"))
        self.assertContains(r, reverse("donation"))

    def test_english_and_bangla_render(self):
        self._set_lang("en")
        r = self.client.get(reverse("home"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Small Acts, Lasting Impact")
        self._set_lang("bn")
        r = self.client.get(reverse("home"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "ক্ষুদ্র অবদান")

    def test_language_switch_preserves_home_route(self):
        r = self.client.post(reverse("set_language"), {"language": "en", "next": "/"})
        self.assertIn(r.status_code, (200, 302))
        if r.status_code == 302:
            self.assertEqual(r.url, "/")

    def test_bilingual_fallback_mission_vision(self):
        mv = HomepageSection.objects.get(section_type=SectionType.MISSION_VISION, order=20)
        mv.content_bn = ""
        mv.save()
        self._set_lang("bn")
        r = self.client.get(reverse("home"))
        self.assertEqual(r.status_code, 200)
        # BN empty → fallback to English CMS mission text
        self.assertContains(r, "helpless")

    def test_seed_idempotent_count(self):
        first = HomepageSection.objects.filter(is_deleted=False).count()
        seed_homepage_defaults()
        self.assertEqual(HomepageSection.objects.filter(is_deleted=False).count(), first)
        self.assertGreaterEqual(first, len(DEFAULT_SECTIONS) - 1)

    def test_homepage_query_budget(self):
        LeadershipPerson.objects.create(
            role=LeadershipRole.SECRETARY,
            name="IMROZ AHMAD",
            role_label_en="Secretary",
            is_published=True,
        )
        Partner.objects.create(name="Partner A", is_active=True)
        author = User.objects.create_user(email="n@example.com", password="x")
        News.objects.create(
            title="N1",
            slug="n1",
            content="c",
            is_published=True,
            author=author,
        )
        with CaptureQueriesContext(connection) as ctx:
            r = self.client.get(reverse("home"))
            self.assertEqual(r.status_code, 200)
        self.assertLessEqual(
            len(ctx),
            30,
            "Homepage query count too high: %s" % [q["sql"][:80] for q in ctx],
        )
