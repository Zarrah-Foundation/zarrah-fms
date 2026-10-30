"""Idempotent default HomepageSection content for a clean DB.

Never overwrites admin-edited rows. Known leftover *default* copy from earlier
seeds (old slogan, invented mission/vision, hardcoded ৳50 payable claim) may
be refreshed only when the stored text still matches those exact defaults.
"""

from __future__ import annotations

from cms.home_content import pack_mission_vision
from cms.models import HomepageSection, SectionType
from pages.organization_data import (
    INTRO_BN,
    INTRO_EN,
    NATURE_BN,
    NATURE_EN,
    PRINCIPAL_OFFICE_BN,
    PRINCIPAL_OFFICE_EN,
    PURPOSE_BN,
    PURPOSE_EN,
    SEO_DESCRIPTION_BN,
    SEO_DESCRIPTION_EN,
    SLOGAN_BN,
    SLOGAN_EN,
)

DEFAULT_SECTIONS = [
    {
        "section_type": SectionType.HERO,
        "order": 10,
        "title_en": SLOGAN_EN,
        "title_bn": SLOGAN_BN,
        "content_en": INTRO_EN,
        "content_bn": INTRO_BN,
        "button_text_en": "Donate",
        "button_text_bn": "দান করুন",
        "button_link": "/donation/",
        "is_published": True,
        "is_visible": True,
        "config": {
            "eyebrow_en": "Zarrah Foundation",
            "eyebrow_bn": "জার্‌রাহ ফাউন্ডেশন",
            "secondary_button_text_en": "Become a Member",
            "secondary_button_text_bn": "সদস্য হন",
            "secondary_button_link": "/membership/",
        },
    },
    {
        "section_type": SectionType.TRUST_BAR,
        "order": 15,
        "title_en": "Registered · Non-profit · Humanitarian",
        "title_bn": "নিবন্ধিত · অলাভজনক · মানবকল্যাণমূলক",
        "content_en": (
            "Registered under the Societies Registration Act, 1860. "
            "Registration details are published in Site Settings and the footer."
        ),
        "content_bn": (
            "সোসাইটি নিবন্ধন আইন, ১৮৬০ এর অধীনে নিবন্ধিত। "
            "নিবন্ধন তথ্য সাইট সেটিংস ও ফুটারে প্রকাশিত।"
        ),
        "button_text_en": "",
        "button_text_bn": "",
        "button_link": "",
        "is_published": True,
        "is_visible": True,
    },
    {
        "section_type": SectionType.APPROACH,
        "order": 25,
        "title_en": "Who we are",
        "title_bn": "আমরা কারা",
        "content_en": INTRO_EN,
        "content_bn": INTRO_BN,
        "button_text_en": "About the Foundation",
        "button_text_bn": "ফাউন্ডেশন সম্পর্কে",
        "button_link": "/about/",
        "is_published": True,
        "is_visible": True,
    },
    {
        "section_type": SectionType.MISSION_VISION,
        "order": 20,
        "title_en": "Purpose & Objectives",
        "title_bn": "লক্ষ্য ও উদ্দেশ্য",
        "content_en": pack_mission_vision(PURPOSE_EN, NATURE_EN),
        "content_bn": pack_mission_vision(PURPOSE_BN, NATURE_BN),
        "button_text_en": "Read the objectives",
        "button_text_bn": "উদ্দেশ্য পড়ুন",
        "button_link": "/objectives/",
        "is_published": True,
        "is_visible": True,
        "config": {
            "mission_title_en": "Our Mission",
            "mission_title_bn": "আমাদের লক্ষ্য",
            "vision_title_en": "Organizational Nature",
            "vision_title_bn": "সাংগঠনিক পরিচিতি",
        },
    },
    {
        "section_type": SectionType.PROGRAM_LIST,
        "order": 30,
        "title_en": "Areas of Work",
        "title_bn": "কর্মক্ষেত্রসমূহ",
        "content_en": (
            "These areas group the Foundation's documented objectives. "
            "They are not a list of completed programmes or impact statistics."
        ),
        "content_bn": (
            "এই ক্ষেত্রগুলো ফাউন্ডেশনের নথিভুক্ত উদ্দেশ্যকে গুচ্ছ করে। "
            "এগুলো সম্পন্ন কর্মসূচি বা প্রভাবের পরিসংখ্যানের তালিকা নয়।"
        ),
        "button_text_en": "Read the objectives",
        "button_text_bn": "উদ্দেশ্য পড়ুন",
        "button_link": "/objectives/",
        "is_published": True,
        "is_visible": True,
    },
    {
        "section_type": SectionType.APPROACH,
        "order": 35,
        "title_en": "Organizational Structure",
        "title_bn": "সংগঠনিক কাঠামো",
        "content_en": (
            "The Memorandum establishes three principal bodies: the Advisory Council, "
            "the Executive Council and the General Council. Roles and occupancy are "
            "published only where verified."
        ),
        "content_bn": (
            "গঠনতন্ত্রে তিনটি প্রধান পরিষদ রয়েছে: উপদেষ্টা পরিষদ, কার্যনির্বাহী পরিষদ "
            "এবং সাধারণ পরিষদ। পদ ও দায়িত্ব কেবল যাচাইকৃত তথ্য থাকলে প্রকাশিত হয়।"
        ),
        "button_text_en": "See structure",
        "button_text_bn": "কাঠামো দেখুন",
        "button_link": "/about/#structure",
        "is_published": True,
        "is_visible": True,
    },
    {
        "section_type": SectionType.CTA,
        "order": 38,
        "title_en": "Zarrah Skills",
        "title_bn": "জার্‌রাহ স্কিলস",
        "content_en": "Skills, training and learning portal of Zarrah Foundation.",
        "content_bn": "জার্‌রাহ ফাউন্ডেশনের দক্ষতা উন্নয়ন ও প্রশিক্ষণ পোর্টাল।",
        "button_text_en": "Visit Zarrah Skills",
        "button_text_bn": "জার্‌রাহ স্কিলস দেখুন",
        "button_link": "https://skills.zarrah.org/",
        "is_published": True,
        "is_visible": True,
        "config": {"eyebrow_en": "Official portal", "eyebrow_bn": "অফিসিয়াল পোর্টাল"},
    },
    {
        "section_type": SectionType.LEADERSHIP,
        "order": 40,
        "title_en": "Leadership",
        "title_bn": "নেতৃত্ব",
        "content_en": (
            "Public officers of Zarrah Foundation, as published in the leadership directory."
        ),
        "content_bn": (
            "নেতৃত্ব তালিকায় প্রকাশিত জার্‌রাহ ফাউন্ডেশনের কর্মকর্তাবৃন্দ।"
        ),
        "button_text_en": "Full leadership",
        "button_text_bn": "সম্পূর্ণ নেতৃত্ব",
        "button_link": "/about/#leadership",
        "is_published": True,
        "is_visible": True,
    },
    {
        "section_type": SectionType.IMPACT_STATS,
        "order": 45,
        "title_en": "Impact Statistics",
        "title_bn": "প্রভাবের পরিসংখ্যান",
        "content_en": (
            "Statistics appear here only when the Foundation publishes verified figures. "
            "This section stays hidden until those records exist."
        ),
        "content_bn": (
            "যাচাইকৃত পরিসংখ্যান প্রকাশিত হলেই এখানে দেখা যাবে। "
            "সেই রেকর্ড না থাকলে এই অংশ লুকানো থাকে।"
        ),
        "button_text_en": "",
        "button_text_bn": "",
        "button_link": "",
        "is_published": True,
        "is_visible": True,
    },
    {
        "section_type": SectionType.TESTIMONIALS,
        "order": 50,
        "title_en": "Testimonials",
        "title_bn": "প্রশংসাপত্র",
        "content_en": "",
        "content_bn": "",
        "button_text_en": "",
        "button_text_bn": "",
        "button_link": "",
        "is_published": False,
        "is_visible": True,
    },
    {
        "section_type": SectionType.PARTNERS,
        "order": 60,
        "title_en": "Partners & Technology Supporters",
        "title_bn": "অংশীদার ও প্রযুক্তি সহায়ক",
        "content_en": (
            "Organizations and platforms supporting Zarrah Foundation's work. "
            "Technology listings describe nonprofit eligibility or service benefits, "
            "not commercial sponsorship or endorsement."
        ),
        "content_bn": (
            "জার্‌রাহ ফাউন্ডেশনের কাজকে সহায়তা করা সংস্থা ও প্ল্যাটফর্ম। "
            "প্রযুক্তি তালিকা অলাভজনক যোগ্যতা বা সেবা সুবিধা বোঝায় — বাণিজ্যিক স্পনসরশিপ বা সমর্থন নয়।"
        ),
        "button_text_en": "",
        "button_text_bn": "",
        "button_link": "",
        "is_published": True,
        "is_visible": True,
    },
    {
        "section_type": SectionType.NEWS_GRID,
        "order": 70,
        "title_en": "News",
        "title_bn": "সংবাদ",
        "content_en": "Updates published by Zarrah Foundation.",
        "content_bn": "জার্‌রাহ ফাউন্ডেশন কর্তৃক প্রকাশিত আপডেট।",
        "button_text_en": "All news",
        "button_text_bn": "সব সংবাদ",
        "button_link": "/news/",
        "is_published": True,
        "is_visible": True,
    },
    {
        "section_type": SectionType.TRANSPARENCY_PREVIEW,
        "order": 80,
        "title_en": "Transparency & Accountability",
        "title_bn": "স্বচ্ছতা ও জবাবদিহিতা",
        "content_en": (
            "Governance, legal and published financial documents. Private ledgers are not shown. "
            "Organizational rules come from the Memorandum; this website's tools keep records."
        ),
        "content_bn": (
            "সুশাসন, আইনগত ও প্রকাশিত আর্থিক দলিল। অভ্যন্তরীণ হিসাব এখানে দেখানো হয় না। "
            "সংগঠনিক নিয়মাবলি গঠনতন্ত্র থেকে; এই ওয়েবসাইটের সরঞ্জাম রেকর্ড সংরক্ষণ করে।"
        ),
        "button_text_en": "View Transparency",
        "button_text_bn": "স্বচ্ছতা দেখুন",
        "button_link": "/transparency/",
        "is_published": True,
        "is_visible": True,
    },
    {
        "section_type": SectionType.CTA,
        "order": 90,
        "title_en": "Membership",
        "title_bn": "সদস্যপদ",
        "content_en": (
            "Adults who agree with the Foundation's objectives and constitution may apply. "
            "Applications are reviewed; membership is not automatic. Current fees are those "
            "set in Membership Fee Settings and shown at checkout."
        ),
        "content_bn": (
            "ফাউন্ডেশনের উদ্দেশ্য ও গঠনতন্ত্রে সম্মত প্রাপ্তবয়স্ক ব্যক্তি আবেদন করতে পারেন। "
            "আবেদন পর্যালোচনা করা হয়; সদস্যপদ স্বয়ংক্রিয় নয়। বর্তমান ফি সদস্যপদ ফি সেটিংস "
            "অনুযায়ী চেকআউটে দেখানো হয়।"
        ),
        "button_text_en": "Apply for Membership",
        "button_text_bn": "সদস্যপদের জন্য আবেদন",
        "button_link": "/membership/apply/",
        "is_published": True,
        "is_visible": True,
    },
    {
        "section_type": SectionType.CTA,
        "order": 100,
        "title_en": "Donate",
        "title_bn": "দান করুন",
        "content_en": (
            "Donations support Zarrah Foundation's documented public-welfare objectives."
        ),
        "content_bn": (
            "দান জার্‌রাহ ফাউন্ডেশনের নথিভুক্ত জনকল্যাণমূলক উদ্দেশ্যে সহায়তা করে।"
        ),
        "button_text_en": "Donate Now",
        "button_text_bn": "দান করুন",
        "button_link": "/donation/",
        "is_published": True,
        "is_visible": True,
    },
    {
        "section_type": SectionType.CTA,
        "order": 110,
        "title_en": "Contact",
        "title_bn": "যোগাযোগ",
        "content_en": "Principal office: Sakhipur, Tangail, Bangladesh. Use the contact page for official channels.",
        "content_bn": "প্রধান কার্যালয়: সখিপুর, টাঙ্গাইল, বাংলাদেশ। অফিসিয়াল যোগাযোগের জন্য যোগাযোগ পাতা ব্যবহার করুন।",
        "button_text_en": "Contact us",
        "button_text_bn": "যোগাযোগ করুন",
        "button_link": "/contact/",
        "is_published": True,
        "is_visible": True,
    },
]

