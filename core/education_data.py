"""Bilingual, fully-conditional education selector data.

No free-text is allowed anywhere in the membership application's education
section — every value below is a fixed, selectable option. The structure
mirrors Bangladesh's real education systems:

    General    -> Stage   -> Class (only for stages that have one)
    Qaumi      -> Marhala
    Alia       -> Level
    Technical  -> Level

Each leaf is a ``{"value": ..., "en": ..., "bn": ...}`` dict so templates /
JavaScript can render either language without a second data source. This is
served to the client as one small JSON blob (see members/views.py) — it is
tiny (a few KB) so it is safe to load eagerly, unlike the much larger
Bangladesh geo dataset.
"""

EDUCATION_TYPES = [
    {"value": "GENERAL", "en": "General Education", "bn": "সাধারণ শিক্ষা"},
    {"value": "QAUMI", "en": "Qaumi Madrasah", "bn": "কওমি মাদ্রাসা"},
    {"value": "ALIA", "en": "Alia Madrasah", "bn": "আলিয়া মাদ্রাসা"},
    {"value": "TECHNICAL", "en": "Technical / Vocational", "bn": "কারিগরি / ভোকেশনাল"},
]

# education_type -> list of {"value","en","bn"} for the "Stage / Marhala / Level" field.
EDUCATION_STAGES = {
    "GENERAL": [
        {"value": "PRIMARY", "en": "Primary (Class 1-5)", "bn": "প্রাথমিক (১ম-৫ম শ্রেণি)"},
        {"value": "JUNIOR_SECONDARY", "en": "Junior Secondary (Class 6-8)", "bn": "নিম্ন মাধ্যমিক (৬ষ্ঠ-৮ম শ্রেণি)"},
        {"value": "SECONDARY", "en": "Secondary / SSC (Class 9-10)", "bn": "মাধ্যমিক / এসএসসি (৯ম-১০ম শ্রেণি)"},
        {"value": "HIGHER_SECONDARY", "en": "Higher Secondary / HSC (Class 11-12)", "bn": "উচ্চ মাধ্যমিক / এইচএসসি (১১শ-১২শ শ্রেণি)"},
        {"value": "DIPLOMA", "en": "Diploma", "bn": "ডিপ্লোমা"},
        {"value": "BACHELOR", "en": "Bachelor's Degree", "bn": "স্নাতক (ব্যাচেলর)"},
        {"value": "MASTERS", "en": "Master's Degree", "bn": "স্নাতকোত্তর (মাস্টার্স)"},
        {"value": "PHD", "en": "MPhil / PhD", "bn": "এমফিল / পিএইচডি"},
    ],
    "QAUMI": [
        {"value": "EBTEDAYEE", "en": "Ebtedayee", "bn": "ইবতেদায়ী"},
        {"value": "MUTAWASSITAH", "en": "Mutawassitah", "bn": "মুতাওয়াসসিতাহ"},
        {"value": "SANABIYYA_AMMAH", "en": "Sanabiyyah Ammah", "bn": "সানাবিয়্যাহ আম্মাহ"},
        {"value": "SANABIYYA_ULYA", "en": "Sanabiyyah Ulya (Fazilat)", "bn": "সানাবিয়্যাহ উলইয়া (ফযীলত)"},
        {"value": "TAKMIL", "en": "Takmil (Dawra-e-Hadith)", "bn": "তাকমিল (দাওরায়ে হাদীস)"},
    ],
    "ALIA": [
        {"value": "EBTEDAYEE", "en": "Ebtedayee", "bn": "ইবতেদায়ী"},
        {"value": "DAKHIL", "en": "Dakhil", "bn": "দাখিল"},
        {"value": "ALIM", "en": "Alim", "bn": "আলিম"},
        {"value": "FAZIL", "en": "Fazil", "bn": "ফাযিল"},
        {"value": "KAMIL", "en": "Kamil", "bn": "কামিল"},
    ],
    "TECHNICAL": [
        {"value": "SSC_VOC", "en": "SSC (Vocational)", "bn": "এসএসসি (ভোকেশনাল)"},
        {"value": "HSC_VOC", "en": "HSC (Vocational/BM)", "bn": "এইচএসসি (ভোকেশনাল/বিএম)"},
        {"value": "DIPLOMA_ENG", "en": "Diploma in Engineering", "bn": "ডিপ্লোমা ইন ইঞ্জিনিয়ারিং"},
        {"value": "DIPLOMA_AGRI", "en": "Diploma in Agriculture", "bn": "ডিপ্লোমা ইন এগ্রিকালচার"},
        {"value": "DIPLOMA_TEXTILE", "en": "Diploma in Textile Engineering", "bn": "ডিপ্লোমা ইন টেক্সটাইল ইঞ্জিনিয়ারিং"},
        {"value": "TRADE_NTVQF", "en": "Trade Course / NTVQF Certificate", "bn": "ট্রেড কোর্স / এনটিভিকিউএফ সার্টিফিকেট"},
        {"value": "BSC_ENG", "en": "B.Sc in Engineering", "bn": "বিএসসি ইন ইঞ্জিনিয়ারিং"},
    ],
}

# Only General-education stages break down into individual classes.
EDUCATION_CLASSES = {
    "PRIMARY": [{"value": f"CLASS_{n}", "en": f"Class {n}", "bn": f"{n} শ্রেণি"} for n in range(1, 6)],
    "JUNIOR_SECONDARY": [{"value": f"CLASS_{n}", "en": f"Class {n}", "bn": f"{n} শ্রেণি"} for n in range(6, 9)],
    "SECONDARY": [{"value": f"CLASS_{n}", "en": f"Class {n}", "bn": f"{n} শ্রেণি"} for n in (9, 10)],
    "HIGHER_SECONDARY": [{"value": f"CLASS_{n}", "en": f"Class {n}", "bn": f"{n} শ্রেণি"} for n in (11, 12)],
}

EDUCATION_CURRENT_STATUS = [
    {"value": "CURRENT", "en": "Currently Studying", "bn": "অধ্যয়নরত"},
    {"value": "COMPLETED", "en": "Completed", "bn": "সম্পন্ন"},
]
