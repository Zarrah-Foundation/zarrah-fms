from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from donations.ownership import donations_for_user


class MyDonationsView(LoginRequiredMixin, ListView):
    template_name = "dashboard/donations/my_list.html"
    context_object_name = "donations"
    paginate_by = 25

    def get_queryset(self):
        qs = donations_for_user(self.request.user)
        return qs.order_by("-created_at") if qs is not None else []