# Do not seed testimonials or partners — those appear only with verified records.
DEFAULT_TESTIMONIALS = []

_OLD_HERO_TITLES_EN = frozenset({"From the atom, For the Helpless."})
_OLD_HERO_TITLES_BN = frozenset(
    {"পরমাণু থেকে, অসহায়দের জন্য।", "ক্ষুদ্র কাজ, স্থায়ী প্রভাব"}
)
_OLD_TAGLINES_EN = frozenset(
    {
        "Serving humanity through compassion and community.",
        "From the atom, For the Helpless.",
        "",
    }
)
_OLD_TAGLINES_BN = frozenset(
    {
        "",
        "পরমাণু থেকে, অসহায়দের জন্য।",
        "ক্ষুদ্র কাজ, স্থায়ী প্রভাব",
    }
)
# Distinctive leftover marketing copy from earlier seeds — not Memorandum text.
_OLD_MARKETING_FRAGMENTS = (
    "empowering communities through education",
    "become one of the most trusted nonprofit",
    "to serve humanity through education, healthcare",
    "smallest act of kindness can create lasting change",
    "smallest effort",
    "focus areas that guide zarrah foundation",
    "sustain education, healthcare, relief",
    "approved members pay a mandatory",
    "dedicated individuals guiding",
    "strengthen community programs",
    "partners & collaborators",
    "latest updates",
    "community-focused",
)


