"""Authenticated recurring donation management (dashboard)."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DetailView, ListView

from donations.models import DonationSubscription, SubscriptionStatus
from donations.recurring_services import cancel_subscription


class MyRecurringDonationsView(LoginRequiredMixin, ListView):
    template_name = "dashboard/donations/my_recurring_list.html"
    context_object_name = "subscriptions"
    paginate_by = 25

    def get_queryset(self):
        return (
            DonationSubscription.objects.filter(user=self.request.user)
            .select_related("category")
            .order_by("-created_at")
        )


class MyRecurringDonationDetailView(LoginRequiredMixin, DetailView):
    template_name = "dashboard/donations/my_recurring_detail.html"
    context_object_name = "subscription"

    def get_queryset(self):
        return DonationSubscription.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["charges"] = self.object.charges.order_by("-created_at")[:50]
        return ctx


class MyRecurringDonationCancelView(LoginRequiredMixin, View):
    def post(self, request, pk):
        sub = get_object_or_404(DonationSubscription, pk=pk, user=request.user)
        if sub.status == SubscriptionStatus.CANCELLED:
            messages.info(request, _("This subscription is already cancelled."))
        else:
            cancel_subscription(
                sub, actor=request.user, reason="Cancelled from member dashboard"
            )
            messages.success(request, _("Your recurring donation has been cancelled."))
        return redirect("dashboard-my-recurring-detail", pk=sub.pk)
