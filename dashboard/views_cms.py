"""Website CMS: homepage section editor (hero + sections).

Footer, SEO, social links and site identity live in Site Settings
(``dashboard-site-settings``); this module manages the ordered homepage
sections over the existing ``cms.HomepageSection`` model. The ``cms`` permission
module exposes ``view`` and ``edit`` only, so create/delete reuse ``edit``.
"""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l

from cms.gallery_service import attach_many, attach_media_to_section, create_media, normalize_orders
from cms.models import HomepageSection, HomepageSectionImage, SectionType
from cms.section_meta import language_completeness, publish_status, section_meta
from dashboard.crud import DashCreateView, DashDeleteView, DashListView, DashUpdateView
from dashboard.forms import HomepageSectionForm, HomepageSectionImageFormSet
from rbac.permissions import has_action


class HomepageSectionList(DashListView):
    model = HomepageSection
    permission_module = "cms"
    ordering = ["order"]
    page_title = _l("Homepage Sections")
    page_icon = "bi-window"
    template_name = "dashboard/cms/section_list.html"
    create_url_name = "dashboard-cms-section-create"
    edit_url_name = "dashboard-cms-section-edit"
    delete_url_name = "dashboard-cms-section-delete"

    def get_queryset(self):
        return HomepageSection.objects.filter(is_deleted=False).order_by("order")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        can_edit = has_action(self.request.user, "cms", "edit")
        ctx["can_create"] = can_edit
        ctx["can_edit"] = can_edit
        ctx["can_delete"] = can_edit
        ctx["page_subtitle"] = _l(
            "Core homepage sections are edited here. Data-driven sections only control "
            "presentation — content comes from Community, News, or About."
        )
        rows = []
        for section in ctx["object_list"]:
            meta = section_meta(section.section_type)
            rows.append(
                {
                    "section": section,
                    "meta": meta,
                    "status": publish_status(section),
                    "langs": language_completeness(section),
                    "manage_url_name": meta.get("manage_url_name"),
                }
            )
        ctx["section_rows"] = rows
        return ctx


