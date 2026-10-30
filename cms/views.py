from django.db.models import Prefetch
from django.utils.translation import get_language
from django.views.generic import TemplateView

from cms.home_content import (
    DATA_DRIVEN_SECTION_TYPES,
    default_mission_vision_pair,
    focus_areas,
    split_mission_vision,
)
from cms.models import HomepageSection, HomepageSectionImage, ImpactStatistic, SectionType
from cms.section_meta import display_count_from_config
from community.models import LeadershipPerson, Partner, Testimonial
from finance.models import FinancialSummary, MonthlyFinancialSummary
from news.models import News


class _SyntheticSection:
    """In-memory section so testimonials/partners/news render even without CMS rows."""

    def __init__(self, section_type, title_en, title_bn="", order=9000, content_en="", content_bn=""):
        self.section_type = section_type
        self.order = order
        self.is_visible = True
        self.is_published = True
        self.is_deleted = False
        self.title_en = title_en
        self.title_bn = title_bn
        self.content_en = content_en
        self.content_bn = content_bn
        self.image = None
        self.button_text_en = ""
        self.button_text_bn = ""
        self.button_link = ""
        self.config = {}
        self.pk = None

    def get_config(self):
        return self.config if isinstance(self.config, dict) else {}

    @property
    def template_name(self):
        return f"cms/sections/{self.section_type.lower()}.html"


def _section_title(section, field="title"):
    lang = get_language() or "en"
    if lang.startswith("bn"):
        primary = getattr(section, f"{field}_bn", None) or ""
        secondary = getattr(section, f"{field}_en", None) or ""
    else:
        primary = getattr(section, f"{field}_en", None) or ""
        secondary = getattr(section, f"{field}_bn", None) or ""
    return (primary or secondary or "").strip()


def _mission_vision_for_section(section):
    mission_en, mission_bn, vision_en, vision_bn = default_mission_vision_pair()
    en_m, en_v = split_mission_vision(section.content_en)
    bn_m, bn_v = split_mission_vision(section.content_bn)
    # Prefer CMS language → other CMS language → approved about_data defaults.
    return {
        "mission_en": en_m or bn_m or mission_en,
        "mission_bn": bn_m or en_m or mission_bn,
        "vision_en": en_v or bn_v or vision_en,
        "vision_bn": bn_v or en_v or vision_bn,
    }


def _config_for(section):
    if hasattr(section, "get_config"):
        return section.get_config()
    return getattr(section, "config", None) or {}


