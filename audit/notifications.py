"""Notification creation + retrieval service.

``notify()`` is the single entry point for emitting notifications. Icon and
priority are auto-derived from the notification type unless overridden, per the
spec ("Icons should automatically depend on notification type").

Notifications can be addressed to a specific ``user`` and/or a ``target_role``
(role-wide broadcast). Retrieval helpers resolve both, including RBAC roles
whose ``legacy_role`` matches, so role-targeted notices reach the right people
regardless of how their role is assigned.

Read state for personal notifications uses ``Notification.is_read``. Read state
for role broadcasts (``user=NULL``) uses per-user ``NotificationRead`` receipts
so one admin marking read does not clear the notice for everyone.
"""

from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from audit.models import Notification, NotificationPriority, NotificationRead, NotificationType

# Icon per type (Bootstrap Icons).
TYPE_ICONS = {
    NotificationType.NEW_APPLICATION: "bi-file-earmark-person",
    NotificationType.MEMBERSHIP_APPROVED: "bi-check-circle",
    NotificationType.MEMBERSHIP_REJECTED: "bi-x-circle",
    NotificationType.NEW_DONATION: "bi-heart",
    NotificationType.LARGE_DONATION: "bi-cash-coin",
    NotificationType.PAYMENT_FAILED: "bi-exclamation-octagon",
    NotificationType.FEE_DUE: "bi-alarm",
    NotificationType.FEE_PAID: "bi-cash-coin",
    NotificationType.NEW_CONTACT_MESSAGE: "bi-envelope",
    NotificationType.VOLUNTEER_REGISTRATION: "bi-hand-thumbs-up",
    NotificationType.NEWS_PENDING_REVIEW: "bi-newspaper",
    NotificationType.FINANCE_ENTRY: "bi-wallet2",
    NotificationType.ROLE_ASSIGNED: "bi-shield-check",
    NotificationType.USER_CREATED: "bi-person-plus",
    NotificationType.SYSTEM_WARNING: "bi-exclamation-triangle",
    NotificationType.ELECTION_OPENED: "bi-ui-checks-grid",
    NotificationType.ELECTION_CLOSING_SOON: "bi-hourglass-split",
    NotificationType.ELECTION_RESULTS: "bi-bar-chart",
    NotificationType.MEETING_INVITATION: "bi-calendar-event",
    NotificationType.MEETING_UPDATED: "bi-calendar2-week",
    NotificationType.MEETING_CANCELLED: "bi-calendar-x",
    NotificationType.MEETING_REMINDER: "bi-alarm",
    NotificationType.RESOLUTION_AWAITING_SIGNATURE: "bi-pen",
    NotificationType.RESOLUTION_FULLY_SIGNED: "bi-check2-all",
    NotificationType.RESOLUTION_FINALIZED: "bi-file-earmark-check",
    NotificationType.RESOLUTION_NEW_VERSION: "bi-file-earmark-diff",
    NotificationType.GENERAL: "bi-bell",
}

# Default priority per type.
TYPE_PRIORITY = {
    NotificationType.NEW_APPLICATION: NotificationPriority.NORMAL,
    NotificationType.MEMBERSHIP_APPROVED: NotificationPriority.NORMAL,
    NotificationType.MEMBERSHIP_REJECTED: NotificationPriority.NORMAL,
    NotificationType.NEW_DONATION: NotificationPriority.NORMAL,
    NotificationType.LARGE_DONATION: NotificationPriority.HIGH,
    NotificationType.PAYMENT_FAILED: NotificationPriority.HIGH,
    NotificationType.FEE_DUE: NotificationPriority.NORMAL,
    NotificationType.FEE_PAID: NotificationPriority.NORMAL,
    NotificationType.NEW_CONTACT_MESSAGE: NotificationPriority.NORMAL,
    NotificationType.VOLUNTEER_REGISTRATION: NotificationPriority.NORMAL,
    NotificationType.NEWS_PENDING_REVIEW: NotificationPriority.NORMAL,
    NotificationType.FINANCE_ENTRY: NotificationPriority.LOW,
    NotificationType.ROLE_ASSIGNED: NotificationPriority.NORMAL,
    NotificationType.USER_CREATED: NotificationPriority.LOW,
    NotificationType.SYSTEM_WARNING: NotificationPriority.CRITICAL,
    NotificationType.ELECTION_OPENED: NotificationPriority.HIGH,
    NotificationType.ELECTION_CLOSING_SOON: NotificationPriority.HIGH,
    NotificationType.ELECTION_RESULTS: NotificationPriority.NORMAL,
    NotificationType.MEETING_INVITATION: NotificationPriority.HIGH,
    NotificationType.MEETING_UPDATED: NotificationPriority.NORMAL,
    NotificationType.MEETING_CANCELLED: NotificationPriority.HIGH,
    NotificationType.MEETING_REMINDER: NotificationPriority.HIGH,
    NotificationType.RESOLUTION_AWAITING_SIGNATURE: NotificationPriority.HIGH,
    NotificationType.RESOLUTION_FULLY_SIGNED: NotificationPriority.NORMAL,
    NotificationType.RESOLUTION_FINALIZED: NotificationPriority.NORMAL,
    NotificationType.RESOLUTION_NEW_VERSION: NotificationPriority.HIGH,
    NotificationType.GENERAL: NotificationPriority.NORMAL,
}

