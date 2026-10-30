"""Reusable, permission-gated CRUD scaffolding for simple CMS-managed models.

Subclass the mixins below, set ``permission_module`` + a few attributes, and
you get a styled list / create / edit / delete flow that matches the dashboard
design system. Complex modules (members, donations) use bespoke views instead.
"""

from django.contrib import messages
from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from rbac.mixins import ActionRequiredMixin
from rbac.permissions import has_action


class DashListView(ActionRequiredMixin, ListView):
    permission_action = "view"
    paginate_by = 25
    template_name = "dashboard/generic/list.html"

    # Config
    search_fields = []
    columns = []  # [{"label": "Name", "field": "name_en"}, ...]
    page_title = ""
    page_icon = "bi-collection"
    create_url_name = None
    edit_url_name = None
    delete_url_name = None

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q and self.search_fields:
            cond = Q()
            for field in self.search_fields:
                cond |= Q(**{f"{field}__icontains": q})
            qs = qs.filter(cond)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        module = self.get_permission_module()
        ctx.update(
            {
                "page_title": self.page_title,
                "page_icon": self.page_icon,
                "columns": self.columns,
                "search_query": self.request.GET.get("q", ""),
                "has_search": bool(self.search_fields),
                "create_url_name": self.create_url_name,
                "edit_url_name": self.edit_url_name,
                "delete_url_name": self.delete_url_name,
                "can_create": has_action(user, module, "create"),
                "can_edit": has_action(user, module, "edit"),
                "can_delete": has_action(user, module, "delete"),
            }
        )
        return ctx


class DashCreateView(ActionRequiredMixin, CreateView):
    permission_action = "create"
    template_name = "dashboard/generic/form.html"
    page_title = ""
    success_url_name = None

    def get_success_url(self):
        return reverse(self.success_url_name)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Created successfully."))
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = self.page_title or _("Create")
        ctx["is_create"] = True
        if self.success_url_name:
            ctx["cancel_url"] = reverse(self.success_url_name)
        return ctx


class DashUpdateView(ActionRequiredMixin, UpdateView):
    permission_action = "edit"
    template_name = "dashboard/generic/form.html"
    page_title = ""
    success_url_name = None

    def get_success_url(self):
        return reverse(self.success_url_name)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Saved successfully."))
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = self.page_title or _("Edit")
        ctx["is_create"] = False
        if self.success_url_name:
            ctx["cancel_url"] = reverse(self.success_url_name)
        return ctx


class DashDeleteView(ActionRequiredMixin, DeleteView):
    permission_action = "delete"
    template_name = "dashboard/generic/confirm_delete.html"
    success_url_name = None

    def get_success_url(self):
        return reverse(self.success_url_name)

    def form_valid(self, form):
        messages.success(self.request, _("Deleted successfully."))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.success_url_name:
            ctx["cancel_url"] = reverse(self.success_url_name)
        return ctx
