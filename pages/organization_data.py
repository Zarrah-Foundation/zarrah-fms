"""Verified public organizational facts for zarrah.org.

Sources (only):
  A. Memorandum / Articles already transcribed in ``pages.constitution_data``
  B. SiteSettings / MembershipFeeSettings / LeadershipPerson in the application
  C. Administrator-provided slogan in this sprint: "Small Acts, Lasting Impact"

Do not add impact numbers, programs, partners, testimonials or other claims
that are not in those sources.
"""

from __future__ import annotations

from pages.constitution_data import (
    ADJOURNED,
    EXECUTIVE_POSTS,
    FOUNDERS,
    MEETINGS,
    MEMBERSHIP_ELIGIBILITY,
    MEMBERSHIP_FEES,
    MOA_AREA,
    MOA_DISSOLUTION,
    MOA_INCOME,
    MOA_NATURE,
    MOA_OFFICE,
    OBJECTIVES,
    ORG_STRUCTURE,
    QUORUM,
)

SLOGAN_EN = "Small Acts, Lasting Impact"
SLOGAN_BN = "ক্ষুদ্র অবদান, দীর্ঘস্থায়ী প্রভাব"

NAME_EN = "Zarrah Foundation"
NAME_BN = "জার্‌রাহ ফাউন্ডেশন"

# Principal / registered office — Memorandum Article 2 (line-broken for display).
PRINCIPAL_OFFICE_EN = (
    "Holding No. NA-134,\n"
    "Ward No. 01,\n"
    "Sakhipur Municipality,\n"
    "Post Office: Sakhipur-1950,\n"
    "Upazila: Sakhipur,\n"
    "District: Tangail,\n"
    "Dhaka Division,\n"
    "Bangladesh."
)
PRINCIPAL_OFFICE_BN = (
    "হোল্ডিং নং এনএ-১৩৪,\n"
    "ওয়ার্ড নং ০১,\n"
    "সখিপুর পৌরসভা,\n"
    "পোস্ট অফিস: সখিপুর-১৯৫০,\n"
    "উপজেলা: সখিপুর,\n"
    "জেলা: টাঙ্গাইল,\n"
    "ঢাকা বিভাগ,\n"
    "বাংলাদেশ।"
)

INTRO_EN = (
    "Zarrah Foundation is a voluntary, non-profit, non-political and humanitarian "
    "society formed under the Societies Registration Act, 1860. It exists to support "
    "helpless, disadvantaged and assistance-seeking people through lawful means and "
    "to carry out public-welfare activities."
)
INTRO_BN = (
    "জার্‌রাহ ফাউন্ডেশন সোসাইটি নিবন্ধন আইন, ১৮৬০ এর অধীনে গঠিত একটি স্বেচ্ছাসেবী, "
    "অলাভজনক, অরাজনৈতিক ও মানবকল্যাণমূলক সোসাইটি। এটি আইনসম্মত উপায়ে অসহায়, "
    "সুবিধাবঞ্চিত ও সহায়তাপ্রার্থী মানুষকে সহযোগিতা এবং জনকল্যাণমূলক কার্যক্রম "
    "পরিচালনার জন্য প্রতিষ্ঠিত।"
)

PURPOSE_EN = OBJECTIVES[0]["en"]
PURPOSE_BN = OBJECTIVES[0]["bn"]

NATURE_EN = (
    "Zarrah Foundation is a non-profit, non-political, voluntary and humanitarian "
    "organisation. Its income, donations, assets and funds are used only for its "
    "documented objectives — not for members' personal benefit."
)
NATURE_BN = (
    "জার্‌রাহ ফাউন্ডেশন একটি অলাভজনক, অরাজনৈতিক, স্বেচ্ছাসেবী ও মানবকল্যাণমূলক "
    "প্রতিষ্ঠান। এর আয়, অনুদান, সম্পত্তি ও তহবিল শুধুমাত্র নথিভুক্ত উদ্দেশ্য বাস্তবায়নে "
    "ব্যয় হয় — সদস্যদের ব্যক্তিগত স্বার্থে নয়।"
)

