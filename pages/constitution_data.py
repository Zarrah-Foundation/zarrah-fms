"""Structured bilingual content for the Constitution page.

Source of truth: Memorandum of Association & Articles of Association of
Zarrah Foundation (Societies Registration Act, 1860).

The official PDF lives at::

    media/Memorandum of Association of Zarrah Foundation.pdf

Privacy: founding-member personal data (NID, TIN, phone, email, address,
date of birth, signatures) is intentionally omitted from this public page.
"""

from urllib.parse import quote

# Public download path for the registered PDF (spaces encoded).
PDF_FILENAME = "Memorandum of Association of Zarrah Foundation.pdf"
PDF_MEDIA_PATH = f"/media/{quote(PDF_FILENAME)}"

# Display metadata for the official download card (UI only — not legal text).
PDF_META = {
    "size_label": "PDF",
    "size_approx": "~1.5 MB",
    "updated_bn": "০২ জুলাই ২০২৬",
    "updated_en": "02 July 2026",
    "pages_label": "15 pages",
}

# Official registration facts already published on the About page.
REGISTRATION = {
    "act_bn": "সোসাইটি নিবন্ধন আইন, ১৮৬০ (১৮৬০ সালের ২১ নং আইন)",
    "act_en": "The Societies Registration Act, 1860 (Act No. XXI of 1860)",
    "number": "S-15000/2026",
    "date_bn": "০২ জুলাই ২০২৬",
    "date_en": "02 July 2026",
}

HERO = {
    "eyebrow_bn": "সোসাইটি নিবন্ধন আইন, ১৮৬০",
    "eyebrow_en": "Societies Registration Act, 1860",
    "title_bn": "গঠনতন্ত্র",
    "title_en": "Constitution",
    "subtitle_bn": (
        "জাররাহ ফাউন্ডেশনের সংঘস্মারক ও গঠনতন্ত্র — সংস্থার নাম, উদ্দেশ্য, সদস্যপদ, "
        "সাংগঠনিক কাঠামো, অর্থব্যবস্থা এবং পরিচালনা সংক্রান্ত আনুষ্ঠানিক বিধান।"
    ),
    "subtitle_en": (
        "The Memorandum of Association and Articles of Association of Zarrah Foundation — "
        "the official rules governing our name, objectives, membership, organisational "
        "structure, finances and governance."
    ),
}

ABOUT = {
    "title_bn": "গঠনতন্ত্র সম্পর্কে",
    "title_en": "About the Constitution",
    "bn": (
        "বর্তমান সমাজে বিরাজমান নানাবিধ অবক্ষয় রোধ এবং মানবিক মূল্যবোধের বিকাশে একটি "
        "স্বেচ্ছাসেবী ও জনকল্যাণমূলক প্রতিষ্ঠানের প্রয়োজনীয়তা অনস্বীকার্য। সমাজের একটি বড় "
        "অংশ বেকারত্ব ও দারিদ্র্যের কষাঘাতে জর্জরিত। মানুষের মৌলিক চাহিদা, বিশেষত খাদ্যের "
        "অভাব তার নৈতিক, সামাজিক ও মানবিক জীবনকে মারাত্মকভাবে ব্যাহত করে। তাই সমাজের অসহায় ও "
        "সুবিধাবঞ্চিত মানুষের মৌলিক অধিকার নিশ্চিতকরণ, কর্মসংস্থান সৃষ্টির মাধ্যমে বেকারত্ব দূরীকরণ "
        "এবং সর্বপরি একটি মানবিক ও স্বনির্ভর সমাজ গঠনের মহান ব্রত নিয়ে "
        "'জার্‌রাহ ফাউন্ডেশন (Zarrah Foundation)'-এর আত্মপ্রকাশ।"
    ),
    "en": (
        "There is an undeniable need for a voluntary and public welfare institution "
        "the various depredations prevailing in the present society and to develop human values. "
        "A large section of the society is suffering from poverty and unemployment. "
        "The lack of basic human needs, especially food, severely disrupts its moral, "
        "social and human life. Hence, the Zarrah Foundation's great pledge to ensure "
        "the basic rights of the helpless and disadvantaged people of the society, "
        "to eliminate unemployment by creating jobs, and above all to build a humane "
        "and self-reliant society."
    ),
}

# ---- Memorandum of Association ----

MOA_NAME = {
    "clause_bn": "ধারা-১",
    "clause_en": "Article 1",
    "title_bn": "নামকরণ",
    "title_en": "Name",
    "bn": "এই প্রতিষ্ঠানের নাম বাংলায়: জার্‌রাহ ফাউন্ডেশন; ইংরেজিতে: Zarrah Foundation।",
    "en": "The name of this institution is, in Bangla: জার্‌রাহ ফাউন্ডেশন; and in English: Zarrah Foundation.",
}

MOA_OFFICE = {
    "clause_bn": "ধারা-২",
    "clause_en": "Article 2",
    "title_bn": "ঠিকানা",
    "title_en": "Registered Office",
    "bn": (
        "প্রধান কার্যালয়ের ঠিকানা: হোল্ডিং নং এনএ-১৩৪, ওয়ার্ড নং ০১, পৌরসভা: সখিপুর পৌরসভা, "
        "পোস্ট: সখিপুর-১৯৫০, উপজেলা: সখিপুর, জেলা: টাঙ্গাইল, বিভাগ: ঢাকা, বাংলাদেশ। "
        "কার্যনির্বাহী পরিষদের সিদ্ধান্তক্রমে এবং যথাযথ কর্তৃপক্ষের অনুমতিক্রমে প্রধান কার্যালয় "
        "স্থানান্তর এবং দেশের যেকোনো স্থানে শাখা কার্যালয় স্থাপন করা যাবে।"
    ),
    "en": (
        "Head office address: Holding No. NA-134, Ward No. 01, Sakhipur Municipality, "
        "Post: Sakhipur-1950, Upazila: Sakhipur, District: Tangail, Division: Dhaka, Bangladesh. "
        "Subject to a decision of the Executive Council and approval of the competent authority, "
        "the head office may be relocated and branch offices may be established anywhere in the country."
    ),
}

MOA_AREA = {
    "clause_bn": "ধারা-৩",
    "clause_en": "Article 3",
    "title_bn": "কার্য এলাকা",
    "title_en": "Operational Area",
    "bn": (
        "প্রতিষ্ঠানের কার্যক্রম বাংলাদেশের সর্বত্র পরিচালিত হবে। প্রয়োজনবোধে আইনানুগ প্রক্রিয়া "
        "অনুসরণপূর্বক আন্তর্জাতিক পর্যায়েও কার্যক্রম পরিচালনা করা যাবে।"
    ),
    "en": (
        "The Foundation's activities shall be carried out throughout Bangladesh. Where necessary, "
        "and following lawful procedures, programmes may also be conducted internationally."
    ),
}

MOA_NATURE = {
    "clause_bn": "ধারা-৪",
    "clause_en": "Article 4",
    "title_bn": "প্রতিষ্ঠানের প্রকৃতি",
    "title_en": "Nature of the Organisation",
    "items": [
        {"bn": "অলাভজনক (Non-Profit)", "en": "Non-Profit", "icon": "bi-heart"},
        {"bn": "অরাজনৈতিক (Non-Political)", "en": "Non-Political", "icon": "bi-shield-check"},
        {"bn": "স্বেচ্ছাসেবী (Voluntary)", "en": "Voluntary", "icon": "bi-hand-thumbs-up"},
        {"bn": "মানবকল্যাণমূলক (Humanitarian)", "en": "Humanitarian", "icon": "bi-people"},
    ],
}

