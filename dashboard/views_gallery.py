"""Homepage gallery media library endpoints (CMS edit permission)."""

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import View

from cms.gallery_service import MediaInUseError, delete_media_permanently
from cms.models import CmsMedia, HomepageSectionImage
from rbac.mixins import ActionRequiredMixin
from rbac.permissions import has_action


class CmsMediaLibraryView(ActionRequiredMixin, View):
    """Media picker fragment / JSON for selecting existing gallery images."""

    permission_module = "cms"
    permission_action = "edit"

    def get(self, request):
        q = (request.GET.get("q") or "").strip()
        section_id = request.GET.get("section")
        already = set()
        if section_id:
            already = set(
                str(x)
                for x in HomepageSectionImage.objects.filter(section_id=section_id).values_list(
                    "media_id", flat=True
                )
            )
        qs = CmsMedia.objects.all().order_by("-created_at")
        if q:
            qs = qs.filter(original_filename__icontains=q)
        qs = qs[:100]
        items = [
            {
                "id": str(m.id),
                "url": m.image.url if m.image else "",
                "name": m.display_name,
                "created": m.created_at.strftime("%Y-%m-%d"),
                "in_gallery": str(m.id) in already,
                "usage_count": m.gallery_usages.count(),
            }
            for m in qs
        ]
        if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("format") == "json":
            return JsonResponse({"results": items})
        return render(
            request,
            "dashboard/cms/media_library_partial.html",
            {
                "media_items": items,
                "search_query": q,
                "section_id": section_id or "",
            },
        )


class CmsMediaDeleteView(ActionRequiredMixin, View):
    """Permanent delete with in-use protection."""

    permission_module = "cms"
    permission_action = "edit"

    def get(self, request, pk):
        media = get_object_or_404(CmsMedia, pk=pk)
        usages = list(
            HomepageSectionImage.objects.filter(media=media)
            .select_related("section")
            .order_by("section__order")
        )
        return render(
            request,
            "dashboard/cms/media_delete_confirm.html",
            {
                "media": media,
                "usages": usages,
                "usage_count": len(usages),
                "cancel_url": request.GET.get("next")
                or reverse("dashboard-cms-homepage"),
            },
        )

    def post(self, request, pk):
        media = get_object_or_404(CmsMedia, pk=pk)
        next_url = request.POST.get("next") or reverse("dashboard-cms-homepage")
        force = request.POST.get("force") == "1"
        try:
            delete_media_permanently(media, force=force)
            messages.success(request, _("Image permanently deleted."))
        except MediaInUseError as exc:
            messages.error(
                request,
                _(
                    "This image is used in %(count)s gallery(ies). "
                    "Remove it from those galleries first, or confirm forced delete."
                )
                % {"count": exc.usage_count},
            )
            return redirect(
                reverse("dashboard-cms-media-delete", kwargs={"pk": pk})
                + f"?next={next_url}"
            )
        return redirect(next_url)


def user_can_edit_cms(user) -> bool:
    return has_action(user, "cms", "edit")
