"""Role-based dashboard sidebar configuration.

Backward-compatible entry point kept for existing imports. The menu is now
permission-driven (see :mod:`dashboard.navigation`): each entry is shown only
when the user holds the relevant action permission, and links to modules not
yet shipped are skipped automatically. Superusers and users whose legacy
``accounts.User.role`` maps to a seeded system role keep full access.
"""

from dashboard.navigation import build_sidebar


def get_sidebar_sections(user, current_path=""):
    """Return ``[(section_label, [item_dict, ...]), ...]`` for the user.

    ``item_dict`` = ``{icon, label, url, active}``.
    """
    return build_sidebar(user, current_path)