OBJECTIVES = [
    {
        "code": "ক",
        "icon": "bi-heart-pulse",
        "title_bn": "মানবিক সহায়তা",
        "title_en": "Humanitarian Assistance",
        "bn": "আইনসম্মত উপায়ে অসহায়, সুবিধাবঞ্চিত ও প্রয়োজনীয় সহায়তাপ্রার্থী মানুষকে সহযোগিতা করা সোসাইটির প্রথম ও প্রধান লক্ষ্য হবে।",
        "en": "Assisting helpless, disadvantaged and needy persons through lawful means shall be the first and primary objective of the Society.",
    },
    {
        "code": "খ",
        "icon": "bi-people-fill",
        "title_bn": "নিঃস্বার্থ জনকল্যাণ",
        "title_en": "Selfless Public Welfare",
        "bn": (
            "সোসাইটি এবং সংশ্লিষ্ট সদস্যবৃন্দ নিঃস্বার্থভাবে ও জনকল্যাণমূলক উদ্দেশ্যে কাজ করবে। "
            "সোসাইটি সম্পূর্ণ অরাজনৈতিক, অলাভজনক ও মানবকল্যাণমূলক প্রতিষ্ঠান হিসেবে পরিচালিত হবে "
            "এবং কোনো রাজনৈতিক দল, প্রার্থী বা রাজনৈতিক কার্যক্রমের সাথে প্রত্যক্ষ বা পরোক্ষভাবে "
            "সম্পৃক্ত থাকবে না।"
        ),
        "en": (
            "The Society and its members shall work selflessly for public welfare. The Society shall "
            "operate entirely as a non-political, non-profit and humanitarian institution and shall not "
            "be associated, directly or indirectly, with any political party, candidate or political programme."
        ),
    },
    {
        "code": "গ",
        "icon": "bi-building",
        "title_bn": "সামাজিক উন্নয়ন",
        "title_en": "Community Development",
        "bn": "সামাজিক সচেতনতা, মানবিক উন্নয়ন ও সামাজিক উন্নয়নমূলক কার্যক্রম পরিচালনা করবে।",
        "en": "It shall conduct programmes on social awareness, human development and community development.",
    },
    {
        "code": "ঘ",
        "icon": "bi-tools",
        "title_bn": "দক্ষতা উন্নয়ন ও উদ্যোক্তা তৈরি",
        "title_en": "Skill Development & Entrepreneurship",
        "bn": (
            "বেকারত্ব হ্রাস এবং আত্মকর্মসংস্থানের সুযোগ সৃষ্টির লক্ষ্যে পেশাগত, কারিগরি ও দক্ষতা "
            "উন্নয়নমূলক প্রশিক্ষণ কার্যক্রম পরিচালনা করা এবং উদ্যোক্তা উন্নয়নমূলক সহায়তা প্রদান।"
        ),
        "en": (
            "To reduce unemployment and create self-employment opportunities, it shall run vocational, "
            "technical and skill-development training programmes and provide entrepreneurship support."
        ),
    },
    {
        "code": "ঙ",
        "icon": "bi-shield-exclamation",
        "title_bn": "মাদকবিরোধী সচেতনতা",
        "title_en": "Anti-Drug Awareness",
        "bn": "মাদকবিরোধী সচেতনতামূলক ও পুনর্বাসন সহায়ক কার্যক্রম পরিচালনা করা।",
        "en": "It shall conduct anti-drug awareness and rehabilitation-support programmes.",
    },
    {
        "code": "চ",
        "icon": "bi-globe2",
        "title_bn": "সহযোগিতা ও সমন্বয়",
        "title_en": "Partnership & Coordination",
        "bn": (
            "স্থানীয়, জাতীয় এবং আন্তর্জাতিক সমাজসেবামূলক প্রতিষ্ঠানগুলোর মধ্যে যোগাযোগ প্রতিষ্ঠার "
            "মাধ্যমে সেবামূলক কাজে পারস্পরিক সহযোগিতা ও সমন্বয় বৃদ্ধি করা।"
        ),
        "en": (
            "It shall strengthen mutual cooperation and coordination in welfare work by establishing "
            "links among local, national and international social-service organisations."
        ),
    },
    {
        "code": "ছ",
        "icon": "bi-cloud-lightning-rain",
        "title_bn": "দুর্যোগ ত্রাণ",
        "title_en": "Disaster Relief",
        "bn": "দেশের বিভিন্ন দুর্যোগে ক্ষতিগ্রস্ত মানুষকে আর্থিক, মানবিক সহায়তা প্রদান করে তাদের পুনর্বাসন ত্বরান্বিত করা।",
        "en": "It shall provide economic and humanitarian assistance to people affected by disasters across the country and accelerate their rehabilitation.",
    },
    {
        "code": "জ",
        "icon": "bi-hospital",
        "title_bn": "স্বাস্থ্যসেবা ও রক্তদান",
        "title_en": "Healthcare & Blood Donation",
        "bn": (
            "স্বাস্থ্যসেবা সহায়তা, চিকিৎসা পরামর্শ, স্বাস্থ্য সচেতনতা, রক্তদান কার্যক্রম পরিচালনা করা "
            "এবং পাশাপাশি দুরারোগ্য রোগে আক্রান্ত অসহায় ব্যক্তিকে আর্থিক সহায়তা প্রদান।"
        ),
        "en": (
            "It shall provide healthcare assistance, medical advice, health awareness and blood-donation "
            "programmes, and financial support to helpless persons suffering from incurable diseases."
        ),
    },
    {
        "code": "ঝ",
        "icon": "bi-mortarboard",
        "title_bn": "শিক্ষা ও শিশু পুনর্বাসন",
        "title_en": "Education & Child Rehabilitation",
        "bn": (
            "এতিম, পথশিশু ও সুবিধাবঞ্চিত শিশু-কিশোরদের পুনর্বাসন, শিক্ষা, মানবিক সহায়তা এবং "
            "দক্ষতা উন্নয়নমূলক কার্যক্রম পরিচালনা করা।"
        ),
        "en": (
            "It shall run rehabilitation, education, humanitarian assistance and skill-development "
            "programmes for orphans, street children and disadvantaged children and adolescents."
        ),
    },
    {
        "code": "ঞ",
        "icon": "bi-person-arms-up",
        "title_bn": "সামাজিক সুরক্ষা",
        "title_en": "Social Protection",
        "bn": (
            "শিশু শ্রম, শিশু অপরাধ, মাদকাসক্তি ও সামাজিক অবক্ষয় রোধে সচেতনতামূলক, প্রতিরোধমূলক "
            "ও পুনর্বাসন সহায়ক কার্যক্রম পরিচালনা করা এবং এ বিষয়ে কার্যকরী ভূমিকা পালন করা।"
        ),
        "en": (
            "It shall conduct awareness, prevention and rehabilitation programmes on child labour, "
            "child abuse, drug addiction and social ills, and play an effective role in these areas."
        ),
    },
    {
        "code": "ট",
        "icon": "bi-wallet2",
        "title_bn": "আয় ও সম্পত্তির সীমাবদ্ধতা",
        "title_en": "Non-Distribution of Income",
        "bn": (
            "সোসাইটির অর্জিত কোনো আয়, মুনাফা বা সম্পত্তি কোনো সদস্য ব্যক্তিগতভাবে গ্রহণ করতে পারবেন না। "
            "সকল আয় ও সম্পত্তি শুধুমাত্র সোসাইটির লক্ষ্য ও উদ্দেশ্য বাস্তবায়নে ব্যয় করা হবে।"
        ),
        "en": (
            "No member may personally receive any income, profit or property of the Society. "
            "All income and assets shall be used solely to advance the Society's aims and objects."
        ),
    },
]

MOA_INCOME = {
    "clause_bn": "ধারা-৬",
    "clause_en": "Article 6",
    "title_bn": "আয় ও সম্পত্তির ব্যবহার",
    "title_en": "Use of Income & Assets",
    "bn": (
        "প্রতিষ্ঠানের সকল আয়, অনুদান, সম্পত্তি ও তহবিল সকলক্ষেত্রে শুধুমাত্র প্রতিষ্ঠানের লক্ষ্য ও "
        "উদ্দেশ্য বাস্তবায়নে ব্যয় করা হবে। কোনো সদস্য, প্রতিষ্ঠাতা, কর্মকর্তা বা ব্যক্তি প্রতিষ্ঠানের "
        "আয়, সম্পত্তি বা মুনাফা ব্যক্তিগতভাবে গ্রহণ বা ভোগ করতে পারবেন না।"
    ),
    "en": (
        "All income, grants, property and funds of the Foundation shall be applied solely towards "
        "its aims and objects. No member, founder, officer or person may personally receive or enjoy "
        "the Foundation's income, property or profit."
    ),
}

MOA_DISSOLUTION = {
    "clause_bn": "ধারা-৭",
    "clause_en": "Article 7",
    "title_bn": "বিলুপ্তি ধারা",
    "title_en": "Dissolution Clause",
    "bn": (
        "প্রতিষ্ঠান বিলুপ্ত হলে সকল দায়-দেনা পরিশোধের পর অবশিষ্ট সম্পত্তি বা অর্থ "
        "“The Societies Registration Act, 1860” অনুযায়ী সমজাতীয় উদ্দেশ্যসম্পন্ন অন্য কোনো "
        "নিবন্ধিত অলাভজনক প্রতিষ্ঠানের নিকট হস্তান্তর করা হবে। কোনো সদস্য ব্যক্তিগতভাবে উক্ত "
        "সম্পত্তির অংশীদার হবেন না।"
    ),
    "en": (
        "If the Foundation is dissolved, after settlement of all liabilities any remaining property "
        "or funds shall, in accordance with the Societies Registration Act, 1860, be transferred to "
        "another registered non-profit organisation with similar objects. No member shall personally "
        "share in such property."
    ),
}

