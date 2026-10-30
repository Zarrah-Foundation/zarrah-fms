"""Context injected into every dashboard page's shell.

Guarded by the ``/dashboard/`` path prefix so it adds no cost to public pages.
Provides the permission-aware sidebar, the notification bell state, and a
lightweight breadcrumb root — so individual views don't each have to assemble
the shell chrome.
"""

from dashboard.navigation import build_sidebar


def dashboard_shell(request):
    path = request.path or ""
    if not path.startswith("/dashboard/") and path != "/dashboard":
        return {}

    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}

    from audit.notifications import recent_for_user, unread_count_for_user

    return {
        "sidebar_sections": build_sidebar(user, path),
        "dash_unread_count": unread_count_for_user(user),
        "dash_recent_notifications": recent_for_user(user, limit=8),
    }
