import os
import re
import uuid

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.encoding import filepath_to_uri

from core.media_access import is_private_media_path, normalize_media_path


class SecureMediaStorage(FileSystemStorage):
    """Sanitize filenames, enforce size cap, and rewrite private URLs.

    Private member/application documents resolve to ``PROTECTED_MEDIA_URL``
    so templates never emit open ``/media/members/...`` links. Public assets
    keep the normal ``MEDIA_URL``.
    """

    def get_valid_name(self, name):
        name = os.path.basename(name)
        name = re.sub(r"[^\w.\-]", "_", name)
        return f"{uuid.uuid4().hex}_{name}"

    def _save(self, name, content):
        max_size = getattr(settings, "MAX_UPLOAD_SIZE", 10 * 1024 * 1024)
        content.seek(0, os.SEEK_END)
        size = content.tell()
        content.seek(0)
        if size > max_size:
            raise ValueError(f"File exceeds maximum size of {max_size} bytes.")
        return super()._save(name, content)

    def url(self, name):
        normalized = normalize_media_path(name) or name
        if is_private_media_path(normalized):
            base = getattr(settings, "PROTECTED_MEDIA_URL", "/protected-media/")
            if not base.endswith("/"):
                base = f"{base}/"
            return f"{base}{filepath_to_uri(normalized)}"
        return super().url(name)