FOUNDERS = [
    {"name": "MD. BABUL HOSSAIN", "role_bn": "চেয়ারম্যান ও প্রতিষ্ঠাতা সদস্য", "role_en": "Chairman & Founder Member"},
    {"name": "IMROZ AHMAD", "role_bn": "সচিব ও প্রতিষ্ঠাতা সদস্য", "role_en": "Secretary & Founder Member"},
    {"name": "MD. TANVIR AHMED", "role_bn": "প্রতিষ্ঠাতা সদস্য", "role_en": "Founder Member"},
    {"name": "TANVIR AHMAD", "role_bn": "প্রতিষ্ঠাতা সদস্য", "role_en": "Founder Member"},
    {"name": "MD. TANIQUR RAHMAN", "role_bn": "প্রতিষ্ঠাতা সদস্য", "role_en": "Founder Member"},
    {"name": "ASIFUR RAHMAN AKASH", "role_bn": "প্রতিষ্ঠাতা সদস্য", "role_en": "Founder Member"},
    {"name": "AL-AMIN", "role_bn": "সদস্য", "role_en": "Member"},
    {"name": "MD MAINE UDDIN", "role_bn": "সদস্য", "role_en": "Member"},
    {"name": "MD MUJAHID ISLAM", "role_bn": "সদস্য", "role_en": "Member"},
]

FOUNDERS_INTRO = {
    "bn": "জাররাহ ফাউন্ডেশন প্রতিষ্ঠায় স্বাক্ষরকারী সদস্যবৃন্দ — যাঁদের নেতৃত্ব ও অঙ্গীকারে এই সংস্থা গঠিত হয়েছে।",
    "en": "The subscribers who established Zarrah Foundation — whose leadership and commitment founded this organisation.",
}

FOUNDERS_PRIVACY = {
    "bn": "গোপনীয়তার স্বার্থে জাতীয় পরিচয়পত্র, ফোন নম্বর, ঠিকানা, ইমেইল, টিআইএন, জন্মতারিখ ও স্বাক্ষর এই পাবলিক সংস্করণে ইচ্ছাকৃতভাবে বাদ দেওয়া হয়েছে।",
    "en": "For privacy reasons, National ID, phone number, address, email, TIN, date of birth and signatures are intentionally omitted from the public version of this Constitution.",
}


def _founder_card(person):
    """Presentation helpers only — names and designations are unchanged."""
    role = person["role_en"]
    skip = {"MD", "MD.", "M.D.", "M.D"}
    words = [w for w in person["name"].replace(".", " ").split() if w.upper() not in skip and w]
    initials = "".join(w[0] for w in words[:2]).upper() or person["name"][:1].upper()

    if "Chairman" in role:
        badge_bn, badge_en, tier = "চেয়ারম্যান", "Chairman", "chairman"
    elif "Secretary" in role:
        badge_bn, badge_en, tier = "সচিব", "Secretary", "secretary"
    elif "Treasurer" in role:
        badge_bn, badge_en, tier = "কোষাধ্যক্ষ", "Treasurer", "officer"
    elif "Founder" in role:
        badge_bn, badge_en, tier = "প্রতিষ্ঠাতা সদস্য", "Founder Member", "founder"
    else:
        badge_bn, badge_en, tier = "সদস্য", "Member", "member"

    return {
        **person,
        "initials": initials,
        "badge_bn": badge_bn,
        "badge_en": badge_en,
        "tier": tier,
        "is_officer": tier in ("chairman", "secretary", "officer"),
    }

# ---- Articles of Association ----

AOA_DEFINITIONS = {
    "title_bn": "সংজ্ঞাসমূহ",
    "title_en": "Definitions",
    "intro_bn": "গঠনতন্ত্রে উল্লেখিত বিষয়সমূহের মধ্যে পার্থক্য বা অসামঞ্জস্য কিছু না থাকলে—",
    "intro_en": "Unless there is anything repugnant in the subject or context—",
    "items": [
        {
            "bn": "‘সোসাইটি’ বলতে পূর্ণনামে ‘Zarrah Foundation’ কে বুঝাবে।",
            "en": "“Society” means Zarrah Foundation in its full name.",
        },
        {
            "bn": "‘আইন’ বলতে The Societies Registration Act, 1860 (Act No. XXI of 1860) কে বুঝাবে।",
            "en": "“Act” means the Societies Registration Act, 1860 (Act No. XXI of 1860).",
        },
        {
            "bn": "‘সদস্য’ বলতে Zarrah Foundation-এর তালিকাভুক্ত সদস্যকে বুঝাবে।",
            "en": "“Member” means a person enrolled on the membership register of Zarrah Foundation.",
        },
        {
            "bn": "১৮৬০ সালের সোসাইটি নিবন্ধীকরণ আইনের বিধান যেসকল বিষয়ে সোসাইটির জন্য প্রযোজ্য, তা এই সোসাইটির জন্যও প্রযোজ্য হবে।",
            "en": "Provisions of the Societies Registration Act, 1860 that apply to societies shall also apply to this Society.",
        },
    ],
}

MEMBERSHIP_ELIGIBILITY = {
    "title_bn": "সদস্য হওয়ার যোগ্যতা",
    "title_en": "Membership Eligibility",
    "intro_bn": "কার্য এলাকায় বসবাসকারী অথবা সোসাইটির লক্ষ্য ও উদ্দেশ্যের সাথে সম্পৃক্ত যেকোনো ব্যক্তি, যদি—",
    "intro_en": "Any person residing in the operational area, or connected with the Society's aims and objects, may apply if they—",
    "items": [
        {"bn": "কমপক্ষে ১৮ (আঠারো) বছর বয়সী;", "en": "are at least 18 (eighteen) years of age;"},
        {"bn": "সুস্থ মস্তিষ্কসম্পন্ন এবং আইনত অযোগ্য ঘোষিত নন;", "en": "are of sound mind and not legally declared disqualified;"},
        {
            "bn": "কোনো ফৌজদারি অপরাধে আদালত কর্তৃক দণ্ডিত নন (নৈতিক স্খলনজাতিত অপরাধের ক্ষেত্রে);",
            "en": "have not been convicted by a court of a criminal offence involving moral turpitude;",
        },
        {
            "bn": "সোসাইটির লক্ষ্য, উদ্দেশ্য ও গঠনতন্ত্রের সকল ধারায় প্রতি সম্মতি জ্ঞাপন করেন;",
            "en": "express agreement with all clauses of the Society's aims, objects and constitution;",
        },
        {
            "bn": "সোসাইটির অরাজনৈতিক ও অলাভজনক চরিত্রকে সম্মান করেন এবং কোনো রাজনৈতিক কার্যক্রমে সোসাইটির নাম ব্যবহার করেন না;",
            "en": "respect the Society's non-political and non-profit character and do not use its name for any political programme;",
        },
    ],
    "outro_bn": (
        "তিনি নির্ধারিত ফরমে আবেদন করতে পারবেন। আবেদনপত্র কার্যনির্বাহী পরিষদের সভায় অনুমোদিত "
        "হলে নির্ধারিত ভর্তি ফি ও সদস্য চাঁদা প্রদান সাপেক্ষে সদস্যপদ প্রদান করা হবে। "
        "কার্যনির্বাহী পরিষদের সিদ্ধান্তই এ বিষয়ে চূড়ান্ত বলে বিবেচিত হবে।"
    ),
    "outro_en": (
        "they may apply in the prescribed form. Upon approval by the Executive Council and "
        "payment of the prescribed admission fee and membership subscription, membership shall be "
        "granted. The decision of the Executive Council shall be final in this regard."
    ),
}

MEMBERSHIP_FEES = {
    "title_bn": "সদস্যপদের ভর্তি ও সদস্য চাঁদা",
    "title_en": "Membership Fees",
    "admission_bn": "ভর্তি ফি মাত্র ১০০ (একশত) টাকা",
    "admission_en": "Admission fee of only BDT 100 (one hundred)",
    "monthly_bn": "মাসিক চাঁদার পরিমাণ ৫০ (পঞ্চাশ) টাকা",
    "monthly_en": "Monthly subscription of BDT 50 (fifty)",
    "note_bn": "সময়ের সাথে সংগতি রেখে কার্যনির্বাহী পরিষদ প্রয়োজনবোধে ভর্তি ফি এবং সদস্য চাঁদার পরিমাণ পুনঃ নির্ধারণ করতে পারে।",
    "note_en": "The Executive Council may, as circumstances require, revise the admission fee and membership subscription.",
}

