"""
Bilingual Privacy Policy content for Zarrah Foundation.

Expands the existing public statement that the Foundation collects only
information necessary to provide services and does not share personal data
with third parties without consent — organised for a professional NGO policy page.
"""

LAST_UPDATED = {
    "bn": "২৩ জুলাই ২০২৬",
    "en": "23 July 2026",
}

HERO = {
    "eyebrow_bn": "গোপনীয়তা নীতি",
    "eyebrow_en": "Privacy Policy",
    "title_bn": "গোপনীয়তা নীতি",
    "title_en": "Privacy Policy",
    "subtitle_bn": (
        "জাররাহ ফাউন্ডেশন আপনার গোপনীয়তাকে সম্মান করে। আমরা শুধুমাত্র সেবা প্রদানের জন্য "
        "প্রয়োজনীয় তথ্য সংগ্রহ করি এবং আপনার সম্মতি ছাড়া তৃতীয় পক্ষের সাথে ব্যক্তিগত তথ্য ভাগ করি না।"
    ),
    "subtitle_en": (
        "Zarrah Foundation respects your privacy. We collect only the information necessary "
        "to provide our services and do not share personal data with third parties without consent."
    ),
}

PRINCIPLES = [
    {
        "icon": "bi-shield-lock-fill",
        "title_bn": "ন্যূনতম তথ্য সংগ্রহ",
        "title_en": "Data Minimisation",
        "text_bn": "সেবা প্রদানের জন্য প্রয়োজনীয় তথ্যই সংগ্রহ করা হয় এবং তা নির্ধারিত উদ্দেশ্যে ব্যবহার করা হয়।",
        "text_en": "Only information required to provide services is collected, and it is used for stated purposes.",
    },
    {
        "icon": "bi-lock-fill",
        "title_bn": "তথ্য নিরাপত্তা",
        "title_en": "Information Security",
        "text_bn": "অননুমোদিত প্রবেশ, পরিবর্তন বা প্রকাশ রোধে প্রশাসনিক ও প্রযুক্তিগত সুরক্ষা প্রয়োগ করা হয়।",
        "text_en": "Administrative and technical measures are applied to reduce unauthorised access, alteration or disclosure.",
    },
    {
        "icon": "bi-file-text",
        "title_bn": "স্বচ্ছতা",
        "title_en": "Transparency",
        "text_bn": "কী তথ্য সংগ্রহ করা হয়, কীভাবে ব্যবহার করা হয় এবং কোন পরিস্থিতিতে প্রকাশ করা হয় তা এই নীতিতে বর্ণিত।",
        "text_en": "This Policy describes what information is collected, how it is used, and the circumstances in which it may be disclosed.",
    },
    {
        "icon": "bi-person-check",
        "title_bn": "ব্যক্তিগত অধিকার",
        "title_en": "Individual Rights",
        "text_bn": "প্রযোজ্য আইনের অধীনে তথ্য দেখা, সংশোধন, মুছে ফেলা বা সম্মতি প্রত্যাহারের অনুরোধ করা যায়।",
        "text_en": "Subject to applicable law, individuals may request access, correction, deletion or withdrawal of consent.",
    },
]

TOC = [
    {"id": "introduction", "bn": "ভূমিকা", "en": "Introduction"},
    {"id": "collect", "bn": "সংগৃহীত তথ্য", "en": "Information We Collect"},
    {"id": "use", "bn": "তথ্যের ব্যবহার", "en": "Use of Information"},
    {"id": "cookies", "bn": "কুকিজ", "en": "Cookies"},
    {"id": "third-party", "bn": "তৃতীয় পক্ষ", "en": "Third-party Services"},
    {"id": "sharing", "bn": "তথ্য ভাগাভাগি", "en": "Sharing"},
    {"id": "security", "bn": "নিরাপত্তা", "en": "Security"},
    {"id": "retention", "bn": "সংরক্ষণ", "en": "Retention"},
    {"id": "rights", "bn": "আপনার অধিকার", "en": "User Rights"},
    {"id": "children", "bn": "শিশুদের গোপনীয়তা", "en": "Children"},
    {"id": "international", "bn": "আন্তর্জাতিক দর্শক", "en": "International"},
    {"id": "updates", "bn": "নীতি হালনাগাদ", "en": "Policy Updates"},
    {"id": "contact", "bn": "যোগাযোগ", "en": "Contact"},
]

