"""Bilingual Terms of Service content for Zarrah Foundation.

Structured similarly to ``privacy_data.py``. Wording is appropriate for a
Bangladeshi nonprofit and avoids inventing unsupported legal claims.
"""

LAST_UPDATED = {
    "bn": "৮ আগস্ট ২০২৬",
    "en": "8 August 2026",
}

HERO = {
    "eyebrow_bn": "সেবার শর্তাবলি",
    "eyebrow_en": "Terms of Service",
    "title_bn": "সেবার শর্তাবলি",
    "title_en": "Terms of Service",
    "subtitle_bn": (
        "জাররাহ ফাউন্ডেশনের ওয়েবসাইট ও সংশ্লিষ্ট ডিজিটাল সেবা ব্যবহারের শর্তাবলি। "
        "সাইট ব্যবহার করে আপনি এই শর্তাবলি মেনে চলতে সম্মত হন।"
    ),
    "subtitle_en": (
        "These Terms govern use of Zarrah Foundation’s website and related digital services. "
        "By using the site, you agree to these Terms."
    ),
}

TOC = [
    {"id": "introduction", "title_bn": "ভূমিকা", "title_en": "Introduction"},
    {"id": "acceptance", "title_bn": "গ্রহণযোগ্যতা", "title_en": "Acceptance"},
    {"id": "eligibility", "title_bn": "যোগ্যতা", "title_en": "Eligibility"},
    {"id": "accounts", "title_bn": "অ্যাকাউন্ট", "title_en": "Accounts"},
    {"id": "donations", "title_bn": "দান", "title_en": "Donations"},
    {"id": "membership", "title_bn": "সদস্যপদ", "title_en": "Membership"},
    {"id": "responsibilities", "title_bn": "ব্যবহারকারীর দায়িত্ব", "title_en": "User Responsibilities"},
    {"id": "ip", "title_bn": "বুদ্ধিবৃত্তিক সম্পত্তি", "title_en": "Intellectual Property"},
    {"id": "third_party", "title_bn": "তৃতীয় পক্ষের সেবা", "title_en": "Third-party Services"},
    {"id": "privacy", "title_bn": "গোপনীয়তা", "title_en": "Privacy"},
    {"id": "disclaimers", "title_bn": "দাবিত্যাগ", "title_en": "Disclaimers"},
    {"id": "liability", "title_bn": "দায় সীমাবদ্ধতা", "title_en": "Limitation of Liability"},
    {"id": "changes", "title_bn": "পরিবর্তন", "title_en": "Changes"},
    {"id": "contact", "title_bn": "যোগাযোগ", "title_en": "Contact"},
]