MEMBERSHIP_CANCEL = {
    "title_bn": "সদস্য পদ বাতিল",
    "title_en": "Cancellation of Membership",
    "items": [
        {"bn": "(ক) কোন সদস্য স্বেচ্ছায় পদত্যাগ করলে।", "en": "(a) If a member resigns voluntarily."},
        {
            "bn": "(খ) কোন সদস্য মানসিকভাবে ভারসাম্যহীন/পাগলামি কিংবা মৃত্যুবরণ করলে।",
            "en": "(b) If a member becomes mentally unbalanced or dies.",
        },
        {
            "bn": (
                "(গ) কোন সদস্য সোসাইটির গঠনতন্ত্র পরিপন্থী কোনো কার্যকলাপের সাথে জড়িত হলে এবং তা "
                "লিখিত অভিযোগের ভিত্তিতে কার্যনির্বাহী পরিষদ তদন্ত কমিটি গঠন করে কমিটি কর্তৃক প্রমাণিত হলে। "
                "সেক্ষেত্রে অভিযুক্ত সদস্যকে আত্মপক্ষ সমর্থনের সুযোগ প্রদান করা হবে।"
            ),
            "en": (
                "(c) If a member engages in activities contrary to the constitution and, upon a written "
                "complaint, an investigation committee formed by the Executive Council finds the "
                "allegation proved. The accused member shall be given an opportunity of self-defence."
            ),
        },
        {
            "bn": "(ঘ) এক বছরের বেশি সময় সোসাইটির সদস্য চাঁদা না দিলে কিংবা সোসাইটির সাথে সংশ্লিষ্টতা না থাকলে।",
            "en": "(d) If membership dues remain unpaid for more than one year, or the member ceases to be associated with the Society.",
        },
        {
            "bn": "(ঙ) সোসাইটিতে বেতনভুক্ত কর্মচারী হলে।",
            "en": "(e) If the person becomes a salaried employee of the Society.",
        },
    ],
}

MEMBERSHIP_RESTORE = {
    "title_bn": "বাতিলকৃত সদস্যপদ পুনঃলাভ",
    "title_en": "Restoration of Membership",
    "bn": (
        "ক্রমিক নং ৩.৩-এর (খ) এবং (গ) ব্যতীত অন্যান্য যে কোনো কারণে সদস্য পদ বাতিল হলে সে "
        "উক্ত কারণ ব্যাখ্যা করে পরিচালক কিংবা সচিবের নিকট সদস্য পদ পুনঃলাভের জন্য আবেদন করতে হবে। "
        "আবেদন পত্র পরবর্তী কার্যনির্বাহী পরিষদ সভায় অনুমোদনের জন্য পেশ করতে হবে এবং তা অনুমোদিত "
        "হলে পুনঃভর্তি ফি মাত্র ১০০/- (একশত) টাকা এবং বকেয়া সহ চাঁদা পরিশোধ করে বাতিলকৃত "
        "সদস্যপদ পুনঃ লাভ করা যাবে।"
    ),
    "en": (
        "Except under clauses 3.3 (b) and (c), a person whose membership was cancelled for any "
        "other reason may apply to the Director or Secretary for restoration, explaining the "
        "cause. The application shall be placed before the next Executive Council meeting; "
        "if approved, membership may be restored upon payment of a re-admission fee of BDT 100 "
        "and any outstanding subscription."
    ),
}

ORG_STRUCTURE = [
    {
        "key": "advisory",
        "icon": "bi-shield-lock",
        "title_bn": "উপদেষ্টা পরিষদ",
        "title_en": "Advisory Council",
        "summary_bn": "সর্বোচ্চ প্রশাসনিক ও তত্ত্বাবধায়ক পরিষদ; সদস্য সংখ্যা ৫ (পাঁচ) জন।",
        "summary_en": "Highest administrative and supervisory council; five (5) members.",
        "details_bn": (
            "এই পরিষদ-এ অন্তর্ভূক্ত হওয়ার জন্য সোসাইটির কোন সদস্য স্বেচ্ছায় ইচ্ছাপোষণ করতে পারবে না "
            "এবং অন্য সদস্যকে ভোট দেওয়ার জন্য বলতে পারবে না। সোসাইটির মোট সদস্য সংখ্যা বৃদ্ধির সাথে এ সংখ্যা "
            "বৃদ্ধি হতে পারে, যা উপদেষ্টা পরিষদ এবং কার্যনির্বাহী পরিষদের সাথে সমন্বয় করে করা হবে। "
            "প্রতি ৪ (চার) বছর অন্তে উপদেষ্টা কমিটির সদস্য পদ পুনঃ গঠনের জন্য বিশেষ নির্বাচন "
            "প্রক্রিয়া অনুসরণ করা হবে।"
        ),
        "details_en": (
            "No member may voluntarily seek or vote others into this council. Its size may grow with "
            "total membership, in coordination with the Advisory Council and Executive Council. "
            "Every four (4) years a special election process reconstitutes Advisory Council membership."
        ),
    },
    {
        "key": "executive",
        "icon": "bi-kanban",
        "title_bn": "কার্যনির্বাহী পরিষদ",
        "title_en": "Executive Council",
        "summary_bn": "দৈনন্দিন পরিচালনা; সর্বোচ্চ সদস্য সংখ্যা ২০ (বিশ) জন; প্রতি ৩ বছর অন্তে নতুন কমিটি।",
        "summary_en": "Day-to-day management; maximum twenty (20) members; reconstituted every three years.",
        "details_bn": (
            "প্রতি ৩ (তিন) বছর অন্তে কার্যনির্বাহী পরিষদের নতুন কমিটি গঠন করা হবে। চেয়ারম্যান ও "
            "সচিব বিশেষ নির্বাচন ব্যবস্থায় নির্বাচিত হবেন; বাকি পদগুলোর জন্য উপদেষ্টা পরিষদ কর্তৃক "
            "যোগ্য ব্যক্তি নির্বাচিত হবেন। প্রয়োজনবোধে দেশের যেকোনো স্থানে আঞ্চলিক বা শাখা কমিটি "
            "গঠন করা যেতে পারে।"
        ),
        "details_en": (
            "A new Executive Council is formed every three (3) years. The Chairman and Secretary "
            "are elected under the special election system; remaining posts are filled by qualified "
            "persons chosen by the Advisory Council. Regional or branch committees may be formed "
            "anywhere in the country as needed."
        ),
    },
    {
        "key": "general",
        "icon": "bi-people",
        "title_bn": "সাধারণ পরিষদ",
        "title_en": "General Council",
        "summary_bn": "সকল তালিকাভুক্ত সদস্য নিয়ে গঠিত; সর্বোচ্চ নীতি-নির্ধারণী কর্তৃপক্ষ।",
        "summary_en": "Comprises all enrolled members; the highest policy-making authority.",
        "details_bn": (
            "সাধারণ পরিষদের কর্তব্যসমূহ: (ক) বার্ষিক প্রতিবেদন ও হিসাব অনুমোদন; (খ) গঠনতন্ত্র "
            "সংশোধন বিষয়ে চূড়ান্ত মত প্রদান; (গ) গুরুত্বপূর্ণ নীতিগত সিদ্ধান্ত অনুমোদন; "
            "(ঘ) বিলুপ্তি বিষয়ে চূড়ান্ত সিদ্ধান্ত।"
        ),
        "details_en": (
            "Duties of the General Council include: (a) approving the annual report and accounts; "
            "(b) final opinion on constitutional amendments; (c) approving important policy decisions; "
            "and (d) final decision on dissolution."
        ),
    },
]

ADVISORY_POWERS = {
    "title_bn": "উপদেষ্টা পরিষদের ক্ষমতা",
    "title_en": "Powers of the Advisory Council",
    "items": [
        {
            "bn": "প্রতিষ্ঠাকালীন সময় থেকে সর্বোচ্চ ৫ (পাঁচ) বছর উপদেষ্টা পরিষদ চেয়ারম্যান ও সচিব মনোনয়ন করবেন।",
            "en": "For up to five (5) years from establishment, the Advisory Council shall nominate the Chairman and Secretary.",
        },
        {
            "bn": "প্রতি ৩ (তিন) বছর অন্তে সকল পর্যায়ে কার্যনির্বাহী পরিষদের নির্বাচন অনুষ্ঠান করা।",
            "en": "Conduct Executive Council elections at all levels every three (3) years.",
        },
        {
            "bn": "বার্ষিক আয় ব্যয়ের হিসাব ও বাজেট অনুমোদন করা।",
            "en": "Approve annual income–expenditure accounts and the budget.",
        },
        {
            "bn": "দুই-তৃতীয়াংশ সাধারণ সদস্যের ভোটে গঠনতন্ত্র সংশোধনের প্রস্তাব রেজিস্ট্রেশন কর্তৃপক্ষের নিকট অনুমোদনের জন্য প্রেরণ।",
            "en": "Forward constitutional amendment proposals approved by a two-thirds vote of general members to the registration authority.",
        },
        {"bn": "সংস্থার নীতি নির্ধারণী সিদ্ধান্ত গ্রহণ।", "en": "Take policy decisions of the organisation."},
        {
            "bn": "যে কোনো সংকটমূহূর্তে এ পরিষদের সিদ্ধান্তই চূড়ান্ত।",
            "en": "In any crisis, the decision of this Board shall be final.",
        },
    ],
}