SEO_DESCRIPTION_EN = (
    "Zarrah Foundation (zarrah.org) is a voluntary, non-profit, non-political "
    "humanitarian organisation in Bangladesh. Small Acts, Lasting Impact."
)
SEO_DESCRIPTION_BN = (
    "জার্‌রাহ ফাউন্ডেশন (zarrah.org) বাংলাদেশের একটি স্বেচ্ছাসেবী, অলাভজনক, "
    "অরাজনৈতিক ও মানবকল্যাণমূলক সংস্থা। ক্ষুদ্র অবদান, দীর্ঘস্থায়ী প্রভাব।"
)

OBJECTIVES_PAGE = {
    "title_en": "Objectives",
    "title_bn": "উদ্দেশ্যসমূহ",
    "intro_en": (
        "The following objectives are taken from the Memorandum of Association of "
        "Zarrah Foundation. They describe the organisation's documented purpose. "
        "They are not a list of completed projects."
    ),
    "intro_bn": (
        "নিম্নলিখিত উদ্দেশ্যসমূহ জার্‌রাহ ফাউন্ডেশনের সংঘস্মারক থেকে গৃহীত। "
        "এগুলো প্রতিষ্ঠানের নথিভুক্ত উদ্দেশ্য বর্ণনা করে — সম্পন্ন প্রকল্পের তালিকা নয়।"
    ),
    "areas_note_en": (
        "These headings group the same documented objectives for readability. "
        "They do not add programmes beyond the Memorandum."
    ),
    "areas_note_bn": (
        "এই শিরোনামগুলো একই নথিভুক্ত উদ্দেশ্যকে পাঠযোগ্যভাবে গুচ্ছ করে। "
        "গঠনতন্ত্রের বাইরে নতুন কর্মসূচি যোগ করা হয়নি।"
    ),
    "source_title_en": "As recorded in the Memorandum",
    "source_title_bn": "সংঘস্মারকে নথিভুক্ত উদ্দেশ্য",
}

SKILLS_URL = "https://skills.zarrah.org/"
SKILLS = {
    "title_en": "Zarrah Skills",
    "title_bn": "জার্‌রাহ স্কিলস",
    "text_en": "Skills, training and learning portal of Zarrah Foundation.",
    "text_bn": "জার্‌রাহ ফাউন্ডেশনের দক্ষতা উন্নয়ন ও প্রশিক্ষণ পোর্টাল।",
    "url": SKILLS_URL,
}

# Public meeting cadence — administrator-confirmed reading of the Memorandum.
# Do not describe Advisory or Executive Council meetings as monthly.
MEETINGS_PUBLIC = {
    "title_en": "Calling of Meetings",
    "title_bn": "সভা আহ্বান",
    "intro_en": (
        "The Memorandum sets the following meeting rules. Digital tools on this "
        "website are used to keep records; they are not themselves legal authority."
    ),
    "intro_bn": (
        "গঠনতন্ত্রে নিম্নলিখিত সভার নিয়ম নির্ধারিত। এই ওয়েবসাইটের ডিজিটাল সরঞ্জাম "
        "রেকর্ড সংরক্ষণে ব্যবহৃত হয়; সেগুলো নিজে আইনগত কর্তৃত্ব নয়।"
    ),
    "items": [
        {
            "en": "Executive Council meetings: at least once every three months",
            "bn": "কার্যনির্বাহী পরিষদের সভা: সর্বোচ্চ তিন মাসের মধ্যে অন্তত একবার",
        },
        {
            "en": "Advisory Council meeting: at least once annually",
            "bn": "উপদেষ্টা পরিষদের সভা: বছরে অন্তত একবার",
        },
        {
            "en": "AGM: at least once annually",
            "bn": "সাধারণ পরিষদের বার্ষিক সাধারণ সভা (AGM): বছরে অন্তত একবার",
        },
        {
            "en": "Emergency meeting: may be called with 24 hours' notice",
            "bn": "জরুরি সভা: ২৪ ঘণ্টার নোটিশে আহ্বান করা যেতে পারে",
        },
        {
            "en": "Virtual/Online meetings are permitted under the organization's rules",
            "bn": "ভার্চুয়াল/অনলাইন সভার ব্যবস্থা করা যেতে পারে",
        },
    ],
}

