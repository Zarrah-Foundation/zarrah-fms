from django.urls import path

from members import fee_payment_views, public_fee_views, views

urlpatterns = [
    path("membership/", views.MembershipInfoView.as_view(), name="membership"),
    path("membership/apply/", views.MemberApplicationView.as_view(), name="membership-apply"),
    path("membership/status/", views.application_status_request, name="membership-status"),
    path(
        "membership/status/view/",
        views.application_status_view,
        name="membership-status-view",
    ),
    path(
        "membership/status/upload/<uuid:request_id>/",
        views.application_status_upload,
        name="membership-status-upload",
    ),
    path(
        "membership/status/<str:token>/",
        views.application_status_token,
        name="membership-status-token",
    ),
    # PAY-WP2: anonymous current-month membership fee (SSLCommerz one-time).
    path(
        "membership-fee-payment/",
        public_fee_views.public_fee_payment_start,
        name="public-membership-fee-payment",
    ),
    path(
        "membership-fee-payment/verify/",
        public_fee_views.public_fee_payment_verify,
        name="public-membership-fee-verify",
    ),
    path(
        "membership-fee-payment/pay/",
        public_fee_views.public_fee_payment_pay,
        name="public-membership-fee-pay",
    ),
    path(
        "membership/fees/pay/success/",
        fee_payment_views.membership_fee_pay_success,
        name="membership-fee-pay-success",
    ),
    path(
        "membership/fees/pay/fail/",
        fee_payment_views.membership_fee_pay_fail,
        name="membership-fee-pay-fail",
    ),
    path(
        "membership/fees/pay/cancel/",
        fee_payment_views.membership_fee_pay_cancel,
        name="membership-fee-pay-cancel",
    ),
    path(
        "membership/fees/pay/ipn/",
        fee_payment_views.membership_fee_pay_ipn,
        name="membership-fee-pay-ipn",
    ),
]