EXECUTIVE_POSTS = [
    {"bn": "চেয়ারম্যান", "en": "Chairman", "elect_bn": "বিশেষ নির্বাচন ব্যবস্থা", "elect_en": "Special election"},
    {"bn": "সচিব", "en": "Secretary", "elect_bn": "বিশেষ নির্বাচন ব্যবস্থা", "elect_en": "Special election"},
    {"bn": "কোষাধ্যক্ষ", "en": "Treasurer", "elect_bn": "উপদেষ্টা পরিষদ কর্তৃক", "elect_en": "By Advisory Council"},
    {"bn": "সহ-কোষাধ্যক্ষ", "en": "Co-Treasurer", "elect_bn": "উপদেষ্টা পরিষদ কর্তৃক", "elect_en": "By Advisory Council"},
    {"bn": "আইন বিষয়ক সম্পাদক", "en": "Legal Affairs Secretary", "elect_bn": "উপদেষ্টা পরিষদ কর্তৃক", "elect_en": "By Advisory Council"},
    {"bn": "সহকারী আইন বিষয়ক সম্পাদক", "en": "Assistant Legal Affairs Secretary", "elect_bn": "উপদেষ্টা পরিষদ কর্তৃক", "elect_en": "By Advisory Council"},
    {"bn": "প্রচার ও জনসংযোগ সম্পাদক", "en": "Publicity & Public Relations Secretary", "elect_bn": "উপদেষ্টা পরিষদ কর্তৃক", "elect_en": "By Advisory Council"},
    {"bn": "সহকারী প্রচার ও জনসংযোগ সম্পাদক", "en": "Assistant Publicity & PR Secretary", "elect_bn": "উপদেষ্টা পরিষদ কর্তৃক", "elect_en": "By Advisory Council"},
    {"bn": "শিক্ষা ও প্রশিক্ষণ বিষয়ক সম্পাদক", "en": "Education & Training Secretary", "elect_bn": "উপদেষ্টা পরিষদ কর্তৃক", "elect_en": "By Advisory Council"},
    {"bn": "সহকারী শিক্ষা ও প্রশিক্ষণ বিষয়ক সম্পাদক", "en": "Assistant Education & Training Secretary", "elect_bn": "উপদেষ্টা পরিষদ কর্তৃক", "elect_en": "By Advisory Council"},
    {"bn": "দুর্যোগ ও পুনর্বাসন বিষয়ক সম্পাদক", "en": "Disaster & Rehabilitation Secretary", "elect_bn": "উপদেষ্টা পরিষদ কর্তৃক", "elect_en": "By Advisory Council"},
    {"bn": "সহকারী দুর্যোগ ও পুনর্বাসন বিষয়ক সম্পাদক", "en": "Assistant Disaster & Rehabilitation Secretary", "elect_bn": "উপদেষ্টা পরিষদ কর্তৃক", "elect_en": "By Advisory Council"},
    {"bn": "চিকিৎসা ও রক্তদান কর্মসূচী বিষয়ক সম্পাদক", "en": "Medical & Blood Donation Secretary", "elect_bn": "উপদেষ্টা পরিষদ কর্তৃক", "elect_en": "By Advisory Council"},
    {"bn": "সহকারী চিকিৎসা ও রক্তদান কর্মসূচী বিষয়ক সম্পাদক", "en": "Assistant Medical & Blood Donation Secretary", "elect_bn": "উপদেষ্টা পরিষদ কর্তৃক", "elect_en": "By Advisory Council"},
]

EXECUTIVE_DUTIES = {
    "title_bn": "কার্যনির্বাহী পরিষদের দায়িত্ব ও কর্তব্য",
    "title_en": "Duties of the Executive Council",
    "items": [
        {
            "bn": "কার্যনির্বাহী পরিষদ দৈনন্দিন কার্যক্রমের জন্য উপদেষ্টা পরিষদের নিকট দায়ী থাকবে।",
            "en": "The Executive Council shall be accountable to the Advisory Council for day-to-day operations.",
        },
        {
            "bn": "জরুরি অস্থায়ী সাড়া প্রচারের ব্যবস্থা করা এবং ভবিষ্যতে গঠিত আঞ্চলিক বা শাখা কার্যালয়কে প্রয়োজনীয় নির্দেশনা প্রদান।",
            "en": "Arrange urgent temporary publicity responses and issue necessary directions to future regional or branch offices.",
        },
        {
            "bn": "সোসাইটির বার্ষিক বাজেট প্রণয়ন করে যথাসময়ে উপদেষ্টা পরিষদ সভায় অনুমোদনের জন্য পেশ করা।",
            "en": "Prepare the annual budget and submit it in due time to the Advisory Council for approval.",
        },
        {
            "bn": "প্রয়োজনে প্রকারভেদে কর্মকর্তা/কর্মচারী নিয়োগ করা।",
            "en": "Appoint officers/employees of various categories as needed.",
        },
        {
            "bn": "অনুমোদিত বাজেটের আওতায় এ পরিষদ নতুন নতুন কর্মসূচী গ্রহণ করতে পারে।",
            "en": "Within the approved budget, the Committee may adopt new programmes.",
        },
        {"bn": "নির্বাচন কমিশন গঠন করা।", "en": "Form an election commission."},
        {"bn": "সকল প্রকার সভা আহ্বানের ব্যবস্থা করা।", "en": "Arrange the calling of all types of meetings."},
        {
            "bn": "সোসাইটির জন্য দেশাদি ও দেশবিদেশ পর্যায়ে তহবিল সংগ্রহ ও রক্ষণাবেক্ষণ করা।",
            "en": "Raise and maintain funds for the Society nationally and internationally.",
        },
    ],
}

