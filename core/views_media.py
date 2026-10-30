"""Serve public and private media with path classification and authz."""

from __future__ import annotations

import mimetypes
import os

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.views.decorators.http import require_GET

from core.media_access import (
    absolute_media_path,
    is_private_media_path,
    is_public_media_path,
    normalize_media_path,
    user_can_access_private_media,
)


def _file_response(full_path: str, *, as_attachment: bool = False) -> FileResponse:
    content_type, _ = mimetypes.guess_type(full_path)
    response = FileResponse(
        open(full_path, "rb"),
        as_attachment=as_attachment,
        filename=os.path.basename(full_path),
        content_type=content_type or "application/octet-stream",
    )
    response["X-Content-Type-Options"] = "nosniff"
    return response


@require_GET
def serve_public_media(request, path):
    """Serve only classified public media under MEDIA_URL.

    Private prefixes always 404 here so guessed ``/media/members/...`` URLs
    cannot bypass authorization.
    """
    name = normalize_media_path(path)
    if not name or is_private_media_path(name) or not is_public_media_path(name):
        raise Http404
    full = absolute_media_path(name)
    if not full:
        raise Http404
    return _file_response(full)


@require_GET
def serve_protected_media(request, path):
    """Serve private media after object-level authorization."""
    name = normalize_media_path(path)
    if not name or not is_private_media_path(name):
        raise Http404
    if not user_can_access_private_media(request, name):
        if not getattr(request.user, "is_authenticated", False):
            raise Http404
        return HttpResponseForbidden("You do not have permission to access this file.")
    full = absolute_media_path(name)
    if not full:
        raise Http404
    return _file_response(full, as_attachment=True)
