from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from cms.homepage_defaults import DEFAULT_SECTIONS, seed_homepage_defaults
from cms.models import HomepageSection, SectionType
from community.models import Testimonial


class HomepageSeedTests(TestCase):
    def test_seed_creates_defaults(self):
        result = seed_homepage_defaults()
        self.assertGreaterEqual(result["created_sections"], 1)
        self.assertTrue(
            HomepageSection.objects.filter(
                section_type=SectionType.HERO, order=10, is_published=True
            ).exists()
        )
        self.assertFalse(Testimonial.objects.filter(is_published=True).exists())

    def test_seed_is_idempotent(self):
        seed_homepage_defaults()
        count = HomepageSection.objects.count()
        result = seed_homepage_defaults()
        self.assertEqual(result["created_sections"], 0)
        self.assertEqual(HomepageSection.objects.count(), count)

    def test_seed_does_not_overwrite_customized_content(self):
        seed_homepage_defaults()
        hero = HomepageSection.objects.get(section_type=SectionType.HERO, order=10)
        hero.title_en = "Custom Hero Title"
        hero.content_en = "Admin edited copy"
        hero.is_published = False
        hero.save()
        seed_homepage_defaults()
        hero.refresh_from_db()
        self.assertEqual(hero.title_en, "Custom Hero Title")
        self.assertEqual(hero.content_en, "Admin edited copy")
        self.assertFalse(hero.is_published)

    def test_management_command(self):
        call_command("seed_homepage_defaults")
        self.assertEqual(
            HomepageSection.objects.filter(is_deleted=False).count(),
            len(DEFAULT_SECTIONS),
        )

    def test_home_renders_seeded_sections(self):
        seed_homepage_defaults()
        response = Client().get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Zarrah Foundation")
        # Empty/unpublished testimonials must not invent placeholder cards.
        Testimonial.objects.all().update(content_en="", content_bn="", is_published=True)
        response = Client().get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    def test_seed_refreshes_leftover_marketing_copy(self):
        seed_homepage_defaults()
        hero = HomepageSection.objects.get(section_type=SectionType.HERO, order=10)
        hero.title_en = "Small Acts, Lasting Impact"
        hero.content_en = (
            "Zarrah Foundation is a registered nonprofit committed to empowering "
            "communities through education, healthcare, humanitarian assistance."
        )
        hero.save()
        mv = HomepageSection.objects.get(section_type=SectionType.MISSION_VISION, order=20)
        mv.content_en = (
            "To serve humanity through education, healthcare.\n---\n"
            "To become one of the most trusted nonprofit organizations."
        )
        mv.save()
        result = seed_homepage_defaults()
        self.assertGreaterEqual(result["refreshed_sections"], 1)
        hero.refresh_from_db()
        mv.refresh_from_db()
        self.assertIn("voluntary, non-profit, non-political", hero.content_en)
        self.assertNotIn("most trusted nonprofit", mv.content_en)
        self.assertNotIn("empowering communities through education", hero.content_en)

    def test_unpublished_section_not_on_home(self):
        seed_homepage_defaults()
        HomepageSection.objects.filter(section_type=SectionType.HERO, order=10).update(
            is_published=False
        )
        response = Client().get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        # Other defaults still publish; hero custom title path unused.
        self.assertFalse(
            HomepageSection.objects.filter(
                section_type=SectionType.HERO, is_published=True, is_visible=True
            ).exists()
        )