def _has_old_marketing(text: str) -> bool:
    lowered = (text or "").lower()
    return any(fragment in lowered for fragment in _OLD_MARKETING_FRAGMENTS)


def _apply_section_spec(section, spec) -> None:
    section.title_en = spec["title_en"]
    section.title_bn = spec["title_bn"]
    section.content_en = spec["content_en"]
    section.content_bn = spec["content_bn"]
    if spec.get("button_text_en") is not None:
        section.button_text_en = spec.get("button_text_en") or ""
    if spec.get("button_text_bn") is not None:
        section.button_text_bn = spec.get("button_text_bn") or ""
    if spec.get("button_link") is not None:
        section.button_link = spec.get("button_link") or ""
    cfg = section.get_config()
    cfg.update(spec.get("config") or {})
    section.config = cfg
    section.save()


def _create_section(spec, order):
    return HomepageSection.objects.create(
        section_type=spec["section_type"],
        order=order,
        title_en=spec.get("title_en") or "",
        title_bn=spec.get("title_bn") or "",
        content_en=spec.get("content_en") or "",
        content_bn=spec.get("content_bn") or "",
        button_text_en=spec.get("button_text_en") or "",
        button_text_bn=spec.get("button_text_bn") or "",
        button_link=spec.get("button_link") or "",
        is_published=bool(spec.get("is_published", True)),
        is_visible=bool(spec.get("is_visible", True)),
        is_deleted=False,
        config=spec.get("config") or {},
    )