INTRODUCTION = {
    "title_bn": "ভূমিকা",
    "title_en": "Introduction",
    "bn": (
        "এই গোপনীয়তা নীতি ব্যাখ্যা করে যে জাররাহ ফাউন্ডেশন (\"আমরা\", \"আমাদের\" বা \"ফাউন্ডেশন\") "
        "ওয়েবসাইট, সদস্যপদ, অনুদান, স্বেচ্ছাসেবা এবং যোগাযোগ সেবার মাধ্যমে কীভাবে ব্যক্তিগত তথ্য "
        "সংগ্রহ, ব্যবহার, সংরক্ষণ ও সুরক্ষা করে। আমাদের ওয়েবসাইট ব্যবহার করে বা আমাদের সাথে "
        "যোগাযোগ করে আপনি এই নীতির সাথে পরিচিত হচ্ছেন বলে ধরে নেওয়া হয়।"
    ),
    "en": (
        "This Privacy Policy explains how Zarrah Foundation (\"we\", \"us\" or \"the Foundation\") "
        "collects, uses, stores and protects personal information through our website, membership, "
        "donations, volunteering and communication services. By using our website or contacting us, "
        "you acknowledge this Policy."
    ),
    "notice_bn": (
        "আমরা কেবল সেবা প্রদানের জন্য প্রয়োজনীয় তথ্য সংগ্রহ করি এবং আপনার সম্মতি ছাড়া "
        "তৃতীয় পক্ষের সাথে ব্যক্তিগত তথ্য ভাগ করি না — আইনগত বাধ্যবাধকতা বা সেবা প্রদানের "
        "জন্য প্রয়োজনীয় ক্ষেত্র ছাড়া।"
    ),
    "notice_en": (
        "We collect only the information necessary to provide our services and do not share "
        "personal data with third parties without consent — except where required by law or "
        "strictly necessary to deliver a requested service."
    ),
}

COLLECT_INTRO = {
    "bn": "সেবা পরিচালনার ধরন অনুযায়ী আমরা নিম্নলিখিত শ্রেণির তথ্য সংগ্রহ করতে পারি।",
    "en": "Depending on how you interact with us, we may collect the following categories of information.",
}

COLLECT_CATEGORIES = [
    {
        "icon": "bi-person-fill",
        "title_bn": "ব্যক্তিগত তথ্য",
        "title_en": "Personal Information",
        "bn": "নাম, পূর্ণ নাম, জন্মতারিখ (প্রযোজ্য ক্ষেত্রে), জাতীয় পরিচয় সংক্রান্ত তথ্য যেখানে আইন বা সদস্যপদ যাচাইয়ের জন্য প্রয়োজন, এবং অ্যাকাউন্ট সম্পর্কিত বিবরণ।",
        "en": "Name, full name, date of birth (where applicable), identity-related details where required by law or membership verification, and account-related details.",
    },
    {
        "icon": "bi-envelope-fill",
        "title_bn": "যোগাযোগের তথ্য",
        "title_en": "Contact Information",
        "bn": "ইমেইল ঠিকানা, মোবাইল নম্বর, পোস্টাল ঠিকানা এবং যোগাযোগ ফর্ম বা স্বেচ্ছাসেবা আবেদনে প্রদত্ত অন্যান্য যোগাযোগের বিবরণ।",
        "en": "Email address, phone number, postal address and other contact details you provide through forms, membership or volunteer applications.",
    },
    {
        "icon": "bi-people-fill",
        "title_bn": "সদস্যপদ সংক্রান্ত তথ্য",
        "title_en": "Membership Information",
        "bn": "সদস্যপদ আবেদন, সদস্য ধরন, ফি ও অবস্থা, জরুরি যোগাযোগ এবং সংস্থার কার্যক্রমে অংশগ্রহণ সম্পর্কিত তথ্য।",
        "en": "Membership applications, membership type, fees and status, emergency contacts and information related to participation in Foundation activities.",
    },
    {
        "icon": "bi-heart-fill",
        "title_bn": "অনুদান সংক্রান্ত তথ্য",
        "title_en": "Donation Information",
        "bn": "দাতার নাম ও যোগাযোগ, অনুদানের পরিমাণ, রসিদ নম্বর, লেনদেনের অবস্থা এবং পেমেন্ট গেটওয়ে থেকে প্রাপ্ত নিশ্চিতকরণ তথ্য। আমরা সম্পূর্ণ কার্ড নম্বর সংরক্ষণ করি না।",
        "en": "Donor name and contact details, donation amount, receipt number, transaction status and confirmation data received from the payment gateway. We do not store full card numbers.",
    },
    {
        "icon": "bi-hdd-network-fill",
        "title_bn": "প্রযুক্তিগত তথ্য",
        "title_en": "Technical Information",
        "bn": "আইপি ঠিকানা, ব্রাউজার ধরন, ডিভাইস তথ্য, পেজ ভিউ, রেফারার এবং কুকিজ বা অনুরূপ প্রযুক্তির মাধ্যমে সংগৃহীত লগ তথ্য — সাইট নিরাপত্তা ও কর্মক্ষমতার জন্য।",
        "en": "IP address, browser type, device information, page views, referrers and log data collected via cookies or similar technologies — for security and performance.",
    },
]

