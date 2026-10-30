"""Classify media paths and authorize private document access."""

from __future__ import annotations

import os
from pathlib import PurePosixPath

from django.conf import settings
from django.db.models import Q

# Private member/application/governance uploads — never serve via open /media/ alias.
PRIVATE_MEDIA_PREFIXES = (
    "members/photos/",
    "members/identity/",
    "members/cv/",
    "members/requested_docs/",
    "members/documents/",
    "members/signatures/",
    "resolutions/signatures/",
    "meetings/",
)

# Intended for public website / CDN-style serving.
PUBLIC_MEDIA_PREFIXES = (
    "brand/",
    "cms/",
    "community/",
    "news/",
    "donations/",
    "reports/",
)


def normalize_media_path(path: str) -> str:
    """Return a safe relative POSIX path under MEDIA_ROOT, or empty if invalid."""
    if not path:
        return ""
    raw = str(path).replace("\\", "/").lstrip("/")
    # Reject absolute / traversal attempts.
    if raw.startswith(("..",)) or "/../" in f"/{raw}/" or raw.startswith("/"):
        return ""
    cleaned = PurePosixPath(raw)
    parts = cleaned.parts
    if ".." in parts or cleaned.is_absolute():
        return ""
    return cleaned.as_posix()


def is_private_media_path(path: str) -> bool:
    name = normalize_media_path(path)
    if not name:
        return False
    return any(name.startswith(prefix) for prefix in PRIVATE_MEDIA_PREFIXES)


def is_public_media_path(path: str) -> bool:
    name = normalize_media_path(path)
    if not name:
        return False
    if is_private_media_path(name):
        return False
    return any(name.startswith(prefix) for prefix in PUBLIC_MEDIA_PREFIXES)


def absolute_media_path(relative: str) -> str | None:
    """Resolve to an absolute filesystem path inside MEDIA_ROOT, or None."""
    name = normalize_media_path(relative)
    if not name:
        return None
    root = os.path.abspath(str(settings.MEDIA_ROOT))
    full = os.path.abspath(os.path.join(root, name))
    if not full.startswith(root + os.sep) and full != root:
        return None
    if not os.path.isfile(full):
        return None
    return full


def _staff_can_view_member_docs(user) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    from rbac.permissions import has_action

    return has_action(user, "members", "view") or has_action(
        user, "applications", "view"
    )


def _staff_can_view_governance_media(user) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    from rbac.permissions import has_action

    return (
        has_action(user, "meetings", "view")
        or has_action(user, "resolutions", "view")
        or has_action(user, "resolution_documents", "download")
    )


def _owns_member_signature(user, path: str) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    member = getattr(user, "member_profile", None)
    if member is None:
        return False
    sig = getattr(member, "signature_image", None)
    return bool(sig and getattr(sig, "name", None) == path)


def _owns_resolution_signature_snapshot(user, path: str) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    member = getattr(user, "member_profile", None)
    if member is None:
        return False
    from governance.models import ResolutionSignature

    return ResolutionSignature.objects.filter(
        member=member, signature_image=path
    ).exists()


def _session_application(request):
    from members.models import MemberApplication
    from members.views import STATUS_SESSION_KEY

    app_id = request.session.get(STATUS_SESSION_KEY)
    if not app_id:
        return None
    return MemberApplication.objects.filter(pk=app_id).first()


def _path_belongs_to_application(application, path: str) -> bool:
    if application is None:
        return False
    for field in ("photo", "identity_document", "cv"):
        f = getattr(application, field, None)
        if f and getattr(f, "name", None) == path:
            return True
    return application.document_requests.filter(uploaded_file=path).exists()


def user_can_access_private_media(request, relative_path: str) -> bool:
    """Object-level authorization for a private media relative path."""
    path = normalize_media_path(relative_path)
    if not path or not is_private_media_path(path):
        return False

    user = getattr(request, "user", None)

    # Staff / RBAC — membership docs
    if _staff_can_view_member_docs(user):
        return True

    # Staff / RBAC — governance signatures and meeting files
    if path.startswith(
        ("members/signatures/", "resolutions/signatures/", "meetings/")
    ) and _staff_can_view_governance_media(user):
        return True

    # Applicant status session — only that application's files
    application = _session_application(request)
    if _path_belongs_to_application(application, path):
        return True

    if not user or not user.is_authenticated:
        return False

    # Own digital signature (profile)
    if path.startswith("members/signatures/") and _owns_member_signature(user, path):
        return True

    # Own resolution signature snapshot (immutable historical copy)
    if path.startswith("resolutions/signatures/") and _owns_resolution_signature_snapshot(
        user, path
    ):
        return True

    # Meeting private files: staff-only (no participant self-serve via raw media)
    if path.startswith("meetings/"):
        return False

    # Verified email preferred for member self-access
    from accounts.verification import is_email_verified

    if not is_email_verified(user) and not getattr(user, "is_staff", False):
        # Allow if they still own the application by email (edge) — only with session
        # already handled above. Deny unverified cross-access.
        return False

    # Own MemberDocument
    from members.models import MemberDocument

    if hasattr(user, "member_profile"):
        member = user.member_profile
        if MemberDocument.objects.filter(member=member, file=path).exists():
            return True

    # Application filed with this user's email
    from members.models import MemberApplication

    if user.email and MemberApplication.objects.filter(
        Q(email__iexact=user.email)
        & (
            Q(photo=path)
            | Q(identity_document=path)
            | Q(cv=path)
        )
    ).exists():
        return True
    if user.email and MemberApplication.objects.filter(
        email__iexact=user.email, document_requests__uploaded_file=path
    ).exists():
        return True

    return False
