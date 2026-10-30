"""Community modules: volunteers, testimonials, contact messages, FAQs, partners."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l
from django.views.decorators.http import require_POST

from cms.models import ImpactStatistic
from community.models import (
    FAQ,
    ContactMessage,
    LeadershipPerson,
    Partner,
    Testimonial,
    Volunteer,
    VolunteerStatus,
)
from dashboard.crud import DashCreateView, DashDeleteView, DashListView, DashUpdateView
from dashboard.forms import FAQForm, ImpactStatisticForm, LeadershipPersonForm, PartnerForm, TestimonialForm
from rbac.permissions import has_action


# =========================================================================
# Volunteers
# =========================================================================

@login_required
def volunteers_list(request):
    if not has_action(request.user, "volunteers", "view"):
        return redirect("dashboard")
    qs = Volunteer.objects.all()
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q))
    if status:
        qs = qs.filter(status=status)
    page_obj = Paginator(qs, 25).get_page(request.GET.get("page"))
    return render(
        request,
        "dashboard/community/volunteers_list.html",
        {
            "page_obj": page_obj,
            "volunteers": page_obj.object_list,
            "search_query": q,
            "status": status,
            "statuses": VolunteerStatus.choices,
            "can_edit": has_action(request.user, "volunteers", "edit"),
            "can_delete": has_action(request.user, "volunteers", "delete"),
        },
    )


@login_required
def volunteer_detail(request, pk):
    if not has_action(request.user, "volunteers", "view"):
        return redirect("dashboard")
    volunteer = get_object_or_404(Volunteer, pk=pk)
    return render(
        request,
        "dashboard/community/volunteer_detail.html",
        {
            "volunteer": volunteer,
            "statuses": VolunteerStatus.choices,
            "can_edit": has_action(request.user, "volunteers", "edit"),
        },
    )


@login_required
@require_POST
def volunteer_set_status(request, pk):
    if not has_action(request.user, "volunteers", "edit"):
        return redirect("dashboard")
    volunteer = get_object_or_404(Volunteer, pk=pk)
    new_status = request.POST.get("status")
    if new_status in VolunteerStatus.values:
        volunteer.status = new_status
        volunteer.save(update_fields=["status"])
        messages.success(request, _("Volunteer status updated."))
    return redirect("dashboard-volunteer-detail", pk=pk)


@login_required
@require_POST
def volunteer_delete(request, pk):
    if not has_action(request.user, "volunteers", "delete"):
        return redirect("dashboard")
    volunteer = get_object_or_404(Volunteer, pk=pk)
    volunteer.delete()
    messages.success(request, _("Volunteer deleted."))
    return redirect("dashboard-volunteers")


# =========================================================================
# Contact messages
# =========================================================================

@login_required
def contact_messages_list(request):
    if not has_action(request.user, "contact_messages", "view"):
        return redirect("dashboard")
    qs = ContactMessage.objects.all()
    q = request.GET.get("q", "").strip()
    unread = request.GET.get("unread") == "1"
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q) | Q(subject__icontains=q))
    if unread:
        qs = qs.filter(is_read=False)
    page_obj = Paginator(qs, 25).get_page(request.GET.get("page"))
    return render(
        request,
        "dashboard/community/contact_list.html",
        {
            "page_obj": page_obj,
            "contact_messages": page_obj.object_list,
            "search_query": q,
            "unread": unread,
            "unread_count": ContactMessage.objects.filter(is_read=False).count(),
            "can_delete": has_action(request.user, "contact_messages", "delete"),
        },
    )


@login_required
def contact_message_detail(request, pk):
    if not has_action(request.user, "contact_messages", "view"):
        return redirect("dashboard")
    message = get_object_or_404(ContactMessage, pk=pk)
    if not message.is_read:
        message.is_read = True
        message.save(update_fields=["is_read"])
    return render(
        request,
        "dashboard/community/contact_detail.html",
        {
            "message": message,
            "can_delete": has_action(request.user, "contact_messages", "delete"),
        },
    )


@login_required
@require_POST
def contact_message_delete(request, pk):
    if not has_action(request.user, "contact_messages", "delete"):
        return redirect("dashboard")
    message = get_object_or_404(ContactMessage, pk=pk)
    message.delete()
    messages.success(request, _("Message deleted."))
    return redirect("dashboard-contact-messages")


# =========================================================================
# Testimonials (generic CRUD)
# =========================================================================

class TestimonialList(DashListView):
    model = Testimonial
    permission_module = "testimonials"
    ordering = ["display_order", "-created_at"]
    search_fields = ["author_name", "designation"]
    page_title = _l("Testimonials")
    page_icon = "bi-chat-quote"
    columns = [
        {"label": _l("Author"), "field": "author_name"},
        {"label": _l("Designation"), "field": "designation"},
        {"label": _l("Order"), "field": "display_order"},
        {"label": _l("Published"), "field": "is_published"},
    ]
    create_url_name = "dashboard-testimonial-create"
    edit_url_name = "dashboard-testimonial-edit"
    delete_url_name = "dashboard-testimonial-delete"


class TestimonialCreate(DashCreateView):
    model = Testimonial
    permission_module = "testimonials"
    form_class = TestimonialForm
    page_title = _l("Add Testimonial")
    success_url_name = "dashboard-testimonials"


class TestimonialUpdate(DashUpdateView):
    model = Testimonial
    permission_module = "testimonials"
    form_class = TestimonialForm
    page_title = _l("Edit Testimonial")
    success_url_name = "dashboard-testimonials"


class TestimonialDelete(DashDeleteView):
    model = Testimonial
    permission_module = "testimonials"
    success_url_name = "dashboard-testimonials"


# =========================================================================
# FAQs (generic CRUD)
# =========================================================================

class FAQList(DashListView):
    model = FAQ
    permission_module = "faqs"
    ordering = ["display_order"]
    search_fields = ["question_en", "question_bn"]
    page_title = _l("FAQs")
    page_icon = "bi-question-circle"
    columns = [
        {"label": _l("Question"), "field": "question_en"},
        {"label": _l("Order"), "field": "display_order"},
        {"label": _l("Active"), "field": "is_active"},
    ]
    create_url_name = "dashboard-faq-create"
    edit_url_name = "dashboard-faq-edit"
    delete_url_name = "dashboard-faq-delete"


class FAQCreate(DashCreateView):
    model = FAQ
    permission_module = "faqs"
    form_class = FAQForm
    page_title = _l("Add FAQ")
    success_url_name = "dashboard-faqs"


class FAQUpdate(DashUpdateView):
    model = FAQ
    permission_module = "faqs"
    form_class = FAQForm
    page_title = _l("Edit FAQ")
    success_url_name = "dashboard-faqs"


class FAQDelete(DashDeleteView):
    model = FAQ
    permission_module = "faqs"
    success_url_name = "dashboard-faqs"


# =========================================================================
# Partners (generic CRUD)
# =========================================================================

class PartnerList(DashListView):
    model = Partner
    permission_module = "partners"
    ordering = ["display_order", "name"]
    search_fields = ["name"]
    page_title = _l("Partners")
    page_icon = "bi-building"
    columns = [
        {"label": _l("Name"), "field": "name"},
        {"label": _l("Relationship"), "field": "relationship_type"},
        {"label": _l("Order"), "field": "display_order"},
        {"label": _l("Active"), "field": "is_active"},
    ]
    create_url_name = "dashboard-partner-create"
    edit_url_name = "dashboard-partner-edit"
    delete_url_name = "dashboard-partner-delete"


class PartnerCreate(DashCreateView):
    model = Partner
    permission_module = "partners"
    form_class = PartnerForm
    page_title = _l("Add Partner")
    success_url_name = "dashboard-partners"


class PartnerUpdate(DashUpdateView):
    model = Partner
    permission_module = "partners"
    form_class = PartnerForm
    page_title = _l("Edit Partner")
    success_url_name = "dashboard-partners"


class PartnerDelete(DashDeleteView):
    model = Partner
    permission_module = "partners"
    success_url_name = "dashboard-partners"


# =========================================================================
# Leadership (About page profiles)
# =========================================================================

class LeadershipList(DashListView):
    model = LeadershipPerson
    permission_module = "leadership"
    ordering = ["display_order", "role"]
    search_fields = ["name", "role_label_en", "role_label_bn"]
    page_title = _l("Leadership")
    page_icon = "bi-person-badge"
    columns = [
        {"label": _l("Name"), "field": "name"},
        {"label": _l("Role"), "field": "role"},
        {"label": _l("Order"), "field": "display_order"},
        {"label": _l("Published"), "field": "is_published"},
    ]
    create_url_name = "dashboard-leadership-create"
    edit_url_name = "dashboard-leadership-edit"
    delete_url_name = "dashboard-leadership-delete"


class LeadershipCreate(DashCreateView):
    model = LeadershipPerson
    permission_module = "leadership"
    form_class = LeadershipPersonForm
    page_title = _l("Add Leadership")
    success_url_name = "dashboard-leadership"


class LeadershipUpdate(DashUpdateView):
    model = LeadershipPerson
    permission_module = "leadership"
    form_class = LeadershipPersonForm
    page_title = _l("Edit Leadership")
    success_url_name = "dashboard-leadership"


class LeadershipDelete(DashDeleteView):
    model = LeadershipPerson
    permission_module = "leadership"
    success_url_name = "dashboard-leadership"


class ImpactStatisticList(DashListView):
    model = ImpactStatistic
    permission_module = "cms"
    permission_action = "view"
    ordering = ["display_order", "created_at"]
    search_fields = ["label_en", "label_bn", "value"]
    page_title = _l("Impact Statistics")
    page_icon = "bi-bar-chart"
    columns = [
        {"label": _l("Value"), "field": "value"},
        {"label": _l("Label"), "field": "label_en"},
        {"label": _l("Order"), "field": "display_order"},
        {"label": _l("Published"), "field": "is_published"},
    ]
    create_url_name = "dashboard-impact-stat-create"
    edit_url_name = "dashboard-impact-stat-edit"
    delete_url_name = "dashboard-impact-stat-delete"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        can_edit = has_action(self.request.user, "cms", "edit")
        ctx["can_create"] = can_edit
        ctx["can_edit"] = can_edit
        ctx["can_delete"] = can_edit
        ctx["page_subtitle"] = _l(
            "Publish only verified organizational figures. Unpublish a statistic or the "
            "homepage Impact Statistics section to hide it. Do not enter estimated or marketing numbers."
        )
        return ctx


class ImpactStatisticCreate(DashCreateView):
    model = ImpactStatistic
    permission_module = "cms"
    permission_action = "edit"
    form_class = ImpactStatisticForm
    page_title = _l("Add statistic")
    success_url_name = "dashboard-impact-stats"


class ImpactStatisticUpdate(DashUpdateView):
    model = ImpactStatistic
    permission_module = "cms"
    permission_action = "edit"
    form_class = ImpactStatisticForm
    page_title = _l("Edit statistic")
    success_url_name = "dashboard-impact-stats"


class ImpactStatisticDelete(DashDeleteView):
    model = ImpactStatistic
    permission_module = "cms"
    permission_action = "edit"
    success_url_name = "dashboard-impact-stats"
