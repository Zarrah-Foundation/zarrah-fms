"""Election notifications via existing audit.notify infrastructure."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from audit.models import NotificationType
from audit.notifications import notify
from voting.models import Election, ElectionAdminAction, ElectionElectorate, ElectionStatus

User = get_user_model()

# Notify when fewer than this many hours remain until end_at.
CLOSING_SOON_HOURS = 6


def _link_member_list():
    try:
        return reverse("my-elections")
    except Exception:
        return "/dashboard/my-elections/"


def notify_election_opened(election):
    link = _link_member_list()
    title = "Election opened"
    message = f"{election.title_en} is now open for voting."
    users = User.objects.filter(
        pk__in=ElectionElectorate.objects.filter(election=election).values_list(
            "user_id", flat=True
        )
    )
    for user in users.iterator():
        notify(
            title=title,
            message=message,
            ntype=NotificationType.ELECTION_OPENED,
            user=user,
            related_object=election,
            link=link,
        )


def notify_election_results_available(election):
    try:
        link = reverse("my-election-results", kwargs={"pk": election.pk})
    except Exception:
        link = _link_member_list()
    title = "Election results available"
    message = f"Results for {election.title_en} have been published."
    users = User.objects.filter(
        pk__in=ElectionElectorate.objects.filter(election=election).values_list(
            "user_id", flat=True
        )
    )
    for user in users.iterator():
        notify(
            title=title,
            message=message,
            ntype=NotificationType.ELECTION_RESULTS,
            user=user,
            related_object=election,
            link=link,
        )


def maybe_notify_election_closing_soon(election: Election) -> bool:
    """
    Best-effort closing-soon notice without Celery.

    Called from member/admin list paths. Sends at most once per election
    (tracked via ElectionAdminAction CLOSING_SOON_NOTIFIED).
    """
    if election.status != ElectionStatus.OPEN or not election.end_at:
        return False
    now = timezone.now()
    if election.end_at <= now:
        return False
    if election.end_at > now + timedelta(hours=CLOSING_SOON_HOURS):
        return False
    if ElectionAdminAction.objects.filter(
        election=election, action="CLOSING_SOON_NOTIFIED"
    ).exists():
        return False

    link = _link_member_list()
    title = "Election closing soon"
    message = f"{election.title_en} closes soon. Cast your vote if you have not already."
    users = User.objects.filter(
        pk__in=ElectionElectorate.objects.filter(election=election).values_list(
            "user_id", flat=True
        )
    )
    for user in users.iterator():
        notify(
            title=title,
            message=message,
            ntype=NotificationType.ELECTION_CLOSING_SOON,
            user=user,
            related_object=election,
            link=link,
        )
    ElectionAdminAction.objects.create(
        election=election,
        actor=None,
        action="CLOSING_SOON_NOTIFIED",
        notes=f"threshold={CLOSING_SOON_HOURS}h",
    )
    return True
