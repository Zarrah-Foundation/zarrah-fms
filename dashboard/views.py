import json
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from accounts.models import Role
from audit.models import ActivityLog
from audit.notifications import recent_for_user, unread_count_for_user
from core.choices import DonationStatus
from donations.models import Donation, DonationSubscription
from finance.models import Expense, Income, MonthlyFinancialSummary
from members.models import (
    ApplicationStatus,
    Member,
    MemberApplication,
    MembershipFee,
    MemberStatus,
)


def role_required(*roles):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("login")
            if request.user.role not in roles and not request.user.is_superuser:
                return redirect("dashboard")
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        role = user.role

        ctx["role"] = role
        ctx["is_admin"] = role in (
            Role.SUPER_ADMIN,
            Role.EXECUTIVE_ADMIN,
            Role.REGIONAL_ADMIN,
        ) or user.is_superuser
        ctx["is_finance"] = ctx["is_admin"] or role == Role.FINANCE_OFFICER
        ctx["is_executive"] = role in (Role.SUPER_ADMIN, Role.EXECUTIVE_ADMIN) or user.is_superuser
        ctx["is_member"] = role == Role.MEMBER
        ctx["is_donor"] = role == Role.DONOR

        if ctx["is_admin"] or ctx["is_finance"]:
            ctx.update(self._admin_stats(user, role))

        if ctx["is_member"]:
            try:
                ctx["member_profile"] = user.member_profile
                ctx["membership_fees"] = MembershipFee.objects.filter(
                    member=user.member_profile
                ).order_by("-year", "-month")
            except Member.DoesNotExist:
                ctx["member_profile"] = None

        if ctx["is_donor"] or user.is_authenticated:
            from donations.ownership import donations_for_user

            owned = donations_for_user(user)
            ctx["user_donations"] = (
                owned.order_by("-created_at")[:10] if owned is not None else []
            )
            ctx["user_subscriptions"] = DonationSubscription.objects.filter(user=user)

        # Same service as bell/list — includes role broadcasts + NotificationRead.
        unread = [
            n for n in recent_for_user(user, limit=20) if getattr(n, "viewer_is_unread", False)
        ][:10]
        ctx["notifications"] = unread
        ctx["notifications_unread_count"] = unread_count_for_user(user)
        ctx["recent_activity"] = ActivityLog.objects.filter(user=user).order_by("-created_at")[:10]

        return ctx

    def _admin_stats(self, user, role):
        ctx = {}
        ctx["pending_applications"] = MemberApplication.objects.filter(
            status=ApplicationStatus.PENDING
        ).count()
        ctx["pending_members"] = Member.objects.filter(status=MemberStatus.PENDING).count()
        ctx["total_members"] = Member.objects.filter(status=MemberStatus.APPROVED).count()
        ctx["total_donations"] = Donation.objects.filter(status=DonationStatus.COMPLETED).count()
        ctx["total_income"] = Income.objects.aggregate(total=Sum("amount"))["total"] or 0
        ctx["total_expense"] = Expense.objects.aggregate(total=Sum("amount"))["total"] or 0

        ctx["recent_donations"] = Donation.objects.select_related("category").order_by(
            "-created_at"
        )[:10]
        ctx["latest_applications"] = MemberApplication.objects.filter(
            status=ApplicationStatus.PENDING
        ).order_by("-created_at")[:5]

        if role == Role.REGIONAL_ADMIN and hasattr(user, "member_profile"):
            ctx["regional_members"] = Member.objects.filter(
                district=user.member_profile.district
            ).order_by("-created_at")[:20]

        # QuerySets don't support negative indexing/slicing (`qs[-12:]` raises
        # ValueError), so take the latest 12 rows in descending order with a
        # normal positive slice, then reverse in Python for chronological display.
        summaries = list(
            reversed(
                list(
                    MonthlyFinancialSummary.objects.order_by("-year", "-month").values(
                        "year", "month", "total_income", "total_expense"
                    )[:12]
                )
            )
        )
        ctx["finance_chart_labels"] = json.dumps([f"{s['year']}-{s['month']:02d}" for s in summaries])
        ctx["finance_chart_income"] = json.dumps([s["total_income"] for s in summaries])
        ctx["finance_chart_expense"] = json.dumps([s["total_expense"] for s in summaries])

        six_months_ago = timezone.now() - timedelta(days=180)
        donation_trend = (
            Donation.objects.filter(status=DonationStatus.COMPLETED, created_at__gte=six_months_ago)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(total=Sum("amount"))
            .order_by("month")
        )
        ctx["donation_trend_labels"] = json.dumps(
            [d["month"].strftime("%Y-%m") for d in donation_trend]
        )
        ctx["donation_trend_values"] = json.dumps([d["total"] for d in donation_trend])

        membership_growth = (
            Member.objects.filter(created_at__gte=six_months_ago)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )
        ctx["membership_growth_labels"] = json.dumps(
            [m["month"].strftime("%Y-%m") for m in membership_growth]
        )
        ctx["membership_growth_values"] = json.dumps([m["count"] for m in membership_growth])

        return ctx


@method_decorator(login_required, name="dispatch")
class AdminApplicationsView(TemplateView):
    template_name = "dashboard/applications.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.role not in (Role.SUPER_ADMIN, Role.EXECUTIVE_ADMIN, Role.REGIONAL_ADMIN):
            return redirect("dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = MemberApplication.objects.filter(status=ApplicationStatus.PENDING).order_by("-created_at")
        if self.request.user.role == Role.REGIONAL_ADMIN:
            try:
                district = self.request.user.member_profile.district
                qs = qs.filter(present_district=district)
            except Member.DoesNotExist:
                qs = qs.none()
        ctx["applications"] = qs
        return ctx
