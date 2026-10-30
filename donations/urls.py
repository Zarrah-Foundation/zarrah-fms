from django.urls import path

from donations import recurring_views, views

urlpatterns = [
    path("donation/", views.DonationListView.as_view(), name="donation"),
    path("donation/create/", views.DonationCreateView.as_view(), name="donation-create"),
    path("donation/success/", views.DonationSuccessView.as_view(), name="donation-success"),
    path("donation/fail/", views.DonationFailView.as_view(), name="donation-fail"),
    path("donation/cancel/", views.DonationCancelView.as_view(), name="donation-cancel"),
    path("donation/ipn/", views.donation_ipn, name="donation-ipn"),
    path(
        "donation/recurring/",
        recurring_views.RecurringDonationCreateView.as_view(),
        name="donation-recurring",
    ),
    path(
        "donation/recurring/success/",
        recurring_views.RecurringSuccessView.as_view(),
        name="donation-recurring-success",
    ),
    path(
        "donation/recurring/fail/",
        recurring_views.RecurringFailView.as_view(),
        name="donation-recurring-fail",
    ),
    path(
        "donation/recurring/cancel/",
        recurring_views.RecurringCancelReturnView.as_view(),
        name="donation-recurring-cancel",
    ),
    path(
        "donation/recurring/ipn/",
        recurring_views.recurring_ipn,
        name="donation-recurring-ipn",
    ),
    path(
        "donation/recurring/manage/<str:token>/",
        recurring_views.GuestRecurringManageView.as_view(),
        name="donation-recurring-manage",
    ),
    path(
        "donation/receipt/<uuid:pk>/",
        views.DonationReceiptView.as_view(),
        name="donation-receipt",
    ),
    path(
        "donation/receipt/<uuid:pk>/pdf/",
        views.DonationReceiptPdfView.as_view(),
        name="donation-receipt-pdf",
    ),
    path(
        "donation/receipt/<uuid:pk>/email/",
        views.DonationReceiptEmailView.as_view(),
        name="donation-receipt-email",
    ),
]