USE_INTRO = {
    "bn": "সংগৃহীত তথ্য আমরা নিম্নলিখিত উদ্দেশ্যে ব্যবহার করতে পারি।",
    "en": "We may use collected information for the following purposes.",
}

USE_ITEMS = [
    {
        "icon": "bi-person-badge",
        "title_bn": "সদস্যপদ ব্যবস্থাপনা",
        "title_en": "Membership management",
        "bn": "আবেদন যাচাই, সদস্য রেকর্ড রক্ষণাবেক্ষণ এবং সদস্য সেবা প্রদান।",
        "en": "Verifying applications, maintaining member records and providing membership services.",
    },
    {
        "icon": "bi-credit-card",
        "title_bn": "অনুদান প্রক্রিয়াকরণ",
        "title_en": "Donation processing",
        "bn": "অনলাইন ও অন্যান্য অনুদান গ্রহণ, রসিদ প্রদান এবং আর্থিক স্বচ্ছতা বজায় রাখা।",
        "en": "Receiving online and other donations, issuing receipts and maintaining financial transparency.",
    },
    {
        "icon": "bi-chat-dots",
        "title_bn": "যোগাযোগ",
        "title_en": "Communication",
        "bn": "আপনার প্রশ্নের জবাব, আপডেট পাঠানো এবং সেবা সংক্রান্ত বিজ্ঞপ্তি প্রদান।",
        "en": "Responding to enquiries, sending updates and providing service-related notices.",
    },
    {
        "icon": "bi-hand-thumbs-up",
        "title_bn": "স্বেচ্ছাসেবা ব্যবস্থাপনা",
        "title_en": "Volunteer management",
        "bn": "স্বেচ্ছাসেবক আবেদন মূল্যায়ন এবং কার্যক্রমে অংশগ্রহণ সমন্বয়।",
        "en": "Assessing volunteer applications and coordinating participation in programmes.",
    },
    {
        "icon": "bi-bar-chart-line",
        "title_bn": "প্রতিবেদন ও স্বচ্ছতা",
        "title_en": "Reporting",
        "bn": "অভ্যন্তরীণ প্রতিবেদন এবং প্রকাশ্য স্বচ্ছতা প্রতিবেদন (যেখানে ব্যক্তি শনাক্তযোগ্য নয়)।",
        "en": "Internal reporting and public transparency reports (where individuals are not identified).",
    },
    {
        "icon": "bi-bank",
        "title_bn": "আইনগত সম্মতি",
        "title_en": "Legal compliance",
        "bn": "প্রযোজ্য আইন, নিয়ন্ত্রক অনুরোধ এবং হিসাবরক্ষণ বাধ্যবাধকতা পূরণ।",
        "en": "Meeting applicable laws, regulatory requests and accounting obligations.",
    },
]

