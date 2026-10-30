"""Public content authenticity: slogan, cadence, skills, stats, supporters."""

from django.conf import settings
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import User
from cms.homepage_defaults import seed_homepage_defaults
from cms.models import HomepageSection, ImpactStatistic, SectionType
from community.models import LeadershipPerson, LeadershipRole, Partner, Testimonial
from news.models import News


class ContentAuthenticityTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_superuser(
            email="seed-admin@example.com", password="pass12345"
        )
        seed_homepage_defaults()
        self.client = Client()

    def _en(self, path="/"):
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "en"
        self.client.post(reverse("set_language"), {"language": "en", "next": path})
        return self.client.get(path)

    def _bn(self, path="/"):
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "bn"
        self.client.post(reverse("set_language"), {"language": "bn", "next": path})
        return self.client.get(path)

    def test_official_slogan_en_bn(self):
        r = self._en("/")
        self.assertContains(r, "Small Acts, Lasting Impact")
        self.assertNotContains(r, "From the atom, For the Helpless.")
        r = self._bn("/")
        self.assertContains(r, "ক্ষুদ্র অবদান, দীর্ঘস্থায়ী প্রভাব")
        self.assertNotContains(r, "ক্ষুদ্র কাজ, স্থায়ী প্রভাব")

    def test_meeting_cadence_not_monthly(self):
        r = self._en("/about/")
        self.assertContains(r, "at least once every three months")
        self.assertContains(r, "at least once annually")
        self.assertNotContains(r, "shall meet monthly")
        self.assertContains(r, "Advisory Council")
        self.assertContains(r, "Executive Council")
        self.assertContains(r, "General Council")
        self.assertNotContains(r, "Advisory Board")
        self.assertNotContains(r, "Executive Committee")

    def test_leadership_chairman_and_secretary_visible(self):
        self.assertTrue(
            LeadershipPerson.objects.filter(
                role=LeadershipRole.CHAIRMAN, is_published=True
            ).exists()
        )
        self.assertTrue(
            LeadershipPerson.objects.filter(
                role=LeadershipRole.SECRETARY, is_published=True
            ).exists()
        )
        r = self._en("/about/")
        self.assertContains(r, "MD. BABUL HOSSAIN")
        self.assertContains(r, "IMROZ AHMAD")
        home = self._en("/")
        self.assertContains(home, "MD. BABUL HOSSAIN")

    def test_zarrah_skills_link(self):
        r = self._en("/")
        self.assertContains(r, "https://skills.zarrah.org/")
        self.assertContains(r, "Zarrah Skills")
        about = self._en("/about/")
        self.assertContains(about, "Skills, training and learning portal")
        self.assertContains(about, 'target="_blank"')

    def test_skills_news_published_and_qa_news_hidden(self):
        News.objects.create(
            title="Test",
            slug="test-qa",
            content="demo",
            is_published=True,
            author=self.author,
        )
        News.objects.create(
            title="Manual QA Article",
            slug="manual-qa-article-2",
            content="demo",
            is_published=True,
            author=self.author,
        )
        seed_homepage_defaults()
        self.assertTrue(
            News.objects.filter(slug="zarrah-skills-portal", is_published=True).exists()
        )
        self.assertFalse(News.objects.filter(title="Test", is_published=True).exists())
        self.assertFalse(
            News.objects.filter(title="Manual QA Article", is_published=True).exists()
        )
        r = self._en("/")
        self.assertContains(r, "Zarrah Skills portal")
        self.assertNotContains(r, "Manual QA Article")

    def test_empty_testimonials_hidden(self):
        Testimonial.objects.all().delete()
        r = self._en("/")
        self.assertNotContains(r, "home-testimonials-title")

    def test_empty_quote_not_shown(self):
        Testimonial.objects.all().delete()
        Testimonial.objects.create(
            author_name="Chairman",
            designation="Chairman",
            content_en="  ",
            is_published=True,
        )
        r = self._en("/")
        self.assertNotContains(r, "home-testimonials-title")

    def test_partner_relationship_type_displayed(self):
        self.assertTrue(Partner.objects.filter(name="Goodstack", is_active=True).exists())
        self.assertTrue(
            Partner.objects.filter(name="Ahmad Solution Ltd", is_active=True).exists()
        )
        r = self._en("/")
        self.assertContains(r, "Technology Supporters")
        self.assertContains(r, "Goodstack")
        self.assertContains(r, "Nonprofit eligibility platform")
        self.assertContains(r, "Ahmad Solution Ltd")
        self.assertNotContains(r, "strategic partnership")
        self.assertNotContains(r, "my company")
        self.assertContains(r, "zf-supporter-card__name")
        self.assertContains(r, "zf-supporter-card__mark")
        self.assertNotContains(r, 'href=""')

    def test_impact_stats_hidden_by_default(self):
        self.assertFalse(ImpactStatistic.objects.filter(is_published=True).exists())
        r = self._en("/")
        self.assertNotContains(r, "home-impact-title")
        self.assertNotContains(r, "10,000+")
        self.assertNotContains(r, "500+ volunteers")

    def test_impact_stats_show_when_published(self):
        HomepageSection.objects.filter(section_type=SectionType.IMPACT_STATS).update(
            is_published=True, is_visible=True, title_en="Impact Statistics"
        )
        ImpactStatistic.objects.create(
            value="12",
            label_en="Registered members",
            label_bn="নিবন্ধিত সদস্য",
            is_published=True,
            display_order=1,
        )
        r = self._en("/")
        self.assertContains(r, "home-impact-title")
        self.assertContains(r, "Registered members")
        self.assertContains(r, "12")

    def test_impact_stats_unpublished_item_hidden(self):
        HomepageSection.objects.filter(section_type=SectionType.IMPACT_STATS).update(
            is_published=True, is_visible=True, title_en="Impact Statistics"
        )
        ImpactStatistic.objects.create(
            value="99",
            label_en="Draft only",
            is_published=False,
        )
        r = self._en("/")
        self.assertNotContains(r, "Draft only")
        self.assertNotContains(r, "home-impact-title")

    def test_impact_stats_section_hide_overrides_published_items(self):
        HomepageSection.objects.filter(section_type=SectionType.IMPACT_STATS).update(
            is_published=False, is_visible=True, title_en="Impact Statistics"
        )
        ImpactStatistic.objects.create(
            value="12",
            label_en="Registered members",
            is_published=True,
        )
        r = self._en("/")
        self.assertNotContains(r, "home-impact-title")
        self.assertNotContains(r, "Registered members")

    def test_financial_summaries_visible_when_published(self):
        from finance.models import FinancialSummary, MonthlyFinancialSummary

        FinancialSummary.objects.create(
            year=2099,
            total_income=285,
            total_expense=0,
            net_balance=285,
            is_published=True,
        )
        MonthlyFinancialSummary.objects.create(
            year=2099,
            month=8,
            total_income=285,
            total_expense=0,
            net_balance=285,
            is_published=True,
        )
        home = self._en("/")
        self.assertContains(home, "Financial summaries are published periodically")
        self.assertContains(home, "2099")
        transparency = self._en("/transparency/")
        self.assertContains(transparency, "285")
        self.assertContains(transparency, "2099-08")
        self.assertContains(transparency, "organizational summaries, not audited reports")

    def test_objectives_and_about_routes(self):
        about = self._en("/about/")
        self.assertContains(about, "Skills")
        self.assertContains(about, "MD. BABUL HOSSAIN")
        objectives = self._en("/objectives/")
        self.assertContains(objectives, "Humanitarian Assistance")
        constitution = self._en("/constitution/")
        self.assertContains(constitution, "Executive Council Structure")
        self.assertNotContains(constitution, "Executive Committee Structure")

    def test_contact_identity(self):
        r = self._en("/contact/")
        self.assertContains(r, "Sakhipur")
        self.assertContains(r, "Tangail")
        self.assertContains(r, "Zarrah Foundation")

    def test_language_switch_home(self):
        r = self.client.post(reverse("set_language"), {"language": "bn", "next": "/"})
        self.assertIn(r.status_code, (200, 302))


class ImpactStatsAdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email="stats-admin@example.com", password="pass12345"
        )
        self.client = Client()
        self.client.force_login(self.admin)

    def test_crud_create_and_list(self):
        r = self.client.get(reverse("dashboard-impact-stats"))
        self.assertEqual(r.status_code, 200)
        r = self.client.post(
            reverse("dashboard-impact-stat-create"),
            {
                "value": "3",
                "label_en": "Published programs",
                "label_bn": "প্রকাশিত কর্মসূচি",
                "description_en": "",
                "description_bn": "",
                "display_order": 1,
                "is_published": "on",
            },
        )
        self.assertEqual(r.status_code, 302)
        obj = ImpactStatistic.objects.get(label_en="Published programs")
        self.assertEqual(obj.value, "3")
        self.assertTrue(obj.is_published)
        edit = self.client.get(reverse("dashboard-impact-stat-edit", args=[obj.pk]))
        self.assertEqual(edit.status_code, 200)
        self.client.post(reverse("dashboard-impact-stat-delete", args=[obj.pk]), {})
        self.assertFalse(ImpactStatistic.objects.filter(pk=obj.pk).exists())
