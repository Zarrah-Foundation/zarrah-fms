from django.urls import path
from django.views.generic import RedirectView

from pages import views

urlpatterns = [
    path("about/", views.AboutView.as_view(), name="about"),
    # Canonical fragments on About — keep legacy/marketing URLs working without duplicating pages.
    path(
        "mission-vision/",
        RedirectView.as_view(url="/about/#mission-vision", permanent=False),
        name="mission-vision",
    ),
    path("objectives/", views.ObjectivesView.as_view(), name="objectives"),
    path(
        "leadership/",
        RedirectView.as_view(url="/about/#leadership", permanent=False),
        name="leadership",
    ),
    path("constitution/", views.ConstitutionView.as_view(), name="constitution"),
    path("faq/", views.FAQView.as_view(), name="faq"),
    path("privacy/", views.PrivacyView.as_view(), name="privacy"),
    path("terms/", views.TermsView.as_view(), name="terms"),
    path("contact/", views.ContactView.as_view(), name="contact"),
    path("volunteer/", views.VolunteerView.as_view(), name="volunteer"),
]