def _refresh_known_default_copy() -> int:
    """Replace leftover seeded copy that still matches previous defaults."""
    updated = 0
    spec_by_key = {(s["section_type"], s["order"]): s for s in DEFAULT_SECTIONS}

    hero = HomepageSection.objects.filter(
        section_type=SectionType.HERO, order=10, is_deleted=False
    ).first()
    if hero and (
        (hero.title_en or "") in _OLD_HERO_TITLES_EN
        or (hero.title_bn or "") in _OLD_HERO_TITLES_BN
        or _has_old_marketing(hero.content_en)
        or _has_old_marketing(hero.title_en)
    ):
        _apply_section_spec(hero, spec_by_key[(SectionType.HERO, 10)])
        updated += 1

    for section in HomepageSection.objects.filter(is_deleted=False):
        blob = f"{section.title_en}\n{section.content_en}"
        if not _has_old_marketing(blob):
            continue
        spec = spec_by_key.get((section.section_type, section.order))
        if spec is None and section.section_type == SectionType.MISSION_VISION:
            spec = spec_by_key.get((SectionType.MISSION_VISION, 20))
        if spec is None and section.section_type == SectionType.APPROACH:
            spec = spec_by_key.get((SectionType.APPROACH, 25))
        if spec is None and section.section_type == SectionType.PROGRAM_LIST:
            spec = spec_by_key.get((SectionType.PROGRAM_LIST, 30))
        if spec is None and section.section_type == SectionType.CTA:
            if "৳50" in (section.content_en or "") or "mandatory" in (section.content_en or "").lower():
                spec = spec_by_key.get((SectionType.CTA, 90))
            elif "donation" in (section.button_link or "").lower() or "donate" in (
                section.title_en or ""
            ).lower():
                spec = spec_by_key.get((SectionType.CTA, 100))
        if spec is None and section.section_type == SectionType.PARTNERS:
            spec = spec_by_key.get((SectionType.PARTNERS, 60))
        if spec is None and section.section_type == SectionType.LEADERSHIP:
            spec = spec_by_key.get((SectionType.LEADERSHIP, 40))
        if spec is None and section.section_type == SectionType.NEWS_GRID:
            spec = spec_by_key.get((SectionType.NEWS_GRID, 70))
        if spec is None and section.section_type == SectionType.TRUST_BAR:
            spec = spec_by_key.get((SectionType.TRUST_BAR, 15))
        if spec is None:
            continue
        if section.section_type == SectionType.HERO:
            continue
        _apply_section_spec(section, spec)
        updated += 1
    updated += HomepageSection.objects.filter(
        section_type=SectionType.PROGRAM_LIST,
        title_bn="কর্মক্ষেত্র",
        is_deleted=False,
    ).update(title_bn="কর্মক্ষেত্রসমূহ")
    for section in HomepageSection.objects.filter(
        section_type=SectionType.MISSION_VISION,
        is_deleted=False,
    ):
        cfg = dict(section.config or {})
        if cfg.get("vision_title_bn") == "প্রতিষ্ঠানের প্রকৃতি":
            cfg["vision_title_bn"] = "সাংগঠনিক পরিচিতি"
            section.config = cfg
            section.save(update_fields=["config"])
            updated += 1
    return updated


