from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from core.views_media import serve_protected_media, serve_public_media

urlpatterns = [
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("", include("cms.urls")),
    path("", include("pages.urls")),
    path("", include("accounts.urls")),
    path("", include("members.urls")),
    path("", include("donations.urls")),
    path("", include("reports.urls")),
    path("", include("news.urls")),
    path("", include("finance.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("public/", include("governance.urls")),
    path("api/", include("foundation_api.urls")),
    # Private documents — always through Django authz (DEBUG and production).
    path(
        "protected-media/<path:path>",
        serve_protected_media,
        name="protected-media",
    ),
    # Public media classification (blocks private prefixes even if guessed).
    path("media/<path:path>", serve_public_media, name="public-media"),
]

# Local static only when DEBUG — production uses collectstatic + web server alias.
if settings.DEBUG:
    urlpatterns += static(
        settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0]
    )

admin.site.site_header = "Zarrah Foundation Admin"
admin.site.site_title = "Zarrah Foundation"
admin.site.index_title = "Administration"
