"""Phase 6 final: fee period formatting, member-centric summaries, RBAC."""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import activate, deactivate

from accounts.models import Role
from core.choices import DonationStatus, PaymentMethod
from members.billing import (
    MEMBERSHIP_MONTHLY_FEE_BDT,
    add_months,
    current_year_month,
    ensure_ledger_months,
    mark_fee_months_paid,
    paid_through,
    record_admin_fee_payment,
)
from members.fee_notifications import notify_fee_due
from members.fee_summary import annotate_members_for_fee_list, summarize_member_fees, summaries_for_members
from members.models import Member, MemberStatus, MembershipFee
from members.periods import format_fee_period, format_fee_period_short
from rbac.management.commands.seed_rbac import Command as SeedRbac

User = get_user_model()


def _verified_user(email, role=Role.MEMBER):
    user = User.objects.create_user(email=email, password="Str0ngPass!23", role=role)
    user.email_verified = timezone.now()
    user.save(update_fields=["email_verified"])
    return user


def _member(email="fee-ux@example.com", phone="01730000001", **extra):
    user = _verified_user(email)
    return Member.objects.create(
        member_id=f"ZF-UX-{phone[-4:]}",
        user=user,
        first_name="Fee",
        last_name="User",
        phone=phone,
        present_address="Dhaka",
        district="Dhaka",
        status=MemberStatus.APPROVED,
        joined_at=timezone.now().replace(day=1),
        **extra,
    )


class FeePeriodFormatTests(TestCase):
    def test_english_long_and_short(self):
        activate("en")
        try:
            self.assertEqual(format_fee_period(2026, 12), "December 2026")
            self.assertEqual(format_fee_period_short(2026, 12), "Dec 2026")
        finally:
            deactivate()

    def test_bangla_localization(self):
        activate("bn")
        try:
            self.assertIn("২০২৬" if False else "2026", format_fee_period(2026, 12))
            self.assertIn("ডিসেম্বর", format_fee_period(2026, 12))
            self.assertIn("ডিসে", format_fee_period_short(2026, 12))
        finally:
            deactivate()

    def test_model_period_label(self):
        member = _member()
        cy, cm = current_year_month()
        ensure_ledger_months(member, cy, cm)
        fee = MembershipFee.objects.get(member=member, year=cy, month=cm)
        activate("en")
        try:
            self.assertNotRegex(fee.period_label, r"^\d{4}-\d{2}$")
            self.assertIn(str(cy), fee.period_label)
        finally:
            deactivate()


class MemberFeeSummaryTests(TestCase):
    def test_pending_count_and_amount(self):
        member = _member(phone="01730000002")
        cy, cm = current_year_month()
        ensure_ledger_months(member, cy, cm)
        summary = summarize_member_fees(member, ensure_ledger=False)
        self.assertGreaterEqual(summary.pending_months, 1)
        self.assertEqual(
            summary.pending_amount,
            Decimal(str(MEMBERSHIP_MONTHLY_FEE_BDT)) * summary.pending_months,
        )
        self.assertIsNone(summary.paid_through)

    def test_contiguous_paid_through_and_prepaid_not_pending(self):
        member = _member(phone="01730000003")
        cy, cm = current_year_month()
        ny, nm = add_months(cy, cm, 1)
        n2y, n2m = add_months(cy, cm, 2)
        ensure_ledger_months(member, n2y, n2m)
        mark_fee_months_paid(
            member,
            [{"year": cy, "month": cm}, {"year": ny, "month": nm}, {"year": n2y, "month": n2m}],
            payment_method=PaymentMethod.CASH,
            source="ADMIN",
        )
        self.assertEqual(paid_through(member), (n2y, n2m))
        summary = summarize_member_fees(member, ensure_ledger=False)
        self.assertEqual(summary.paid_through, (n2y, n2m))
        # Future prepaid months must not count as pending.
        self.assertEqual(summary.pending_months, 0)
        self.assertEqual(summary.pending_amount, Decimal("0"))

    def test_no_invented_history(self):
        member = _member(phone="01730000004")
        summary = summarize_member_fees(member, ensure_ledger=True)
        # Ledger may create current pending rows — never fabricate COMPLETED payments.
        self.assertIsNone(summary.last_payment)
        self.assertFalse(
            MembershipFee.objects.filter(
                member=member, status=DonationStatus.COMPLETED
            ).exists()
        )

    def test_list_annotation_avoids_extra_paid_through_queries(self):
        m1 = _member(email="a1@example.com", phone="01730000011")
        m2 = _member(email="a2@example.com", phone="01730000012")
        cy, cm = current_year_month()
        for m in (m1, m2):
            ensure_ledger_months(m, cy, cm)
            mark_fee_months_paid(
                m,
                [{"year": cy, "month": cm}],
                payment_method=PaymentMethod.CASH,
                source="ADMIN",
            )
        qs = list(annotate_members_for_fee_list(Member.objects.filter(pk__in=[m1.pk, m2.pk])))
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as ctx:
            # Prefetched completed fees — paid_through computed in Python only.
            summaries = summaries_for_members(qs)
        self.assertLessEqual(len(ctx), 1, [q["sql"] for q in ctx])
        self.assertEqual(summaries[m1.pk].paid_through, (cy, cm))
        self.assertEqual(summaries[m2.pk].pending_months, 0)


class FeeAdminUXAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        SeedRbac().handle()

    def test_member_cannot_view_another_members_fee_detail(self):
        owner = _member(email="owner@example.com", phone="01730000021")
        other = _member(email="other@example.com", phone="01730000022")
        client = Client()
        client.force_login(owner.user)
        response = client.get(
            reverse("dashboard-membership-fee-detail", kwargs={"pk": other.pk})
        )
        # Members without membership_fees.view are redirected away.
        self.assertEqual(response.status_code, 302)

    def test_finance_can_view_member_centric_list_and_detail(self):
        finance = _verified_user("finance-ux@example.com", role=Role.FINANCE_OFFICER)
        member = _member(email="listed@example.com", phone="01730000023")
        ensure_ledger_months(member, *current_year_month())
        client = Client()
        client.force_login(finance)
        list_resp = client.get(reverse("dashboard-membership-fees"))
        self.assertEqual(list_resp.status_code, 200)
        self.assertContains(list_resp, member.member_id)
        self.assertContains(list_resp, "View Details")
        detail = client.get(
            reverse("dashboard-membership-fee-detail", kwargs={"pk": member.pk})
        )
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "Monthly fees")
        self.assertContains(detail, str(int(MEMBERSHIP_MONTHLY_FEE_BDT)))

    def test_fee_detail_shows_payment_source(self):
        finance = _verified_user("finance-src@example.com", role=Role.FINANCE_OFFICER)
        member = _member(email="src@example.com", phone="01730000024")
        cy, cm = current_year_month()
        record_admin_fee_payment(
            member,
            [{"year": cy, "month": cm}],
            payment_method=PaymentMethod.CASH,
            actor=finance,
        )
        client = Client()
        client.force_login(finance)
        detail = client.get(
            reverse("dashboard-membership-fee-detail", kwargs={"pk": member.pk})
        )
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "Cash")

    def test_my_fees_uses_human_period_labels(self):
        member = _member(email="mine@example.com", phone="01730000025")
        ensure_ledger_months(member, *current_year_month())
        client = Client()
        client.force_login(member.user)
        activate("en")
        try:
            response = client.get(reverse("dashboard-my-fees"))
            self.assertEqual(response.status_code, 200)
            cy, cm = current_year_month()
            label = format_fee_period(cy, cm)
            self.assertContains(response, label)
            self.assertContains(response, "Paid through")
        finally:
            deactivate()

    def test_fee_due_notification_human_period(self):
        from audit.models import Notification, NotificationType

        member = _member(email="due-n@example.com", phone="01730000026")
        cy, cm = current_year_month()
        # Create fee without ensure_ledger (which already emits FEE_DUE).
        fee = MembershipFee.objects.create(
            member=member,
            year=cy,
            month=cm,
            amount=MEMBERSHIP_MONTHLY_FEE_BDT,
            status=DonationStatus.PENDING,
        )
        activate("en")
        try:
            n = notify_fee_due(fee)
            self.assertIsNotNone(n)
            label = format_fee_period(cy, cm, language="en")
            self.assertIn(label, n.message)
            raw = "%d-%02d" % (cy, cm)
            self.assertNotIn(raw, n.message)
            self.assertEqual(
                Notification.objects.filter(
                    type=NotificationType.FEE_DUE, object_id=str(fee.pk)
                ).count(),
                1,
            )
        finally:
            deactivate()