def _unpublish_seeded_placeholder_testimonial() -> int:
    from community.models import Testimonial

    qs = Testimonial.objects.filter(author_name="IMROZ AHMAD", is_published=True)
    count = 0
    for t in qs:
        en = (t.content_en or "").replace(" ", "")
        if "morethananorganization" in en.lower() or "commitmenttoservinghumanity" in en.lower():
            t.is_published = False
            t.save(update_fields=["is_published"])
            count += 1
    return count


def _deactivate_placeholder_partner() -> int:
    """Founder name used as a partner tile is leftover placeholder, not a verified org."""
    from community.models import Partner

    qs = Partner.objects.filter(name__iexact="IMROZ AHMAD", is_active=True)
    count = 0
    for partner in qs:
        if partner.url or partner.logo:
            continue
        partner.is_active = False
        partner.save(update_fields=["is_active"])
        count += 1
    return count


def seed_site_identity() -> dict:
    """Fill empty SiteSettings identity fields; replace only known old taglines."""
    from core.models import SiteSettings

    obj = SiteSettings.load()
    changed = False
    if (obj.tagline_en or "").strip() in _OLD_TAGLINES_EN:
        obj.tagline_en = SLOGAN_EN
        changed = True
    if (obj.tagline_bn or "").strip() in _OLD_TAGLINES_BN:
        obj.tagline_bn = SLOGAN_BN
        changed = True
    if (obj.foundation_name_bn or "").strip() in ("", "জার্‌রাহ"):
        obj.foundation_name_bn = "জার্‌রাহ ফাউন্ডেশন"
        changed = True
    if not (obj.address_en or "").strip():
        obj.address_en = PRINCIPAL_OFFICE_EN
        changed = True
    if not (obj.address_bn or "").strip():
        obj.address_bn = PRINCIPAL_OFFICE_BN
        changed = True
    if not (obj.meta_description or "").strip():
        obj.meta_description = SEO_DESCRIPTION_EN
        changed = True
    if not (obj.foundation_description_en or "").strip():
        obj.foundation_description_en = INTRO_EN
        changed = True
    if not (obj.foundation_description_bn or "").strip():
        obj.foundation_description_bn = INTRO_BN
        changed = True
    if (obj.meta_title or "").strip() in ("", "Zarrah Foundation"):
        obj.meta_title = f"Zarrah Foundation — {SLOGAN_EN}"
        changed = True
    if not (obj.website_url or "").strip():
        obj.website_url = "https://zarrah.org"
        changed = True
    if changed:
        obj.save()
    return {"updated": changed}