# Priority accent color (Tailwind text token) for the UI dot.
PRIORITY_DOT = {
    NotificationPriority.LOW: "bg-ink-light",
    NotificationPriority.NORMAL: "bg-info",
    NotificationPriority.HIGH: "bg-warning",
    NotificationPriority.CRITICAL: "bg-danger",
}


def icon_for(ntype):
    return TYPE_ICONS.get(ntype, "bi-bell")


def priority_for(ntype):
    return TYPE_PRIORITY.get(ntype, NotificationPriority.NORMAL)


def notify(
    *,
    title,
    message,
    ntype=NotificationType.GENERAL,
    user=None,
    target_role=None,
    priority=None,
    icon=None,
    link="",
    related_object=None,
):
    """Create and return a Notification. Never raises for missing optionals."""
    kwargs = {
        "title": title[:300],
        "message": message,
        "type": ntype,
        "priority": priority or priority_for(ntype),
        "icon": icon or icon_for(ntype),
        "link": link or "",
        "user": user,
        "target_role": target_role,
    }
    if related_object is not None and related_object.pk is not None:
        from django.contrib.contenttypes.models import ContentType

        kwargs["content_type"] = ContentType.objects.get_for_model(related_object)
        kwargs["object_id"] = str(related_object.pk)
    return Notification.objects.create(**kwargs)


def notify_roles(roles, **kwargs):
    """Emit one role-targeted notification per role in ``roles``.

    ``roles`` is an iterable of legacy role values (accounts.Role). Returns the
    list of created notifications.
    """
    created = []
    seen = set()
    for role in roles:
        if not role or role in seen:
            continue
        seen.add(role)
        created.append(notify(target_role=role, user=None, **kwargs))
    return created


# Legacy roles that make up the administrative audience.
ADMIN_ROLES = ["SUPER_ADMIN", "EXECUTIVE_ADMIN"]


def _visibility_q(user):
    """Q matching notifications addressed to this user or one of their roles."""
    q = Q(user=user)
    roles = set()
    legacy = getattr(user, "role", None)
    if legacy:
        roles.add(legacy)
    # RBAC roles the user holds that map to a legacy role also count.
    try:
        from rbac.models import UserRole

        roles.update(
            UserRole.objects.filter(user=user, role__legacy_role__isnull=False)
            .values_list("role__legacy_role", flat=True)
        )
    except Exception:
        pass
    if roles:
        q |= Q(user__isnull=True, target_role__in=list(roles))
    return q


def for_user_qs(user):
    if not getattr(user, "is_authenticated", False):
        return Notification.objects.none()
    return Notification.objects.filter(_visibility_q(user))


def annotate_read_state(qs, user):
    """Annotate ``viewer_is_unread`` for personal + role-broadcast rows."""
    receipt = NotificationRead.objects.filter(notification_id=OuterRef("pk"), user=user)
    return qs.annotate(has_read_receipt=Exists(receipt))


def notification_is_unread(notification, user):
    if notification.user_id == user.id:
        return not notification.is_read
    if notification.user_id is None:
        if hasattr(notification, "has_read_receipt"):
            return not notification.has_read_receipt
        return not NotificationRead.objects.filter(
            notification=notification, user=user
        ).exists()
    return False


def unread_q_for_user(user):
    receipt = NotificationRead.objects.filter(notification_id=OuterRef("pk"), user=user)
    return Q(user=user, is_read=False) | (
        Q(user__isnull=True) & ~Exists(receipt)
    )


def unread_count_for_user(user):
    if not getattr(user, "is_authenticated", False):
        return 0
    return for_user_qs(user).filter(unread_q_for_user(user)).count()


def recent_for_user(user, limit=8):
    qs = annotate_read_state(for_user_qs(user), user).select_related("content_type")[:limit]
    items = list(qs)
    for n in items:
        n.viewer_is_unread = notification_is_unread(n, user)
    return items


def mark_read_for_user(notification, user):
    """Mark a visible notification as read for ``user``. Returns True if ok."""
    if not for_user_qs(user).filter(pk=notification.pk).exists():
        return False
    if notification.user_id == user.id:
        notification.mark_read()
        return True
    if notification.user_id is None:
        NotificationRead.objects.get_or_create(
            notification=notification,
            user=user,
            defaults={"read_at": timezone.now()},
        )
        return True
    return False


def mark_all_read_for_user(user):
    now = timezone.now()
    personal = for_user_qs(user).filter(user=user, is_read=False)
    personal.update(is_read=True, read_at=now)
    role_unread = for_user_qs(user).filter(user__isnull=True).exclude(reads__user=user)
    NotificationRead.objects.bulk_create(
        [NotificationRead(notification=n, user=user, read_at=now) for n in role_unread],
        ignore_conflicts=True,
    )