# Presentation groupings of documented objectives — not separate programmes.
AREAS_OF_WORK = [
    {
        "icon": "bi-heart",
        "title_en": "Humanitarian Support",
        "title_bn": "মানবিক সহায়তা",
        "text_en": OBJECTIVES[0]["en"],
        "text_bn": OBJECTIVES[0]["bn"],
    },
    {
        "icon": "bi-mortarboard",
        "title_en": "Education & Training",
        "title_bn": "শিক্ষা ও প্রশিক্ষণ",
        "text_en": OBJECTIVES[8]["en"],
        "text_bn": OBJECTIVES[8]["bn"],
    },
    {
        "icon": "bi-tools",
        "title_en": "Skills & Employment",
        "title_bn": "দক্ষতা ও কর্মসংস্থান",
        "text_en": OBJECTIVES[3]["en"],
        "text_bn": OBJECTIVES[3]["bn"],
    },
    {
        "icon": "bi-hospital",
        "title_en": "Health & Blood Donation",
        "title_bn": "স্বাস্থ্যসেবা ও রক্তদান",
        "text_en": OBJECTIVES[7]["en"],
        "text_bn": OBJECTIVES[7]["bn"],
    },
    {
        "icon": "bi-cloud-lightning-rain",
        "title_en": "Disaster Response & Rehabilitation",
        "title_bn": "দুর্যোগ মোকাবিলা ও পুনর্বাসন",
        "text_en": OBJECTIVES[6]["en"],
        "text_bn": OBJECTIVES[6]["bn"],
    },
    {
        "icon": "bi-emoji-smile",
        "title_en": "Child & Youth Support",
        "title_bn": "শিশু ও কিশোর সহায়তা",
        "text_en": OBJECTIVES[8]["en"],
        "text_bn": OBJECTIVES[8]["bn"],
    },
    {
        "icon": "bi-shield-exclamation",
        "title_en": "Drug Awareness & Rehabilitation",
        "title_bn": "মাদক সচেতনতা ও পুনর্বাসন",
        "text_en": OBJECTIVES[4]["en"],
        "text_bn": OBJECTIVES[4]["bn"],
    },
    {
        "icon": "bi-people",
        "title_en": "Social Awareness & Development",
        "title_bn": "সামাজিক সচেতনতা ও উন্নয়ন",
        "text_en": OBJECTIVES[2]["en"],
        "text_bn": OBJECTIVES[2]["bn"],
    },
    {
        "icon": "bi-briefcase",
        "title_en": "Employment & Entrepreneurship",
        "title_bn": "কর্মসংস্থান ও উদ্যোক্তা সহায়তা",
        "text_en": OBJECTIVES[3]["en"],
        "text_bn": OBJECTIVES[3]["bn"],
    },
]