OFFICER_ROLES = [
    {
        "title_bn": "চেয়ারম্যানের দায়িত্ব ও ক্ষমতা",
        "title_en": "Powers & Duties of the Chairman",
        "items": [
            {
                "bn": "চেয়ারম্যান সোসাইটির সাংবিধানিক প্রধান এবং কার্যনির্বাহী পরিষদের সভায় সভাপতিত্ব করেন।",
                "en": "The Chairman is the constitutional head of the Society and presides over Executive Council meetings.",
            },
            {
                "bn": "তিনি উপদেষ্টা পরিষদকে কোনো বিষয়ে সভা আহ্বানের জন্য সুপারিশ করতে পারেন।",
                "en": "He may recommend that the Advisory Council convene a meeting on any matter.",
            },
            {
                "bn": "সচিবের মাধ্যমে কার্যনির্বাহী পরিষদের সভা আহ্বান ও স্থগিত করতে পারেন।",
                "en": "Through the Secretary, he may call or adjourn Executive Council meetings.",
            },
            {
                "bn": "সোসাইটির উন্নতি ও সার্বিক কর্মকাণ্ডের প্রতি দৃষ্টি রাখেন এবং এ বিষয়ে সচিবকে প্রয়োজনীয় পরামর্শ দেন।",
                "en": "He oversees the Society's progress and overall activities and advises the Secretary as needed.",
            },
            {
                "bn": "কোনো বিষয়ে সিদ্ধান্তের ক্ষেত্রে দ্বিমত দেখা দিলে উপদেষ্টা পরিষদের পরামর্শ নিয়ে সমন্বয়ী আলোচনা করতে হবে; সেক্ষেত্রে উপদেষ্টা পরিষদের সিদ্ধান্তই চূড়ান্ত বলে বিবেচিত হবে।",
                "en": "If disagreement arises on a decision, coordination shall follow Advisory Council advice; the Advisory Council's decision shall then be final.",
            },
            {
                "bn": "কার্যনির্বাহী পরিষদ অথবা উপদেষ্টা পরিষদ কর্তৃক প্রদত্ত অন্য যে কোনো দায়িত্ব পালন করেন।",
                "en": "He performs any other duty assigned by the Executive Council or Advisory Council.",
            },
            {
                "bn": "চেয়ারম্যানের অনুপস্থিতিতে উপদেষ্টা পরিষদের একজন এই দায়িত্ব পালন করবেন; তিনি উপদেষ্টা পরিষদের সভার মাধ্যমে মনোনীত হবেন।",
                "en": "In the Chairman's absence, a member of the Advisory Council shall act, nominated through an Advisory Council meeting.",
            },
        ],
    },
    {
        "title_bn": "সচিবের দায়িত্ব ও ক্ষমতা",
        "title_en": "Powers & Duties of the Secretary",
        "items": [
            {
                "bn": "চেয়ারম্যানের পরামর্শে কার্যনির্বাহী পরিষদের সভা আহ্বান করেন।",
                "en": "Calls Executive Council meetings in consultation with the Chairman.",
            },
            {
                "bn": "কার্যনির্বাহী পরিষদের সভাসমূহের কার্যবিবরণী লেখেন এবং তা সংরক্ষণ করেন।",
                "en": "Prepares and keeps the minutes of Executive Council meetings.",
            },
            {
                "bn": "অন্যান্য সম্পাদক/সদস্যদের সহযোগিতায় উভয় পরিষদের সকল সিদ্ধান্তসমূহ বাস্তবায়ন করেন।",
                "en": "Implements decisions of both boards with the cooperation of other secretaries/members.",
            },
            {
                "bn": "সোসাইটির সকল প্রকার সম্পত্তির সংরক্ষণ, উন্নয়ন ও ব্যবস্থাপনার দায়িত্ব পালন করেন।",
                "en": "Is responsible for safeguarding, developing and managing all Society property.",
            },
            {"bn": "সকল নথিপত্রাদি সংরক্ষণ করেন।", "en": "Keeps all records and documents."},
            {
                "bn": "বিভিন্ন কর্তৃপক্ষের সহিত পত্র যোগাযোগ করেন।",
                "en": "Corresponds with various authorities.",
            },
            {
                "bn": "সকল কার্যক্রম বাস্তবায়ন ক্ষেত্রে তিনি নিবিড় তত্ত্বাবধান করেন।",
                "en": "Closely supervises implementation of all programmes.",
            },
            {
                "bn": "কার্যনির্বাহী পরিষদের অনুমোদনক্রমে সোসাইটির পক্ষে সকল প্রকার আর্থিক লেনদেন ও নগদান আয় ব্যয়ের হিসাবসহ ব্যাংক হিসাব পরিচালনা করেন।",
                "en": "With Executive Council approval, manages financial transactions, cash accounts and bank accounts on behalf of the Society.",
            },
            {
                "bn": "বার্ষিক কার্যক্রমের প্রতিবেদন তৈরি করে চেয়ারম্যানের অনুমতিক্রমে অনুমোদনের জন্য উপদেষ্টা পরিষদের সভায় পেশ করেন।",
                "en": "Prepares the annual activity report and, with the Chairman's consent, submits it to the Advisory Council for approval.",
            },
            {
                "bn": "কোষাধ্যক্ষের মাধ্যমে তিনি বার্ষিক অডিট প্রতিবেদন তৈরি করে উপদেষ্টা পরিষদ সভায় পেশ করেন।",
                "en": "Through the Treasurer, prepares the annual audit report and presents it to the Advisory Council.",
            },
        ],
    },
    {
        "title_bn": "কোষাধ্যক্ষের দায়িত্ব ও কর্তব্য",
        "title_en": "Duties of the Treasurer",
        "items": [
            {
                "bn": "সোসাইটির আয় ও ব্যয় এর হিসাব রক্ষণাবেক্ষণ করেন।",
                "en": "Maintains the Society's income and expenditure accounts.",
            },
            {
                "bn": "সোসাইটির জন্য চাঁদা আদায় করেন এবং হিসাব সংরক্ষণ করেন।",
                "en": "Collects subscriptions and keeps accounts.",
            },
            {
                "bn": "আয়, ব্যয় ও মাসিক হিসাব বিবরণী এবং বাজেট প্রস্তুত করেন এবং সচিবের অনুমতিক্রমে তা উপদেষ্টা পরিষদে অনুমোদনের জন্য পেশ করেন।",
                "en": "Prepares income, expenditure and monthly statements and the budget, and submits them via the Secretary for Advisory Council approval.",
            },
            {
                "bn": "অডিট কাজে সার্বিক সহায়তা প্রদান করেন।",
                "en": "Provides full support to audit work.",
            },
        ],
    },
    {
        "title_bn": "অন্যান্য বিষয়ভিত্তিক সম্পাদকদের দায়িত্ব",
        "title_en": "Duties of Other Subject Secretaries",
        "items": [
            {
                "bn": "সকল ক্ষেত্রে পরিষদের নির্দেশনা অনুসরণ করেন।",
                "en": "Follow the Board's directions in all matters.",
            },
            {
                "bn": "বিশেষ খাতে নিয়োজিত সম্পাদকগণ তাদের খাতের সকল কার্যক্রম পরিচালনা করেন।",
                "en": "Secretaries assigned to specific portfolios manage all programmes in their areas.",
            },
            {
                "bn": "যেহেতু সম্পাদকগণ তাদের খাত সম্পর্কীয় দক্ষতাসম্পন্ন হন, তাই যেকোনো সিদ্ধান্ত গ্রহণের ক্ষেত্রে উভয় পরিষদ তাদের পরামর্শকে সর্বোচ্চ গুরুত্বের সহিত বিবেচনা করবেন।",
                "en": "Because portfolio secretaries are skilled in their fields, both boards shall give the highest weight to their advice when taking decisions.",
            },
        ],
    },
]

MEETINGS = {
    "title_bn": "সভা আহ্বান",
    "title_en": "Calling of Meetings",
    "bn": (
        "কার্যনির্বাহী পরিষদের সভা সর্বোচ্চ তিন মাসের মধ্যে অন্তত একবার অনুষ্ঠিত হতে হবে। "
        "উপদেষ্টা পরিষদের সভা বছরে অন্তত একবার অনুষ্ঠিত হবে। সাধারণ পরিষদের বার্ষিক সাধারণ "
        "সভা (AGM) বছরে অন্তত একবার অনুষ্ঠিত হবে। জরুরি সভা ২৪ ঘণ্টার নোটিশে আহ্বান করা যেতে "
        "পারে। ভার্চুয়াল/অনলাইন সভার ব্যবস্থা করা যেতে পারে। অনলাইন মাধ্যমে অনুষ্ঠিত সভার "
        "উপস্থিতি এবং গৃহীত সিদ্ধান্তসমূহ সর্বত্র অনুষ্ঠিত সভার মতোই আইনগতভাবে বৈধ বলে গণ্য হবে।"
    ),
    "en": (
        "At least one Executive Council meeting shall be held within every three (3) months. "
        "The Advisory Council shall meet at least once annually / at year-end. At least one "
        "Annual General Meeting (AGM) of general members shall be held each year. An emergency "
        "meeting may be called on 24 hours' notice. Virtual/online meetings are permitted under "
        "the organization's rules; attendance and decisions of online meetings are treated in "
        "the same manner as physical meetings."
    ),
}

QUORUM = {
    "title_bn": "সভা কোরাম",
    "title_en": "Quorum",
    "bn": (
        "কার্যনির্বাহী পরিষদ ও উপদেষ্টা পরিষদের সভায় মোট সদস্যের ২/৩ (দুই-তৃতীয়াংশ) উপস্থিতিতে "
        "কোরাম পূর্ণ হবে। তবে সাধারণ পরিষদের (বার্ষিক সাধারণ সভা বা AGM) ক্ষেত্রে মোট তালিকাভুক্ত "
        "সদস্যের ১/৩ (এক-তৃতীয়াংশ) উপস্থিতিতে কোরাম পূর্ণ বলে বিবেচিত হবে।"
    ),
    "en": (
        "Quorum for Executive Council and Advisory Council meetings is two-thirds (2/3) of total "
        "members. For the General Council (AGM), quorum is one-third (1/3) of total enrolled members."
    ),
}

ADJOURNED = {
    "title_bn": "স্থগিত সভা",
    "title_en": "Adjourned Meeting",
    "bn": (
        "কোরামের অভাবে কোন সভা স্থগিত হলে একই আলোচ্যসূচীর উপর ভিত্তি করে পরবর্তী ৭ (সাত) "
        "দিনের মধ্যে সভা আহ্বান করতে হবে। এই সভায় যতজন উপস্থিত হলে তাতেই সভা বৈধ হবে। "
        "এক্ষেত্রে কোরামের প্রয়োজন নেই।"
    ),
    "en": (
        "If a meeting is adjourned for want of quorum, it shall be reconvened within the next "
        "seven (7) days on the same agenda. Whatever number then attends shall constitute a "
        "valid meeting; no quorum is required."
    ),
}

