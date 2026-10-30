"""Single source of truth for the action-based permission catalog.

Every dashboard module declares the *actions* it supports here. Permissions
are seeded from this registry (see ``rbac.management.commands.seed_rbac``) as
``<module>.<action>`` codenames, e.g. ``members.approve``.

Adding a new capability is a two-step, additive change:
1. Add the module/action here.
2. Run ``python manage.py seed_rbac`` to materialize the new Permission rows.

Nothing is ever removed automatically, so existing role grants keep working.
"""

# Common action verbs reused across CRUD-style modules.
CRUD = ["view", "create", "edit", "delete"]

# Ordered so the generated permission matrix reads naturally in the UI.
MODULES = {
    "dashboard": {
        "label": "Dashboard",
        "actions": ["view"],
    },
    "members": {
        "label": "Members",
        "actions": CRUD
        + [
            "approve",
            "reject",
            "export",
            "print",
            "manage_positions",
            "profile_download",
            "bulk_report",
            "edit_sensitive",
        ],
    },
    "applications": {
        "label": "Membership Applications",
        "actions": [
            "view",
            "edit",
            "review",
            "approve",
            "reject",
            "delete",
            "export",
            "download",
            "bulk_report",
            "edit_sensitive",
        ],
    },
    "membership_types": {
        "label": "Membership Types",
        "actions": CRUD,
    },
    "membership_fees": {
        "label": "Membership Fees",
        "actions": CRUD + ["export", "print"],
    },
    "donations": {
        "label": "Donations",
        "actions": CRUD
        + [
            "export",
            "print",
            "recurring_view",
            "recurring_manage",
            "recurring_cancel",
        ],
    },
    "payments": {
        "label": "Payment Management",
        "actions": [
            "view",
            "manage",
            "configuration",
            "webhooks",
            "refunds_view",
            "refunds_request",
            "refunds_approve",
            "recurring_view",
            "recurring_manage",
            "transactions_view",
            "logs_view",
        ],
    },
    "donation_categories": {
        "label": "Donation Categories",
        "actions": CRUD,
    },
    "quick_amounts": {
        "label": "Quick Amounts",
        "actions": CRUD,
    },
    "payment_methods": {
        "label": "Payment Methods",
        "actions": CRUD,
    },
    "finance": {
        "label": "Finance",
        "actions": CRUD + ["export", "print"],
    },
    "news": {
        "label": "News",
        "actions": CRUD + ["publish"],
    },
    "news_categories": {
        "label": "News Categories",
        "actions": CRUD,
    },
    "reports": {
        "label": "Reports",
        "actions": CRUD + ["export", "print"],
    },
    "transparency": {
        "label": "Transparency",
        "actions": CRUD,
    },
    "volunteers": {
        "label": "Volunteers",
        "actions": CRUD + ["export"],
    },
    "testimonials": {
        "label": "Testimonials",
        "actions": CRUD,
    },
    "contact_messages": {
        "label": "Contact Messages",
        "actions": ["view", "delete", "export"],
    },
    "faqs": {
        "label": "FAQs",
        "actions": CRUD,
    },
    "partners": {
        "label": "Partners",
        "actions": CRUD,
    },
    "leadership": {
        "label": "Leadership",
        "actions": CRUD,
    },
    "cms": {
        "label": "Website CMS",
        "actions": ["view", "edit"],
    },
    "site_settings": {
        "label": "Site Settings",
        "actions": ["view", "edit"],
    },
    "voting": {
        "label": "Voting",
        "actions": CRUD,
    },
    "elections": {
        "label": "Elections",
        "actions": CRUD + ["manage"],
    },
    "meetings": {
        "label": "Meetings",
        "actions": CRUD
        + [
            "manage",
            "manage_participants",
            "manage_attendance",
            "manage_agenda",
            "finalize",
        ],
    },
    "resolutions": {
        "label": "Resolutions",
        "actions": CRUD
        + [
            "manage",
            "sign",
            "manage_signers",
            "finalize",
            "publish",
        ],
    },
    "resolution_documents": {
        "label": "Resolution Documents",
        "actions": ["download"],
    },
    "resolution_public_sharing": {
        "label": "Resolution Public Sharing",
        "actions": ["manage"],
    },
    "users": {
        "label": "Users",
        "actions": CRUD + ["reset_password", "deactivate"],
    },
    "roles": {
        "label": "Roles & Permissions",
        "actions": CRUD + ["assign"],
    },
    "notifications": {
        "label": "Notifications",
        "actions": ["view"],
    },
}

# Human-friendly labels for action verbs (fallback: title-cased verb).
ACTION_LABELS = {
    "view": "View",
    "create": "Create",
    "edit": "Edit",
    "delete": "Delete",
    "approve": "Approve",
    "reject": "Reject",
    "review": "Review",
    "export": "Export",
    "print": "Print",
    "publish": "Publish",
    "assign": "Assign",
    "reset_password": "Reset Password",
    "deactivate": "Deactivate",
    "manage": "Manage",
    "manage_participants": "Manage Participants",
    "manage_attendance": "Manage Attendance",
    "manage_agenda": "Manage Agenda",
    "manage_positions": "Manage Positions",
    "profile_download": "Download Profile PDF",
    "bulk_report": "Bulk PDF Report",
    "edit_sensitive": "Edit Sensitive Fields",
    "finalize": "Finalize",
    "sign": "Sign / Approve",
    "manage_signers": "Manage Signers",
    "download": "Download",
    "recurring_view": "View Recurring Donations",
    "recurring_manage": "Manage Recurring Donations",
    "recurring_cancel": "Cancel Recurring Donations",
    "configuration": "Configuration",
    "webhooks": "Webhooks / IPN",
    "refunds_view": "View Refunds",
    "refunds_request": "Request Refunds",
    "refunds_approve": "Approve Refunds",
    "transactions_view": "View Transactions",
    "logs_view": "View Payment Logs",
}


def codename(module, action):
    return f"{module}.{action}"


def action_label(action):
    return ACTION_LABELS.get(action, action.replace("_", " ").title())


def iter_permissions():
    """Yield ``(module, action, codename, label)`` for every declared permission."""
    for module, meta in MODULES.items():
        module_label = meta["label"]
        for action in meta["actions"]:
            yield (
                module,
                action,
                codename(module, action),
                f"{module_label}: {action_label(action)}",
            )


def all_codenames():
    return [code for _m, _a, code, _label in iter_permissions()]
