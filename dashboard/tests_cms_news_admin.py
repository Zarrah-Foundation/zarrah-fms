"""Regression tests: type-aware Homepage CMS admin + News create/save."""

import tempfile
from io import BytesIO

from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from accounts.models import User
from cms.homepage_defaults import seed_homepage_defaults
from cms.home_content import split_mission_vision
from cms.models import HomepageSection, HomepageSectionImage, SectionType
from cms.section_meta import language_completeness, publish_status, section_meta
from dashboard.forms import HomepageSectionForm, NewsForm
from news.models import News
from pages.about_data import MISSION_VISION


def _png(name="x.png", size=(40, 40), color=(20, 120, 80)):
    buf = BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


class HomepageSectionFormTests(TestCase):
    def setUp(self):
        seed_homepage_defaults()

    def test_hero_form_fields(self):
        hero = HomepageSection.objects.get(section_type=SectionType.HERO, order=10)
        form = HomepageSectionForm(instance=hero, lock_section_type=True)
        self.assertIn("eyebrow_en", form.fields)
        self.assertIn("secondary_button_link", form.fields)
        self.assertIn("image", form.fields)
        self.assertNotIn("display_count", form.fields)
        self.assertNotIn("mission_content_en", form.fields)

    def test_mission_vision_form_fields_and_labels(self):
        mv = HomepageSection.objects.get(section_type=SectionType.MISSION_VISION, order=20)
        form = HomepageSectionForm(instance=mv, lock_section_type=True)
        self.assertIn("mission_content_en", form.fields)
        self.assertIn("mission_content_bn", form.fields)
        self.assertIn("vision_content_en", form.fields)
        self.assertIn("vision_content_bn", form.fields)
        self.assertEqual(form.fields["mission_title_bn"].initial, "আমাদের লক্ষ্য")
        self.assertEqual(form.fields["vision_title_bn"].initial, "সাংগঠনিক পরিচিতি")
        self.assertEqual(form.fields["mission_title_en"].initial, "Our Mission")
        self.assertEqual(form.fields["vision_title_en"].initial, "Organizational Nature")
        self.assertNotIn("image", form.fields)
        self.assertNotIn("secondary_button_link", form.fields)

    def test_mission_vision_pack_on_save(self):
        mv = HomepageSection.objects.get(section_type=SectionType.MISSION_VISION, order=20)
        form = HomepageSectionForm(
            data={
                "section_type": SectionType.MISSION_VISION,
                "order": mv.order,
                "is_visible": True,
                "is_published": True,
                "title_en": "Mission & Vision",
                "title_bn": "লক্ষ্য ও অভিলক্ষ্য",
                "mission_title_en": "Our Mission",
                "mission_title_bn": "আমাদের লক্ষ্য",
                "vision_title_en": "Our Vision",
                "vision_title_bn": "আমাদের অভিলক্ষ্য",
                "mission_content_en": "Mission EN body",
                "mission_content_bn": "Mission BN body",
                "vision_content_en": "Vision EN body",
                "vision_content_bn": "Vision BN body",
            },
            instance=mv,
            lock_section_type=True,
        )
        self.assertTrue(form.is_valid(), form.errors)
        obj = form.save()
        self.assertEqual(split_mission_vision(obj.content_en)[0], "Mission EN body")
        self.assertEqual(split_mission_vision(obj.content_bn)[1], "Vision BN body")
        self.assertEqual(obj.get_config()["mission_title_bn"], "আমাদের লক্ষ্য")

    def test_testimonials_presentation_only(self):
        sec = HomepageSection.objects.get(section_type=SectionType.TESTIMONIALS)
        form = HomepageSectionForm(instance=sec, lock_section_type=True)
        self.assertIn("display_count", form.fields)
        self.assertIn("title_en", form.fields)
        self.assertNotIn("image", form.fields)
        self.assertNotIn("button_link", form.fields)
        self.assertIn("Testimonials", str(section_meta(SectionType.TESTIMONIALS)["source_help"]))

    def test_partners_and_news_presentation(self):
        partners = HomepageSection.objects.get(section_type=SectionType.PARTNERS)
        news = HomepageSection.objects.get(section_type=SectionType.NEWS_GRID)
        pf = HomepageSectionForm(instance=partners, lock_section_type=True)
        nf = HomepageSectionForm(instance=news, lock_section_type=True)
        self.assertIn("display_count", pf.fields)
        self.assertNotIn("image", pf.fields)
        self.assertIn("display_count", nf.fields)
        self.assertIn("button_link", nf.fields)

    def test_gallery_editor_profile(self):
        sec = HomepageSection.objects.create(
            section_type=SectionType.GALLERY_PREVIEW,
            order=55,
            title_en="Gallery",
            is_published=True,
            is_visible=True,
        )
        form = HomepageSectionForm(instance=sec, lock_section_type=True)
        self.assertEqual(form.editor_key, "gallery")
        self.assertNotIn("button_link", form.fields)

    def test_about_data_mission_vision_terminology(self):
        self.assertEqual(MISSION_VISION["mission"]["title_bn"], "আমাদের লক্ষ্য")
        self.assertEqual(MISSION_VISION["vision"]["title_bn"], "সাংগঠনিক পরিচিতি")
        self.assertEqual(MISSION_VISION["mission"]["title_en"], "Our Mission")
        self.assertEqual(MISSION_VISION["vision"]["title_en"], "Organizational Nature")


