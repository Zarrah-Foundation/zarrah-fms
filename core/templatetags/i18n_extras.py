"""Small template-tag helpers for bilingual (Bangla/English) content.

Content data modules in this project (e.g. ``core/education_data.py``,
``pages/about_data.py``) represent bilingual text as plain dicts/objects with
parallel ``..._en`` / ``..._bn`` (or ``en`` / ``bn``) keys — the same
convention ``cms.models.HomepageSection`` uses for its ``title_en`` /
``title_bn`` fields. The ``bl`` filter below picks the right one for the
current active language so templates don't need to repeat
``{% if LANGUAGE_CODE == 'bn' %}...{% else %}...{% endif %}`` everywhere.

Because it works on both dicts and plain objects, the exact same filter
keeps working unmodified if this content is later moved into real Django
models — that's the point: templates stay CMS-ready without any rewrite.
"""

from django import template
from django.utils.html import format_html
from django.utils.translation import get_language

register = template.Library()


@register.filter(name="bl")
def bilingual(value, field=None):
    """Return the current-language variant of a bilingual value.

    Usage:
        {{ item|bl }}          -> value["bn"] or value["en"]
        {{ item|bl:"title" }}  -> value["title_bn"] or value["title_en"]
    """
    if value is None:
        return ""

    suffix = "bn" if (get_language() or "").startswith("bn") else "en"
    key = f"{field}_{suffix}" if field else suffix

    # Prefer active language, then the other language (never force an empty string
    # when a usable translation exists in either field).
    primary_key = f"{field}_{suffix}" if field else suffix
    secondary_suffix = "en" if suffix == "bn" else "bn"
    secondary_key = f"{field}_{secondary_suffix}" if field else secondary_suffix

    if isinstance(value, dict):
        result = value.get(primary_key)
        if result:
            return result
        other = value.get(secondary_key)
        return other if other else ""

    result = getattr(value, primary_key, None)
    if result:
        return result
    other = getattr(value, secondary_key, None)
    return other if other else ""


def _lang_span(value, lang):
    """Wrap ``value`` in a <span lang="..."> so it always renders in the
    correct type family (see :lang() rules in static/src/input.css),
    regardless of the surrounding page's active language.

    Use this for proper nouns, codes, emails and URLs that are always one
    language/script — e.g. a chairman's English name or a registration
    number shown on an otherwise-Bangla page. Do NOT use it for ordinary
    translated strings; those already inherit the correct lang from
    <html lang="{{ LANGUAGE_CODE }}">.
    """
    if value in (None, ""):
        return ""
    return format_html('<span lang="{}">{}</span>', lang, value)


@register.filter(name="lang_en", is_safe=True)
def lang_en(value):
    """Usage: {{ "MD. BABUL HOSSAIN"|lang_en }} -> <span lang="en">MD. BABUL HOSSAIN</span>"""
    return _lang_span(value, "en")


@register.filter(name="lang_bn", is_safe=True)
def lang_bn(value):
    """Usage: {{ some_bangla_only_value|lang_bn }} -> <span lang="bn">...</span>"""
    return _lang_span(value, "bn")