class HomeView(TemplateView):
    template_name = "cms/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        gallery_qs = (
            HomepageSectionImage.objects.filter(is_active=True)
            .select_related("media")
            .order_by("order", "created_at")
        )
        sections = list(
            HomepageSection.objects.filter(
                is_deleted=False, is_published=True, is_visible=True
            )
            .prefetch_related(Prefetch("gallery_images", queryset=gallery_qs))
            .order_by("order")
        )

        def _limit_for(section_type, default):
            for s in sections:
                if s.section_type == section_type:
                    return display_count_from_config(_config_for(s), default)
            return default

        testimonial_limit = _limit_for(SectionType.TESTIMONIALS, 8)
        partner_limit = _limit_for(SectionType.PARTNERS, 16)
        news_limit = _limit_for(SectionType.NEWS_GRID, 3)
        leadership_limit = _limit_for(SectionType.LEADERSHIP, 6)

        testimonials = list(
            Testimonial.objects.filter(is_published=True).order_by(
                "display_order", "-created_at"
            )[: max(testimonial_limit, 16)]
        )
        ctx["home_testimonials"] = [
            t
            for t in testimonials
            if (t.content_en or "").strip() or (t.content_bn or "").strip()
        ][:testimonial_limit]

        ctx["home_partners"] = [
            p
            for p in Partner.objects.filter(is_active=True).order_by(
                "display_order", "name"
            )[: max(partner_limit, 24)]
            if (p.name or "").strip()
        ][:partner_limit]
        ctx["home_news"] = list(
            News.objects.filter(is_published=True)
            .select_related("category")
            .order_by("-published_at", "-created_at")[:news_limit]
        )
        leaders = list(
            LeadershipPerson.objects.filter(is_published=True).order_by(
                "display_order", "role", "name"
            )[:leadership_limit]
        )
        ctx["home_leadership"] = [p.as_card_dict() for p in leaders]
        ctx["home_focus_areas"] = focus_areas()
        ctx["home_impact_stats"] = list(
            ImpactStatistic.objects.filter(is_published=True).order_by(
                "display_order", "created_at"
            )
        )
        ctx["home_yearly_summaries"] = list(
            FinancialSummary.objects.filter(is_published=True).order_by("-year")[:3]
        )
        ctx["home_monthly_summaries"] = list(
            MonthlyFinancialSummary.objects.filter(is_published=True).order_by(
                "-year", "-month"
            )[:6]
        )

        present_types = {s.section_type for s in sections}

        # Synthesize chrome for data-driven sections when CMS row is missing.
        if ctx["home_testimonials"] and SectionType.TESTIMONIALS not in present_types:
            sections.append(
                _SyntheticSection(
                    SectionType.TESTIMONIALS,
                    title_en="Voices from Our Community",
                    title_bn="আমাদের সম্প্রদায়ের কণ্ঠস্বর",
                    order=8500,
                )
            )
        if ctx["home_partners"] and SectionType.PARTNERS not in present_types:
            sections.append(
                _SyntheticSection(
                    SectionType.PARTNERS,
                    title_en="Partners & Technology Supporters",
                    title_bn="অংশীদার ও প্রযুক্তি সহায়ক",
                    order=8600,
                    content_en=(
                        "Organizations and platforms supporting Zarrah Foundation's work."
                    ),
                    content_bn="জার্‌রাহ ফাউন্ডেশনের কাজকে সহায়তা করা সংস্থা ও প্ল্যাটফর্ম।",
                )
            )
        if ctx["home_news"] and SectionType.NEWS_GRID not in present_types:
            sections.append(
                _SyntheticSection(
                    SectionType.NEWS_GRID,
                    title_en="News",
                    title_bn="সংবাদ",
                    order=8700,
                )
            )
        if ctx["home_leadership"] and SectionType.LEADERSHIP not in present_types:
            sections.append(
                _SyntheticSection(
                    SectionType.LEADERSHIP,
                    title_en="Leadership",
                    title_bn="নেতৃত্ব",
                    order=8400,
                )
            )

        has_leadership_section = any(
            s.section_type == SectionType.LEADERSHIP for s in sections
        )

        legacy_optional = {
            SectionType.FEATURED_CAMPAIGN,
            SectionType.GALLERY_PREVIEW,
            SectionType.VOLUNTEER_CTA,
        }

        visible = []
        for section in sections:
            st = section.section_type
            title = _section_title(section)
            content = (
                (section.content_en or "").strip() or (section.content_bn or "").strip()
            )
            if st == SectionType.IMPACT_STATS:
                if not ctx["home_impact_stats"]:
                    continue
            if st in DATA_DRIVEN_SECTION_TYPES:
                if st == SectionType.TESTIMONIALS and not ctx["home_testimonials"]:
                    continue
                if st == SectionType.PARTNERS and not ctx["home_partners"]:
                    continue
                if st == SectionType.NEWS_GRID and not ctx["home_news"]:
                    continue
                if st == SectionType.LEADERSHIP and not ctx["home_leadership"]:
                    continue
                if st == SectionType.IMPACT_STATS and not ctx["home_impact_stats"]:
                    continue
            # Prefer dedicated Leadership section over legacy Leadership CTA.
            if (
                has_leadership_section
                and st == SectionType.CTA
                and "leadership" in (section.button_link or "").lower()
            ):
                continue
            # Hide empty legacy shells (prevents "None" / blank blocks on old DBs).
            if st == SectionType.GALLERY_PREVIEW:
                has_gallery = False
                if hasattr(section, "gallery_images"):
                    has_gallery = any(
                        getattr(img, "is_active", True)
                        and getattr(img, "media_id", None)
                        and getattr(getattr(img, "media", None), "image", None)
                        for img in section.gallery_images.all()
                    )
                if not has_gallery and not section.image and not title and not content:
                    continue
                if not has_gallery and not section.image:
                    # Heading-only gallery shells stay hidden (no broken slider).
                    continue
            elif st in legacy_optional and not title and not content and not section.image:
                continue
            if st == SectionType.HERO and not title and not content:
                continue
            if st == SectionType.PROGRAM_LIST and not title and not content:
                continue
            if st not in (
                SectionType.TRUST_BAR,
                *DATA_DRIVEN_SECTION_TYPES,
            ) and not title and not content:
                if st != SectionType.GALLERY_PREVIEW:
                    continue
            visible.append(section)

        # One hero only — prefer the latest ordered published hero with content.
        heroes = [s for s in visible if s.section_type == SectionType.HERO]
        if len(heroes) > 1:
            keep = max(heroes, key=lambda s: (s.order, bool(_section_title(s))))
            visible = [
                s for s in visible if s.section_type != SectionType.HERO or s.pk == keep.pk
            ]

        # Attach mission/vision dict once for template convenience (first MV section).
        for section in visible:
            if section.section_type == SectionType.MISSION_VISION:
                ctx["mission_vision"] = _mission_vision_for_section(section)
                break
        else:
            m_en, m_bn, v_en, v_bn = default_mission_vision_pair()
            ctx["mission_vision"] = {
                "mission_en": m_en,
                "mission_bn": m_bn,
                "vision_en": v_en,
                "vision_bn": v_bn,
            }

        ctx["sections"] = visible
        return ctx
