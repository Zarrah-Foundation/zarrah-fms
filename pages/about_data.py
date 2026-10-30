"""Structured, bilingual content for the About page.

Public facts come from ``pages.organization_data`` (Memorandum + SiteSettings).
Do not invent impact numbers, programmes, or a formal Mission/Vision statement.
"""

from pages.organization_data import (
    AREAS_OF_WORK,
    INCOME_SOURCES,
    INTRO_BN,
    INTRO_EN,
    MEETINGS_PUBLIC,
    MEMBERSHIP_ELIGIBILITY,
    MEMBERSHIP_FEES,
    MOA_AREA,
    MOA_DISSOLUTION,
    MOA_INCOME,
    MOA_NATURE,
    NAME_BN,
    NAME_EN,
    NATURE_BN,
    NATURE_EN,
    OBJECTIVES,
    ORG_STRUCTURE,
    PRINCIPAL_OFFICE_BN,
    PRINCIPAL_OFFICE_EN,
    PURPOSE_BN,
    PURPOSE_EN,
    QUORUM,
    QUORUM_CARDS,
    QUORUM_SECTION,
    FINANCIAL_PRINCIPLES,
    SKILLS,
    SLOGAN_BN,
    SLOGAN_EN,
    ADJOURNED,
    public_founders,
)

HERO = {
    "eyebrow_en": "Registered under the Societies Registration Act, 1860",
    "eyebrow_bn": "সোসাইটি নিবন্ধন আইন, ১৮৬০ এর অধীনে নিবন্ধিত",
    "title_en": NAME_EN,
    "title_bn": NAME_BN,
    "subtitle_en": INTRO_EN,
    "subtitle_bn": INTRO_BN,
    "slogan_en": SLOGAN_EN,
    "slogan_bn": SLOGAN_BN,
    "image": None,
}

WHO_WE_ARE = {
    "eyebrow_en": "Who We Are",
    "eyebrow_bn": "আমরা কারা",
    "title_en": NAME_EN,
    "title_bn": NAME_BN,
    "paragraph_1_en": INTRO_EN,
    "paragraph_1_bn": INTRO_BN,
    "paragraph_2_en": (
        f"{MOA_AREA['en']} The organisation is non-profit, non-political, "
        "voluntary and humanitarian."
    ),
    "paragraph_2_bn": (
        f"{MOA_AREA['bn']} প্রতিষ্ঠানটি অলাভজনক, অরাজনৈতিক, স্বেচ্ছাসেবী ও মানবকল্যাণমূলক।"
    ),
}

REGISTRATION_INFO = {
    "title_en": "Legal identity",
    "title_bn": "আইনগত পরিচয়",
    "subtitle_en": "Societies Registration Act, 1860",
    "subtitle_bn": "সোসাইটি নিবন্ধন আইন, ১৮৬০",
    "rows": [
        {
            "label_en": "Registered name",
            "label_bn": "নিবন্ধিত নাম",
            "value_en": f"{NAME_EN} / {NAME_BN}",
            "value_bn": f"{NAME_BN} / {NAME_EN}",
        },
        {
            "label_en": "Registration No.",
            "label_bn": "নিবন্ধন নম্বর",
            "value_en": "S-15000/2026",
            "value_bn": "S-15000/2026",
            "value_lang": "en",
        },
        {
            "label_en": "Registered On",
            "label_bn": "নিবন্ধনের তারিখ",
            "value_en": "02 July 2026",
            "value_bn": "০২ জুলাই ২০২৬",
        },
        {
            "label_en": "Country",
            "label_bn": "দেশ",
            "value_en": "Bangladesh",
            "value_bn": "বাংলাদেশ",
        },
        {
            "label_en": "Principal office",
            "label_bn": "প্রধান কার্যালয়",
            "value_en": PRINCIPAL_OFFICE_EN.replace("\n", " "),
            "value_bn": PRINCIPAL_OFFICE_BN.replace("\n", " "),
        },
    ],
}