COOKIES = {
    "title_bn": "কুকিজ",
    "title_en": "Cookies",
    "intro_bn": (
        "আমাদের ওয়েবসাইট প্রয়োজনীয় কার্যকারিতা, পছন্দ এবং (প্রযোজ্য ক্ষেত্রে) বিশ্লেষণের জন্য "
        "কুকিজ ও অনুরূপ প্রযুক্তি ব্যবহার করতে পারে।"
    ),
    "intro_en": (
        "Our website may use cookies and similar technologies for essential functionality, "
        "preferences and, where applicable, analytics."
    ),
    "items": [
        {
            "icon": "bi-shield-check",
            "title_bn": "অত্যাবশ্যক কুকিজ",
            "title_en": "Essential cookies",
            "bn": "লগইন, নিরাপত্তা, ভাষা পছন্দ এবং ফর্ম সুরক্ষার জন্য প্রয়োজনীয়। এগুলো ছাড়া সাইট সঠিকভাবে কাজ নাও করতে পারে।",
            "en": "Required for login, security, language preference and form protection. The site may not function correctly without them.",
        },
        {
            "icon": "bi-graph-up",
            "title_bn": "অ্যানালিটিক্স",
            "title_en": "Analytics",
            "bn": "সাইট ব্যবহার ও নিরাপত্তার উদ্দেশ্যে সমষ্টিগত পরিসংখ্যান সংগ্রহ করতে পারে (যদি সক্রিয় থাকে)।",
            "en": "May collect aggregated statistics for site usage and security purposes (when enabled).",
        },
        {
            "icon": "bi-sliders",
            "title_bn": "পছন্দ",
            "title_en": "Preferences",
            "bn": "ভাষা বা ইন্টারফেস পছন্দ সংরক্ষণে ব্যবহৃত হয়।",
            "en": "Used to retain language or interface preferences.",
        },
    ],
    "note_bn": "আপনি ব্রাউজার সেটিংস থেকে কুকিজ নিয়ন্ত্রণ বা মুছে ফেলতে পারেন। অত্যাবশ্যক কুকিজ নিষ্ক্রিয় করলে কিছু সেবা সীমিত হতে পারে।",
    "note_en": "You can control or delete cookies in your browser settings. Disabling essential cookies may limit some services.",
}

THIRD_PARTY = {
    "title_bn": "তৃতীয় পক্ষের সেবা",
    "title_en": "Third-party Services",
    "intro_bn": (
        "সেবা পরিচালনার জন্য ফাউন্ডেশন তৃতীয় পক্ষের সেবা প্রদানকারী ব্যবহার করতে পারে। "
        "এই প্রদানকারীরা কেবল নির্দেশিত পরিসরে এবং প্রয়োজনীয় পরিমাণে তথ্য প্রক্রিয়া করে।"
    ),
    "intro_en": (
        "The Foundation may engage third-party service providers to operate its services. "
        "Such providers process information only as instructed and to the extent necessary."
    ),
    "items": [
        {
            "icon": "bi-credit-card-2-front",
            "title_bn": "পেমেন্ট গেটওয়ে",
            "title_en": "Payment Gateway",
            "bn": "অনলাইন অনুদান প্রক্রিয়াকরণের জন্য SSLCommerz বা অন্যান্য পেমেন্ট সেবা।",
            "en": "SSLCommerz or other payment services used to process online donations.",
        },
        {
            "icon": "bi-envelope-at",
            "title_bn": "ইমেইল",
            "title_en": "Email",
            "bn": "লেনদেনমূলক ইমেইল, রসিদ এবং যোগাযোগ প্রেরণের জন্য ইমেইল সেবা।",
            "en": "Email delivery services for transactional messages, receipts and correspondence.",
        },
        {
            "icon": "bi-cloud",
            "title_bn": "হোস্টিং",
            "title_en": "Hosting",
            "bn": "ওয়েবসাইট ও ডেটাবেস হোস্টিং প্রদানকারী।",
            "en": "Website and database hosting providers.",
        },
        {
            "icon": "bi-bar-chart",
            "title_bn": "অ্যানালিটিক্স",
            "title_en": "Analytics",
            "bn": "সাইট ব্যবহার ও কর্মক্ষমতা বিশ্লেষণের সরঞ্জাম (যদি সক্রিয় থাকে)।",
            "en": "Tools used to analyse site usage and performance (when enabled).",
        },
        {
            "icon": "bi-geo-alt",
            "title_bn": "মানচিত্র",
            "title_en": "Maps",
            "bn": "ঠিকানা বা অবস্থান প্রদর্শনের জন্য মানচিত্র সেবা (প্রযোজ্য ক্ষেত্রে)।",
            "en": "Map services used to display addresses or locations, where applicable.",
        },
        {
            "icon": "bi-share",
            "title_bn": "সামাজিক যোগাযোগ মাধ্যম",
            "title_en": "Social Media",
            "bn": "ফাউন্ডেশনের সামাজিক মিডিয়া পেজ বা এমবেডেড কন্টেন্ট; সংশ্লিষ্ট প্ল্যাটফর্মের নিজস্ব নীতি প্রযোজ্য।",
            "en": "Foundation social media pages or embedded content; the policies of those platforms apply.",
        },
    ],
}

