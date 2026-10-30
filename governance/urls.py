"""Public resolution sharing routes (no login required)."""

from django.urls import path

from governance import views_public

urlpatterns = [
    path(
        "resolutions/<str:token>/",
        views_public.public_resolution_view,
        name="public-resolution",
    ),
    path(
        "resolutions/<str:token>/password/",
        views_public.public_resolution_password,
        name="public-resolution-password",
    ),
    path(
        "resolutions/<str:token>/pdf/",
        views_public.public_resolution_pdf,
        name="public-resolution-pdf",
    ),
    path(
        "resolutions/<str:token>/docx/",
        views_public.public_resolution_docx,
        name="public-resolution-docx",
    ),
]