def _unpublish_empty_testimonials() -> int:
    from community.models import Testimonial

    count = 0
    for t in Testimonial.objects.filter(is_published=True):
        if not (t.content_en or "").strip() and not (t.content_bn or "").strip():
            t.is_published = False
            t.save(update_fields=["is_published"])
            count += 1
    return count


DEFAULT_LEADERSHIP = [
    {
        "role": "CHAIRMAN",
        "name": "MD. BABUL HOSSAIN",
        "role_label_en": "Chairman",
        "role_label_bn": "চেয়ারম্যান",
        "display_order": 10,
    },
    {
        "role": "SECRETARY",
        "name": "IMROZ AHMAD",
        "role_label_en": "Secretary",
        "role_label_bn": "সচিব",
        "display_order": 20,
    },
]


def seed_default_leadership() -> dict:
    """Publish Chairman and Secretary names from the Memorandum if missing."""
    from community.models import LeadershipPerson

    created = 0
    skipped = 0
    for spec in DEFAULT_LEADERSHIP:
        role = spec["role"]
        if LeadershipPerson.objects.filter(role=role, is_published=True).exists():
            skipped += 1
            continue
        if LeadershipPerson.objects.filter(name__iexact=spec["name"], role=role).exists():
            person = LeadershipPerson.objects.filter(
                name__iexact=spec["name"], role=role
            ).first()
            if person and not person.is_published:
                person.is_published = True
                person.save(update_fields=["is_published"])
                created += 1
            else:
                skipped += 1
            continue
        LeadershipPerson.objects.create(
            role=role,
            name=spec["name"],
            role_label_en=spec["role_label_en"],
            role_label_bn=spec["role_label_bn"],
            display_order=spec["display_order"],
            is_published=True,
        )
        created += 1
    return {"created": created, "skipped": skipped}


# Company name taken from the existing public testimonial designation record.
# Technology entries are nonprofit eligibility/benefit relationships, not sponsorships.
DEFAULT_SUPPORTERS = [
    {
        "name": "Ahmad Solution Ltd",
        "url": "",
        "relationship_type": "ORGANIZATIONAL_SUPPORTER",
        "description_en": "Organization supporting Zarrah Foundation's work.",
        "description_bn": "জার্‌রাহ ফাউন্ডেশনের কাজকে সহায়তা করা সংস্থা।",
        "display_order": 10,
    },
    {
        "name": "Goodstack",
        "url": "https://goodstack.org/",
        "relationship_type": "ELIGIBILITY_PLATFORM",
        "description_en": "Verified nonprofit / eligibility platform relationship.",
        "description_bn": "যাচাইকৃত অলাভজনক / যোগ্যতা প্ল্যাটফর্ম সম্পর্ক।",
        "display_order": 20,
    },
    {
        "name": "Canva",
        "url": "https://www.canva.com/",
        "relationship_type": "TECHNOLOGY_BENEFIT",
        "description_en": "Nonprofit technology/service benefit.",
        "description_bn": "অলাভজনক প্রযুক্তি/সেবা সুবিধা।",
        "display_order": 30,
    },
    {
        "name": "Microsoft",
        "url": "https://www.microsoft.com/",
        "relationship_type": "TECHNOLOGY_BENEFIT",
        "description_en": "Nonprofit technology/service benefit.",
        "description_bn": "অলাভজনক প্রযুক্তি/সেবা সুবিধা।",
        "display_order": 40,
    },
    {
        "name": "Zoom",
        "url": "https://www.zoom.com/",
        "relationship_type": "TECHNOLOGY_BENEFIT",
        "description_en": "Nonprofit technology/service benefit.",
        "description_bn": "অলাভজনক প্রযুক্তি/সেবা সুবিধা।",
        "display_order": 50,
    },
    {
        "name": "OpenAI",
        "url": "https://openai.com/",
        "relationship_type": "TECHNOLOGY_BENEFIT",
        "description_en": "Nonprofit technology/service benefit.",
        "description_bn": "অলাভজনক প্রযুক্তি/সেবা সুবিধা।",
        "display_order": 60,
    },
    {
        "name": "Adobe",
        "url": "https://www.adobe.com/",
        "relationship_type": "TECHNOLOGY_BENEFIT",
        "description_en": "Nonprofit technology/service benefit.",
        "description_bn": "অলাভজনক প্রযুক্তি/সেবা সুবিধা।",
        "display_order": 70,
    },
]