SHARING = {
    "title_bn": "তথ্য ভাগাভাগি",
    "title_en": "Information Sharing",
    "bn": (
        "আমরা আপনার ব্যক্তিগত তথ্য বিক্রি করি না। আপনার সম্মতি ছাড়া তৃতীয় পক্ষের সাথে "
        "ব্যক্তিগত তথ্য ভাগ করি না, নিম্নলিখিত সীমিত পরিস্থিতি ছাড়া: (ক) আপনার অনুরোধকৃত "
        "সেবা সম্পন্ন করতে প্রয়োজনীয় সেবা প্রদানকারীদের সাথে; (খ) আইন, আদালত বা নিয়ন্ত্রক "
        "কর্তৃপক্ষের বৈধ অনুরোধে; (গ) ফাউন্ডেশন, ব্যবহারকারী বা জনসাধারণের অধিকার ও নিরাপত্তা "
        "রক্ষায় প্রয়োজন হলে; (ঘ) সংস্থার পুনর্গঠন বা হস্তান্তরের ক্ষেত্রে, উপযুক্ত সুরক্ষা সহ।"
    ),
    "en": (
        "We do not sell your personal information. We do not share personal data with third "
        "parties without your consent, except in limited circumstances: (a) with service "
        "providers necessary to complete a service you requested; (b) when required by law, "
        "court or a competent authority; (c) to protect the rights and safety of the Foundation, "
        "users or the public; or (d) in connection with an organisational restructuring or "
        "transfer, with appropriate safeguards."
    ),
    "callout_bn": "মার্কেটিং বা বিজ্ঞাপনের জন্য আমরা ব্যক্তিগত তথ্য তৃতীয় পক্ষকে প্রদান করি না।",
    "callout_en": "We do not provide personal information to third parties for marketing or advertising.",
}

SECURITY = {
    "title_bn": "তথ্য নিরাপত্তা",
    "title_en": "Data Security",
    "bn": (
        "ফাউন্ডেশন প্রশাসনিক, প্রযুক্তিগত ও সাংগঠনিক ব্যবস্থা প্রয়োগ করে যাতে অননুমোদিত প্রবেশ, "
        "পরিবর্তন, প্রকাশ বা ধ্বংস থেকে ব্যক্তিগত তথ্য সুরক্ষিত থাকে। এতে অ্যাক্সেস নিয়ন্ত্রণ, "
        "এনক্রিপ্টেড সংযোগ (HTTPS), পাসওয়ার্ড সুরক্ষা, ভূমিকাভিত্তিক অনুমতি এবং কর্মী নির্দেশনা "
        "অন্তর্ভুক্ত থাকতে পারে। ইন্টারনেটের মাধ্যমে কোনো তথ্য আদান-প্রদান বা সংরক্ষণ পদ্ধতি "
        "সম্পূর্ণ ঝুঁকিমুক্ত নয়; ফাউন্ডেশন যুক্তিসঙ্গত সতর্কতা অবলম্বন করে।"
    ),
    "en": (
        "The Foundation applies administrative, technical and organisational measures to protect "
        "personal information against unauthorised access, alteration, disclosure or destruction. "
        "These may include access controls, encrypted connections (HTTPS), password protection, "
        "role-based permissions and staff guidance. No method of transmission or storage over the "
        "internet is completely secure; the Foundation takes reasonable precautions."
    ),
    "callout_bn": (
        "যুক্তিসঙ্গত নিরাপত্তা ব্যবস্থা থাকা সত্ত্বেও কোনো তথ্য ব্যবস্থা সম্পূর্ণ ঝুঁকিমুক্ত নয়।"
    ),
    "callout_en": (
        "Notwithstanding reasonable security measures, no information system is free from all risk."
    ),
}