# Kept as PURPOSE / NATURE — not an invented legal Mission/Vision.
MISSION_VISION = {
    "eyebrow_en": "Purpose & Objectives",
    "eyebrow_bn": "আমাদের লক্ষ্য ও উদ্দেশ্য",
    "title_en": "Purpose & Objectives",
    "title_bn": "লক্ষ্য ও উদ্দেশ্য",
    "subtitle_en": (
        "The Memorandum sets the Foundation's purpose and objectives. "
        "The wording below follows that document; it is not a separately titled Mission or Vision statement."
    ),
    "subtitle_bn": (
        "গঠনতন্ত্রে ফাউন্ডেশনের লক্ষ্য ও উদ্দেশ্য নির্ধারিত। নিচের ভাষ্য সেই দলিল অনুসরণ করে; "
        "এটি পৃথকভাবে শিরোনামকৃত মিশন বা ভিশন বাক্য নয়।"
    ),
    "mission": {
        "icon": "bi-bullseye",
        "title_en": "Our Mission",
        "title_bn": "আমাদের লক্ষ্য",
        "text_en": PURPOSE_EN,
        "text_bn": PURPOSE_BN,
    },
    "vision": {
        "icon": "bi-building",
        "title_en": "Organizational Nature",
        "title_bn": "সাংগঠনিক পরিচিতি",
        "text_en": NATURE_EN,
        "text_bn": NATURE_BN,
    },
}

CORE_VALUES = [
    {
        "icon": item.get("icon") or "bi-heart",
        "title_en": item["en"],
        "title_bn": item["bn"],
        "text_en": "",
        "text_bn": "",
    }
    for item in MOA_NATURE["items"]
]

IMPACT_AREAS = AREAS_OF_WORK

TIMELINE = [
    {
        "year": "2026",
        "title_en": "Foundation established",
        "title_bn": "ফাউন্ডেশন প্রতিষ্ঠা",
        "text_en": (
            "Zarrah Foundation was formed as a voluntary, non-profit, non-political "
            "and humanitarian society."
        ),
        "text_bn": (
            "জার্‌রাহ ফাউন্ডেশন একটি স্বেচ্ছাসেবী, অলাভজনক, অরাজনৈতিক ও মানবকল্যাণমূলক "
            "সোসাইটি হিসেবে গঠিত হয়।"
        ),
        "icon": "bi-flag",
        "highlight": False,
    },
    {
        "year": "2026",
        "title_en": "Official registration",
        "title_bn": "সরকারি নিবন্ধন",
        "text_en": "Registered under the Societies Registration Act, 1860.",
        "text_bn": "সোসাইটি নিবন্ধন আইন, ১৮৬০ এর অধীনে নিবন্ধিত হয়।",
        "icon": "bi-patch-check",
        "highlight": False,
    },
]

LEADERSHIP = {
    "eyebrow_en": "Leadership",
    "eyebrow_bn": "নেতৃত্ব",
    "title_en": "Leadership",
    "title_bn": "নেতৃত্ব",
    "subtitle_en": (
        "Public officers listed in the Foundation's leadership directory. "
        "Private identification details from the Memorandum are not published."
    ),
    "subtitle_bn": (
        "ফাউন্ডেশনের নেতৃত্ব তালিকায় প্রকাশিত কর্মকর্তাবৃন্দ। "
        "গঠনতন্ত্রের ব্যক্তিগত পরিচয়পত্র তথ্য এখানে প্রকাশ করা হয় না।"
    ),
    "chairman": None,
    "secretary": None,
    "committee": [],
}

ABOUT_COPY = {
    "nature_intro_en": "The Memorandum describes Zarrah Foundation as:",
    "nature_intro_bn": (
        "সংঘস্মারকে জার্‌রাহ ফাউন্ডেশনকে নিম্নরূপে বর্ণনা করা হয়েছে:"
    ),
    "areas_intro_en": (
        "These areas are presentation groupings of the Foundation's documented "
        "objectives. They are not claims of completed programmes."
    ),
    "areas_intro_bn": (
        "এই ক্ষেত্রগুলো ফাউন্ডেশনের নথিভুক্ত উদ্দেশ্যের উপস্থাপনামূলক গুচ্ছ। "
        "সম্পন্ন কর্মসূচির দাবি নয়।"
    ),
    "structure_intro_en": (
        "The Memorandum establishes three principal bodies. This is a factual "
        "summary, not a claim that every listed office is currently occupied."
    ),
    "structure_intro_bn": (
        "সংঘস্মারকে তিনটি প্রধান পরিষদ নির্ধারিত। এটি তথ্যভিত্তিক সারসংক্ষেপ — "
        "প্রতিটি পদ বর্তমানে পূরণ আছে এমন দাবি নয়।"
    ),
    "leadership_empty_en": (
        "Public leadership profiles will appear here when published by the Foundation."
    ),
    "leadership_empty_bn": (
        "ফাউন্ডেশন কর্তৃক প্রকাশিত হলে পাবলিক নেতৃত্বের পরিচিতি এখানে দেখা যাবে।"
    ),
    "founders_intro_en": (
        "Subscribers named in the Memorandum. Private addresses, phone numbers, "
        "emails, dates of birth, TIN and National ID details are not published."
    ),
    "founders_intro_bn": (
        "সংঘস্মারকে নামিত গ্রাহকবৃন্দ। ব্যক্তিগত ঠিকানা, ফোন নম্বর, ইমেইল, জন্মতারিখ, "
        "টিআইএন ও জাতীয় পরিচয়পত্রের তথ্য প্রকাশ করা হয় না।"
    ),
    "summaries_note_en": (
        "Financial summaries are published periodically as available. Summaries are "
        "not labelled as audited reports unless the source document is an audit report."
    ),
    "summaries_note_bn": (
        "আর্থিক সারসংক্ষেপ সময় সময় প্রকাশিত হয়, যেখানে উপলব্ধ। উৎস দলিল নিরীক্ষা "
        "প্রতিবেদন না হলে সারসংক্ষেপকে নিরীক্ষিত প্রতিবেদন বলা হয় না।"
    ),
}

