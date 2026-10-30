"""Block unverified users from protected areas (dashboard / voting)."""

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin
from django.utils.translation import gettext_lazy as _

from accounts.verification import is_email_verified

# Prefixes that require a verified email (staff/superuser bypass).
PROTECTED_PREFIXES = (
    "/dashboard/",
)


class EmailVerificationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return None
        if is_email_verified(user):
            return None

        path = request.path
        # Allow auth/verify/logout and public pages.
        allowed_prefixes = (
            "/login/",
            "/logout/",
            "/register/",
            "/verify",
            "/forgot-password/",
            "/reset-password/",
            "/i18n/",
            "/admin/",
            "/static/",
            # Public media only (private paths 404 in the media view).
            "/media/",
            # Private media authorizes itself (session applicant / RBAC / owner).
            "/protected-media/",
        )
        if any(path.startswith(p) for p in allowed_prefixes):
            return None
        if not any(path.startswith(p) for p in PROTECTED_PREFIXES):
            return None

        messages.warning(
            request,
            _("Please verify your email address before accessing your account."),
        )
        return redirect(reverse("verify-pending"))