RETENTION = {
    "title_bn": "তথ্য সংরক্ষণ",
    "title_en": "Data Retention",
    "bn": (
        "আমরা ব্যক্তিগত তথ্য কেবল সেই উদ্দেশ্য পূরণের জন্য প্রয়োজনীয় সময় পর্যন্ত সংরক্ষণ করি "
        "যার জন্য তা সংগ্রহ করা হয়েছিল, অথবা আইন, হিসাবরক্ষণ, কর বা বিরোধ নিষ্পত্তির জন্য "
        "যতদিন রাখা বাধ্যতামূলক। সদস্যপদ ও অনুদান রেকর্ড আইনগত ও স্বচ্ছতার প্রয়োজনে "
        "দীর্ঘতর সময় ধরে রাখা হতে পারে। অপ্রয়োজনীয় তথ্য নিরাপদভাবে মুছে ফেলা বা বেনামী করা হয়।"
    ),
    "en": (
        "We retain personal information only for as long as needed to fulfil the purposes for "
        "which it was collected, or as long as required for legal, accounting, tax or dispute "
        "resolution obligations. Membership and donation records may be kept longer where "
        "required by law or transparency duties. Information that is no longer needed is "
        "securely deleted or anonymised."
    ),
}

RIGHTS = {
    "title_bn": "আপনার অধিকার",
    "title_en": "User Rights",
    "intro_bn": "প্রযোজ্য আইনের অধীনে আপনি নিম্নলিখিত অধিকারগুলো প্রয়োগ করতে পারেন।",
    "intro_en": "Subject to applicable law, you may exercise the following rights.",
    "items": [
        {
            "icon": "bi-eye",
            "title_bn": "প্রবেশাধিকার",
            "title_en": "Access",
            "bn": "আমরা আপনার সম্পর্কে কী ব্যক্তিগত তথ্য রাখি তা জানার অনুরোধ।",
            "en": "Request confirmation of and access to personal information we hold about you.",
        },
        {
            "icon": "bi-pencil-square",
            "title_bn": "সংশোধন",
            "title_en": "Correction",
            "bn": "ভুল বা অসম্পূর্ণ তথ্য সংশোধনের অনুরোধ।",
            "en": "Request correction of inaccurate or incomplete information.",
        },
        {
            "icon": "bi-trash",
            "title_bn": "মুছে ফেলা",
            "title_en": "Deletion",
            "bn": "আইনগতভাবে অনুমোদিত ক্ষেত্রে তথ্য মুছে ফেলার অনুরোধ।",
            "en": "Request deletion of information where legally permitted.",
        },
        {
            "icon": "bi-x-circle",
            "title_bn": "সম্মতি প্রত্যাহার",
            "title_en": "Withdraw Consent",
            "bn": "যেখানে প্রক্রিয়াকরণ সম্মতির উপর নির্ভরশীল, সেখানে সম্মতি প্রত্যাহার।",
            "en": "Withdraw consent where processing is based on consent.",
        },
        {
            "icon": "bi-flag",
            "title_bn": "অভিযোগ",
            "title_en": "Complaint",
            "bn": "আমাদের সাথে অভিযোগ জানানো বা উপযুক্ত কর্তৃপক্ষের কাছে অভিযোগ দায়ের।",
            "en": "Raise a concern with us or lodge a complaint with a competent authority.",
        },
    ],
    "note_bn": "অধিকার প্রয়োগের অনুরোধ নিচের যোগাযোগ বিভাগে প্রেরণ করা যেতে পারে। ফাউন্ডেশন যুক্তিসঙ্গত সময়ের মধ্যে সাড়া দেবে এবং প্রয়োজনে পরিচয় যাচাই করতে পারে।",
    "note_en": "Requests to exercise these rights may be sent using the contact details below. The Foundation will respond within a reasonable time and may require identity verification.",
}