def seed_verified_supporters() -> dict:
    from community.models import Partner

    created = 0
    skipped = 0
    for spec in DEFAULT_SUPPORTERS:
        existing = Partner.objects.filter(name__iexact=spec["name"]).first()
        if existing:
            skipped += 1
            continue
        Partner.objects.create(
            name=spec["name"],
            url=spec["url"],
            relationship_type=spec["relationship_type"],
            description_en=spec["description_en"],
            description_bn=spec["description_bn"],
            display_order=spec["display_order"],
            is_active=True,
        )
        created += 1
    return {"created": created, "skipped": skipped}


def _unpublish_qa_news() -> int:
    from news.models import News

    titles = {"test", "manual qa article"}
    count = 0
    for article in News.objects.filter(is_published=True):
        if (article.title or "").strip().lower() in titles:
            article.is_published = False
            article.save(update_fields=["is_published"])
            count += 1
    return count


SKILLS_NEWS = {
    "title": "Zarrah Skills portal is now available",
    "title_bn": "জার্‌রাহ স্কিলস পোর্টাল এখন উপলব্ধ",
    "slug": "zarrah-skills-portal",
    "excerpt": (
        "Zarrah Skills is Zarrah Foundation's official skills, training and learning portal."
    ),
    "excerpt_bn": (
        "জার্‌রাহ স্কিলস জার্‌রাহ ফাউন্ডেশনের অফিসিয়াল দক্ষতা উন্নয়ন, প্রশিক্ষণ ও শিক্ষা পোর্টাল।"
    ),
    "content": (
        "Zarrah Foundation has published Zarrah Skills, its official skills, training and "
        "learning portal.\n\n"
        "Zarrah Skills is operated by Zarrah Foundation. It supports skills development, "
        "training and learning in line with the Foundation's documented education and "
        "skills-development objectives.\n\n"
        "Official portal: https://skills.zarrah.org/\n\n"
        "This announcement does not claim specific course counts, certifications or outcomes."
    ),
    "content_bn": (
        "জার্‌রাহ ফাউন্ডেশন তার অফিসিয়াল দক্ষতা উন্নয়ন, প্রশিক্ষণ ও শিক্ষা পোর্টাল "
        "জার্‌রাহ স্কিলস প্রকাশ করেছে।\n\n"
        "জার্‌রাহ স্কিলস জার্‌রাহ ফাউন্ডেশন পরিচালিত। এটি ফাউন্ডেশনের নথিভুক্ত শিক্ষা ও "
        "দক্ষতা উন্নয়ন উদ্দেশ্যের সাথে সামঞ্জস্য রেখে দক্ষতা উন্নয়ন, প্রশিক্ষণ ও শিক্ষাকে "
        "সহায়তা করে।\n\n"
        "অফিসিয়াল পোর্টাল: https://skills.zarrah.org/\n\n"
        "এই ঘোষণায় নির্দিষ্ট কোর্স সংখ্যা, সনদ বা ফলাফল দাবি করা হয়নি।"
    ),
}