OBJECTIVE_CATEGORIES = [
    {
        "key": "humanitarian",
        "title_en": "Humanitarian Assistance",
        "title_bn": "মানবিক সহায়তা",
        "codes": ("ক", "খ"),
    },
    {
        "key": "education",
        "title_en": "Education & Skills",
        "title_bn": "শিক্ষা ও দক্ষতা",
        "codes": ("ঘ", "ঝ"),
    },
    {
        "key": "health",
        "title_en": "Health",
        "title_bn": "স্বাস্থ্য",
        "codes": ("জ",),
    },
    {
        "key": "children",
        "title_en": "Children & Youth",
        "title_bn": "শিশু ও কিশোর",
        "codes": ("ঝ", "ঞ"),
    },
    {
        "key": "disaster",
        "title_en": "Disaster Response",
        "title_bn": "দুর্যোগ মোকাবিলা",
        "codes": ("ছ",),
    },
    {
        "key": "awareness",
        "title_en": "Social Awareness",
        "title_bn": "সামাজিক সচেতনতা",
        "codes": ("গ", "ঞ"),
    },
    {
        "key": "rehab",
        "title_en": "Rehabilitation",
        "title_bn": "পুনর্বাসন",
        "codes": ("ঙ", "ছ", "ঝ"),
    },
    {
        "key": "partners",
        "title_en": "Coordination & Partnerships",
        "title_bn": "সহযোগিতা ও সমন্বয়",
        "codes": ("চ",),
    },
]


def categorized_objectives():
    by_code = {item["code"]: item for item in OBJECTIVES}
    groups = []
    for cat in OBJECTIVE_CATEGORIES:
        items = [by_code[c] for c in cat["codes"] if c in by_code]
        if items:
            groups.append({**cat, "items": items})
    return groups


INCOME_SOURCES = {
    "title_en": "Documented funding sources",
    "title_bn": "নথিভুক্ত অর্থের উৎস",
    "intro_en": (
        "The Memorandum identifies possible sources of funds. Listing them here "
        "does not mean every source is currently being received."
    ),
    "intro_bn": (
        "গঠনতন্ত্রে সম্ভাব্য অর্থের উৎস উল্লেখ আছে। এখানে তালিকাভুক্তির অর্থ এই নয় যে "
        "প্রতিটি উৎস বর্তমানে গ্রহণ করা হচ্ছে।"
    ),
    "items": [
        {"en": "Membership admission fees", "bn": "সদস্যপদের ভর্তি ফি"},
        {"en": "Membership subscriptions", "bn": "সদস্য চাঁদা"},
        {"en": "Government or private grants", "bn": "সরকারি বা বেসরকারি অনুদান"},
        {"en": "Individual donations", "bn": "ব্যক্তিগত অনুদান"},
        {"en": "Special funds", "bn": "বিশেষ তহবিল"},
        {"en": "Special programmes", "bn": "বিশেষ কর্মসূচি"},
        {"en": "Other lawful income sources", "bn": "অন্যান্য আইনসম্মত আয়"},
    ],
}

QUORUM_SECTION = {
    "title_en": "Meeting Quorum",
    "title_bn": "সভায় কোরাম",
    "intro_en": (
        "The quorum requirement varies according to the council or general "
        "meeting concerned."
    ),
    "intro_bn": "সভা বা পরিষদের ধরন অনুযায়ী কোরামের প্রয়োজনীয়তা নির্ধারিত হয়।",
}

QUORUM_CARDS = [
    {
        "title_en": "Executive Council",
        "title_bn": "কার্যনির্বাহী পরিষদ",
        "ratio": "2/3",
        "caption_en": "of total members",
        "caption_bn": "মোট সদস্যের ২/৩",
        "detail_en": (
            "Two-thirds of the total members must be present to fulfill the quorum."
        ),
        "detail_bn": "কোরাম পূরণের জন্য মোট সদস্যের দুই-তৃতীয়াংশের উপস্থিতি প্রয়োজন।",
        "value_en": "2/3 of total members",
        "value_bn": "মোট সদস্যের ২/৩",
    },
    {
        "title_en": "Advisory Council",
        "title_bn": "উপদেষ্টা পরিষদ",
        "ratio": "2/3",
        "caption_en": "of total members",
        "caption_bn": "মোট সদস্যের ২/৩",
        "detail_en": (
            "Two-thirds of the total members must be present to fulfill the quorum."
        ),
        "detail_bn": "কোরাম পূরণের জন্য মোট সদস্যের দুই-তৃতীয়াংশের উপস্থিতি প্রয়োজন।",
        "value_en": "2/3 of total members",
        "value_bn": "মোট সদস্যের ২/৩",
    },
    {
        "title_en": "General Council / AGM",
        "title_bn": "সাধারণ পরিষদ / AGM",
        "ratio": "1/3",
        "caption_en": "of total listed members",
        "caption_bn": "তালিকাভুক্ত মোট সদস্যের ১/৩",
        "detail_en": (
            "One-third of the total listed members must be present to fulfill the quorum."
        ),
        "detail_bn": (
            "কোরাম পূরণের জন্য তালিকাভুক্ত মোট সদস্যের এক-তৃতীয়াংশের উপস্থিতি প্রয়োজন।"
        ),
        "value_en": "1/3 of total listed members",
        "value_bn": "তালিকাভুক্ত মোট সদস্যের ১/৩",
    },
]