ELECTIONS = {
    "title_bn": "নির্বাচন",
    "title_en": "Elections",
    "bn": (
        "সোসাইটির নির্বাচন ব্যবস্থার জন্য গঠনতন্ত্রে উল্লেখিত নির্বাচনী ব্যবস্থার অনুসরণ করা হবে। "
        "বিশেষ নির্বাচনী ব্যবস্থার ক্ষেত্রে উপদেষ্টা পরিষদ সার্বিক ব্যবস্থার তত্ত্বাবধান করবেন এবং "
        "সাধারণ ভোট প্রক্রিয়া পরিচালনার জন্যও প্রয়োজনীয় কর্মকর্তাগণকে উপদেষ্টা পরিষদ বাছাই করবেন। "
        "সাধারণ নির্বাচনী ব্যবস্থায় উক্ত কর্মকর্তাগণের সম্মিলিত সিদ্ধান্তই চূড়ান্ত হবে।"
    ),
    "en": (
        "Elections shall follow the election system set out in this constitution. For the special "
        "election system, the Advisory Council shall supervise overall arrangements and select "
        "officers needed for the general voting process. Under the general election system, the "
        "collective decision of those officers shall be final."
    ),
}

TERM_YEAR = {
    "title_bn": "পরিষদসমূহের মেয়াদ ও বছর",
    "title_en": "Terms of Office & Financial Year",
    "bn": (
        "উপদেষ্টা পরিষদের মেয়াদ ২ (দুই) বছর এবং সকল কার্যনির্বাহী পরিষদের মেয়াদ ১ (এক) বছর হবে। "
        "১ জানুয়ারি থেকে ৩১ ডিসেম্বর পর্যন্ত সময়কে বছর হিসেবে গণনা করা হবে।"
    ),
    "en": (
        "The Advisory Council's term is two (2) years and each Executive Council's term is one (1) year. "
        "The year is counted from 1 January to 31 December."
    ),
}

SUB_COMMITTEE = {
    "title_bn": "সাব-কমিটি গঠন",
    "title_en": "Formation of Sub-Committees",
    "bn": (
        "যেকোনো বিশেষ পরিস্থিতিতে জন্য কার্যনির্বাহী পরিষদের সভায় অনুমোদনের মাধ্যমে সাব-কমিটি "
        "গঠন ও তহবিল খোলা যেতে পারে। উক্ত কমিটি এবং তহবিলের পরিচালনার জন্য একটি বিশেষ "
        "বিধিমালা প্রণয়ন করতে হবে, যা উপদেষ্টা পরিষদ কর্তৃক অনুমোদিত হতে হবে।"
    ),
    "en": (
        "For any special situation, a sub-committee may be formed and a fund opened with "
        "Executive Council approval. Special rules for managing that committee and fund "
        "must be framed and approved by the Advisory Council."
    ),
}

LEGAL_REP = {
    "title_bn": "আইনগত প্রতিনিধিত্ব",
    "title_en": "Legal Representation",
    "bn": (
        "সোসাইটির পক্ষে যে কোনো মামলা বা হাজিরা, মোকদ্দমা, নোটিশ গ্রহণ বা আইনগত কার্যক্রম "
        "পরিচালনার ক্ষমতা সচিবের উপর ন্যস্ত থাকবে। প্রয়োজনবোধে কার্যনির্বাহী পরিষদের "
        "সিদ্ধান্তক্রমে অন্য কোনো প্রতিনিধিকে দায়িত্ব প্রদান করা যাবে।"
    ),
    "en": (
        "Authority to conduct any suit or appearance, litigation, receive notices or legal "
        "proceedings on behalf of the Society rests with the Secretary. Where needed, another "
        "representative may be authorised by Executive Council decision."
    ),
}

FINANCE_SOURCES = {
    "title_bn": "সোসাইটির আয়ের উৎস",
    "title_en": "Sources of Income",
    "items": [
        {
            "bn": (
                "প্রধান উৎস হবে সদস্য ভর্তি ফি ও সদস্য চাঁদা, দেশাদি কিংবা দেশবিদেশ অনুদান, "
                "ব্যক্তিগত অনুদান; কোনো বিশেষ তহবিল কিংবা বিশেষ কর্মসূচীর মাধ্যমে তহবিল সংগ্রহ "
                "করা যেতে পারে। সোসাইটি আইনানুগভাবে আয়ের উৎস সৃষ্টি করতে পারে, তবে অর্জিত "
                "সকল আয় সোসাইটির লক্ষ্য ও উদ্দেশ্য বাস্তবায়নে ব্যয় হবে এবং কোনো সদস্য "
                "ব্যক্তিগতভাবে লাভবান হবেন না।"
            ),
            "en": (
                "Primary sources are membership admission fees and subscriptions, domestic or "
                "foreign grants, and individual donations; funds may also be raised through special "
                "funds or programmes. The Society may lawfully create income sources, but all "
                "income shall be spent on its aims and objects and no member shall personally profit."
            ),
        },
        {
            "bn": (
                "সোসাইটির নামে অর্জিত স্থাবর ও অস্থাবর সকল সম্পত্তি সোসাইটির নিজস্ব সম্পত্তি "
                "হিসেবে বিবেচিত হবে এবং কোনো সদস্য, পদাধিকারী বা প্রতিষ্ঠাতা সদস্য উক্ত "
                "সম্পত্তির উপরে ব্যক্তিগত দাবিকোনো দাবি করতে পারবেন না।"
            ),
            "en": (
                "All movable and immovable property acquired in the Society's name shall be its "
                "own property; no member, office-bearer or founder member may make any personal "
                "claim over such property."
            ),
        },
    ],
}

FINANCE_EXPENSE = {
    "title_bn": "সোসাইটির ব্যয়ের ক্ষেত্রসমূহ",
    "title_en": "Areas of Expenditure",
    "items": [
        {"bn": "সমাজের মানুষের নৈতিক উন্নয়নমূলক কর্মসূচীতে ব্যয়।", "en": "Programmes for moral development of society."},
        {"bn": "শিক্ষা ও প্রশিক্ষণ কাজে যন্ত্রপাতি ও উপকরণ ক্রয়ে নিদর্শ।", "en": "Purchase of equipment and materials for education and training."},
        {"bn": "দারিদ্র্য দূরীকরণের বিভিন্ন প্রকারে ব্যয়।", "en": "Various poverty-reduction expenditures."},
        {"bn": "বিভিন্ন দুর্যোগে ক্ষতিগ্রস্তদের ত্রাণ ও পুনর্বাসনে ব্যয়।", "en": "Relief and rehabilitation for disaster victims."},
        {"bn": "পথশিশুদের পুনর্বাসনে ব্যয়।", "en": "Rehabilitation of street children."},
        {"bn": "কোনো বিশেষ উদ্দেশ্যে গঠিত তহবিলের অর্থ শুধুমাত্র সেই খাতেই ব্যয় করা হবে।", "en": "Money in a special-purpose fund shall be spent only for that purpose."},
        {"bn": "কোনো বিশেষ কাজে নিয়োজিত কর্মচারীদের বেতন-ভাতা।", "en": "Salaries and allowances of staff engaged for specific work."},
        {"bn": "অন্যান্য ব্যয়।", "en": "Other expenditure."},
    ],
}

ACCOUNTS = {
    "title_bn": "হিসাব রক্ষণাবেক্ষণ",
    "title_en": "Maintenance of Accounts",
    "items": [
        {
            "bn": "সোসাইটির সকল অর্থই সিডিউল ব্যাংকে জমাদি অথবা স্থায়ী হিসাবে জমা থাকবে।",
            "en": "All Society funds shall be kept in a scheduled bank on current or fixed deposit.",
        },
        {
            "bn": (
                "কার্যনির্বাহী পরিষদের চেয়ারম্যান, সচিব এবং কোষাধ্যক্ষের যেকোনো দুইজনের যৌথ "
                "স্বাক্ষরে পরিচালিত এক বা একাধিক অভিন্ন হিসাবে সোসাইটির মূল্য অর্থ জমা থাকবে। "
                "সকল লেনদেন ব্যাংকিং পদ্ধতিতে সম্পন্ন করা হবে।"
            ),
            "en": (
                "Society funds shall be held in one or more joint accounts operated by any two of "
                "the Chairman, Secretary and Treasurer. All transactions shall be completed through banking methods."
            ),
        },
        {
            "bn": (
                "কোনো বিশেষ কারণ ছাড়া সোসাইটির অর্থ কোনো সদস্য তার নিকট ৭ (সাত) দিনের বেশি "
                "রাখতে পারবে না। এরকম ঘটনা ঘটলে সঠিক তদন্তের মাধ্যমে ঘটনার সঠিক ব্যাখ্যা "
                "প্রদান করতে হবে।"
            ),
            "en": (
                "Except for special reasons, no member may retain Society money for more than "
                "seven (7) days. Any such occurrence must be properly investigated and explained."
            ),
        },
    ],
}