LEGAL = {
    "eyebrow_en": "Governance & Accountability",
    "eyebrow_bn": "সুশাসন ও জবাবদিহিতা",
    "title_en": "Governance & legal documents",
    "title_bn": "সুশাসন ও আইনগত দলিল",
    "subtitle_en": (
        "Organizational rules are set out in the Memorandum. Digital tools on this "
        "website are used to keep records; they are not themselves legal authority."
    ),
    "subtitle_bn": (
        "সংগঠনিক নিয়মাবলি গঠনতন্ত্রে নির্ধারিত। এই ওয়েবসাইটের ডিজিটাল সরঞ্জাম রেকর্ড "
        "সংরক্ষণে ব্যবহৃত হয়; সেগুলো নিজে আইনগত কর্তৃত্ব নয়।"
    ),
    "documents": [
        {
            "icon": "bi-file-earmark-text",
            "title_en": "Constitution / Memorandum",
            "title_bn": "গঠনতন্ত্র / সংঘস্মারক",
            "text_en": "Governing document defining name, objectives, membership and structure.",
            "text_bn": "নাম, উদ্দেশ্য, সদস্যপদ ও কাঠামো নির্ধারণকারী পরিচালনা দলিল।",
            "url_name": "constitution",
            "cta_en": "Read Constitution",
            "cta_bn": "গঠনতন্ত্র পড়ুন",
        },
        {
            "icon": "bi-journal-text",
            "title_en": "Reports",
            "title_bn": "প্রতিবেদন",
            "text_en": "Public publications and organizational reports when issued.",
            "text_bn": "প্রকাশিত প্রতিবেদন ও প্রকাশনা, যেগুলো প্রকাশিত হয়েছে।",
            "url_name": "reports",
            "cta_en": "View Reports",
            "cta_bn": "প্রতিবেদন দেখুন",
        },
        {
            "icon": "bi-eye",
            "title_en": "Transparency",
            "title_bn": "স্বচ্ছতা",
            "text_en": "Governance, legal and published financial summaries.",
            "text_bn": "সুশাসন, আইনগত ও প্রকাশিত আর্থিক সারসংক্ষেপ।",
            "url_name": "transparency",
            "cta_en": "View Transparency",
            "cta_bn": "স্বচ্ছতা দেখুন",
        },
    ],
    "trust_indicators": [
        {"icon": "bi-patch-check", "label_en": "Registered society", "label_bn": "নিবন্ধিত সোসাইটি"},
        {"icon": "bi-bank", "label_en": "Funds held through banking arrangements", "label_bn": "ব্যাংকিং ব্যবস্থায় তহবিল"},
        {"icon": "bi-clipboard-check", "label_en": "Accounts subject to audit", "label_bn": "হিসাব নিরীক্ষার অধীন"},
        {"icon": "bi-people", "label_en": "Member-governed councils", "label_bn": "সদস্য পরিষদ দ্বারা পরিচালিত"},
    ],
}