FINANCIAL_PRINCIPLES = {
    "title_en": "Financial Principles",
    "title_bn": "আর্থিক নীতিমালা",
    "intro_en": (
        "The following points present the Foundation's documented rules on income, "
        "property and accountability. They do not add claims beyond those rules."
    ),
    "intro_bn": (
        "নিম্নলিখিত বিষয়গুলো আয়, সম্পত্তি ও জবাবদিহিতা সংক্রান্ত ফাউন্ডেশনের নথিভুক্ত "
        "বিধি উপস্থাপন করে। এগুলো সেই বিধির বাইরে নতুন দাবি যোগ করে না।"
    ),
    "points": [
        {
            "title_en": "Purpose-bound funds",
            "title_bn": "উদ্দেশ্যভিত্তিক তহবিল",
            "text_en": (
                "Foundation income, donations, assets and funds are dedicated to the "
                "Foundation's objectives."
            ),
            "text_bn": (
                "ফাউন্ডেশনের আয়, অনুদান, সম্পদ ও তহবিল প্রতিষ্ঠানের উদ্দেশ্য বাস্তবায়নে "
                "ব্যবহারের জন্য নিবেদিত।"
            ),
        },
        {
            "title_en": "No personal distribution",
            "title_bn": "ব্যক্তিগত বণ্টন নিষিদ্ধ",
            "text_en": (
                "Members, founders and officers cannot personally receive the "
                "Foundation's income, property or profit."
            ),
            "text_bn": (
                "সদস্য, প্রতিষ্ঠাতা ও কর্মকর্তারা ব্যক্তিগতভাবে ফাউন্ডেশনের আয়, সম্পদ বা "
                "মুনাফা গ্রহণ করতে পারেন না।"
            ),
        },
        {
            "title_en": "Banking-based fund management",
            "title_bn": "ব্যাংকিং ব্যবস্থায় তহবিল সংরক্ষণ",
            "text_en": "Funds are maintained through banking arrangements.",
            "text_bn": "প্রতিষ্ঠানের তহবিল ব্যাংকিং ব্যবস্থার মাধ্যমে সংরক্ষণ করা হয়।",
        },
        {
            "title_en": "Audit / accountability",
            "title_bn": "নিরীক্ষা ও জবাবদিহিতা",
            "text_en": (
                "Accounts are subject to audit according to the organisation's rules."
            ),
            "text_bn": "প্রতিষ্ঠানের বিধিবিধান অনুযায়ী হিসাব নিরীক্ষার আওতাভুক্ত।",
        },
    ],
}

