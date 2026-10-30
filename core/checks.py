"""Deployment / production security system checks.

Heavy production rules register with ``deploy=True`` so they run under
``python manage.py check --deploy`` without breaking local tests that
temporarily override ``DEBUG=False``.
"""

from django.conf import settings
from django.core.checks import Error, Warning, register


@register(deploy=True)
def production_security_checks(app_configs, **kwargs):
    errors = []
    debug = getattr(settings, "DEBUG", False)

    secret = getattr(settings, "SECRET_KEY", "") or ""
    lowered = secret.lower()
    if any(
        frag in lowered
        for frag in (
            "django-insecure",
            "change-me",
            "local-dev-only",
            "not-for-production",
        )
    ):
        if debug:
            errors.append(
                Warning(
                    "SECRET_KEY looks like a development placeholder.",
                    hint="Set a unique SECRET_KEY before deploying with DEBUG=False.",
                    id="zarrah.W001",
                )
            )
        else:
            errors.append(
                Error(
                    "SECRET_KEY is insecure or uses a development placeholder.",
                    hint="Set a strong SECRET_KEY in the environment.",
                    id="zarrah.E001",
                )
            )

    if not debug:
        hosts = getattr(settings, "ALLOWED_HOSTS", []) or []
        if not hosts or hosts == ["*"]:
            errors.append(
                Error(
                    "ALLOWED_HOSTS is empty or overly broad for production.",
                    id="zarrah.E002",
                )
            )
        if not getattr(settings, "CSRF_TRUSTED_ORIGINS", None):
            errors.append(
                Warning(
                    "CSRF_TRUSTED_ORIGINS is empty while DEBUG=False.",
                    hint="Set HTTPS origins, e.g. https://example.org",
                    id="zarrah.W002",
                )
            )
        if not getattr(settings, "SESSION_COOKIE_SECURE", False):
            errors.append(
                Error(
                    "SESSION_COOKIE_SECURE must be True when DEBUG=False.",
                    id="zarrah.E003",
                )
            )
        if not getattr(settings, "CSRF_COOKIE_SECURE", False):
            errors.append(
                Error(
                    "CSRF_COOKIE_SECURE must be True when DEBUG=False.",
                    id="zarrah.E004",
                )
            )
        if getattr(settings, "SSLCOMMERZ_IS_SANDBOX", True):
            errors.append(
                Warning(
                    "SSLCOMMERZ_IS_SANDBOX is True while DEBUG=False.",
                    hint="Confirm production SSLCommerz credentials and disable sandbox.",
                    id="zarrah.W003",
                )
            )
        if getattr(settings, "ALLOW_MOCK_AUTOPAY_WHEN_DEBUG_FALSE", False):
            errors.append(
                Warning(
                    "ALLOW_MOCK_AUTOPAY_WHEN_DEBUG_FALSE is enabled.",
                    hint="Disable this in real production; MOCK charges mark fees paid without money.",
                    id="zarrah.W004",
                )
            )

    return errors