def seed_zarrah_skills_news() -> dict:
    from django.utils import timezone

    from accounts.models import User
    from news.models import News

    existing = News.objects.filter(slug=SKILLS_NEWS["slug"]).first()
    if existing:
        if not existing.is_published:
            existing.is_published = True
            existing.published_at = existing.published_at or timezone.now()
            existing.save(update_fields=["is_published", "published_at"])
        return {"created": 0, "skipped": 1}
    author = User.objects.filter(is_superuser=True).first() or User.objects.order_by("pk").first()
    if author is None:
        return {"created": 0, "skipped": 0}
    News.objects.create(
        title=SKILLS_NEWS["title"],
        title_bn=SKILLS_NEWS["title_bn"],
        slug=SKILLS_NEWS["slug"],
        excerpt=SKILLS_NEWS["excerpt"],
        excerpt_bn=SKILLS_NEWS["excerpt_bn"],
        content=SKILLS_NEWS["content"],
        content_bn=SKILLS_NEWS["content_bn"],
        is_published=True,
        published_at=timezone.now(),
        author=author,
    )
    return {"created": 1, "skipped": 0}


def _hide_empty_impact_stats_section() -> int:
    """Hide leftover untitled IMPACT_STATS shells. Keep the named CMS section
    published so verified statistics can appear without a second publish step.
    The homepage still omits the block when no published ImpactStatistic rows exist.
    """
    updated = 0
    for section in HomepageSection.objects.filter(
        section_type=SectionType.IMPACT_STATS, is_deleted=False
    ):
        title = (section.title_en or "").strip() or (section.title_bn or "").strip()
        if not title:
            if section.is_published:
                section.is_published = False
                section.save(update_fields=["is_published"])
                updated += 1
            continue
        if (
            section.order == 45
            and (section.title_en or "").strip() == "Impact Statistics"
            and (not section.is_published or not section.is_visible)
        ):
            section.is_published = True
            section.is_visible = True
            section.save(update_fields=["is_published", "is_visible"])
            updated += 1
    return updated


def seed_homepage_defaults(*, verbosity: int = 1) -> dict:
    """Create missing default sections. Never overwrite existing rows."""
    created_sections = 0
    skipped_sections = 0
    for spec in DEFAULT_SECTIONS:
        exists = HomepageSection.objects.filter(
            section_type=spec["section_type"],
            order=spec["order"],
            is_deleted=False,
        ).exists()
        if exists:
            skipped_sections += 1
            continue
        order = spec["order"]
        if spec["section_type"] == SectionType.LEADERSHIP:
            if HomepageSection.objects.filter(
                section_type=SectionType.CTA, order=40, is_deleted=False
            ).exists():
                order = 42
            if HomepageSection.objects.filter(
                section_type=SectionType.LEADERSHIP, is_deleted=False
            ).exists():
                skipped_sections += 1
                continue
        _create_section(spec, order)
        created_sections += 1

    refreshed = _refresh_known_default_copy()
    unpublished_quotes = _unpublish_seeded_placeholder_testimonial()
    unpublished_empty = _unpublish_empty_testimonials()
    deactivated_partners = _deactivate_placeholder_partner()
    identity = seed_site_identity()
    leadership = seed_default_leadership()
    supporters = seed_verified_supporters()
    unpublished_qa = _unpublish_qa_news()
    skills_news = seed_zarrah_skills_news()
    hidden_stats = _hide_empty_impact_stats_section()

    return {
        "created_sections": created_sections,
        "skipped_sections": skipped_sections,
        "created_testimonials": 0,
        "skipped_testimonials": 0,
        "refreshed_sections": refreshed,
        "unpublished_placeholder_testimonials": unpublished_quotes + unpublished_empty,
        "deactivated_placeholder_partners": deactivated_partners,
        "identity_updated": identity["updated"],
        "leadership_created": leadership["created"],
        "supporters_created": supporters["created"],
        "qa_news_unpublished": unpublished_qa,
        "skills_news_created": skills_news["created"],
        "hidden_empty_impact_sections": hidden_stats,
    }