# Chrome labels that must switch with EN/BN even when msgfmt is unavailable.
_ZF_LABELS = {
    "Objectives": ("Objectives", "উদ্দেশ্যসমূহ"),
    "Privacy": ("Privacy", "গোপনীয়তা"),
    "Terms": ("Terms", "শর্তাবলি"),
    "Home": ("Home", "হোম"),
    "About": ("About", "আমাদের সম্পর্কে"),
    "Constitution": ("Constitution", "গঠনতন্ত্র"),
    "Contact": ("Contact", "যোগাযোগ"),
    "Contact Us": ("Contact Us", "যোগাযোগ করুন"),
    "Language": ("Language", "ভাষা"),
    "Category": ("Category", "শ্রেণি"),
    "Date": ("Date", "তারিখ"),
    "Download": ("Download", "ডাউনলোড"),
    "Breadcrumb": ("Breadcrumb", "ব্রেডক্রাম্ব"),
    "Learn About Us": ("Learn About Us", "আমাদের সম্পর্কে জানুন"),
    "Areas of Work": ("Areas of Work", "কর্মক্ষেত্রসমূহ"),
    "Organizational Nature": ("Organizational Nature", "সাংগঠনিক পরিচিতি"),
    "Organizational Structure": ("Organizational Structure", "সাংগঠনিক কাঠামো"),
    "Financial Principles": ("Financial Principles", "আর্থিক নীতিমালা"),
    "View Transparency": ("View Transparency", "স্বচ্ছতা দেখুন"),
    "View Transparency documents": ("View Transparency documents", "স্বচ্ছতার নথি দেখুন"),
    "Governance & Accountability": ("Governance & Accountability", "সুশাসন ও জবাবদিহিতা"),
    "Transparency & Accountability": ("Transparency & Accountability", "স্বচ্ছতা ও জবাবদিহিতা"),
    "Transparency": ("Transparency", "স্বচ্ছতা"),
    "Reports": ("Reports", "প্রতিবেদন"),
    "Publications": ("Publications", "প্রকাশনা"),
    "Reports & Publications": ("Reports & Publications", "প্রতিবেদন ও প্রকাশনা"),
    "View Reports & publications": ("View Reports & publications", "প্রতিবেদন ও প্রকাশনা দেখুন"),
    "View Reports": ("View Reports", "প্রতিবেদন দেখুন"),
    "View Governance Documents": ("View Governance Documents", "শাসন ও নীতিমালার নথি দেখুন"),
    "Meeting Quorum": ("Meeting Quorum", "সভায় কোরাম"),
    "Quorum": ("Quorum", "কোরাম"),
    "Membership": ("Membership", "সদস্যপদ"),
    "Membership information": ("Membership information", "সদস্যপদের তথ্য"),
    "Become a Member": ("Become a Member", "সদস্য হোন"),
    "Read the documented objectives": ("Read the documented objectives", "নথিভুক্ত উদ্দেশ্য পড়ুন"),
    "Visit Zarrah Skills": ("Visit Zarrah Skills", "জার্‌রাহ স্কিলস দেখুন"),
    "Founding members": ("Founding members", "প্রতিষ্ঠাতা সদস্যবৃন্দ"),
    "Read the Constitution / Memorandum": (
        "Read the Constitution / Memorandum",
        "গঠনতন্ত্র / সংঘস্মারক পড়ুন",
    ),
    "Last updated": ("Last updated", "সর্বশেষ হালনাগাদ"),
    "Contents": ("Contents", "সূচি"),
    "Download document": ("Download document", "দলিল ডাউনলোড"),
    "Download unavailable": ("Download unavailable", "ডাউনলোড উপলব্ধ নয়"),
    "Financial Transparency": ("Financial Transparency", "আর্থিক স্বচ্ছতা"),
    "Yearly Summary": ("Yearly Summary", "বার্ষিক সারসংক্ষেপ"),
    "Recent Monthly Summary": ("Recent Monthly Summary", "সাম্প্রতিক মাসিক সারসংক্ষেপ"),
    "Year": ("Year", "বছর"),
    "Income": ("Income", "আয়"),
    "Expense": ("Expense", "ব্যয়"),
    "Balance": ("Balance", "স্থিতি"),
    "Period": ("Period", "সময়কাল"),
    "Governance": ("Governance", "সুশাসন"),
    "Policies": ("Policies", "নীতিমালা"),
    "Other Public Documents": ("Other Public Documents", "অন্যান্য পাবলিক নথি"),
    "Previous": ("Previous", "পূর্ববর্তী"),
    "Next": ("Next", "পরবর্তী"),
    "No public documents are currently available.": (
        "No public documents are currently available.",
        "বর্তমানে কোনো পাবলিক নথি উপলব্ধ নেই।",
    ),
    "No public yearly summaries yet.": (
        "No public yearly summaries yet.",
        "এখনো কোনো পাবলিক বার্ষিক সারসংক্ষেপ নেই।",
    ),
    "No public monthly summaries yet.": (
        "No public monthly summaries yet.",
        "এখনো কোনো পাবলিক মাসিক সারসংক্ষেপ নেই।",
    ),
    "Accountability": ("Accountability", "জবাবদিহিতা"),
    "Yearly summary": ("Yearly summary", "বার্ষিক সারসংক্ষেপ"),
    "Monthly summary": ("Monthly summary", "মাসিক সারসংক্ষেপ"),
    "Financial summaries": ("Financial summaries", "আর্থিক সারসংক্ষেপ"),
    "Legal documents": ("Legal documents", "আইনগত নথি"),
    "Public policies": ("Public policies", "পাবলিক নীতিমালা"),
    "Financial summaries are published periodically as available.": (
        "Financial summaries are published periodically as available.",
        "আর্থিক সারসংক্ষেপ সময় সময় প্রকাশিত হয়, যেখানে উপলব্ধ।",
    ),
    "(opens in a new tab)": ("(opens in a new tab)", "(নতুন ট্যাবে খুলবে)"),
    "Back to top": ("Back to top", "উপরে যান"),
    "Registration No.": ("Registration No.", "নিবন্ধন নম্বর"),
    "Registration Date": ("Registration Date", "নিবন্ধনের তারিখ"),
    # Membership public chrome
    "Membership Requirements": ("Membership Requirements", "সদস্যপদের যোগ্যতা"),
    "Check Application Status": ("Check Application Status", "আবেদনের অবস্থা দেখুন"),
    "Pay Membership Fee": ("Pay Membership Fee", "সদস্যপদ ফি পরিশোধ করুন"),
    "Contact Admin": ("Contact Admin", "প্রশাসনের সাথে যোগাযোগ করুন"),
    "Apply for Membership": ("Apply for Membership", "সদস্যপদের জন্য আবেদন করুন"),
    "Apply for membership": ("Apply for membership", "সদস্যপদের জন্য আবেদন করুন"),
    "1. Apply": ("1. Apply", "১. আবেদন"),
    "2. Review": ("2. Review", "২. যাচাই"),
    "3. Approval": ("3. Approval", "৩. অনুমোদন"),
    "Submit the membership application form": (
        "Submit the membership application form",
        "সদস্যপদ আবেদন ফরম জমা দিন",
    ),
    "The Executive Council reviews applications": (
        "The Executive Council reviews applications",
        "কার্যনির্বাহী পরিষদ আবেদনগুলো যাচাই করে",
    ),
    "Approved members receive a Member ID and dashboard access": (
        "Approved members receive a Member ID and dashboard access",
        "অনুমোদিত সদস্যরা সদস্য পরিচিতি নম্বর ও ড্যাশবোর্ড সুবিধা পান",
    ),
    "Zarrah Foundation is a voluntary, non-profit, non-political humanitarian society. Membership is by application and review — it is not automatic.": (
        "Zarrah Foundation is a voluntary, non-profit, non-political humanitarian society. Membership is by application and review — it is not automatic.",
        "জার্‌রাহ ফাউন্ডেশন একটি স্বেচ্ছাসেবী, অলাভজনক ও অরাজনৈতিক মানবিক সোসাইটি। সদস্যপদ আবেদন ও যাচাইয়ের মাধ্যমে হয় — স্বয়ংক্রিয় নয়।",
    ),
    "Membership of Zarrah Foundation — eligibility, application and fees as set by the organisation.": (
        "Membership of Zarrah Foundation — eligibility, application and fees as set by the organisation.",
        "জার্‌রাহ ফাউন্ডেশনের সদস্যপদ — প্রতিষ্ঠানের নির্ধারিত যোগ্যতা, আবেদন ও ফি।",
    ),
    "Join Zarrah Foundation": ("Join Zarrah Foundation", "জার্‌রাহ ফাউন্ডেশনে যোগ দিন"),
    "Membership Application": ("Membership Application", "সদস্যপদ আবেদন"),
    "Fill out every section carefully. Fields marked with an asterisk (*) are required. Your application will be reviewed by our team before approval.": (
        "Fill out every section carefully. Fields marked with an asterisk (*) are required. Your application will be reviewed by our team before approval.",
        "প্রতিটি অংশ মনোযোগ দিয়ে পূরণ করুন। তারকাচিহ্ন (*) দেওয়া ঘরগুলো আবশ্যক। অনুমোদনের আগে আমাদের দল আবেদন যাচাই করবে।",
    ),
    "Application sections": ("Application sections", "আবেদনের অংশসমূহ"),
    "Personal Information": ("Personal Information", "ব্যক্তিগত তথ্য"),
    "Identity": ("Identity", "পরিচয়"),
    "Address": ("Address", "ঠিকানা"),
    "Present Address": ("Present Address", "বর্তমান ঠিকানা"),
    "Permanent Address": ("Permanent Address", "স্থায়ী ঠিকানা"),
    "Expatriates": ("Expatriates", "প্রবাসী"),
    "Education": ("Education", "শিক্ষা"),
    "Occupation": ("Occupation", "পেশা"),
    "Additional Information": ("Additional Information", "অতিরিক্ত তথ্য"),
    "Submit Application": ("Submit Application", "আবেদন জমা দিন"),
    "By submitting, you confirm the information provided is accurate. Your application will remain pending until reviewed by an administrator.": (
        "By submitting, you confirm the information provided is accurate. Your application will remain pending until reviewed by an administrator.",
        "জমা দিয়ে আপনি নিশ্চিত করছেন যে দেওয়া তথ্য সঠিক। প্রশাসকের যাচাই সম্পন্ন না হওয়া পর্যন্ত আবেদন অপেক্ষমাণ থাকবে।",
    ),
    "Please review and correct the following before submitting:": (
        "Please review and correct the following before submitting:",
        "জমা দেওয়ার আগে নিচের বিষয়গুলো দেখে সংশোধন করুন:",
    ),
    "Name (in Bangla)": ("Name (in Bangla)", "নাম (বাংলায়)"),
    "Name (in English)": ("Name (in English)", "নাম (ইংরেজিতে)"),
    "Father's Name": ("Father's Name", "পিতার নাম"),
    "Mother's Name": ("Mother's Name", "মাতার নাম"),
    "Gender": ("Gender", "লিঙ্গ"),
    "Blood Group": ("Blood Group", "রক্তের গ্রুপ"),
    "Marital Status": ("Marital Status", "বৈবাহিক অবস্থা"),
    "Religion": ("Religion", "ধর্ম"),
    "Photo": ("Photo", "ছবি"),
    "Email Address": ("Email Address", "ইমেইল ঠিকানা"),
    "Mobile Number": ("Mobile Number", "মোবাইল নম্বর"),
    "Emergency Contact Name": ("Emergency Contact Name", "জরুরি যোগাযোগের নাম"),
    "Emergency Contact Number": ("Emergency Contact Number", "জরুরি যোগাযোগের নম্বর"),
    "Relation": ("Relation", "সম্পর্ক"),
    "Identity Type": ("Identity Type", "পরিচয়পত্রের ধরন"),
    "ID Number": ("ID Number", "পরিচয়পত্র নম্বর"),
    "Identity Document": ("Identity Document", "পরিচয়পত্রের দলিল"),
    "Present Address (Details)": ("Present Address (Details)", "বর্তমান ঠিকানা (বিস্তারিত)"),
    "Permanent address same as present address": (
        "Permanent address same as present address",
        "স্থায়ী ঠিকানা বর্তমান ঠিকানার মতো",
    ),
    "Permanent Address (Details)": ("Permanent Address (Details)", "স্থায়ী ঠিকানা (বিস্তারিত)"),
    "I am an expatriate": ("I am an expatriate", "আমি প্রবাসী"),
    "State / Province": ("State / Province", "রাজ্য / প্রদেশ"),
    "City": ("City", "শহর"),
    "Postal Code": ("Postal Code", "পোস্টাল কোড"),
    "Full Foreign Address": ("Full Foreign Address", "পূর্ণ বিদেশি ঠিকানা"),
    "Passport Number": ("Passport Number", "পাসপোর্ট নম্বর"),
    "Education Type": ("Education Type", "শিক্ষার ধরন"),
    "Current Status": ("Current Status", "বর্তমান অবস্থা"),
    "Institution Name": ("Institution Name", "প্রতিষ্ঠানের নাম"),
    "Passing Year": ("Passing Year", "পাসের বছর"),
    "Result": ("Result", "ফলাফল"),
    "I am a student": ("I am a student", "আমি শিক্ষার্থী"),
    "Designation": ("Designation", "পদবি"),
    "Organization Name": ("Organization Name", "প্রতিষ্ঠানের নাম"),
    "Workplace Address": ("Workplace Address", "কর্মস্থলের ঠিকানা"),
    "Facebook Profile Link": ("Facebook Profile Link", "ফেসবুক প্রোফাইল লিংক"),
    "Volunteer Experience": ("Volunteer Experience", "স্বেচ্ছাসেবা অভিজ্ঞতা"),
    "CV / Resume": ("CV / Resume", "সিভি / জীবনবৃত্তান্ত"),
    "Date of Birth": ("Date of Birth", "জন্ম তারিখ"),
    "Country": ("Country", "দেশ"),
    "Division": ("Division", "বিভাগ"),
    "District": ("District", "জেলা"),
    "Upazila": ("Upazila", "উপজেলা"),
    "Union / Ward": ("Union / Ward", "ইউনিয়ন / ওয়ার্ড"),
    "Stage / Marhala / Level": ("Stage / Marhala / Level", "স্তর / মারহালা / লেভেল"),
    "Class": ("Class", "শ্রেণি"),
    "Type your Union Parishad or Ward name.": (
        "Type your Union Parishad or Ward name.",
        "আপনার ইউনিয়ন পরিষদ বা ওয়ার্ডের নাম লিখুন।",
    ),
    "Supported: JPG, PNG, WEBP · Max 3MB": (
        "Supported: JPG, PNG, WEBP · Max 3MB",
        "সমর্থিত: JPG, PNG, WEBP · সর্বোচ্চ ৩ এমবি",
    ),
    "Supported: JPG, PNG, WEBP, PDF · Max 3MB": (
        "Supported: JPG, PNG, WEBP, PDF · Max 3MB",
        "সমর্থিত: JPG, PNG, WEBP, PDF · সর্বোচ্চ ৩ এমবি",
    ),
    "Format: dd/mm/yyyy": ("Format: dd/mm/yyyy", "বিন্যাস: দিন/মাস/বছর"),
    "Application Status": ("Application Status", "আবেদনের অবস্থা"),
    "Enter your application reference and the email address used on the application. If they match, we will email you a one-time link to view your status.": (
        "Enter your application reference and the email address used on the application. If they match, we will email you a one-time link to view your status.",
        "আবেদনের রেফারেন্স এবং আবেদনে ব্যবহৃত ইমেইল লিখুন। মিললে অবস্থা দেখার জন্য একটি একবার-ব্যবহারযোগ্য লিংক ইমেইলে পাঠানো হবে।",
    ),
    "Send status link": ("Send status link", "অবস্থার লিংক পাঠান"),
    "Application reference": ("Application reference", "আবেদনের রেফারেন্স"),
    "Email used on the application": ("Email used on the application", "আবেদনে ব্যবহৃত ইমেইল"),
    "Reference": ("Reference", "রেফারেন্স"),
    "Submitted": ("Submitted", "জমা হয়েছে"),
    "Status": ("Status", "অবস্থা"),
    "Message from admin": ("Message from admin", "প্রশাসকের বার্তা"),
    "Your application has been approved. Check your email for login details if an email was provided.": (
        "Your application has been approved. Check your email for login details if an email was provided.",
        "আপনার আবেদন অনুমোদিত হয়েছে। ইমেইল দিয়ে থাকলে লগইনের তথ্য ইনবক্সে দেখুন।",
    ),
    "Your application was rejected.": ("Your application was rejected.", "আপনার আবেদন প্রত্যাখ্যান করা হয়েছে।"),
    "Additional documents were requested. Please upload only the documents listed below.": (
        "Additional documents were requested. Please upload only the documents listed below.",
        "অতিরিক্ত দলিল চাওয়া হয়েছে। নিচে তালিকাভুক্ত দলিলগুলোই আপলোড করুন।",
    ),
    "Your application is under review.": ("Your application is under review.", "আপনার আবেদন যাচাইয়ের মধ্যে আছে।"),
    "Your application is pending review.": ("Your application is pending review.", "আপনার আবেদন যাচাইয়ের অপেক্ষায় আছে।"),
    "Requested documents": ("Requested documents", "চাওয়া দলিল"),
    "Upload": ("Upload", "আপলোড"),
    "Upload document": ("Upload document", "দলিল আপলোড করুন"),
    "Membership Fee Payment": ("Membership Fee Payment", "সদস্যপদ ফি পরিশোধ"),
    "You can pay the current month's membership fee without logging in.": (
        "You can pay the current month's membership fee without logging in.",
        "লগইন ছাড়াই চলতি মাসের সদস্যপদ ফি পরিশোধ করতে পারেন।",
    ),
    "Payments for previous or future months require you to log in to your account.": (
        "Payments for previous or future months require you to log in to your account.",
        "আগের বা পরের মাসের ফি পরিশোধ করতে অ্যাকাউন্টে লগইন করতে হবে।",
    ),
    "Already paid": ("Already paid", "ইতিমধ্যে পরিশোধিত"),
    "Login to your account": ("Login to your account", "আপনার অ্যাকাউন্টে লগইন করুন"),
    "Pay for another member": ("Pay for another member", "অন্য সদস্যের জন্য পরিশোধ করুন"),
    "Confirm payment": ("Confirm payment", "পরিশোধ নিশ্চিত করুন"),
    "Member Name": ("Member Name", "সদস্যের নাম"),
    "Membership ID": ("Membership ID", "সদস্য পরিচিতি নম্বর"),
    "Fee Period": ("Fee Period", "ফি সময়কাল"),
    "Membership Fee": ("Membership Fee", "সদস্যপদ ফি"),
    "Payment method": ("Payment method", "পেমেন্ট পদ্ধতি"),
    "Payment Method": ("Payment Method", "পেমেন্ট পদ্ধতি"),
    "Secure online payment via SSLCommerz (cards and wallets enabled on the merchant store).": (
        "Secure online payment via SSLCommerz (cards and wallets enabled on the merchant store).",
        "SSLCommerz-এর মাধ্যমে নিরাপদ অনলাইন পেমেন্ট (মার্চেন্ট স্টোরে চালু কার্ড ও ওয়ালেট)।",
    ),
    "Pay Now": ("Pay Now", "এখনই পরিশোধ করুন"),
    "Redirecting…": ("Redirecting…", "পুনর্নির্দেশ করা হচ্ছে…"),
    "You will be redirected to a secure payment page. Do not refresh while payment is processing.": (
        "You will be redirected to a secure payment page. Do not refresh while payment is processing.",
        "আপনাকে নিরাপদ পেমেন্ট পৃষ্ঠায় নিয়ে যাওয়া হবে। পেমেন্ট চলাকালে রিফ্রেশ করবেন না।",
    ),
    "Use a different Membership ID": ("Use a different Membership ID", "অন্য সদস্য পরিচিতি নম্বর ব্যবহার করুন"),
    "Verify Membership": ("Verify Membership", "সদস্যপদ যাচাই করুন"),
    "Enter the Membership ID exactly as issued by Zarrah Foundation.": (
        "Enter the Membership ID exactly as issued by Zarrah Foundation.",
        "জার্‌রাহ ফাউন্ডেশন যেভাবে সদস্য পরিচিতি নম্বর দিয়েছে, ঠিক সেভাবেই লিখুন।",
    ),
    "Already have an account?": ("Already have an account?", "ইতিমধ্যে অ্যাকাউন্ট আছে?"),
    "Log in to pay other months": ("Log in to pay other months", "অন্য মাসের ফি দিতে লগইন করুন"),
    "Member": ("Member", "সদস্য"),
    "Amount": ("Amount", "পরিমাণ"),
    "Transaction ID": ("Transaction ID", "লেনদেন নম্বর"),
    "Payment Status": ("Payment Status", "পেমেন্টের অবস্থা"),
    "Success": ("Success", "সফল"),
    "Thank you. The membership fee payment was completed successfully.": (
        "Thank you. The membership fee payment was completed successfully.",
        "ধন্যবাদ। সদস্যপদ ফি সফলভাবে পরিশোধ হয়েছে।",
    ),
    "This field is required.": ("This field is required.", "এই ঘরটি আবশ্যক।"),
    "You must be at least 18 years old to apply.": (
        "You must be at least 18 years old to apply.",
        "আবেদন করতে আপনার বয়স কমপক্ষে ১৮ বছর হতে হবে।",
    ),
    # Donation public chrome
    "Donation": ("Donation", "অনুদান"),
    "Donate": ("Donate", "দান করুন"),
    "Donate Now": ("Donate Now", "এখনই অনুদান দিন"),
    "Make a Donation": ("Make a Donation", "অনুদান দিন"),
    "Support Our Work": ("Support Our Work", "আমাদের কাজকে সহায়তা করুন"),
    "Your contribution helps Zarrah Foundation serve communities with compassion, transparency and care.": (
        "Your contribution helps Zarrah Foundation serve communities with compassion, transparency and care.",
        "আপনার অনুদান জার্‌রাহ ফাউন্ডেশনকে সহানুভূতি, স্বচ্ছতা ও যত্ন নিয়ে সমাজসেবায় সহায়তা করে।",
    ),
    "One-time Donation": ("One-time Donation", "এককালীন অনুদান"),
    "One-time": ("One-time", "এককালীন"),
    "One-time gift": ("One-time gift", "এককালীন অনুদান"),
    "Recurring Donation": ("Recurring Donation", "নিয়মিত অনুদান"),
    "Monthly Donation": ("Monthly Donation", "মাসিক অনুদান"),
    "Monthly": ("Monthly", "মাসিক"),
    "Monthly recurring": ("Monthly recurring", "মাসিক নিয়মিত অনুদান"),
    "Donation Amount": ("Donation Amount", "অনুদানের পরিমাণ"),
    "Donation Amount (BDT)": ("Donation Amount (BDT)", "অনুদানের পরিমাণ (টাকা)"),
    "Custom Amount": ("Custom Amount", "নিজস্ব পরিমাণ"),
    "Donor information": ("Donor information", "দাতার তথ্য"),
    "Continue": ("Continue", "এগিয়ে যান"),
    "Secure Payment": ("Secure Payment", "নিরাপদ পেমেন্ট"),
    "Donation Form": ("Donation Form", "অনুদান ফরম"),
    "Choose a category, pick a suggested amount or enter your own, then proceed to secure payment.": (
        "Choose a category, pick a suggested amount or enter your own, then proceed to secure payment.",
        "একটি খাত বেছে নিন, প্রস্তাবিত পরিমাণ নির্বাচন করুন অথবা নিজস্ব পরিমাণ লিখে নিরাপদ পেমেন্টে এগিয়ে যান।",
    ),
    "Select a suggested amount or type any amount in BDT.": (
        "Select a suggested amount or type any amount in BDT.",
        "প্রস্তাবিত পরিমাণ বেছে নিন অথবা টাকায় যেকোনো পরিমাণ লিখুন।",
    ),
    "Select a category": ("Select a category", "একটি খাত নির্বাচন করুন"),
    "Donation Category": ("Donation Category", "অনুদানের খাত"),
    "Name": ("Name", "নাম"),
    "Phone or Email": ("Phone or Email", "ফোন অথবা ইমেইল"),
    "Enter a Bangladeshi mobile number or a valid email address.": (
        "Enter a Bangladeshi mobile number or a valid email address.",
        "বাংলাদেশি মোবাইল নম্বর অথবা বৈধ ইমেইল লিখুন।",
    ),
    "Donate on behalf of": ("Donate on behalf of", "যাঁর পক্ষে অনুদান"),
    "optional": ("optional", "ঐচ্ছিক"),
    "Anonymous Donation": ("Anonymous Donation", "নাম প্রকাশে অনিচ্ছুক অনুদান"),
    "Proceed to Payment": ("Proceed to Payment", "পেমেন্টে এগিয়ে যান"),
    "You will be redirected to a secure payment page. Payment gateway options will expand as additional providers are enabled.": (
        "You will be redirected to a secure payment page. Payment gateway options will expand as additional providers are enabled.",
        "আপনাকে নিরাপদ পেমেন্ট পৃষ্ঠায় নিয়ে যাওয়া হবে। অতিরিক্ত প্রদানকারী চালু হলে পেমেন্ট অপশন বাড়বে।",
    ),
    "No donation categories available at this time.": (
        "No donation categories available at this time.",
        "এই মুহূর্তে কোনো অনুদান খাত উপলব্ধ নেই।",
    ),
    "Payment Successful": ("Payment Successful", "পেমেন্ট সফল হয়েছে"),
    "Payment Failed": ("Payment Failed", "পেমেন্ট ব্যর্থ হয়েছে"),
    "Payment Cancelled": ("Payment Cancelled", "পেমেন্ট বাতিল করা হয়েছে"),
    "Donation Successful": ("Donation Successful", "অনুদান সফল হয়েছে"),
    "Thank You!": ("Thank You!", "ধন্যবাদ!"),
    "Your donation of": ("Your donation of", "আপনার অনুদান"),
    "has been received.": ("has been received.", "গ্রহণ করা হয়েছে।"),
    "Receipt Number:": ("Receipt Number:", "রসিদ নম্বর:"),
    "Receipt Number": ("Receipt Number", "রসিদ নম্বর"),
    "Transaction ID:": ("Transaction ID:", "লেনদেন নম্বর:"),
    "View Receipt": ("View Receipt", "রসিদ দেখুন"),
    "Download PDF": ("Download PDF", "পিডিএফ ডাউনলোড"),
    "Return Home": ("Return Home", "হোমে ফিরুন"),
    "Your payment could not be processed. Please try again.": (
        "Your payment could not be processed. Please try again.",
        "আপনার পেমেন্ট সম্পন্ন করা যায়নি। অনুগ্রহ করে আবার চেষ্টা করুন।",
    ),
    "Try Again": ("Try Again", "আবার চেষ্টা করুন"),
    "Try again": ("Try again", "আবার চেষ্টা করুন"),
    "You cancelled the payment. No charges were made.": (
        "You cancelled the payment. No charges were made.",
        "আপনি পেমেন্ট বাতিল করেছেন। কোনো চার্জ হয়নি।",
    ),
    "Return to Donation": ("Return to Donation", "অনুদান পৃষ্ঠায় ফিরুন"),
    "Donation Receipt": ("Donation Receipt", "অনুদানের রসিদ"),
    "Print": ("Print", "প্রিন্ট"),
    "Email Receipt": ("Email Receipt", "রসিদ ইমেইল করুন"),
    "Donor Name": ("Donor Name", "দাতার নাম"),
    "On Behalf Of": ("On Behalf Of", "যাঁর পক্ষে"),
    "Give Monthly": ("Give Monthly", "মাসিক অনুদান দিন"),
    "Recurring Support": ("Recurring Support", "নিয়মিত সহায়তা"),
    "Set up a monthly donation. You can cancel anytime via your secure management link or dashboard.": (
        "Set up a monthly donation. You can cancel anytime via your secure management link or dashboard.",
        "মাসিক অনুদান শুরু করুন। নিরাপদ ব্যবস্থাপনা লিংক বা ড্যাশবোর্ড থেকে যেকোনো সময় বাতিল করা যায়।",
    ),
    "Prefer a one-time gift?": ("Prefer a one-time gift?", "এককালীন অনুদান দিতে চান?"),
    "Monthly donations are not available yet.": (
        "Monthly donations are not available yet.",
        "মাসিক অনুদান এখনো উপলব্ধ নয়।",
    ),
    "Frequency": ("Frequency", "সময়কাল"),
    "Provider": ("Provider", "প্রদানকারী"),
    "bKash and Nagad recurring are not available in this release.": (
        "bKash and Nagad recurring are not available in this release.",
        "এই সংস্করণে bKash ও Nagad-এর নিয়মিত অনুদান উপলব্ধ নয়।",
    ),
    "Monthly amount (BDT)": ("Monthly amount (BDT)", "মাসিক পরিমাণ (টাকা)"),
    "Required so we can send receipts and manage your subscription.": (
        "Required so we can send receipts and manage your subscription.",
        "রসিদ পাঠাতে এবং নিয়মিত অনুদান পরিচালনা করতে এটি প্রয়োজন।",
    ),
    "Message (optional)": ("Message (optional)", "বার্তা (ঐচ্ছিক)"),
    "Continue to secure authorization": ("Continue to secure authorization", "নিরাপদ অনুমোদনে এগিয়ে যান"),
    "Recurring donations are not available right now.": (
        "Recurring donations are not available right now.",
        "এই মুহূর্তে নিয়মিত অনুদান উপলব্ধ নয়।",
    ),
    "New recurring donations are currently unavailable.": (
        "New recurring donations are currently unavailable.",
        "নতুন নিয়মিত অনুদান এই মুহূর্তে উপলব্ধ নয়।",
    ),
    "New recurring donations cannot be started.": (
        "New recurring donations cannot be started.",
        "নতুন নিয়মিত অনুদান শুরু করা যাবে না।",
    ),
    "New recurring donations disabled": (
        "New recurring donations disabled",
        "নতুন নিয়মিত অনুদান বন্ধ আছে",
    ),
    "Monthly donation active": ("Monthly donation active", "মাসিক অনুদান সক্রিয়"),
    "Thank you — your monthly gift is active": (
        "Thank you — your monthly gift is active",
        "ধন্যবাদ — আপনার মাসিক অনুদান সক্রিয় হয়েছে",
    ),
    "Save this private link to manage or cancel your subscription:": (
        "Save this private link to manage or cancel your subscription:",
        "অনুদান পরিচালনা বা বাতিল করতে এই ব্যক্তিগত লিংকটি সংরক্ষণ করুন:",
    ),
    "View in dashboard": ("View in dashboard", "ড্যাশবোর্ডে দেখুন"),
    "Back to donations": ("Back to donations", "অনুদানে ফিরুন"),
    "Authorization failed": ("Authorization failed", "অনুমোদন ব্যর্থ হয়েছে"),
    "Your monthly donation was not activated. No recurring schedule was started.": (
        "Your monthly donation was not activated. No recurring schedule was started.",
        "আপনার মাসিক অনুদান সক্রিয় হয়নি। কোনো নিয়মিত তফসিল শুরু হয়নি।",
    ),
    "Authorization cancelled": ("Authorization cancelled", "অনুমোদন বাতিল হয়েছে"),
    "You cancelled before completing authorization. No monthly donation was set up.": (
        "You cancelled before completing authorization. No monthly donation was set up.",
        "অনুমোদন শেষ করার আগে আপনি বাতিল করেছেন। কোনো মাসিক অনুদান সেট হয়নি।",
    ),
    "Start again": ("Start again", "আবার শুরু করুন"),
    "Please correct the errors below.": ("Please correct the errors below.", "নিচের ত্রুটিগুলো সংশোধন করুন।"),
    "Please enter your name.": ("Please enter your name.", "অনুগ্রহ করে আপনার নাম লিখুন।"),
    "Amount must be greater than zero.": ("Amount must be greater than zero.", "পরিমাণ শূন্যের বেশি হতে হবে।"),
    "Payment initialization failed.": ("Payment initialization failed.", "পেমেন্ট শুরু করা যায়নি।"),
    # Contact public chrome
    "Send Message": ("Send Message", "বার্তা পাঠান"),
    "Send a message": ("Send a message", "বার্তা পাঠান"),
    "Submit": ("Submit", "জমা দিন"),
    "Office Address": ("Office Address", "অফিসের ঠিকানা"),
    "Phone": ("Phone", "ফোন"),
    "Email": ("Email", "ইমেইল"),
    "Office Hours": ("Office Hours", "অফিস সময়"),
    "Google Maps": ("Google Maps", "Google Maps"),
    "Open in Google Maps": ("Open in Google Maps", "Google Maps-এ খুলুন"),
    "Map": ("Map", "মানচিত্র"),
    "Subject": ("Subject", "বিষয়"),
    "Message": ("Message", "বার্তা"),
    "WhatsApp": ("WhatsApp", "WhatsApp"),
    "Zarrah Foundation is a voluntary, non-profit, non-political humanitarian organisation. Reach us for membership, donations and general enquiries.": (
        "Zarrah Foundation is a voluntary, non-profit, non-political humanitarian organisation. Reach us for membership, donations and general enquiries.",
        "জার্‌রাহ ফাউন্ডেশন একটি স্বেচ্ছাসেবী, অলাভজনক ও অরাজনৈতিক মানবিক সংস্থা। সদস্যপদ, অনুদান ও সাধারণ জিজ্ঞাসার জন্য আমাদের সাথে যোগাযোগ করুন।",
    ),
    "Your message has been sent. We will get back to you soon.": (
        "Your message has been sent. We will get back to you soon.",
        "আপনার বার্তা পাঠানো হয়েছে। আমরা শিগগিরই উত্তর দেব।",
    ),
    "Map location will appear here once configured in Site Settings.": (
        "Map location will appear here once configured in Site Settings.",
        "সাইট সেটিংসে নির্ধারণ করা হলে এখানে মানচিত্র দেখা যাবে।",
    ),
    "We use the details you send only to respond to this enquiry.": (
        "We use the details you send only to respond to this enquiry.",
        "আপনার পাঠানো তথ্য শুধু এই জিজ্ঞাসার উত্তর দিতে ব্যবহার করা হয়।",
    ),
    # Payment settings (CMS)
    "Recurring Donations": ("Recurring Donations", "নিয়মিত অনুদান"),
    "Enabled": ("Enabled", "সক্রিয়"),
    "Disabled": ("Disabled", "নিষ্ক্রিয়"),
    "When disabled, the recurring/monthly donation option is hidden from the public donation page and new recurring subscriptions cannot be started.": (
        "When disabled, the recurring/monthly donation option is hidden from the public donation page and new recurring subscriptions cannot be started.",
        "এটি বন্ধ থাকলে পাবলিক অনুদান পৃষ্ঠায় নিয়মিত/মাসিক অনুদানের বিকল্প দেখানো হবে না এবং নতুন নিয়মিত অনুদান শুরু করা যাবে না।",
    ),
    "Existing active subscriptions are not cancelled automatically.": (
        "Existing active subscriptions are not cancelled automatically.",
        "বিদ্যমান সক্রিয় নিয়মিত অনুদান স্বয়ংক্রিয়ভাবে বাতিল হয় না।",
    ),
    "Payment Settings": ("Payment Settings", "পেমেন্ট সেটিংস"),
    "One-time donations enabled": ("One-time donations enabled", "এককালীন অনুদান সক্রিয়"),
    "Public current-month membership fee": (
        "Public current-month membership fee",
        "পাবলিক চলতি-মাসের সদস্যপদ ফি",
    ),
    "Membership Autopay enabled": ("Membership Autopay enabled", "সদস্যপদ অটোপে সক্রিয়"),
    "Minimum donation": ("Minimum donation", "সর্বনিম্ন অনুদান"),
    "Maximum donation": ("Maximum donation", "সর্বোচ্চ অনুদান"),
    "Allowed recurring frequencies: MONTHLY only.": (
        "Allowed recurring frequencies: MONTHLY only.",
        "নিয়মিত অনুদানের অনুমোদিত সময়কাল: শুধু মাসিক।",
    ),
    "Save": ("Save", "সংরক্ষণ"),
    "Your application has been submitted. Reference: %(ref)s. We will review it shortly. Use Check Application Status with this reference and your email to track progress.": (
        "Your application has been submitted. Reference: %(ref)s. We will review it shortly. Use Check Application Status with this reference and your email to track progress.",
        "আপনার আবেদন জমা হয়েছে। রেফারেন্স: %(ref)s। আমরা শিগগিরই যাচাই করব। অগ্রগতি দেখতে এই রেফারেন্স ও ইমেইল দিয়ে আবেদনের অবস্থা দেখুন ব্যবহার করুন।",
    ),
    "Pay another fee": ("Pay another fee", "অন্য ফি পরিশোধ করুন"),
    "If an application matches that reference and email, a one-time status link has been sent. Please check your inbox.": (
        "If an application matches that reference and email, a one-time status link has been sent. Please check your inbox.",
        "রেফারেন্স ও ইমেইল মিললে অবস্থা দেখার একটি একবার-ব্যবহারযোগ্য লিংক পাঠানো হয়েছে। ইনবক্স দেখুন।",
    ),
    "Donate": ("Donate", "দান করুন"),
    "Login": ("Login", "লগইন"),
    "Zarrah Skills": ("Zarrah Skills", "জার্‌রাহ স্কিলস"),
    "News": ("News", "সংবাদ"),
    "Menu": ("Menu", "মেনু"),
    "Legal": ("Legal", "আইনগত"),
    "FAQ": ("FAQ", "প্রশ্নোত্তর"),
    "My Account": ("My Account", "আমার অ্যাকাউন্ট"),
    "Open menu": ("Open menu", "মেনু খুলুন"),
    "Close menu": ("Close menu", "মেনু বন্ধ করুন"),
    "Main menu": ("Main menu", "প্রধান মেনু"),
    "Mobile navigation": ("Mobile navigation", "মোবাইল নেভিগেশন"),
    "Primary navigation": ("Primary navigation", "প্রধান নেভিগেশন"),
    "Newsletter": ("Newsletter", "নিউজলেটার"),
    "Get in touch": ("Get in touch", "যোগাযোগ করুন"),
    "All rights reserved.": ("All rights reserved.", "সর্বস্বত্ব সংরক্ষিত।"),
}