AUDIT = {
    "title_bn": "হিসাব নিরীক্ষা",
    "title_en": "Audit",
    "bn": (
        "অনুমোদিত অডিট ফার্ম/চারটার্ড অ্যাকাউন্ট্যান্ট দ্বারা অডিট সম্পন্ন করা হবে এবং প্রযোজ্য "
        "ক্ষেত্রে নিবন্ধীকরণ কর্তৃপক্ষের নিকট দাখিল করা হবে।"
    ),
    "en": (
        "Audit shall be completed by an approved audit firm / chartered accountant and, where "
        "applicable, filed with the registration authority."
    ),
}

AMENDMENTS = {
    "title_bn": "গঠনতন্ত্রের সংশোধন",
    "title_en": "Amendments",
    "bn": (
        "উপদেষ্টা পরিষদ সভায় ২/৩ (দুই তৃতীয়াংশ) সদস্যের অনুমোদনক্রমে গঠনতন্ত্রের যে কোনো "
        "ধারা বা উপ-ধারা সংশোধন করা যাবে এবং নিবন্ধীকরণ কর্তৃপক্ষের অনুমোদন সাপেক্ষে তা "
        "কার্যকর হবে।"
    ),
    "en": (
        "Any clause or sub-clause of the constitution may be amended with the approval of "
        "two-thirds (2/3) of members present at an Advisory Council meeting, and shall take "
        "effect subject to approval by the registration authority."
    ),
}

AOA_DISSOLUTION = {
    "title_bn": "সোসাইটির বিলুপ্তি",
    "title_en": "Dissolution of the Society",
    "bn": (
        "উপদেষ্টা পরিষদ সভায় মোট সদস্যের ৩/৫ (তিন পঞ্চমাংশ) সদস্যের ভোটে সোসাইটির "
        "বিলুপ্তি ঘোষণার প্রস্তাব অনুমোদনক্রমে রেজিস্ট্রেশন কর্তৃপক্ষের নিকট চূড়ান্ত অনুমোদনের "
        "জন্য প্রেরণ করতে হবে। সোসাইটি ভঙ্গ যাওয়ার পর দায়-দেনা পরিশোধের পরেও যদি কোন "
        "সম্পত্তি অবশিষ্ট থাকে, তবে নিবন্ধীকরণ কর্তৃপক্ষের অনুমোদনক্রমে অনুরূপ লক্ষ্য ও "
        "উদ্দেশ্য সম্পন্ন অন্য কোন নিবন্ধীকৃত সোসাইটিকে উক্ত উদ্বৃত্ত বিষয় সম্পত্তি প্রদান করা "
        "যাবে। বিলুপ্তির বিষয়ে রেজিস্ট্রেশন কর্তৃপক্ষের সুপারিশক্রমে দেশাদি সিদ্ধান্তই চূড়ান্ত "
        "বলে বিবেচিত হবে।"
    ),
    "en": (
        "A proposal to dissolve the Society, approved by three-fifths (3/5) of total members "
        "voting at an Advisory Council meeting, shall be sent to the registration authority for "
        "final approval. After winding up and settling liabilities, any remaining property may, "
        "with registration-authority approval, be given to another registered society with "
        "similar aims and objects. On dissolution, the decision of the registration authority "
        "shall be final."
    ),
}

LAW_COMPLIANCE = {
    "title_bn": "আইন অনুসরণ",
    "title_en": "Compliance with Law",
    "bn": (
        "এই গঠনতন্ত্র The Societies Registration Act, 1860 (Act No. XXI of 1860)-এর বিধান "
        "অনুসারে প্রণীত এবং উক্ত আইনের সাথে সাংঘর্ষিক কোনো ধারা থাকলে আইনের বিধান প্রাধান্য পাবে।"
    ),
    "en": (
        "This constitution is framed in accordance with the Societies Registration Act, 1860 "
        "(Act No. XXI of 1860). If any clause conflicts with that Act, the provisions of the Act shall prevail."
    ),
}

LEGAL_NOTICE = {
    "title_bn": "আইনগত নোটিশ",
    "title_en": "Legal Notice",
    "bn": (
        "এই ওয়েব পৃষ্ঠাটি জাররাহ ফাউন্ডেশনের নিবন্ধিত সংঘস্মারক ও গঠনতন্ত্রের সহজপাঠ্য উপস্থাপনা। "
        "ওয়েব সংস্করণ এবং অফিসিয়ালি নিবন্ধিত পিডিএফ-এর মধ্যে কোনো অসামঞ্জস্য দেখা দিলে, "
        "অফিসিয়ালি নিবন্ধিত পিডিএফ প্রাধান্য পাবে।"
    ),
    "en": (
        "This web page is a readable presentation of Zarrah Foundation's registered Memorandum "
        "and Articles of Association. In case of any inconsistency between this web version and "
        "the officially registered PDF, the officially registered PDF shall prevail."
    ),
}

TOC = [
    {"id": "about", "bn": "গঠনতন্ত্র সম্পর্কে", "en": "About"},
    {"id": "memorandum", "bn": "সংঘস্মারক", "en": "Memorandum"},
    {"id": "objectives", "bn": "লক্ষ্য ও উদ্দেশ্য", "en": "Objectives"},
    {"id": "structure", "bn": "সাংগঠনিক কাঠামো", "en": "Structure"},
    {"id": "executive", "bn": "কার্যনির্বাহী পরিষদ", "en": "Executive Council"},
    {"id": "membership", "bn": "সদস্যপদ", "en": "Membership"},
    {"id": "governance", "bn": "সভা ও পরিচালনা", "en": "Governance"},
    {"id": "finance", "bn": "অর্থ ও নিরীক্ষা", "en": "Finance & Audit"},
    {"id": "amendments", "bn": "সংশোধন ও বিলুপ্তি", "en": "Amendments"},
    {"id": "founders", "bn": "প্রতিষ্ঠাতা সদস্য", "en": "Founders"},
    {"id": "download", "bn": "পিডিএফ ডাউনলোড", "en": "Download PDF"},
]


def resolve_registration():
    """Prefer SiteSettings registration facts over static constitution defaults."""
    import copy

    reg = copy.deepcopy(REGISTRATION)
    try:
        from core.models import SiteSettings
        from django.utils.formats import date_format

        settings = SiteSettings.load()
        if settings.registration_number:
            reg["number"] = settings.registration_number
        if settings.registration_date:
            formatted = date_format(settings.registration_date, "j F Y")
            reg["date_en"] = formatted
            reg["date_bn"] = formatted
    except Exception:
        pass
    return reg


def get_context():
    return {
        "constitution_pdf_url": PDF_MEDIA_PATH,
        "constitution_pdf_meta": PDF_META,
        "constitution_registration": resolve_registration(),
        "constitution_hero": HERO,
        "constitution_about": ABOUT,
        "constitution_moa_name": MOA_NAME,
        "constitution_moa_office": MOA_OFFICE,
        "constitution_moa_area": MOA_AREA,
        "constitution_moa_nature": MOA_NATURE,
        "constitution_objectives": OBJECTIVES,
        "constitution_moa_income": MOA_INCOME,
        "constitution_moa_dissolution": MOA_DISSOLUTION,
        "constitution_founders": [_founder_card(p) for p in FOUNDERS],
        "constitution_founders_intro": FOUNDERS_INTRO,
        "constitution_founders_privacy": FOUNDERS_PRIVACY,
        "constitution_definitions": AOA_DEFINITIONS,
        "constitution_eligibility": MEMBERSHIP_ELIGIBILITY,
        "constitution_fees": MEMBERSHIP_FEES,
        "constitution_cancel": MEMBERSHIP_CANCEL,
        "constitution_restore": MEMBERSHIP_RESTORE,
        "constitution_org": ORG_STRUCTURE,
        "constitution_advisory_powers": ADVISORY_POWERS,
        "constitution_executive_posts": EXECUTIVE_POSTS,
        "constitution_executive_duties": EXECUTIVE_DUTIES,
        "constitution_officer_roles": OFFICER_ROLES,
        "constitution_meetings": MEETINGS,
        "constitution_quorum": QUORUM,
        "constitution_adjourned": ADJOURNED,
        "constitution_elections": ELECTIONS,
        "constitution_term_year": TERM_YEAR,
        "constitution_sub_committee": SUB_COMMITTEE,
        "constitution_legal_rep": LEGAL_REP,
        "constitution_finance_sources": FINANCE_SOURCES,
        "constitution_finance_expense": FINANCE_EXPENSE,
        "constitution_accounts": ACCOUNTS,
        "constitution_audit": AUDIT,
        "constitution_amendments": AMENDMENTS,
        "constitution_aoa_dissolution": AOA_DISSOLUTION,
        "constitution_law": LAW_COMPLIANCE,
        "constitution_legal_notice": LEGAL_NOTICE,
        "constitution_toc": TOC,
    }
