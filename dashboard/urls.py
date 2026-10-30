from django.urls import include, path

from dashboard import (
    views,
    views_cms,
    views_community,
    views_content,
    views_donations,
    views_elections,
    views_finance,
    views_gallery,
    views_governance,
    views_membership,
    views_my_donations,
    views_my_fees,
    views_my_recurring,
    views_notifications,
    views_payments,
    views_recurring,
    views_settings,
    views_users,
)

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    # ---- Payment Management Center ----
    path("payments/", views_payments.payments_overview, name="dashboard-payments"),
    path(
        "payments/settings/",
        views_payments.payments_settings,
        name="dashboard-payments-settings",
    ),
    path(
        "payments/capabilities/",
        views_payments.payments_capabilities,
        name="dashboard-payments-capabilities",
    ),
    path(
        "payments/transactions/",
        views_payments.payments_transactions,
        name="dashboard-payments-transactions",
    ),
    path(
        "payments/transactions/<uuid:pk>/",
        views_payments.payments_transaction_detail,
        name="dashboard-payments-transaction-detail",
    ),
    path(
        "payments/transactions/<uuid:txn_pk>/refund/",
        views_payments.payments_refund_request,
        name="dashboard-payments-refund-request",
    ),
    path(
        "payments/recurring/",
        views_payments.payments_recurring,
        name="dashboard-payments-recurring",
    ),
    path(
        "payments/recurring/setup/",
        views_payments.payments_recurring_setup,
        name="dashboard-payments-recurring-setup",
    ),
    path(
        "payments/registration-fees/",
        views_payments.payments_registration_fees,
        name="dashboard-payments-registration-fees",
    ),
    path(
        "payments/webhooks/",
        views_payments.payments_webhooks,
        name="dashboard-payments-webhooks",
    ),
    path(
        "payments/webhooks/<uuid:pk>/",
        views_payments.payments_webhook_detail,
        name="dashboard-payments-webhook-detail",
    ),
    path(
        "payments/refunds/",
        views_payments.payments_refunds,
        name="dashboard-payments-refunds",
    ),
    path(
        "payments/refunds/<uuid:pk>/",
        views_payments.payments_refund_detail,
        name="dashboard-payments-refund-detail",
    ),
    path(
        "payments/refunds/<uuid:pk>/approve/",
        views_payments.payments_refund_approve,
        name="dashboard-payments-refund-approve",
    ),
    path(
        "payments/refunds/<uuid:pk>/reject/",
        views_payments.payments_refund_reject,
        name="dashboard-payments-refund-reject",
    ),
    path(
        "payments/logs/",
        views_payments.payments_logs,
        name="dashboard-payments-logs",
    ),
    path(
        "my-donations/",
        views_my_donations.MyDonationsView.as_view(),
        name="dashboard-my-donations",
    ),
    path(
        "my-recurring/",
        views_my_recurring.MyRecurringDonationsView.as_view(),
        name="dashboard-my-recurring",
    ),
    path(
        "my-recurring/<uuid:pk>/",
        views_my_recurring.MyRecurringDonationDetailView.as_view(),
        name="dashboard-my-recurring-detail",
    ),
    path(
        "my-recurring/<uuid:pk>/cancel/",
        views_my_recurring.MyRecurringDonationCancelView.as_view(),
        name="dashboard-my-recurring-cancel",
    ),
    path("my-fees/", views_my_fees.my_fees, name="dashboard-my-fees"),
    path("my-fees/pay/", views_my_fees.my_fees_pay, name="dashboard-my-fees-pay"),
    path(
        "my-fees/pay/registration/",
        views_my_fees.my_fees_pay_registration,
        name="dashboard-my-fees-pay-registration",
    ),
    path(
        "my-fees/autopay/activate/",
        views_my_fees.my_fees_autopay_activate,
        name="dashboard-my-fees-autopay-activate",
    ),
    path(
        "my-fees/autopay/deactivate/",
        views_my_fees.my_fees_autopay_deactivate,
        name="dashboard-my-fees-autopay-deactivate",
    ),
    path("voting/", include("voting.urls")),

    # ---- Governance (admin) ----
    path("meetings/", views_governance.meetings_list, name="dashboard-meetings"),
    path(
        "meetings/create/",
        views_governance.meeting_create,
        name="dashboard-meeting-create",
    ),
    path(
        "meetings/types/",
        views_governance.meeting_types_list,
        name="dashboard-meeting-types",
    ),
    path(
        "meetings/types/create/",
        views_governance.meeting_type_create,
        name="dashboard-meeting-type-create",
    ),
    path(
        "meetings/types/<uuid:pk>/edit/",
        views_governance.meeting_type_edit,
        name="dashboard-meeting-type-edit",
    ),
    path(
        "meetings/<uuid:pk>/",
        views_governance.meeting_detail,
        name="dashboard-meeting-detail",
    ),
    path(
        "meetings/<uuid:pk>/edit/",
        views_governance.meeting_edit,
        name="dashboard-meeting-edit",
    ),
    path(
        "meetings/<uuid:pk>/transition/",
        views_governance.meeting_transition,
        name="dashboard-meeting-transition",
    ),
    path(
        "meetings/<uuid:pk>/freeze/",
        views_governance.meeting_participants_freeze,
        name="dashboard-meeting-participants-freeze",
    ),
    path(
        "meetings/<uuid:pk>/participants/add-member/",
        views_governance.meeting_participant_add_member,
        name="dashboard-meeting-participant-add-member",
    ),
    path(
        "meetings/<uuid:pk>/participants/add-group/",
        views_governance.meeting_participant_add_group,
        name="dashboard-meeting-participant-add-group",
    ),
    path(
        "meetings/<uuid:pk>/attendance/<uuid:participant_pk>/",
        views_governance.meeting_attendance_mark,
        name="dashboard-meeting-attendance-mark",
    ),
    path(
        "meetings/<uuid:pk>/guests/add/",
        views_governance.meeting_guest_add,
        name="dashboard-meeting-guest-add",
    ),
    path(
        "meetings/<uuid:pk>/guests/<uuid:guest_pk>/edit/",
        views_governance.meeting_guest_edit,
        name="dashboard-meeting-guest-edit",
    ),
    path(
        "meetings/<uuid:pk>/guests/<uuid:guest_pk>/delete/",
        views_governance.meeting_guest_delete,
        name="dashboard-meeting-guest-delete",
    ),
    path(
        "meetings/<uuid:pk>/agenda/add/",
        views_governance.meeting_agenda_add,
        name="dashboard-meeting-agenda-add",
    ),
    path(
        "meetings/<uuid:pk>/agenda/reorder/",
        views_governance.meeting_agenda_reorder,
        name="dashboard-meeting-agenda-reorder",
    ),
    path(
        "meetings/<uuid:pk>/proceedings/",
        views_governance.meeting_proceedings_save,
        name="dashboard-meeting-proceedings-save",
    ),
    path(
        "meetings/<uuid:meeting_pk>/resolutions/create/",
        views_governance.resolution_create,
        name="dashboard-resolution-create",
    ),
    path(
        "resolutions/<uuid:pk>/",
        views_governance.resolution_detail,
        name="dashboard-resolution-detail",
    ),
    path(
        "resolutions/<uuid:pk>/pdf/",
        views_governance.resolution_document_pdf,
        name="dashboard-resolution-pdf",
    ),
    path(
        "resolutions/<uuid:pk>/docx/",
        views_governance.resolution_document_docx,
        name="dashboard-resolution-docx",
    ),

    # ---- My Meetings / Resolutions (members) ----
    path("my-meetings/", views_governance.my_meetings, name="my-meetings"),
    path(
        "my-meetings/<uuid:pk>/",
        views_governance.my_meeting_detail,
        name="my-meeting-detail",
    ),
    path(
        "my-resolutions/",
        views_governance.my_resolutions,
        name="my-resolutions",
    ),
    path(
        "my-resolutions/<uuid:pk>/",
        views_governance.my_resolution_detail,
        name="my-resolution-detail",
    ),
    path(
        "my-resolutions/<uuid:pk>/sign/",
        views_governance.my_resolution_sign,
        name="my-resolution-sign",
    ),
    path(
        "my-resolutions/<uuid:pk>/pdf/",
        views_governance.my_resolution_document_pdf,
        name="my-resolution-pdf",
    ),
    path(
        "my-resolutions/<uuid:pk>/docx/",
        views_governance.my_resolution_document_docx,
        name="my-resolution-docx",
    ),
    path(
        "my-signature/",
        views_governance.my_signature,
        name="my-signature",
    ),

    # ---- My Elections (members) ----
    path("my-elections/", views_elections.my_elections_entry, name="my-elections"),
    path(
        "my-elections/<uuid:pk>/",
        views_elections.my_election_cast_entry,
        name="my-election-cast",
    ),
    path(
        "my-elections/<uuid:pk>/results/",
        views_elections.my_election_results_entry,
        name="my-election-results",
    ),

    # ---- Elections (admin) ----
    path("elections/", views_elections.elections_list, name="dashboard-elections"),
    path("elections/new/", views_elections.election_create, name="dashboard-election-create"),
    path("elections/<uuid:pk>/", views_elections.election_detail, name="dashboard-election-detail"),
    path("elections/<uuid:pk>/edit/", views_elections.election_edit, name="dashboard-election-edit"),
    path("elections/<uuid:pk>/action/", views_elections.election_action, name="dashboard-election-action"),
    path("elections/<uuid:pk>/delete/", views_elections.election_delete, name="dashboard-election-delete"),

    # ---- Membership: Members ----
    path("members/", views_membership.members_list, name="dashboard-members"),
    path("members/new/", views_membership.member_create, name="dashboard-member-create"),
    path("members/<uuid:pk>/", views_membership.member_detail, name="dashboard-member-detail"),
    path("members/<uuid:pk>/edit/", views_membership.member_edit, name="dashboard-member-edit"),
    path("members/<uuid:pk>/pdf/", views_membership.member_pdf, name="dashboard-member-pdf"),
    path("members/<uuid:pk>/delete/", views_membership.member_delete, name="dashboard-member-delete"),
    path("members/<uuid:pk>/notes/", views_membership.member_add_note, name="dashboard-member-note"),
    path("members/<uuid:pk>/documents/", views_membership.member_add_document, name="dashboard-member-document"),
    path(
        "members/<uuid:pk>/positions/assign/",
        views_membership.member_position_assign,
        name="dashboard-member-position-assign",
    ),
    path(
        "members/<uuid:pk>/positions/<uuid:assignment_pk>/edit/",
        views_membership.member_position_edit,
        name="dashboard-member-position-edit",
    ),
    path(
        "members/<uuid:pk>/positions/<uuid:assignment_pk>/end/",
        views_membership.member_position_end,
        name="dashboard-member-position-end",
    ),
    path(
        "members/<uuid:pk>/fees/record/",
        views_membership.fee_record_payment,
        name="dashboard-member-fee-record",
    ),
    path(
        "members/<uuid:pk>/fees/autopay/deactivate/",
        views_membership.fee_deactivate_autopay,
        name="dashboard-member-fee-autopay-deactivate",
    ),
    path(
        "reports/members/",
        views_membership.members_bulk_report,
        name="dashboard-members-bulk-report",
    ),
    path(
        "reports/applications/",
        views_membership.applications_bulk_report,
        name="dashboard-applications-bulk-report",
    ),

    # ---- Membership: Types ----
    path("membership-types/", views_membership.MembershipTypeList.as_view(), name="dashboard-membership-types"),
    path("membership-types/new/", views_membership.MembershipTypeCreate.as_view(), name="dashboard-membership-type-create"),
    path("membership-types/<uuid:pk>/edit/", views_membership.MembershipTypeUpdate.as_view(), name="dashboard-membership-type-edit"),
    path("membership-types/<uuid:pk>/delete/", views_membership.MembershipTypeDelete.as_view(), name="dashboard-membership-type-delete"),

    # ---- Membership: Groups ----
    path("member-groups/", views_membership.MemberGroupList.as_view(), name="dashboard-member-groups"),
    path("member-groups/new/", views_membership.MemberGroupCreate.as_view(), name="dashboard-member-group-create"),
    path("member-groups/<uuid:pk>/edit/", views_membership.MemberGroupUpdate.as_view(), name="dashboard-member-group-edit"),
    path("member-groups/<uuid:pk>/delete/", views_membership.MemberGroupDelete.as_view(), name="dashboard-member-group-delete"),

    # ---- Membership: Applications ----
    path("applications/", views_membership.applications_list, name="dashboard-applications"),
    path("applications/<uuid:pk>/", views_membership.application_detail, name="dashboard-application-detail"),
    path("applications/<uuid:pk>/edit/", views_membership.application_edit, name="dashboard-application-edit"),
    path("applications/<uuid:pk>/pdf/", views_membership.application_pdf, name="dashboard-application-pdf"),
    path("applications/<uuid:pk>/action/", views_membership.application_action, name="dashboard-application-action"),

    # ---- Membership: Fees ----
    path("membership-fees/", views_membership.fees_list, name="dashboard-membership-fees"),
    path(
        "membership-fees/settings/",
        views_membership.fees_settings,
        name="dashboard-membership-fees-settings",
    ),
    path(
        "membership-fees/<uuid:pk>/",
        views_membership.fees_detail,
        name="dashboard-membership-fee-detail",
    ),
    path(
        "membership-fees/<uuid:pk>/registration/",
        views_membership.fee_record_registration,
        name="dashboard-membership-fee-registration",
    ),

    # ---- Donations ----
    path("donations/", views_donations.donations_list, name="dashboard-donations"),
    path("donations/manual/", views_donations.donation_manual_create, name="dashboard-donation-manual"),
    path("donations/reports/", views_donations.donation_reports, name="dashboard-donation-reports"),
    path(
        "donations/recurring/",
        views_recurring.recurring_subscriptions_list,
        name="dashboard-recurring",
    ),
    path(
        "donations/recurring/<uuid:pk>/",
        views_recurring.recurring_subscription_detail,
        name="dashboard-recurring-detail",
    ),
    path(
        "donations/recurring/<uuid:pk>/cancel/",
        views_recurring.recurring_subscription_cancel,
        name="dashboard-recurring-cancel",
    ),
    path(
        "donations/recurring/<uuid:pk>/suspend/",
        views_recurring.recurring_subscription_suspend,
        name="dashboard-recurring-suspend",
    ),
    path("donations/<uuid:pk>/", views_donations.donation_detail, name="dashboard-donation-detail"),
    path("donation-categories/", views_donations.CategoryList.as_view(), name="dashboard-donation-categories"),
    path("donation-categories/new/", views_donations.CategoryCreate.as_view(), name="dashboard-donation-category-create"),
    path("donation-categories/<uuid:pk>/edit/", views_donations.CategoryUpdate.as_view(), name="dashboard-donation-category-edit"),
    path("donation-categories/<uuid:pk>/delete/", views_donations.CategoryDelete.as_view(), name="dashboard-donation-category-delete"),
    path("quick-amounts/", views_donations.QuickAmountList.as_view(), name="dashboard-quick-amounts"),
    path("quick-amounts/new/", views_donations.QuickAmountCreate.as_view(), name="dashboard-quick-amount-create"),
    path("quick-amounts/<uuid:pk>/edit/", views_donations.QuickAmountUpdate.as_view(), name="dashboard-quick-amount-edit"),
    path("quick-amounts/<uuid:pk>/delete/", views_donations.QuickAmountDelete.as_view(), name="dashboard-quick-amount-delete"),
    path("payment-methods/", views_donations.PaymentMethodList.as_view(), name="dashboard-payment-methods"),
    path("payment-methods/new/", views_donations.PaymentMethodCreate.as_view(), name="dashboard-payment-method-create"),
    path("payment-methods/<uuid:pk>/edit/", views_donations.PaymentMethodUpdate.as_view(), name="dashboard-payment-method-edit"),
    path(
        "payment-methods/<uuid:pk>/configure/",
        views_donations.payment_method_configure,
        name="dashboard-payment-method-configure",
    ),
    path(
        "payment-methods/<uuid:pk>/test/",
        views_donations.payment_method_test_connection,
        name="dashboard-payment-method-test",
    ),
    path("payment-methods/<uuid:pk>/delete/", views_donations.PaymentMethodDelete.as_view(), name="dashboard-payment-method-delete"),

    # ---- Finance ----
    path("finance/", views_finance.finance_overview, name="dashboard-finance"),
    path("finance/cash-book/", views_finance.cash_book, name="dashboard-finance-cashbook"),
    path("finance/ledger/", views_finance.ledger, name="dashboard-finance-ledger"),
    path("finance/income/", views_finance.IncomeList.as_view(), name="dashboard-finance-income"),
    path("finance/income/new/", views_finance.IncomeCreate.as_view(), name="dashboard-income-create"),
    path("finance/income/<uuid:pk>/edit/", views_finance.IncomeUpdate.as_view(), name="dashboard-income-edit"),
    path("finance/income/<uuid:pk>/delete/", views_finance.IncomeDelete.as_view(), name="dashboard-income-delete"),
    path("finance/expense/", views_finance.ExpenseList.as_view(), name="dashboard-finance-expense"),
    path("finance/expense/new/", views_finance.ExpenseCreate.as_view(), name="dashboard-expense-create"),
    path("finance/expense/<uuid:pk>/edit/", views_finance.ExpenseUpdate.as_view(), name="dashboard-expense-edit"),
    path("finance/expense/<uuid:pk>/delete/", views_finance.ExpenseDelete.as_view(), name="dashboard-expense-delete"),

    # ---- News ----
    path("news/", views_content.NewsList.as_view(), name="dashboard-news"),
    path("news/new/", views_content.NewsCreate.as_view(), name="dashboard-news-create"),
    path("news/<uuid:pk>/edit/", views_content.NewsUpdate.as_view(), name="dashboard-news-edit"),
    path("news/<uuid:pk>/delete/", views_content.NewsDelete.as_view(), name="dashboard-news-delete"),
    path("news-categories/", views_content.NewsCategoryList.as_view(), name="dashboard-news-categories"),
    path("news-categories/new/", views_content.NewsCategoryCreate.as_view(), name="dashboard-news-category-create"),
    path("news-categories/<uuid:pk>/edit/", views_content.NewsCategoryUpdate.as_view(), name="dashboard-news-category-edit"),
    path("news-categories/<uuid:pk>/delete/", views_content.NewsCategoryDelete.as_view(), name="dashboard-news-category-delete"),

    # ---- Transparency (legal documents) ----
    path("transparency/", views_content.TransparencyList.as_view(), name="dashboard-transparency"),
    path("transparency/new/", views_content.TransparencyCreate.as_view(), name="dashboard-transparency-create"),
    path("transparency/<uuid:pk>/edit/", views_content.TransparencyUpdate.as_view(), name="dashboard-transparency-edit"),
    path("transparency/<uuid:pk>/delete/", views_content.TransparencyDelete.as_view(), name="dashboard-transparency-delete"),

    # ---- Reports export center ----
    path("reports/", views_content.reports_center, name="dashboard-reports"),
    path("reports/export/<str:dataset>/<str:fmt>/", views_content.report_export, name="dashboard-report-export"),
    # ---- Community: Volunteers ----
    path("volunteers/", views_community.volunteers_list, name="dashboard-volunteers"),
    path("volunteers/<uuid:pk>/", views_community.volunteer_detail, name="dashboard-volunteer-detail"),
    path("volunteers/<uuid:pk>/status/", views_community.volunteer_set_status, name="dashboard-volunteer-status"),
    path("volunteers/<uuid:pk>/delete/", views_community.volunteer_delete, name="dashboard-volunteer-delete"),

    # ---- Community: Contact messages ----
    path("contact-messages/", views_community.contact_messages_list, name="dashboard-contact-messages"),
    path("contact-messages/<uuid:pk>/", views_community.contact_message_detail, name="dashboard-contact-message-detail"),
    path("contact-messages/<uuid:pk>/delete/", views_community.contact_message_delete, name="dashboard-contact-message-delete"),

    # ---- Community: Testimonials ----
    path("testimonials/", views_community.TestimonialList.as_view(), name="dashboard-testimonials"),
    path("testimonials/new/", views_community.TestimonialCreate.as_view(), name="dashboard-testimonial-create"),
    path("testimonials/<uuid:pk>/edit/", views_community.TestimonialUpdate.as_view(), name="dashboard-testimonial-edit"),
    path("testimonials/<uuid:pk>/delete/", views_community.TestimonialDelete.as_view(), name="dashboard-testimonial-delete"),

    # ---- Community: FAQs ----
    path("faqs/", views_community.FAQList.as_view(), name="dashboard-faqs"),
    path("faqs/new/", views_community.FAQCreate.as_view(), name="dashboard-faq-create"),
    path("faqs/<uuid:pk>/edit/", views_community.FAQUpdate.as_view(), name="dashboard-faq-edit"),
    path("faqs/<uuid:pk>/delete/", views_community.FAQDelete.as_view(), name="dashboard-faq-delete"),

    # ---- Community: Partners ----
    path("partners/", views_community.PartnerList.as_view(), name="dashboard-partners"),
    path("partners/new/", views_community.PartnerCreate.as_view(), name="dashboard-partner-create"),
    path("partners/<uuid:pk>/edit/", views_community.PartnerUpdate.as_view(), name="dashboard-partner-edit"),
    path("partners/<uuid:pk>/delete/", views_community.PartnerDelete.as_view(), name="dashboard-partner-delete"),

    # ---- Community: Leadership ----
    path("leadership/", views_community.LeadershipList.as_view(), name="dashboard-leadership"),
    path("leadership/new/", views_community.LeadershipCreate.as_view(), name="dashboard-leadership-create"),
    path("leadership/<uuid:pk>/edit/", views_community.LeadershipUpdate.as_view(), name="dashboard-leadership-edit"),
    path("leadership/<uuid:pk>/delete/", views_community.LeadershipDelete.as_view(), name="dashboard-leadership-delete"),

    path("cms/impact-stats/", views_community.ImpactStatisticList.as_view(), name="dashboard-impact-stats"),
    path("cms/impact-stats/new/", views_community.ImpactStatisticCreate.as_view(), name="dashboard-impact-stat-create"),
    path("cms/impact-stats/<uuid:pk>/edit/", views_community.ImpactStatisticUpdate.as_view(), name="dashboard-impact-stat-edit"),
    path("cms/impact-stats/<uuid:pk>/delete/", views_community.ImpactStatisticDelete.as_view(), name="dashboard-impact-stat-delete"),

    # ---- Website CMS: Homepage sections ----
    path("cms/homepage/", views_cms.HomepageSectionList.as_view(), name="dashboard-cms-homepage"),
    path("cms/homepage/new/", views_cms.HomepageSectionCreate.as_view(), name="dashboard-cms-section-create"),
    path("cms/homepage/<uuid:pk>/edit/", views_cms.HomepageSectionUpdate.as_view(), name="dashboard-cms-section-edit"),
    path("cms/homepage/<uuid:pk>/delete/", views_cms.HomepageSectionDelete.as_view(), name="dashboard-cms-section-delete"),
    path("cms/media/", views_gallery.CmsMediaLibraryView.as_view(), name="dashboard-cms-media-library"),
    path("cms/media/<uuid:pk>/delete/", views_gallery.CmsMediaDeleteView.as_view(), name="dashboard-cms-media-delete"),

    # Notification Center
    path("notifications/", views_notifications.notification_list, name="dashboard-notifications"),
    path("notifications/read-all/", views_notifications.notification_mark_all_read, name="dashboard-notifications-read-all"),
    path("notifications/<uuid:pk>/read/", views_notifications.notification_mark_read, name="dashboard-notification-read"),
    path("notifications/<uuid:pk>/delete/", views_notifications.notification_delete, name="dashboard-notification-delete"),
    # ---- Administration: Users ----
    path("users/", views_users.users_list, name="dashboard-users"),
    path("users/new/", views_users.user_create, name="dashboard-user-create"),
    path("users/<uuid:pk>/edit/", views_users.user_edit, name="dashboard-user-edit"),
    path("users/<uuid:pk>/toggle-active/", views_users.user_toggle_active, name="dashboard-user-toggle-active"),
    path("users/<uuid:pk>/reset-password/", views_users.user_reset_password, name="dashboard-user-reset-password"),

    # ---- Administration: Roles ----
    path("roles/", views_users.roles_list, name="dashboard-roles"),
    path("roles/new/", views_users.role_create, name="dashboard-role-create"),
    path("roles/<uuid:pk>/edit/", views_users.role_edit, name="dashboard-role-edit"),
    path("roles/<uuid:pk>/delete/", views_users.role_delete, name="dashboard-role-delete"),

    # Site / SMTP settings (CMS)
    path("settings/site/", views_settings.site_settings_edit, name="dashboard-site-settings"),
    path("settings/smtp/", views_settings.smtp_settings_edit, name="dashboard-smtp-settings"),
    path("settings/smtp/test/", views_settings.smtp_send_test, name="dashboard-smtp-test"),
    path("settings/sms/", views_settings.sms_settings_edit, name="dashboard-sms-settings"),
]
