"""
Django settings for zarrah_foundation project.
"""

from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    SSLCOMMERZ_IS_SANDBOX=(bool, True),
    SESSION_COOKIE_SECURE=(bool, False),
    CSRF_COOKIE_SECURE=(bool, False),
    SECURE_SSL_REDIRECT=(bool, False),
    SECURE_HSTS_INCLUDE_SUBDOMAINS=(bool, True),
    SECURE_HSTS_PRELOAD=(bool, False),
    ALLOW_MOCK_AUTOPAY_WHEN_DEBUG_FALSE=(bool, False),
    SMTP_USE_TLS=(bool, True),
    SMTP_USE_SSL=(bool, False),
)

environ.Env.read_env(BASE_DIR / ".env")

DEBUG = env("DEBUG")

# ---------------------------------------------------------------------------
# SECRET_KEY — never use an insecure fallback when DEBUG=False
# ---------------------------------------------------------------------------
_INSECURE_SECRET_FRAGMENTS = (
    "django-insecure",
    "change-me",
    "changeme",
    "insecure-dev",
    "not-for-production",
    "local-dev-only",
)


def _is_unsafe_secret(value: str) -> bool:
    if not value or not str(value).strip():
        return True
    lowered = str(value).strip().lower()
    if len(str(value).strip()) < 40 and not DEBUG:
        return True
    return any(frag in lowered for frag in _INSECURE_SECRET_FRAGMENTS)


_raw_secret = env("SECRET_KEY", default="")
if _is_unsafe_secret(_raw_secret):
    if DEBUG:
        # Local development only — never used when DEBUG=False.
        SECRET_KEY = "django-insecure-local-dev-only-not-for-production-use"
    else:
        raise ImproperlyConfigured(
            "SECRET_KEY must be set to a strong unique value when DEBUG=False. "
            "Generate one (e.g. python -c \"from django.core.management.utils "
            "import get_random_secret_key; print(get_random_secret_key())\") "
            "and set it in the environment / .env file."
        )
else:
    SECRET_KEY = _raw_secret

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
SITE_URL = env("SITE_URL", default="http://localhost:8000")
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core.apps.CoreConfig",
    "accounts.apps.AccountsConfig",
    "rbac.apps.RbacConfig",
    "members.apps.MembersConfig",
    "donations.apps.DonationsConfig",
    "reports.apps.ReportsConfig",
    "news.apps.NewsConfig",
    "finance.apps.FinanceConfig",
    "audit.apps.AuditConfig",
    "voting.apps.VotingConfig",
    "governance.apps.GovernanceConfig",
    "cms.apps.CmsConfig",
    "pages.apps.PagesConfig",
    "community.apps.CommunityConfig",
    "dashboard.apps.DashboardConfig",
    "rest_framework",
    "foundation_api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "accounts.middleware.EmailVerificationMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "zarrah_foundation.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "core.context_processors.site_settings",
                "dashboard.context_processors.dashboard_shell",
            ],
        },
    },
]

WSGI_APPLICATION = "zarrah_foundation.wsgi.application"