TRANSPARENCY_PAGE = {
    "eyebrow_en": "Transparency",
    "eyebrow_bn": "স্বচ্ছতা",
    "title_en": "Transparency & Accountability",
    "title_bn": "স্বচ্ছতা ও জবাবদিহিতা",
    "intro_en": (
        "Governance, legal and published financial information. Private ledgers are "
        "not shown. Organizational rules come from the Memorandum; digital tools on "
        "this site are used to keep records."
    ),
    "intro_bn": (
        "সুশাসন, আইনগত নথি এবং প্রকাশিত আর্থিক তথ্য এখানে উপস্থাপন করা হয়। "
        "ব্যক্তিগত ও অভ্যন্তরীণ হিসাব-খাতা প্রকাশ করা হয় না। "
        "প্রতিষ্ঠানের সাংগঠনিক বিধিবিধানের ভিত্তি হলো স্মারকলিপি; "
        "এই ওয়েবসাইটের ডিজিটাল সরঞ্জামগুলো তথ্য ও নথি সংরক্ষণে ব্যবহৃত হয়।"
    ),
    "summaries_note_en": (
        "Financial summaries are published periodically as available. These figures "
        "are organizational summaries, not audited reports, unless a published "
        "document is itself an audit report."
    ),
    "summaries_note_bn": (
        "আর্থিক সারসংক্ষেপ সময় সময় প্রকাশিত হয়, যেখানে উপলব্ধ। এই সংখ্যাগুলো "
        "সাংগঠনিক সারসংক্ষেপ — নিরীক্ষিত প্রতিবেদন নয়, যদি না প্রকাশিত দলিলটি নিজেই "
        "একটি নিরীক্ষা প্রতিবেদন হয়।"
    ),
    "governance_intro_en": "Constitution, registration, policies and governance documents.",
    "governance_intro_bn": "গঠনতন্ত্র, নিবন্ধন, নীতিমালা ও সুশাসন সংক্রান্ত নথি।",
    "other_intro_en": "Additional transparency documents selected by the foundation.",
    "other_intro_bn": "ফাউন্ডেশন কর্তৃক নির্বাচিত অতিরিক্ত স্বচ্ছতা সংক্রান্ত নথি।",
}

REPORTS_PAGE = {
    "eyebrow_en": "Publications",
    "eyebrow_bn": "প্রকাশনা",
    "title_en": "Reports & Publications",
    "title_bn": "প্রতিবেদন ও প্রকাশনা",
    "intro_en": "Annual reports, activity reports and other public publications.",
    "intro_bn": "বার্ষিক প্রতিবেদন, কার্যক্রম প্রতিবেদন এবং অন্যান্য পাবলিক প্রকাশনা।",
}


def principal_office(lang="en"):
    return PRINCIPAL_OFFICE_BN if lang == "bn" else PRINCIPAL_OFFICE_EN


def public_founders():
    """Names and public designations from the Memorandum only — no private data."""
    return list(FOUNDERS)


def executive_sample_posts():
    """Sample Executive Council posts from the Memorandum (not occupancy claims)."""
    return list(EXECUTIVE_POSTS)


__all__ = [
    "ADJOURNED",
    "AREAS_OF_WORK",
    "INCOME_SOURCES",
    "INTRO_BN",
    "INTRO_EN",
    "MEETINGS_PUBLIC",
    "MEETINGS",
    "SKILLS",
    "SKILLS_URL",
    "MEMBERSHIP_ELIGIBILITY",
    "MEMBERSHIP_FEES",
    "MOA_AREA",
    "MOA_DISSOLUTION",
    "MOA_INCOME",
    "MOA_NATURE",
    "MOA_OFFICE",
    "NAME_BN",
    "NAME_EN",
    "NATURE_BN",
    "NATURE_EN",
    "OBJECTIVES",
    "OBJECTIVES_PAGE",
    "ORG_STRUCTURE",
    "PRINCIPAL_OFFICE_BN",
    "PRINCIPAL_OFFICE_EN",
    "PURPOSE_BN",
    "PURPOSE_EN",
    "QUORUM",
    "QUORUM_CARDS",
    "QUORUM_SECTION",
    "FINANCIAL_PRINCIPLES",
    "TRANSPARENCY_PAGE",
    "REPORTS_PAGE",
    "SEO_DESCRIPTION_BN",
    "SEO_DESCRIPTION_EN",
    "SLOGAN_BN",
    "SLOGAN_EN",
    "categorized_objectives",
    "executive_sample_posts",
    "principal_office",
    "public_founders",
]