SECTIONS = [
    {
        "id": "introduction",
        "title_bn": "ভূমিকা",
        "title_en": "Introduction",
        "bn": (
            "জাররাহ ফাউন্ডেশন বাংলাদেশে নিবন্ধিত একটি অলাভজনক সংস্থা। এই ওয়েবসাইট "
            "সদস্যপদ, দান, স্বেচ্ছাসেবা, প্রতিবেদন ও সাধারণ তথ্য প্রদানের জন্য পরিচালিত হয়।"
        ),
        "en": (
            "Zarrah Foundation is a registered nonprofit organization in Bangladesh. "
            "This website supports membership, donations, volunteering, public reporting "
            "and general information about the Foundation’s work."
        ),
    },
    {
        "id": "acceptance",
        "title_bn": "গ্রহণযোগ্যতা",
        "title_en": "Acceptance",
        "bn": (
            "সাইট বা সংশ্লিষ্ট সেবা ব্যবহার করে আপনি এই সেবার শর্তাবলি এবং প্রযোজ্য "
            "বাংলাদেশের আইন মেনে চলতে সম্মত হন। আপনি সম্মত না হলে সাইট ব্যবহার করবেন না।"
        ),
        "en": (
            "By accessing or using the site or related services, you agree to these Terms "
            "and applicable laws of Bangladesh. If you do not agree, do not use the site."
        ),
    },
    {
        "id": "eligibility",
        "title_bn": "যোগ্যতা",
        "title_en": "Eligibility",
        "bn": (
            "কিছু সেবা (যেমন সদস্যপদ আবেদন বা ভোট) নির্দিষ্ট যোগ্যতার উপর নির্ভর করতে পারে। "
            "আপনি যে তথ্য প্রদান করেন তা সঠিক ও সম্পূর্ণ রাখার দায়িত্ব আপনার।"
        ),
        "en": (
            "Some services (such as membership applications or voting) may depend on "
            "eligibility criteria set by the Foundation. You are responsible for providing "
            "accurate and complete information."
        ),
    },
    {
        "id": "accounts",
        "title_bn": "অ্যাকাউন্ট",
        "title_en": "Accounts",
        "bn": (
            "অ্যাকাউন্ট তৈরি করলে আপনাকে বৈধ ইমেইল যাচাই করতে হতে পারে। আপনার লগইন "
            "তথ্য সুরক্ষিত রাখার দায়িত্ব আপনার। অননুমোদিত ব্যবহারের সন্দেহ হলে অবিলম্বে "
            "ফাউন্ডেশনকে জানান।"
        ),
        "en": (
            "Creating an account may require email verification. You are responsible for "
            "keeping your login credentials secure. Notify the Foundation promptly if you "
            "suspect unauthorized use of your account."
        ),
    },
    {
        "id": "donations",
        "title_bn": "দান",
        "title_en": "Donations",
        "bn": (
            "অনলাইন দান তৃতীয় পক্ষের পেমেন্ট গেটওয়ের মাধ্যমে প্রক্রিয়া হতে পারে। "
            "লেনদেনের সফলতা গেটওয়ে ও ব্যাংক/মোবাইল ব্যাংকিং সেবার উপর নির্ভর করে। "
            "রসিদ ও স্থিতি সাইটে বা ইমেইলে প্রদর্শিত হতে পারে। দানের উদ্দেশ্য "
            "ফাউন্ডেশনের ঘোষিত লক্ষ্য ও প্রযোজ্য আইনের সাথে সামঞ্জস্যপূর্ণ হতে হবে।"
        ),
        "en": (
            "Online donations may be processed through third-party payment gateways. "
            "Successful completion depends on the gateway and banking or mobile-banking "
            "services. Receipts and status may be shown on the site or by email. Donations "
            "must be consistent with the Foundation’s stated purposes and applicable law."
        ),
    },
    {
        "id": "membership",
        "title_bn": "সদস্যপদ",
        "title_en": "Membership",
        "bn": (
            "সদস্যপদ আবেদন পর্যালোচনার অধীন। অনুমোদন, প্রত্যাখ্যান বা স্থগিতাদেশ "
            "ফাউন্ডেশনের নীতি ও গঠনতন্ত্র অনুযায়ী নির্ধারিত হয়। সদস্যদের অধিকার "
            "ও দায়িত্ব সংশ্লিষ্ট নথি ও ঘোষণায় বর্ণিত থাকে।"
        ),
        "en": (
            "Membership applications are subject to review. Approval, rejection or "
            "suspension is determined under the Foundation’s policies and constitution. "
            "Member rights and responsibilities are described in the relevant governing documents."
        ),
    },
    {
        "id": "responsibilities",
        "title_bn": "ব্যবহারকারীর দায়িত্ব",
        "title_en": "User Responsibilities",
        "bn": (
            "আপনি সাইট অবৈধ, ক্ষতিকর বা বিভ্রান্তিকর উদ্দেশ্যে ব্যবহার করবেন না। "
            "মিথ্যা তথ্য প্রদান, সিস্টেমের নিরাপত্তা লঙ্ঘন, বা অন্যের অধিকার ক্ষুণ্ন "
            "করা নিষিদ্ধ।"
        ),
        "en": (
            "You must not use the site for unlawful, harmful or misleading purposes. "
            "Providing false information, attempting to breach system security, or "
            "infringing the rights of others is prohibited."
        ),
    },
    {
        "id": "ip",
        "title_bn": "বুদ্ধিবৃত্তিক সম্পত্তি",
        "title_en": "Intellectual Property",
        "bn": (
            "সাইটের লেখা, লোগো, নকশা ও অন্যান্য উপকরণ ফাউন্ডেশন বা সংশ্লিষ্ট "
            "অধিকারীর মালিকানাধীন, যদি না অন্যথায় উল্লেখ থাকে। অনুমতি ছাড়া "
            "বাণিজ্যিক পুনঃব্যবহার করা যাবে না।"
        ),
        "en": (
            "Text, logos, design and other materials on the site are owned by the "
            "Foundation or relevant rights holders unless otherwise stated. Commercial "
            "reuse without permission is not allowed."
        ),
    },
    {
        "id": "third_party",
        "title_bn": "তৃতীয় পক্ষের সেবা",
        "title_en": "Third-party Services",
        "bn": (
            "সাইট পেমেন্ট গেটওয়ে, মানচিত্র বা অন্যান্য তৃতীয় পক্ষের সেবা ব্যবহার "
            "করতে পারে। সেই সেবাগুলোর নিজস্ব শর্ত ও গোপনীয়তা নীতি প্রযোজ্য হতে পারে।"
        ),
        "en": (
            "The site may use payment gateways, maps or other third-party services. "
            "Those services may have their own terms and privacy policies."
        ),
    },
    {
        "id": "privacy",
        "title_bn": "গোপনীয়তা",
        "title_en": "Privacy",
        "bn": (
            "ব্যক্তিগত তথ্য প্রক্রিয়াকরণ আমাদের গোপনীয়তা নীতি অনুযায়ী পরিচালিত হয়। "
            "বিস্তারিত জানতে গোপনীয়তা নীতি পাতা দেখুন।"
        ),
        "en": (
            "Processing of personal information is governed by our Privacy Policy. "
            "Please review the Privacy Policy page for details."
        ),
    },
    {
        "id": "disclaimers",
        "title_bn": "দাবিত্যাগ",
        "title_en": "Disclaimers",
        "bn": (
            "সাইটের তথ্য সাধারণ অবহিতির জন্য প্রদান করা হয়। ফাউন্ডেশন যুক্তিসঙ্গত "
            "প্রচেষ্টা করে তথ্য হালনাগাদ রাখতে, তবে সম্পূর্ণতা বা নির্ভুলতার কোনো "
            "পরম নিশ্চয়তা দেওয়া হয় না। সাইট \"যেমন আছে\" ভিত্তিতে প্রদান করা হয়।"
        ),
        "en": (
            "Information on the site is provided for general information. The Foundation "
            "makes reasonable efforts to keep content current, but does not guarantee "
            "absolute completeness or accuracy. The site is provided on an “as is” basis."
        ),
    },
    {
        "id": "liability",
        "title_bn": "দায় সীমাবদ্ধতা",
        "title_en": "Limitation of Liability",
        "bn": (
            "প্রযোজ্য আইন অনুমতি দিলে, ফাউন্ডেশন সাইট ব্যবহার বা ব্যবহার করতে না পারার "
            "ফলে সৃষ্ট পরোক্ষ বা আনুষঙ্গিক ক্ষতির জন্য দায়ী থাকবে না। কিছু বিষয়ে "
            "আইনগত অধিকার সীমিত করা যায় না; সেক্ষেত্রে সেই আইন প্রযোজ্য থাকবে।"
        ),
        "en": (
            "To the extent permitted by applicable law, the Foundation is not liable for "
            "indirect or incidental losses arising from use of, or inability to use, the site. "
            "Where the law does not allow limitation of certain rights, those rights remain."
        ),
    },
    {
        "id": "changes",
        "title_bn": "পরিবর্তন",
        "title_en": "Changes",
        "bn": (
            "ফাউন্ডেশন সময়ে সময়ে এই শর্তাবলি হালনাগাদ করতে পারে। হালনাগাদ এই পাতায় "
            "প্রকাশ করা হবে। পরিবর্তনের পর সাইট ব্যবহার অব্যাহত রাখলে আপডেটেড শর্ত "
            "গ্রহণ করা হয়েছে বলে ধরা হবে।"
        ),
        "en": (
            "The Foundation may update these Terms from time to time. Updates will be "
            "posted on this page. Continued use of the site after changes constitutes "
            "acceptance of the revised Terms."
        ),
    },
    {
        "id": "contact",
        "title_bn": "যোগাযোগ",
        "title_en": "Contact",
        "bn": (
            "এই শর্তাবলি সম্পর্কিত প্রশ্ন যোগাযোগ পাতায় প্রদত্ত মাধ্যমে জমা দেওয়া যেতে পারে।"
        ),
        "en": (
            "Questions about these Terms may be submitted using the channels on the Contact page."
        ),
    },
]


def get_context():
    return {
        "terms_last_updated": LAST_UPDATED,
        "terms_hero": HERO,
        "terms_toc": TOC,
        "terms_sections": SECTIONS,
    }