CHILDREN = {
    "title_bn": "শিশুদের গোপনীয়তা",
    "title_en": "Children's Privacy",
    "bn": (
        "ওয়েবসাইটের সেবা সাধারণত প্রাপ্তবয়স্কদের জন্য নির্ধারিত। ফাউন্ডেশন জেনেশুনে শিশুদের "
        "কাছ থেকে ব্যক্তিগত তথ্য সংগ্রহ করে না। যদি কোনো শিশুর তথ্য সংগৃহীত হয়েছে বলে "
        "মনে হয়, যোগাযোগ করুন; প্রয়োজনীয় ব্যবস্থা নেওয়া হবে।"
    ),
    "en": (
        "Website services are generally intended for adults. The Foundation does not knowingly "
        "collect personal information from children. If it appears that a child’s information "
        "has been collected, contact the Foundation; appropriate steps will be taken."
    ),
}

INTERNATIONAL = {
    "title_bn": "আন্তর্জাতিক দর্শক",
    "title_en": "International Visitors",
    "bn": (
        "জাররাহ ফাউন্ডেশন বাংলাদেশে নিবন্ধিত এবং মূলত বাংলাদেশ থেকে সেবা পরিচালনা করে। "
        "আপনি যদি অন্য দেশ থেকে সাইট ব্যবহার করেন, আপনার তথ্য বাংলাদেশে প্রক্রিয়া ও সংরক্ষণ "
        "হতে পারে। বিভিন্ন দেশে তথ্য সুরক্ষা আইন ভিন্ন হতে পারে।"
    ),
    "en": (
        "Zarrah Foundation is registered in Bangladesh and primarily operates from Bangladesh. "
        "If you access the site from another country, your information may be processed and "
        "stored in Bangladesh. Data protection laws vary by country."
    ),
}

UPDATES = {
    "title_bn": "নীতি হালনাগাদ",
    "title_en": "Policy Updates",
    "bn": (
        "আমরা সময়ে সময়ে এই গোপনীয়তা নীতি হালনাগাদ করতে পারি। পরিবর্তন এই পাতায় প্রকাশ "
        "করা হবে এবং উপরের \"সর্বশেষ হালনাগাদ\" তারিখ আপডেট করা হবে। গুরুত্বপূর্ণ পরিবর্তনের "
        "ক্ষেত্রে আমরা যুক্তিসঙ্গতভাবে অতিরিক্ত বিজ্ঞপ্তি দিতে পারি। হালনাগাদের পর সাইট "
        "ব্যবহার অব্যাহত রাখলে আপডেটেড নীতি গ্রহণ করা হয়েছে বলে ধরা হবে।"
    ),
    "en": (
        "We may update this Privacy Policy from time to time. Changes will be posted on this "
        "page and the \"Last updated\" date above will be revised. For material changes we may "
        "provide additional notice where reasonable. Continued use of the site after an update "
        "constitutes acceptance of the revised Policy."
    ),
}

CONTACT = {
    "title_bn": "যোগাযোগ",
    "title_en": "Contact Information",
    "bn": (
        "গোপনীয়তা সংক্রান্ত প্রশ্ন, অনুরোধ বা অভিযোগ এই নীতিতে প্রদত্ত যোগাযোগ মাধ্যমে "
        "জমা দেওয়া যেতে পারে। ফাউন্ডেশন যুক্তিসঙ্গত সময়ের মধ্যে সাড়া দেবে।"
    ),
    "en": (
        "Privacy-related questions, requests or complaints may be submitted using the contact "
        "details in this Policy. The Foundation will respond within a reasonable time."
    ),
}


def get_context():
    return {
        "privacy_last_updated": LAST_UPDATED,
        "privacy_hero": HERO,
        "privacy_principles": PRINCIPLES,
        "privacy_toc": TOC,
        "privacy_introduction": INTRODUCTION,
        "privacy_collect_intro": COLLECT_INTRO,
        "privacy_collect_categories": COLLECT_CATEGORIES,
        "privacy_use_intro": USE_INTRO,
        "privacy_use_items": USE_ITEMS,
        "privacy_cookies": COOKIES,
        "privacy_third_party": THIRD_PARTY,
        "privacy_sharing": SHARING,
        "privacy_security": SECURITY,
        "privacy_retention": RETENTION,
        "privacy_rights": RIGHTS,
        "privacy_children": CHILDREN,
        "privacy_international": INTERNATIONAL,
        "privacy_updates": UPDATES,
        "privacy_contact": CONTACT,
    }
