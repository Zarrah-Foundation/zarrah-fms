from datetime import timedelta

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.utils import timezone


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    from audit.models import ActivityLog, LoginHistory

    ip = get_client_ip(request) if request else None
    ua = request.META.get("HTTP_USER_AGENT", "")[:500] if request else None

    ActivityLog.objects.create(
        user=user,
        action="LOGIN",
        entity="User",
        entity_id=str(user.id),
        description="User logged in",
        ip_address=ip,
        user_agent=ua,
    )
    LoginHistory.objects.create(
        user=user,
        ip_address=ip,
        user_agent=ua,
        expires_at=timezone.now() + timedelta(days=7),
    )