class _HomepageSectionFormMixin:
    model = HomepageSection
    permission_module = "cms"
    permission_action = "edit"
    form_class = HomepageSectionForm
    template_name = "dashboard/cms/section_form.html"
    success_url_name = "dashboard-cms-homepage"

    def get_success_url(self):
        if self.request.POST.get("save_continue") and self.object:
            return reverse("dashboard-cms-section-edit", kwargs={"pk": self.object.pk})
        return reverse(self.success_url_name)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["lock_section_type"] = bool(getattr(self, "object", None) and self.object.pk)
        return kwargs

    def get_image_formset(self):
        kwargs = {
            "instance": self.object if getattr(self, "object", None) and self.object.pk else None
        }
        if self.request.method == "POST":
            kwargs.update({"data": self.request.POST, "files": self.request.FILES})
        return HomepageSectionImageFormSet(**kwargs)

    def _wants_gallery(self, form):
        st = form.cleaned_data.get("section_type") if form.is_bound else None
        if not st and self.object and self.object.pk:
            st = self.object.section_type
        return st == SectionType.GALLERY_PREVIEW

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        form = ctx.get("form")
        ctx["cancel_url"] = reverse(self.success_url_name)
        ctx["preview_home_url"] = reverse("home")
        ctx["editor_key"] = getattr(form, "editor_key", "generic") if form else "generic"
        ctx["source_help"] = getattr(form, "source_help", "") if form else ""
        manage = getattr(form, "manage_url_name", None) if form else None
        ctx["manage_url"] = reverse(manage) if manage else None
        ctx["image_formset"] = kwargs.get("image_formset") or self.get_image_formset()
        st = None
        if form and form.is_bound:
            st = form.data.get("section_type")
        elif getattr(self, "object", None) and self.object.pk:
            st = self.object.section_type
        else:
            st = self.request.GET.get("type", "").strip().upper() or (
                form.initial.get("section_type") if form else None
            )
        ctx["show_gallery_formset"] = (
            ctx["editor_key"] == "gallery" or st == SectionType.GALLERY_PREVIEW
        )
        if ctx["show_gallery_formset"] and self.object and self.object.pk:
            ctx["gallery_memberships"] = list(
                HomepageSectionImage.objects.filter(section=self.object)
                .select_related("media")
                .order_by("order", "created_at")
            )
            ctx["media_library_url"] = (
                reverse("dashboard-cms-media-library") + f"?section={self.object.pk}"
            )
        else:
            ctx["gallery_memberships"] = []
            ctx["media_library_url"] = reverse("dashboard-cms-media-library")
        return ctx

    def _apply_gallery_uploads_and_attach(self, form):
        """Upload new files + attach selected library media. Returns error message or None."""
        files = form.cleaned_data.get("new_gallery_images") or []
        # Fallback for browsers / widgets that don't bind as a list.
        if not files:
            files = self.request.FILES.getlist("new_gallery_images")
        for uploaded in files:
            try:
                media = create_media(uploaded=uploaded, user=self.request.user)
            except ValidationError as exc:
                return "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
            attach_media_to_section(self.object, media)

        raw_ids = (form.cleaned_data.get("attach_media_ids") or "").strip()
        if raw_ids:
            ids = [part.strip() for part in raw_ids.replace(";", ",").split(",") if part.strip()]
            attach_many(self.object, ids)

        order_raw = (self.request.POST.get("gallery_order") or "").strip()
        if order_raw:
            ordered_ids = [part.strip() for part in order_raw.split(",") if part.strip()]
            normalize_orders(self.object, ordered_ids)
        return None

    def form_valid(self, form):
        wants_gallery = self._wants_gallery(form)
        with transaction.atomic():
            self.object = form.save(commit=False)
            self.object.save()
            form.save_m2m()
            if wants_gallery:
                image_formset = HomepageSectionImageFormSet(
                    self.request.POST,
                    self.request.FILES,
                    instance=self.object,
                )
                if not image_formset.is_valid():
                    return self.form_invalid(form, image_formset=image_formset)
                image_formset.save()
                err = self._apply_gallery_uploads_and_attach(form)
                if err:
                    messages.error(self.request, err)
                    return self.form_invalid(form, image_formset=image_formset)

        if self.request.resolver_match and self.request.resolver_match.url_name == "dashboard-cms-section-create":
            messages.success(self.request, _("Created successfully."))
        else:
            messages.success(self.request, _("Gallery saved successfully.") if wants_gallery else _("Saved successfully."))
        return redirect(self.get_success_url())

    def form_invalid(self, form, image_formset=None):
        return self.render_to_response(
            self.get_context_data(form=form, image_formset=image_formset or self.get_image_formset())
        )


class HomepageSectionCreate(_HomepageSectionFormMixin, DashCreateView):
    page_title = _l("Add Homepage Section")

    def get_initial(self):
        initial = super().get_initial()
        st = self.request.GET.get("type", "").strip().upper()
        if st in SectionType.values:
            initial["section_type"] = st
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["lock_section_type"] = False
        return kwargs


class HomepageSectionUpdate(_HomepageSectionFormMixin, DashUpdateView):
    page_title = _l("Edit Homepage Section")

    def get_queryset(self):
        return HomepageSection.objects.filter(is_deleted=False)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = _(
            "Edit %(type)s"
        ) % {"type": self.object.get_section_type_display()}
        return ctx


class HomepageSectionDelete(DashDeleteView):
    model = HomepageSection
    permission_module = "cms"
    permission_action = "edit"
    success_url_name = "dashboard-cms-homepage"

    def get_queryset(self):
        return HomepageSection.objects.filter(is_deleted=False)

    def form_valid(self, form):
        self.object.is_deleted = True
        self.object.save(update_fields=["is_deleted", "updated_at"])
        messages.success(self.request, _("Deleted successfully."))
        return redirect(self.get_success_url())