_REPORT_TYPE_LABELS = {
    "FINANCIAL": ("Financial Transparency", "আর্থিক স্বচ্ছতা"),
    "ANNUAL": ("Annual Reports", "বার্ষিক প্রতিবেদন"),
    "AUDIT": ("Audit Reports", "নিরীক্ষা প্রতিবেদন"),
    "LEGAL": ("Legal Documents", "আইনগত নথি"),
    "GOVERNANCE": ("Governance Documents", "সুশাসন সংক্রান্ত নথি"),
    "REGISTRATION": ("Registration Documents", "নিবন্ধন নথি"),
    "POLICY": ("Policies", "নীতিমালা"),
    "BOARD": ("Board / Committee Documents", "পরিষদ সংক্রান্ত নথি"),
    "ACTIVITY": ("Activity Reports", "কার্যক্রম প্রতিবেদন"),
    "CONSTITUTION": ("Constitution", "গঠনতন্ত্র"),
    "OTHER": ("Other Public Documents", "অন্যান্য পাবলিক নথি"),
}


def _bn_active():
    return (get_language() or "").startswith("bn")


def zf_text(key):
    """Python helper matching ``zf_label`` (works without compiled .mo files)."""
    pair = _ZF_LABELS.get(key)
    if not pair:
        return key
    return pair[1] if _bn_active() else pair[0]


def apply_zf_form_labels(form, mapping=None):
    """Localize form field labels/help/required messages for the active language."""
    required = zf_text("This field is required.")
    for name, field in form.fields.items():
        key = None
        if mapping and name in mapping:
            key = mapping[name]
        else:
            label = field.label
            key = str(label) if label else ""
        if key and key in _ZF_LABELS:
            field.label = zf_text(key)
        help_key = str(field.help_text) if field.help_text else ""
        if help_key and help_key in _ZF_LABELS:
            field.help_text = zf_text(help_key)
        field.error_messages["required"] = required
        empty = field.widget.attrs.get("placeholder")
        if empty and empty in _ZF_LABELS:
            field.widget.attrs["placeholder"] = zf_text(empty)


@register.simple_tag
def zf_label(key):
    """Return an approved EN/BN chrome label for the active language."""
    return zf_text(key)


@register.simple_tag
def zf_report_type(code):
    """Localized public label for a ReportType value (no model change)."""
    pair = _REPORT_TYPE_LABELS.get(str(code or ""))
    if not pair:
        return code or ""
    return pair[1] if _bn_active() else pair[0]

