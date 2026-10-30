from django.urls import path

from voting import views

urlpatterns = [
    # Legacy product path — redirect only (tables preserved)
    path("", views.legacy_voting_redirect, name="voting-list"),
    path("<uuid:pk>/", views.legacy_voting_redirect, name="voting-cast"),
    path("<uuid:pk>/results/", views.legacy_voting_redirect, name="voting-results"),
    # Compat aliases under /dashboard/voting/elections/
    path("elections/", views.my_elections, name="election-member-list"),
    path("elections/<uuid:pk>/", views.my_election_cast, name="election-member-cast"),
    path(
        "elections/<uuid:pk>/results/",
        views.my_election_results,
        name="election-member-results",
    ),
]