CTA = {
    "title_en": "Support Zarrah Foundation",
    "title_bn": "জার্‌রাহ ফাউন্ডেশনকে সমর্থন করুন",
    "subtitle_en": (
        "Apply for membership, or make a donation to support the Foundation's documented objectives."
    ),
    "subtitle_bn": (
        "সদস্যপদের জন্য আবেদন করুন, অথবা ফাউন্ডেশনের নথিভুক্ত উদ্দেশ্যে সহায়তায় দান করুন।"
    ),
    "buttons": [
        {
            "icon": "bi-people",
            "text_en": "Become a Member",
            "text_bn": "সদস্য হোন",
            "url_name": "membership-apply",
            "variant": "white",
        },
        {
            "icon": "bi-heart",
            "text_en": "Donate",
            "text_bn": "দান করুন",
            "url_name": "donation",
            "variant": "accent",
        },
        {
            "icon": "bi-envelope",
            "text_en": "Contact Us",
            "text_bn": "যোগাযোগ করুন",
            "url_name": "contact",
            "variant": "outline-white",
        },
    ],
}


def _merge_leadership_from_db(leadership):
    """Public leadership is database-driven. Founder names remain available separately."""
    from community.models import LeadershipPerson, LeadershipRole

    data = {
        **leadership,
        "chairman": None,
        "secretary": None,
        "committee": [],
        "people": [],
    }
    people = list(
        LeadershipPerson.objects.filter(is_published=True).order_by(
            "display_order", "role", "name"
        )
    )
    committee = []
    for person in people:
        card = person.as_card_dict()
        data["people"].append(card)
        if person.role == LeadershipRole.CHAIRMAN and data["chairman"] is None:
            data["chairman"] = card
        elif person.role == LeadershipRole.SECRETARY and data["secretary"] is None:
            data["secretary"] = card
        else:
            committee.append(card)
    data["committee"] = committee
    return data


def resolve_registration_info():
    """SiteSettings is the source of truth for registration number/date."""
    import copy

    reg = copy.deepcopy(REGISTRATION_INFO)
    try:
        from django.utils.formats import date_format

        from core.models import SiteSettings

        settings = SiteSettings.load()
        if settings.registration_number:
            reg["number"] = settings.registration_number
            for row in reg["rows"]:
                if row.get("label_en") == "Registration No.":
                    row["value_en"] = settings.registration_number
                    row["value_bn"] = settings.registration_number
        if settings.registration_date:
            formatted = date_format(settings.registration_date, "j F Y")
            reg["date_en"] = formatted
            reg["date_bn"] = formatted
            reg["date"] = settings.registration_date
            for row in reg["rows"]:
                if row.get("label_en") == "Registered On":
                    row["value_en"] = formatted
                    row["value_bn"] = formatted
        address_en = (settings.address_en or "").strip() or PRINCIPAL_OFFICE_EN.replace("\n", " ")
        address_bn = (settings.address_bn or "").strip() or PRINCIPAL_OFFICE_BN.replace("\n", " ")
        for row in reg["rows"]:
            if row.get("label_en") == "Principal office":
                row["value_en"] = address_en.replace("\n", " ")
                row["value_bn"] = address_bn.replace("\n", " ")
    except Exception:
        pass
    return reg


def get_context():
    leadership = _merge_leadership_from_db(LEADERSHIP)
    registration = resolve_registration_info()
    return {
        "about_hero": HERO,
        "about_who_we_are": WHO_WE_ARE,
        "about_registration": registration,
        "about_mission_vision": MISSION_VISION,
        "about_core_values": CORE_VALUES,
        "about_impact_areas": IMPACT_AREAS,
        "about_timeline": TIMELINE,
        "about_leadership": leadership,
        "about_legal": LEGAL,
        "about_copy": ABOUT_COPY,
        "about_quorum_section": QUORUM_SECTION,
        "about_financial_principles": FINANCIAL_PRINCIPLES,
        "about_cta": CTA,
        "about_structure": ORG_STRUCTURE,
        "about_objectives": OBJECTIVES,
        "about_scope": MOA_AREA,
        "about_nature": MOA_NATURE,
        "about_membership_eligibility": MEMBERSHIP_ELIGIBILITY,
        "about_membership_fees_constitutional": MEMBERSHIP_FEES,
        "about_meetings": MEETINGS_PUBLIC,
        "about_skills": SKILLS,
        "about_quorum": QUORUM,
        "about_quorum_cards": QUORUM_CARDS,
        "about_adjourned": ADJOURNED,
        "about_income_use": MOA_INCOME,
        "about_income_sources": INCOME_SOURCES,
        "about_dissolution": MOA_DISSOLUTION,
        "about_founders": public_founders(),
        "about_office_en": PRINCIPAL_OFFICE_EN,
        "about_office_bn": PRINCIPAL_OFFICE_BN,
        "about_slogan_en": SLOGAN_EN,
        "about_slogan_bn": SLOGAN_BN,
    }