if env.bool("USE_SQLITE", default=False):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DB_NAME", default="zarrah_foundation"),
            "USER": env("DB_USER", default="postgres"),
            "PASSWORD": env("DB_PASSWORD", default="postgres"),
            "HOST": env("DB_HOST", default="localhost"),
            "PORT": env("DB_PORT", default="5432"),
        }
    }

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "bn"
LANGUAGES = [
    ("bn", "Bangla"),
    ("en", "English"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "Asia/Dhaka"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
# Private files are served via authenticated Django view, not open aliases.
PROTECTED_MEDIA_URL = "/protected-media/"

STORAGES = {
    "default": {
        "BACKEND": "core.storage.SecureMediaStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

MAX_UPLOAD_SIZE = 10 * 1024 * 1024

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/"
SESSION_COOKIE_AGE = 7 * 24 * 60 * 60

# ---------------------------------------------------------------------------
# HTTPS / cookie security (env-overridable; defaults tighten when not DEBUG)
# ---------------------------------------------------------------------------
if DEBUG:
    SESSION_COOKIE_SECURE = env("SESSION_COOKIE_SECURE")
    CSRF_COOKIE_SECURE = env("CSRF_COOKIE_SECURE")
    SECURE_SSL_REDIRECT = env("SECURE_SSL_REDIRECT")
    SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=0)
else:
    SESSION_COOKIE_SECURE = env("SESSION_COOKIE_SECURE", default=True)
    CSRF_COOKIE_SECURE = env("CSRF_COOKIE_SECURE", default=True)
    SECURE_SSL_REDIRECT = env("SECURE_SSL_REDIRECT", default=True)
    SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)

SECURE_HSTS_INCLUDE_SUBDOMAINS = env("SECURE_HSTS_INCLUDE_SUBDOMAINS")
SECURE_HSTS_PRELOAD = env("SECURE_HSTS_PRELOAD")
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = env("SECURE_REFERRER_POLICY", default="same-origin")
X_FRAME_OPTIONS = env("X_FRAME_OPTIONS", default="DENY")

# Behind cPanel/CloudLinux TLS terminators, trust X-Forwarded-Proto when set.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("SMTP_HOST", default="localhost")
EMAIL_PORT = env.int("SMTP_PORT", default=587)
EMAIL_HOST_USER = env("SMTP_USER", default="")
EMAIL_HOST_PASSWORD = env("SMTP_PASS", default="")
# Port 465 = implicit SSL; 587 = STARTTLS. Never enable both.
_email_use_ssl_default = EMAIL_PORT == 465
EMAIL_USE_SSL = env.bool("SMTP_USE_SSL", default=_email_use_ssl_default)
EMAIL_USE_TLS = env.bool(
    "SMTP_USE_TLS",
    default=(not EMAIL_USE_SSL and EMAIL_PORT in (25, 587, 2525)),
)
if EMAIL_USE_SSL and EMAIL_USE_TLS:
    # Implicit SSL wins — STARTTLS on :465 hangs indefinitely without a timeout.
    EMAIL_USE_TLS = False
# Bound SMTP connect/read so membership/approval emails cannot block request workers.
EMAIL_TIMEOUT = env.int("SMTP_TIMEOUT", default=20)
DEFAULT_FROM_EMAIL = env("SMTP_FROM", default="noreply@zarrah.org")
ADMIN_EMAIL = env("ADMIN_EMAIL", default="admin@zarrah.org")

SSLCOMMERZ_STORE_ID = env("SSLCOMMERZ_STORE_ID", default="")
SSLCOMMERZ_STORE_PASSWORD = env("SSLCOMMERZ_STORE_PASSWORD", default="")
SSLCOMMERZ_IS_SANDBOX = env("SSLCOMMERZ_IS_SANDBOX")
# Recurring EasyCheckout (optional). Without both, recurring checkout stays unavailable.
SSLCOMMERZ_SALT_KEY = env("SSLCOMMERZ_SALT_KEY", default="")
SSLCOMMERZ_RECURRING_PLAN_REFER = env("SSLCOMMERZ_RECURRING_PLAN_REFER", default="")
RECURRING_DONATION_FAILURE_THRESHOLD = env.int(
    "RECURRING_DONATION_FAILURE_THRESHOLD", default=3
)
RECURRING_DONATION_MANAGEMENT_TOKEN_TTL = env.int(
    "RECURRING_DONATION_MANAGEMENT_TOKEN_TTL", default=60 * 60 * 24 * 30
)

SSLCOMMERZ_GATEWAY_URL = (
    "https://sandbox.sslcommerz.com/gwprocess/v4/api.php"
    if SSLCOMMERZ_IS_SANDBOX
    else "https://securepay.sslcommerz.com/gwprocess/v4/api.php"
)
SSLCOMMERZ_VALIDATION_URL = (
    "https://sandbox.sslcommerz.com/validator/api/validationserverAPI.php"
    if SSLCOMMERZ_IS_SANDBOX
    else "https://securepay.sslcommerz.com/validator/api/validationserverAPI.php"
)

# Explicit override only — never enable quietly in production.
ALLOW_MOCK_AUTOPAY_WHEN_DEBUG_FALSE = env("ALLOW_MOCK_AUTOPAY_WHEN_DEBUG_FALSE")

PASSWORD_RESET_TIMEOUT = 86400
EMAIL_VERIFY_TIMEOUT = 86400

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
}
