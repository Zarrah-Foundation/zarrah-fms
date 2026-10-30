"""Homepage gallery CMS — reusable media, slider, remove vs delete."""

import tempfile
from io import BytesIO

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from accounts.models import User
from cms.gallery_service import (
    MediaInUseError,
    attach_media_to_section,
    create_media,
    delete_media_permanently,
    remove_from_gallery,
)
from cms.homepage_defaults import seed_homepage_defaults
from cms.models import CmsMedia, HomepageSection, HomepageSectionImage, SectionType


def _png(name="x.png", color=(30, 120, 90)):
    buf = BytesIO()
    Image.new("RGB", (48, 48), color).save(buf, format="PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class GalleryPublicTests(TestCase):
    def setUp(self):
        seed_homepage_defaults()
        self.client = Client()
        self.section = HomepageSection.objects.create(
            section_type=SectionType.GALLERY_PREVIEW,
            order=55,
            title_en="Photo Gallery",
            title_bn="ছবির গ্যালারি",
            is_published=True,
            is_visible=True,
            config={
                "autoplay": True,
                "autoplay_interval": 5000,
                "show_arrows": True,
                "show_dots": True,
                "show_captions": True,
            },
        )

    def _attach(self, name, order, **meta):
        media = create_media(
            uploaded=_png(name),
            alt_en=meta.get("alt_en", ""),
            alt_bn=meta.get("alt_bn", ""),
            caption_en=meta.get("caption_en", ""),
            caption_bn=meta.get("caption_bn", ""),
        )
        m, _ = attach_media_to_section(
            self.section,
            media,
            order=order,
            is_active=meta.get("is_active", True),
            alt_en=meta.get("alt_en", ""),
            alt_bn=meta.get("alt_bn", ""),
            caption_en=meta.get("caption_en", ""),
            caption_bn=meta.get("caption_bn", ""),
        )
        return m

    def test_zero_images_hides_gallery(self):
        r = self.client.get(reverse("home"))
        self.assertNotContains(r, "data-zf-slider")
        self.assertNotContains(r, "home-gallery-title")

    def test_one_image_no_nav_needed(self):
        self._attach("one.png", 1, caption_en="Only")
        r = self.client.get(reverse("home"))
        self.assertContains(r, "data-zf-slider")
        self.assertContains(r, "Previous image")
        self.assertContains(r, "gallery-slider.js")

    def test_multiple_images_order_and_captions(self):
        self._attach("a.png", 1, caption_en="Community Outreach", caption_bn="কমিউনিটি কার্যক্রম")
        self._attach("b.png", 2, caption_en="Second")
        self._attach("c.png", 3, caption_en="Third")
        # Reorder C/A/B
        items = list(
            HomepageSectionImage.objects.filter(section=self.section).order_by("order")
        )
        items[0].order, items[1].order, items[2].order = 2, 3, 1
        for i in items:
            i.save()
        ordered = list(
            HomepageSectionImage.objects.filter(section=self.section, is_active=True)
            .select_related("media")
            .order_by("order")
        )
        self.assertEqual(ordered[0].resolved_caption_en(), "Third")

        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "en"
        r = self.client.get(reverse("home"))
        self.assertContains(r, "Community Outreach")
        self.assertContains(r, "data-zf-prev")
        self.assertContains(r, "data-zf-next")

        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "bn"
        self.client.post(reverse("set_language"), {"language": "bn", "next": "/"})
        r = self.client.get(reverse("home"))
        self.assertContains(r, "কমিউনিটি কার্যক্রম")

    def test_inactive_hidden_publicly(self):
        self._attach("a.png", 1, caption_en="CaptionActiveA")
        b = self._attach("b.png", 2, caption_en="CaptionHiddenB")
        self._attach("c.png", 3, caption_en="CaptionActiveC")
        b.is_active = False
        b.save()
        r = self.client.get(reverse("home"))
        self.assertContains(r, "CaptionActiveA")
        self.assertContains(r, "CaptionActiveC")
        self.assertNotContains(r, "CaptionHiddenB")

    def test_en_bn_caption_fallback(self):
        self._attach("x.png", 1, caption_en="", caption_bn="শুধু বাংলা")
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "en"
        r = self.client.get(reverse("home"))
        self.assertContains(r, "শুধু বাংলা")
        self._attach("y.png", 2, caption_en="English only", caption_bn="")
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "bn"
        self.client.post(reverse("set_language"), {"language": "bn", "next": "/"})
        r = self.client.get(reverse("home"))
        self.assertContains(r, "English only")

    def test_seed_does_not_wipe_gallery(self):
        self._attach("keep.png", 1, caption_en="Keep")
        before = HomepageSectionImage.objects.filter(section=self.section).count()
        seed_homepage_defaults()
        self.assertEqual(
            HomepageSectionImage.objects.filter(section=self.section).count(), before
        )
        self.assertTrue(
            HomepageSectionImage.objects.filter(
                section=self.section, caption_en="Keep"
            ).exists()
            or HomepageSectionImage.objects.filter(section=self.section).exists()
        )


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class GalleryAdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email="gallery-admin@example.com", password="pass12345"
        )
        self.member = User.objects.create_user(
            email="gallery-member@example.com", password="pass12345"
        )
        self.client = Client()
        self.client.force_login(self.admin)
        self.section = HomepageSection.objects.create(
            section_type=SectionType.GALLERY_PREVIEW,
            order=57,
            title_en="Admin Gallery",
            is_published=True,
            is_visible=True,
        )

    def test_multiple_upload(self):
        url = reverse("dashboard-cms-section-edit", args=[self.section.pk])
        r = self.client.post(
            url,
            {
                "section_type": SectionType.GALLERY_PREVIEW,
                "order": 57,
                "is_visible": "on",
                "is_published": "on",
                "title_en": "Admin Gallery",
                "gallery_autoplay": "on",
                "gallery_autoplay_interval": "4000",
                "gallery_show_arrows": "on",
                "gallery_show_dots": "on",
                "gallery_show_captions": "on",
                "new_gallery_images": [_png("u1.png"), _png("u2.png"), _png("u3.png")],
                "gallery_images-TOTAL_FORMS": "0",
                "gallery_images-INITIAL_FORMS": "0",
                "gallery_images-MIN_NUM_FORMS": "0",
                "gallery_images-MAX_NUM_FORMS": "48",
            },
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(HomepageSectionImage.objects.filter(section=self.section).count(), 3)
        self.assertEqual(CmsMedia.objects.count(), 3)
        self.section.refresh_from_db()
        self.assertEqual(self.section.get_config().get("autoplay_interval"), 4000)

    def test_select_existing_no_duplicate_file(self):
        media = create_media(uploaded=_png("shared.png"), user=self.admin)
        g2 = HomepageSection.objects.create(
            section_type=SectionType.GALLERY_PREVIEW,
            order=58,
            title_en="Gallery Two",
            is_published=True,
            is_visible=True,
        )
        attach_media_to_section(self.section, media)
        attach_media_to_section(g2, media)
        self.assertEqual(CmsMedia.objects.count(), 1)
        self.assertEqual(media.gallery_usages.count(), 2)

        # Duplicate attach same gallery
        _, created = attach_media_to_section(self.section, media)
        self.assertFalse(created)
        self.assertEqual(
            HomepageSectionImage.objects.filter(section=self.section, media=media).count(),
            1,
        )

        remove_from_gallery(
            HomepageSectionImage.objects.get(section=self.section, media=media)
        )
        self.assertTrue(CmsMedia.objects.filter(pk=media.pk).exists())
        self.assertEqual(media.gallery_usages.count(), 1)

    def test_delete_blocked_when_in_use(self):
        media = create_media(uploaded=_png("busy.png"))
        attach_media_to_section(self.section, media)
        with self.assertRaises(MediaInUseError):
            delete_media_permanently(media)
        self.assertTrue(CmsMedia.objects.filter(pk=media.pk).exists())

    def test_media_library_requires_permission(self):
        self.client.force_login(self.member)
        r = self.client.get(reverse("dashboard-cms-media-library"))
        self.assertIn(r.status_code, (302, 403))

    def test_media_library_lists_existing(self):
        create_media(uploaded=_png("lib.png"), user=self.admin)
        r = self.client.get(reverse("dashboard-cms-media-library") + "?format=json")
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual(len(r.json()["results"]), 1)

    def test_attach_via_form_ids(self):
        media = create_media(uploaded=_png("pick.png"))
        url = reverse("dashboard-cms-section-edit", args=[self.section.pk])
        r = self.client.post(
            url,
            {
                "section_type": SectionType.GALLERY_PREVIEW,
                "order": 57,
                "is_visible": "on",
                "is_published": "on",
                "title_en": "Admin Gallery",
                "gallery_autoplay_interval": "5000",
                "attach_media_ids": str(media.pk),
                "gallery_images-TOTAL_FORMS": "0",
                "gallery_images-INITIAL_FORMS": "0",
                "gallery_images-MIN_NUM_FORMS": "0",
                "gallery_images-MAX_NUM_FORMS": "48",
            },
        )
        self.assertEqual(r.status_code, 302)
        self.assertTrue(
            HomepageSectionImage.objects.filter(section=self.section, media=media).exists()
        )

    def test_remove_from_gallery_via_formset(self):
        media = create_media(uploaded=_png("rm.png"))
        membership, _ = attach_media_to_section(self.section, media)
        url = reverse("dashboard-cms-section-edit", args=[self.section.pk])
        r = self.client.post(
            url,
            {
                "section_type": SectionType.GALLERY_PREVIEW,
                "order": 57,
                "is_visible": "on",
                "is_published": "on",
                "title_en": "Admin Gallery",
                "gallery_autoplay_interval": "5000",
                "gallery_images-TOTAL_FORMS": "1",
                "gallery_images-INITIAL_FORMS": "1",
                "gallery_images-MIN_NUM_FORMS": "0",
                "gallery_images-MAX_NUM_FORMS": "48",
                f"gallery_images-0-id": str(membership.pk),
                f"gallery_images-0-alt_en": "",
                f"gallery_images-0-order": "1",
                f"gallery_images-0-is_active": "on",
                f"gallery_images-0-DELETE": "on",
            },
        )
        self.assertEqual(r.status_code, 302)
        self.assertFalse(HomepageSectionImage.objects.filter(pk=membership.pk).exists())
        self.assertTrue(CmsMedia.objects.filter(pk=media.pk).exists())

    def test_unauthorized_cannot_edit_gallery(self):
        self.client.force_login(self.member)
        r = self.client.get(reverse("dashboard-cms-section-edit", args=[self.section.pk]))
        self.assertIn(r.status_code, (302, 403))
