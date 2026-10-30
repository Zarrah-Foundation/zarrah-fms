"""Upload validators.

Deliberately dependency-free: validation relies only on the file size, its
extension, and the ``content_type`` the browser/WSGI server attaches to an
``UploadedFile`` — plus, for images, Pillow's own decoder — so the project
runs unmodified on Windows, Linux, cPanel shared hosting and any VPS
without needing libmagic or any other native system library installed.
"""

import os

from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _
from PIL import Image, UnidentifiedImageError

ALLOWED_IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "webp"]
ALLOWED_DOCUMENT_EXTENSIONS = ["pdf"]
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS + ALLOWED_DOCUMENT_EXTENSIONS

ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_DOCUMENT_CONTENT_TYPES = {"application/pdf"}
ALLOWED_CONTENT_TYPES = ALLOWED_IMAGE_CONTENT_TYPES | ALLOWED_DOCUMENT_CONTENT_TYPES

# Favicons are conventionally .ico or a square PNG — a separate, narrower
# list from ALLOWED_IMAGE_EXTENSIONS above (which is tuned for photo/document
# uploads elsewhere in the project and doesn't include .ico).
ALLOWED_FAVICON_EXTENSIONS = ["ico", "png"]
ALLOWED_FAVICON_CONTENT_TYPES = {"image/x-icon", "image/vnd.microsoft.icon", "image/png"}


@deconstructible
class MaxFileSizeValidator:
    """Reject uploads larger than ``max_size_mb`` megabytes."""

    def __init__(self, max_size_mb=3):
        self.max_size_mb = max_size_mb
        self.max_size = max_size_mb * 1024 * 1024

    def __call__(self, value):
        size = getattr(value, "size", None)
        if size is not None and size > self.max_size:
            raise ValidationError(
                _("File size must not exceed %(max)sMB."),
                params={"max": self.max_size_mb},
                code="file_too_large",
            )

    def __eq__(self, other):
        return isinstance(other, MaxFileSizeValidator) and self.max_size_mb == other.max_size_mb


@deconstructible
class FileTypeValidator:
    """Validate an uploaded file's extension and declared ``content_type``.

    Two independent, lightweight checks — no file-content sniffing and no
    native libraries required:

    1. The filename extension must be in ``allowed_extensions``.
    2. If the browser/WSGI server supplied a ``content_type``, it must be in
       ``allowed_content_types``. (Some servers omit it, in which case this
       check is skipped rather than failing closed on missing metadata.)
    """

    def __init__(self, allowed_extensions=None, allowed_content_types=None):
        self.allowed_extensions = [
            ext.lower().lstrip(".") for ext in (allowed_extensions or ALLOWED_EXTENSIONS)
        ]
        self.allowed_content_types = set(allowed_content_types or ALLOWED_CONTENT_TYPES)

    def __call__(self, value):
        ext = os.path.splitext(value.name or "")[1].lower().lstrip(".")
        if ext not in self.allowed_extensions:
            raise ValidationError(
                _('Unsupported file extension "%(ext)s". Allowed types: %(allowed)s.'),
                params={"ext": ext, "allowed": ", ".join(self.allowed_extensions)},
                code="invalid_extension",
            )

        content_type = getattr(value, "content_type", None)
        if content_type and content_type not in self.allowed_content_types:
            raise ValidationError(
                _('Unsupported file type "%(type)s".'),
                params={"type": content_type},
                code="invalid_content_type",
            )

    def __eq__(self, other):
        return (
            isinstance(other, FileTypeValidator)
            and self.allowed_extensions == other.allowed_extensions
            and self.allowed_content_types == other.allowed_content_types
        )


@deconstructible
class ImageFileValidator(FileTypeValidator):
    """``FileTypeValidator`` restricted to images, plus a real Pillow decode.

    The extension/content-type checks alone only look at metadata supplied
    by the client, which can be spoofed. Actually opening and verifying the
    file with Pillow confirms the bytes decode as a genuine image.
    """

    def __init__(self, allowed_extensions=None, allowed_content_types=None):
        super().__init__(
            allowed_extensions or ALLOWED_IMAGE_EXTENSIONS,
            allowed_content_types or ALLOWED_IMAGE_CONTENT_TYPES,
        )

    def __call__(self, value):
        super().__call__(value)

        value.seek(0)
        try:
            Image.open(value).verify()
        except (UnidentifiedImageError, OSError, ValueError):
            raise ValidationError(
                _("Upload a valid image. The file you uploaded was either not an image or was corrupted."),
                code="invalid_image",
            )
        finally:
            value.seek(0)

    def __eq__(self, other):
        return isinstance(other, ImageFileValidator) and super().__eq__(other)


@deconstructible
class FaviconFileValidator(FileTypeValidator):
    """``FileTypeValidator`` restricted to favicon-appropriate formats
    (.ico / .png), plus a real Pillow decode for the .png case.

    Pillow can't reliably ``.verify()`` every real-world .ico (some contain
    multiple embedded sizes/formats), so the decode check only runs for
    .png uploads; .ico files still get the extension + content-type checks
    above.
    """

    def __init__(self, allowed_extensions=None, allowed_content_types=None):
        super().__init__(
            allowed_extensions or ALLOWED_FAVICON_EXTENSIONS,
            allowed_content_types or ALLOWED_FAVICON_CONTENT_TYPES,
        )

    def __call__(self, value):
        super().__call__(value)

        ext = os.path.splitext(value.name or "")[1].lower().lstrip(".")
        if ext != "png":
            return

        value.seek(0)
        try:
            Image.open(value).verify()
        except (UnidentifiedImageError, OSError, ValueError):
            raise ValidationError(
                _("Upload a valid image. The file you uploaded was either not an image or was corrupted."),
                code="invalid_image",
            )
        finally:
            value.seek(0)

    def __eq__(self, other):
        return isinstance(other, FaviconFileValidator) and super().__eq__(other)