class HomepageCmsAdminViewTests(TestCase):
    def setUp(self):
        seed_homepage_defaults()
        self.admin = User.objects.create_superuser(
            email="cms-admin@example.com", password="pass12345"
        )
        self.client = Client()
        self.client.force_login(self.admin)

    def test_list_shows_status_and_source(self):
        r = self.client.get(reverse("dashboard-cms-homepage"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Published")
        self.assertContains(r, "DATA-DRIVEN")
        self.assertContains(r, "Edit presentation")

    def test_edit_hero_hides_irrelevant_fields(self):
        hero = HomepageSection.objects.get(section_type=SectionType.HERO, order=10)
        r = self.client.get(reverse("dashboard-cms-section-edit", args=[hero.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Hero copy")
        self.assertContains(r, "name=\"eyebrow_en\"")
        self.assertNotContains(r, "name=\"display_count\"")

    def test_publish_status_helper(self):
        hero = HomepageSection.objects.get(section_type=SectionType.HERO, order=10)
        self.assertEqual(publish_status(hero), "published")
        hero.is_published = False
        self.assertEqual(publish_status(hero), "draft")
        hero.is_visible = False
        self.assertEqual(publish_status(hero), "disabled")
        langs = language_completeness(hero)
        self.assertTrue(langs["en"])

    def test_seed_idempotent_and_preserves_edits(self):
        hero = HomepageSection.objects.get(section_type=SectionType.HERO, order=10)
        hero.title_en = "Custom Hero"
        hero.is_published = False
        hero.save()
        before = HomepageSection.objects.filter(is_deleted=False).count()
        seed_homepage_defaults()
        self.assertEqual(HomepageSection.objects.filter(is_deleted=False).count(), before)
        hero.refresh_from_db()
        self.assertEqual(hero.title_en, "Custom Hero")
        self.assertFalse(hero.is_published)

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_gallery_image_upload_persists(self):
        sec = HomepageSection.objects.create(
            section_type=SectionType.GALLERY_PREVIEW,
            order=56,
            title_en="Photos",
            is_published=True,
            is_visible=True,
        )
        url = reverse("dashboard-cms-section-edit", args=[sec.pk])
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Gallery Manager")
        data = {
            "section_type": SectionType.GALLERY_PREVIEW,
            "order": 56,
            "is_visible": "on",
            "is_published": "on",
            "title_en": "Photos",
            "title_bn": "",
            "content_en": "",
            "content_bn": "",
            "gallery_autoplay": "on",
            "gallery_autoplay_interval": "5000",
            "gallery_show_arrows": "on",
            "gallery_show_dots": "on",
            "gallery_show_captions": "on",
            "attach_media_ids": "",
            "new_gallery_images": _png("g1.png"),
            "gallery_images-TOTAL_FORMS": "0",
            "gallery_images-INITIAL_FORMS": "0",
            "gallery_images-MIN_NUM_FORMS": "0",
            "gallery_images-MAX_NUM_FORMS": "48",
        }
        r = self.client.post(url, data, follow=False)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(HomepageSectionImage.objects.filter(section=sec).count(), 1)
        home = self.client.get(reverse("home"))
        self.assertContains(home, "home-gallery-title")
        self.assertContains(home, "data-zf-slider")


class NewsAdminSaveTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email="news-admin@example.com", password="pass12345"
        )
        self.member = User.objects.create_user(
            email="member@example.com", password="pass12345"
        )
        self.client = Client()

    def test_news_create_get(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse("dashboard-news-create"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "novalidate")
        self.assertContains(r, "js-richtext")
        self.assertContains(r, "name=\"title_bn\"")
        self.assertContains(r, "name=\"content_bn\"")

    def test_news_create_post_valid(self):
        self.client.force_login(self.admin)
        r = self.client.post(
            reverse("dashboard-news-create"),
            {
                "title": "Test Article EN",
                "title_bn": "পরীক্ষা নিবন্ধ",
                "slug": "",
                "excerpt": "Short",
                "excerpt_bn": "সংক্ষিপ্ত",
                "content": "<p>Hello <strong>world</strong></p>",
                "content_bn": "<p>বাংলা লেখা</p>",
                "is_published": "on",
            },
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, reverse("dashboard-news"))
        article = News.objects.get(title="Test Article EN")
        self.assertEqual(article.title_bn, "পরীক্ষা নিবন্ধ")
        self.assertIn("Hello", article.content)
        self.assertIn("বাংলা", article.content_bn)
        self.assertTrue(article.is_published)
        self.assertTrue(article.slug)
        msgs = [m.message for m in get_messages(r.wsgi_request)]
        self.assertTrue(any("Created" in m or "created" in m.lower() for m in msgs))

    def test_news_create_post_invalid_missing_title(self):
        self.client.force_login(self.admin)
        r = self.client.post(
            reverse("dashboard-news-create"),
            {"title": "", "content": "<p>x</p>"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(News.objects.count(), 0)
        self.assertContains(r, "form-error")

    def test_news_sanitization_still_active(self):
        form = NewsForm(
            data={
                "title": "Safe",
                "slug": "safe",
                "content": '<p>Hi</p><script>alert(1)</script>',
                "content_bn": '<p>BN</p><script>x</script>',
                "is_published": False,
            }
        )
        form.instance.author = self.admin
        self.assertTrue(form.is_valid(), form.errors)
        self.assertNotIn("<script>", form.cleaned_data["content"])
        self.assertNotIn("<script>", form.cleaned_data["content_bn"])

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_featured_image_upload_and_public(self):
        self.client.force_login(self.admin)
        r = self.client.post(
            reverse("dashboard-news-create"),
            {
                "title": "With Image",
                "title_bn": "ছবিসহ",
                "content": "<p>Body</p>",
                "content_bn": "<p>বডি</p>",
                "is_published": "on",
                "featured_image": _png("feat.png"),
            },
        )
        self.assertEqual(r.status_code, 302)
        article = News.objects.get(title="With Image")
        self.assertTrue(article.featured_image)
        from django.conf import settings

        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "en"
        pub = self.client.get(reverse("news-detail", kwargs={"slug": article.slug}))
        self.assertEqual(pub.status_code, 200)
        self.assertContains(pub, "With Image")
        self.assertTrue(bool(article.featured_image.name))

    def test_published_on_homepage_news(self):
        seed_homepage_defaults()
        self.client.force_login(self.admin)
        self.client.post(
            reverse("dashboard-news-create"),
            {
                "title": "Homepage News Item",
                "content": "<p>Body</p>",
                "is_published": "on",
            },
        )
        r = self.client.get(reverse("home"))
        self.assertContains(r, "Homepage News Item")
        self.assertContains(r, "home-news-title")

    def test_permission_denied_for_unauthorized(self):
        self.client.force_login(self.member)
        r = self.client.get(reverse("dashboard-news-create"))
        self.assertIn(r.status_code, (302, 403))
        self.assertEqual(News.objects.count(), 0)

    def test_form_template_has_save_button_and_novalidate(self):
        """Regression: Save must POST; novalidate avoids TinyMCE/required trap."""
        self.client.force_login(self.admin)
        r = self.client.get(reverse("dashboard-news-create"))
        self.assertContains(r, 'type="submit"')
        self.assertContains(r, "novalidate")
        self.assertContains(r, "tinymce.triggerSave")

    def test_bangla_only_title_still_gets_slug(self):
        """slugify(Bangla) is empty — form must still produce a unique slug."""
        form = NewsForm(
            data={
                "title": "বাংলা শিরোনাম",
                "slug": "",
                "content": "<p>x</p>",
            }
        )
        form.instance.author = self.admin
        self.assertTrue(form.is_valid(), form.errors)
        self.assertTrue(form.cleaned_data["slug"])


class MissionVisionPublicTerminologyTests(TestCase):
    def setUp(self):
        seed_homepage_defaults()
        self.client = Client()

    def test_en_mission_vision_labels(self):
        from django.conf import settings

        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "en"
        r = self.client.get(reverse("home"))
        self.assertContains(r, "Our Mission")
        self.assertContains(r, "Organizational Nature")

    def test_bn_mission_vision_labels(self):
        from django.conf import settings

        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "bn"
        self.client.post(reverse("set_language"), {"language": "bn", "next": "/"})
        r = self.client.get(reverse("home"))
        self.assertContains(r, "আমাদের লক্ষ্য")
        self.assertContains(r, "সাংগঠনিক পরিচিতি")
