"""Declarative, permission-aware dashboard navigation.

The sidebar is built from :data:`NAV`. Each item is gated by an action
permission (``module`` + ``action``, default ``view``) and points at a URL
*name*. URL names that don't resolve yet (a module not shipped in the current
phase) are skipped silently, so the same NAV works across the phased rollout.
"""

from django.urls import NoReverseMatch, reverse

from rbac.permissions import has_action

NAV = [
    {
        "label": "Overview",
        "items": [
            {"icon": "bi-speedometer2", "label": "Dashboard", "url": "dashboard", "module": "dashboard", "action": "view"},
            {"icon": "bi-heart", "label": "My Donations", "url": "dashboard-my-donations", "module": "dashboard", "action": "view"},
            {"icon": "bi-arrow-repeat", "label": "My Recurring Donations", "url": "dashboard-my-recurring", "module": "dashboard", "action": "view"},
            {"icon": "bi-cash-coin", "label": "My Fees", "url": "dashboard-my-fees", "module": "dashboard", "action": "view"},
        ],
    },
    {
        "label": "Membership",
        "items": [
            {"icon": "bi-people", "label": "Members", "url": "dashboard-members", "module": "members", "action": "view"},
            {"icon": "bi-file-earmark-person", "label": "Applications", "url": "dashboard-applications", "module": "applications", "action": "view"},
            {"icon": "bi-card-checklist", "label": "Membership Types", "url": "dashboard-membership-types", "module": "membership_types", "action": "view"},
            {"icon": "bi-diagram-3", "label": "Member Groups", "url": "dashboard-member-groups", "module": "members", "action": "view"},
            {"icon": "bi-cash-stack", "label": "Membership Fees", "url": "dashboard-membership-fees", "module": "membership_fees", "action": "view"},
            {"icon": "bi-file-earmark-pdf", "label": "Members PDF Report", "url": "dashboard-members-bulk-report", "module": "members", "action": "bulk_report"},
            {"icon": "bi-files", "label": "Applications PDF Report", "url": "dashboard-applications-bulk-report", "module": "applications", "action": "bulk_report"},
        ],
    },
    {
        "label": "Payment Management",
        "items": [
            {"icon": "bi-speedometer2", "label": "Overview", "url": "dashboard-payments", "module": "payments", "action": "view"},
            {"icon": "bi-credit-card", "label": "Payment Methods", "url": "dashboard-payment-methods", "module": "payment_methods", "action": "view"},
            {"icon": "bi-sliders2", "label": "Recurring Payment Setup", "url": "dashboard-payments-recurring-setup", "module": "payments", "action": "configuration"},
            {"icon": "bi-arrow-repeat", "label": "Recurring Payments", "url": "dashboard-payments-recurring", "module": "payments", "action": "recurring_view"},
            {"icon": "bi-heart", "label": "Donations", "url": "dashboard-donations", "module": "donations", "action": "view"},
            {"icon": "bi-cash-stack", "label": "Membership Fees", "url": "dashboard-membership-fees", "module": "membership_fees", "action": "view"},
            {"icon": "bi-person-plus", "label": "Registration Fees", "url": "dashboard-payments-registration-fees", "module": "payments", "action": "view"},
            {"icon": "bi-receipt", "label": "Transactions", "url": "dashboard-payments-transactions", "module": "payments", "action": "transactions_view"},
            {"icon": "bi-arrow-counterclockwise", "label": "Refunds", "url": "dashboard-payments-refunds", "module": "payments", "action": "refunds_view"},
            {"icon": "bi-broadcast", "label": "Webhooks / IPN", "url": "dashboard-payments-webhooks", "module": "payments", "action": "webhooks"},
            {"icon": "bi-journal-text", "label": "Payment Logs", "url": "dashboard-payments-logs", "module": "payments", "action": "logs_view"},
            {"icon": "bi-sliders", "label": "Payment Settings", "url": "dashboard-payments-settings", "module": "payments", "action": "configuration"},
            {"icon": "bi-grid-3x3-gap", "label": "Capabilities", "url": "dashboard-payments-capabilities", "module": "payments", "action": "view"},
        ],
    },
    {
        "label": "Donations",
        "items": [
            {"icon": "bi-heart", "label": "Donations", "url": "dashboard-donations", "module": "donations", "action": "view"},
            {"icon": "bi-arrow-repeat", "label": "Recurring Donations", "url": "dashboard-recurring", "module": "donations", "action": "recurring_view"},
            {"icon": "bi-tags", "label": "Categories", "url": "dashboard-donation-categories", "module": "donation_categories", "action": "view"},
            {"icon": "bi-coin", "label": "Quick Amounts", "url": "dashboard-quick-amounts", "module": "quick_amounts", "action": "view"},
            {"icon": "bi-credit-card", "label": "Payment Methods", "url": "dashboard-payment-methods", "module": "payment_methods", "action": "view"},
            {"icon": "bi-graph-up", "label": "Donation Reports", "url": "dashboard-donation-reports", "module": "donations", "action": "export"},
        ],
    },
    {
        "label": "Finance",
        "items": [
            {"icon": "bi-wallet2", "label": "Overview", "url": "dashboard-finance", "module": "finance", "action": "view"},
            {"icon": "bi-arrow-down-circle", "label": "Income", "url": "dashboard-finance-income", "module": "finance", "action": "view"},
            {"icon": "bi-arrow-up-circle", "label": "Expense", "url": "dashboard-finance-expense", "module": "finance", "action": "view"},
        ],
    },
    {
        "label": "Content",
        "items": [
            {"icon": "bi-newspaper", "label": "News", "url": "dashboard-news", "module": "news", "action": "view"},
            {"icon": "bi-collection", "label": "News Categories", "url": "dashboard-news-categories", "module": "news_categories", "action": "view"},
            {"icon": "bi-file-earmark-bar-graph", "label": "Reports", "url": "dashboard-reports", "module": "reports", "action": "view"},
            {"icon": "bi-shield-check", "label": "Transparency", "url": "dashboard-transparency", "module": "transparency", "action": "view"},
        ],
    },
    {
        "label": "Governance",
        "items": [
            {"icon": "bi-calendar-event", "label": "Meetings", "url": "dashboard-meetings", "module": "meetings", "action": "view"},
            {"icon": "bi-tags", "label": "Meeting Types", "url": "dashboard-meeting-types", "module": "meetings", "action": "manage"},
            {"icon": "bi-calendar-check", "label": "My Meetings", "url": "my-meetings", "module": "dashboard", "action": "view"},
            {"icon": "bi-file-earmark-text", "label": "My Resolutions", "url": "my-resolutions", "module": "dashboard", "action": "view"},
            {"icon": "bi-pen", "label": "My Signature", "url": "my-signature", "module": "dashboard", "action": "view"},
        ],
    },
    {
        "label": "Community",
        "items": [
            {"icon": "bi-hand-thumbs-up", "label": "Volunteers", "url": "dashboard-volunteers", "module": "volunteers", "action": "view"},
            {"icon": "bi-chat-quote", "label": "Testimonials", "url": "dashboard-testimonials", "module": "testimonials", "action": "view"},
            {"icon": "bi-envelope", "label": "Contact Messages", "url": "dashboard-contact-messages", "module": "contact_messages", "action": "view"},
            {"icon": "bi-question-circle", "label": "FAQs", "url": "dashboard-faqs", "module": "faqs", "action": "view"},
            {"icon": "bi-building", "label": "Partners", "url": "dashboard-partners", "module": "partners", "action": "view"},
            {"icon": "bi-person-badge", "label": "Leadership", "url": "dashboard-leadership", "module": "leadership", "action": "view"},
            {"icon": "bi-ui-checks-grid", "label": "Elections", "url": "dashboard-elections", "module": "elections", "action": "view"},
            {"icon": "bi-ballot", "label": "My Elections", "url": "my-elections", "module": "dashboard", "action": "view"},
        ],
    },
    {
        "label": "Website",
        "items": [
            {"icon": "bi-window", "label": "Homepage", "url": "dashboard-cms-homepage", "module": "cms", "action": "view"},
            {"icon": "bi-bar-chart", "label": "Impact Statistics", "url": "dashboard-impact-stats", "module": "cms", "action": "view"},
            {"icon": "bi-gear", "label": "Site Settings", "url": "dashboard-site-settings", "module": "site_settings", "action": "view"},
            {"icon": "bi-envelope-gear", "label": "SMTP Settings", "url": "dashboard-smtp-settings", "module": "site_settings", "action": "view"},
            {"icon": "bi-phone", "label": "SMS Settings", "url": "dashboard-sms-settings", "module": "site_settings", "action": "view"},
        ],
    },
    {
        "label": "Administration",
        "items": [
            {"icon": "bi-person-badge", "label": "Users", "url": "dashboard-users", "module": "users", "action": "view"},
            {"icon": "bi-shield-lock", "label": "Roles & Permissions", "url": "dashboard-roles", "module": "roles", "action": "view"},
        ],
    },
]


def build_sidebar(user, current_path=""):
    """Return ``[(section_label, [item_dict, ...]), ...]`` for the given user.

    Each item dict: ``{icon, label, url, active}``. Sections with no visible
    items are omitted.
    """
    sections = []
    for section in NAV:
        items = []
        for item in section["items"]:
            if not has_action(user, item["module"], item.get("action", "view")):
                continue
            try:
                url = reverse(item["url"])
            except NoReverseMatch:
                continue
            active = current_path == url or (
                url != "/dashboard/" and current_path.startswith(url)
            )
            items.append(
                {
                    "icon": item["icon"],
                    "label": item["label"],
                    "url": url,
                    "active": active,
                }
            )
        if items:
            sections.append((section["label"], items))
    return sections
