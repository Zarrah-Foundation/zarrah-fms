"""Notification Center views (list, mark read, mark all read, delete)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from audit.models import Notification
from audit.notifications import (
    annotate_read_state,
    for_user_qs,
    mark_all_read_for_user,
    mark_read_for_user,
    notification_is_unread,
    unread_count_for_user,
    unread_q_for_user,
)


@login_required
def notification_list(request):
    qs = annotate_read_state(for_user_qs(request.user), request.user).select_related(
        "content_type"
    )
    unread_only = request.GET.get("filter") == "unread"
    if unread_only:
        qs = qs.filter(unread_q_for_user(request.user))

    from django.core.paginator import Paginator

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    notifications = list(page_obj.object_list)
    for n in notifications:
        n.viewer_is_unread = notification_is_unread(n, request.user)

    from django.shortcuts import render

    return render(
        request,
        "dashboard/notifications/list.html",
        {
            "page_obj": page_obj,
            "notifications": notifications,
            "unread_only": unread_only,
            "unread_count": unread_count_for_user(request.user),
        },
    )


@login_required
@require_POST
def notification_mark_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk)
    if not mark_read_for_user(notif, request.user):
        raise Http404()
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "unread": unread_count_for_user(request.user)})
    return redirect(request.META.get("HTTP_REFERER") or "dashboard-notifications")


@login_required
@require_POST
def notification_mark_all_read(request):
    mark_all_read_for_user(request.user)
    if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.headers.get(
        "accept", ""
    ).startswith("application/json"):
        return JsonResponse({"ok": True, "unread": 0})
    messages.success(request, _("All notifications marked as read."))
    return redirect(request.META.get("HTTP_REFERER") or "dashboard-notifications")


@login_required
@require_POST
def notification_delete(request, pk):
    # Only personal notifications may be deleted; role broadcasts are shared.
    notif = get_object_or_404(Notification.objects.filter(user=request.user), pk=pk)
    notif.delete()
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "unread": unread_count_for_user(request.user)})
    messages.success(request, _("Notification deleted."))
    return redirect(request.META.get("HTTP_REFERER") or "dashboard-notifications")
