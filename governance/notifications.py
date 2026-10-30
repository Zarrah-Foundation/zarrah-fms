"""Governance meeting/resolution notifications via existing audit + email + SMS."""

from __future__ import annotations

import logging
from typing import Optional

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from audit.models import NotificationType
from audit.notifications import notify
from core.email import send_email
from governance.models import (
    DeliveryStatus,
    Meeting,
    MeetingNotificationLog,
    MeetingParticipant,
    NotificationChannel,
    Resolution,
)

logger = logging.getLogger(__name__)

# Re-export for tests that patch ``governance.notifications.notify``.
__all__ = [
    "notify",
    "notify_meeting_invitation",
    "notify_meeting_update",
    "notify_meeting_cancellation",
    "notify_meeting_reminder",
    "notify_resolution_awaiting_signature",
    "notify_resolution_fully_signed",
    "notify_resolution_finalized",
    "notify_resolution_new_version",
]


def _local_starts(meeting: Meeting):
    return timezone.localtime(meeting.starts_at)


def _meeting_location_line(meeting: Meeting) -> str:
    bits = []
    if meeting.venue_name:
        bits.append(meeting.venue_name.strip())
    if meeting.room_details:
        bits.append(meeting.room_details.strip())
    if meeting.venue_address:
        bits.append(meeting.venue_address.strip())
    return ", ".join(bits)


def _meeting_mode_label(meeting: Meeting) -> str:
    return meeting.get_mode_display()


def _agenda_summary(meeting: Meeting, *, limit: int = 8) -> str:
    items = list(
        meeting.agenda_items.order_by("display_order", "number").values_list(
            "number", "title_bn", "title_en"
        )[:limit]
    )
    if not items:
        return ""
    lines = []
    for number, title_bn, title_en in items:
        title = (title_bn or title_en or "").strip()
        lines.append(f"{number}. {title}")
    return "\n".join(lines)


def _meeting_message_body(meeting: Meeting, *, include_online: bool = True) -> str:
    starts = _local_starts(meeting)
    lines = [
        f"Meeting: {meeting.localized_title('en') or meeting.title_bn}",
        f"Reference: {meeting.reference_id}",
        f"Type: {meeting.meeting_type.localized_name('en')}",
        f"Date: {starts.strftime('%d %B %Y')}",
        f"Time: {starts.strftime('%H:%M')} ({meeting.timezone})",
        f"Mode: {_meeting_mode_label(meeting)}",
    ]
    location = _meeting_location_line(meeting)
    if location:
        lines.append(f"Location: {location}")
    if include_online and meeting.mode in ("ONLINE", "HYBRID") and meeting.meeting_url:
        lines.append(f"Online link: {meeting.meeting_url}")
        if meeting.meeting_id_code:
            lines.append(f"Meeting ID: {meeting.meeting_id_code}")
        # Password only for authorized invitees (this channel), never public pages.
        if meeting.meeting_password:
            lines.append(f"Join code/password: {meeting.meeting_password}")
    agenda = _agenda_summary(meeting)
    if agenda:
        lines.append("Agenda:")
        lines.append(agenda)
    return "\n".join(lines)


def _idempotency_key(
    notification_type: str,
    meeting_id,
    participant_id,
    channel: str,
    *,
    extra: str = "",
) -> str:
    base = f"{notification_type}:{meeting_id}:{participant_id}:{channel}"
    if extra:
        return f"{base}:{extra}"
    return base


def _log_exists(key: str) -> bool:
    return MeetingNotificationLog.objects.filter(idempotency_key=key).exists()


def _create_log(
    *,
    meeting: Optional[Meeting],
    resolution: Optional[Resolution],
    recipient_user,
    recipient_address: str,
    notification_type: str,
    channel: str,
    idempotency_key: str,
    status: str,
    failure_reason: str = "",
) -> MeetingNotificationLog:
    now = timezone.now() if status == DeliveryStatus.SENT else None
    return MeetingNotificationLog.objects.create(
        meeting=meeting,
        resolution=resolution,
        recipient_user=recipient_user,
        recipient_address=recipient_address or "",
        notification_type=notification_type,
        channel=channel,
        idempotency_key=idempotency_key,
        status=status,
        failure_reason=failure_reason or "",
        sent_at=now,
    )


def _recipient_user(participant: MeetingParticipant):
    return getattr(participant.member, "user", None)


def _send_account(
    *,
    meeting: Meeting,
    participant: MeetingParticipant,
    notification_type: str,
    title: str,
    message: str,
    link: str = "",
    ntype: str = NotificationType.GENERAL,
) -> bool:
    user = _recipient_user(participant)
    key = _idempotency_key(
        notification_type, meeting.pk, participant.pk, NotificationChannel.ACCOUNT
    )
    if _log_exists(key):
        return False
    if user is None:
        _create_log(
            meeting=meeting,
            resolution=None,
            recipient_user=None,
            recipient_address="",
            notification_type=notification_type,
            channel=NotificationChannel.ACCOUNT,
            idempotency_key=key,
            status=DeliveryStatus.SKIPPED,
            failure_reason="No user account",
        )
        return False
    try:
        notify(
            title=title,
            message=message,
            ntype=ntype,
            user=user,
            related_object=meeting,
            link=link,
        )
        _create_log(
            meeting=meeting,
            resolution=None,
            recipient_user=user,
            recipient_address=getattr(user, "email", "") or "",
            notification_type=notification_type,
            channel=NotificationChannel.ACCOUNT,
            idempotency_key=key,
            status=DeliveryStatus.SENT,
        )
        return True
    except Exception as exc:
        logger.exception("Account notification failed for %s", key)
        _create_log(
            meeting=meeting,
            resolution=None,
            recipient_user=user,
            recipient_address=getattr(user, "email", "") or "",
            notification_type=notification_type,
            channel=NotificationChannel.ACCOUNT,
            idempotency_key=key,
            status=DeliveryStatus.FAILED,
            failure_reason=str(exc)[:500],
        )
        return False


def _send_email(
    *,
    meeting: Meeting,
    participant: MeetingParticipant,
    notification_type: str,
    subject: str,
    body: str,
    html_message: str | None = None,
) -> bool:
    user = _recipient_user(participant)
    email = (getattr(user, "email", "") or "").strip()
    key = _idempotency_key(
        notification_type, meeting.pk, participant.pk, NotificationChannel.EMAIL
    )
    if _log_exists(key):
        return False
    if not email:
        _create_log(
            meeting=meeting,
            resolution=None,
            recipient_user=user,
            recipient_address="",
            notification_type=notification_type,
            channel=NotificationChannel.EMAIL,
            idempotency_key=key,
            status=DeliveryStatus.SKIPPED,
            failure_reason="No email",
        )
        return False
    try:
        send_email(
            subject=subject,
            message=body,
            recipient_list=[email],
            html_message=html_message,
        )
        _create_log(
            meeting=meeting,
            resolution=None,
            recipient_user=user,
            recipient_address=email,
            notification_type=notification_type,
            channel=NotificationChannel.EMAIL,
            idempotency_key=key,
            status=DeliveryStatus.SENT,
        )
        return True
    except Exception as exc:
        logger.exception("Email notification failed for %s", key)
        _create_log(
            meeting=meeting,
            resolution=None,
            recipient_user=user,
            recipient_address=email,
            notification_type=notification_type,
            channel=NotificationChannel.EMAIL,
            idempotency_key=key,
            status=DeliveryStatus.FAILED,
            failure_reason=str(exc)[:500],
        )
        return False


def _send_sms(
    *,
    meeting: Meeting,
    participant: MeetingParticipant,
    notification_type: str,
    message: str,
) -> bool:
    phone = (getattr(participant.member, "phone", "") or "").strip()
    user = _recipient_user(participant)
    key = _idempotency_key(
        notification_type, meeting.pk, participant.pk, NotificationChannel.SMS
    )
    if _log_exists(key):
        return False
    if not phone:
        _create_log(
            meeting=meeting,
            resolution=None,
            recipient_user=user,
            recipient_address="",
            notification_type=notification_type,
            channel=NotificationChannel.SMS,
            idempotency_key=key,
            status=DeliveryStatus.SKIPPED,
            failure_reason="No phone",
        )
        return False
    try:
        from core.sms.service import SMSService

        ok = SMSService.send_sms(phone, message[:480])
        _create_log(
            meeting=meeting,
            resolution=None,
            recipient_user=user,
            recipient_address=phone,
            notification_type=notification_type,
            channel=NotificationChannel.SMS,
            idempotency_key=key,
            status=DeliveryStatus.SENT if ok else DeliveryStatus.FAILED,
            failure_reason="" if ok else "SMS provider returned false",
        )
        return bool(ok)
    except Exception as exc:
        logger.exception("SMS notification failed for %s", key)
        _create_log(
            meeting=meeting,
            resolution=None,
            recipient_user=user,
            recipient_address=phone,
            notification_type=notification_type,
            channel=NotificationChannel.SMS,
            idempotency_key=key,
            status=DeliveryStatus.FAILED,
            failure_reason=str(exc)[:500],
        )
        return False


def _deliver_meeting_channels(
    meeting: Meeting,
    participant: MeetingParticipant,
    *,
    notification_type: str,
    title: str,
    message: str,
    email_subject: str | None = None,
    email_body: str | None = None,
    email_html: str | None = None,
    link: str = "",
    ntype: str = NotificationType.GENERAL,
) -> None:
    meeting = Meeting.objects.select_related("meeting_type").get(pk=meeting.pk)
    participant = MeetingParticipant.objects.select_related("member__user").get(
        pk=participant.pk
    )
    _send_account(
        meeting=meeting,
        participant=participant,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link,
        ntype=ntype,
    )
    _send_email(
        meeting=meeting,
        participant=participant,
        notification_type=notification_type,
        subject=email_subject or title,
        body=email_body if email_body is not None else message,
        html_message=email_html,
    )
    # Short SMS body without join password to reduce accidental forwarding surface.
    sms_body = (
        f"{title}: {meeting.reference_id} "
        f"{_local_starts(meeting).strftime('%d %b %Y %H:%M')}"
    )
    _send_sms(
        meeting=meeting,
        participant=participant,
        notification_type=notification_type,
        message=sms_body,
    )


def _invitation_email_context(meeting: Meeting) -> dict:
    from django.urls import reverse

    from core.models import SiteSettings

    site = SiteSettings.load()
    foundation = (
        getattr(site, "foundation_name_en", None)
        or getattr(site, "foundation_name_bn", None)
        or "Zarrah Foundation"
    )
    starts = _local_starts(meeting)
    agenda_titles = []
    for number, title_bn, title_en in meeting.agenda_items.order_by(
        "display_order", "number"
    ).values_list("number", "title_bn", "title_en")[:5]:
        title = (title_bn or title_en or "").strip()
        if title:
            agenda_titles.append(f"{number}. {title}")
    online_url = ""
    if meeting.mode in ("ONLINE", "HYBRID") and meeting.meeting_url:
        online_url = meeting.meeting_url
    try:
        rsvp_path = reverse("my-meeting-detail", args=[meeting.pk])
    except Exception:
        rsvp_path = f"/dashboard/my-meetings/{meeting.pk}/"
    site_url = (getattr(site, "website_url", "") or "").rstrip("/")
    rsvp_url = f"{site_url}{rsvp_path}" if site_url else rsvp_path
    return {
        "subject": str(_("Meeting invitation")),
        "foundation_name": foundation,
        "meeting_title": meeting.localized_title("en") or meeting.title_bn,
        "reference": meeting.reference_id,
        "meeting_type": meeting.meeting_type.localized_name("en"),
        "datetime_display": starts.strftime("%d %B %Y, %H:%M"),
        "timezone_name": meeting.timezone,
        "venue": _meeting_location_line(meeting),
        "mode": _meeting_mode_label(meeting),
        "online_url": online_url,
        "agenda_titles": agenda_titles,
        "rsvp_url": rsvp_url,
        "brand_primary": getattr(site, "brand_primary_color", None) or "#0B6B3A",
    }


@transaction.atomic
def notify_meeting_invitation(
    meeting: Meeting,
    participant: MeetingParticipant,
) -> None:
    """Invite a participant (ACCOUNT + EMAIL + SMS). Idempotent per channel."""
    from django.template.loader import render_to_string

    meeting = Meeting.objects.select_related("meeting_type").get(pk=meeting.pk)
    ctx = _invitation_email_context(meeting)
    plain = render_to_string("governance/email/meeting_invitation.txt", ctx)
    html = render_to_string("governance/email/meeting_invitation.html", ctx)
    account_body = _("You are invited to a meeting.") + "\n\n" + _meeting_message_body(
        meeting, include_online=True
    )
    _deliver_meeting_channels(
        meeting,
        participant,
        notification_type="MEETING_INVITATION",
        title=_("Meeting invitation"),
        message=account_body,
        email_subject=ctx["subject"],
        email_body=plain,
        email_html=html,
        link="/dashboard/my-meetings/",
        ntype=NotificationType.MEETING_INVITATION,
    )


@transaction.atomic
def notify_meeting_update(
    meeting: Meeting,
    participant: MeetingParticipant,
) -> None:
    body = _meeting_message_body(meeting, include_online=True)
    message = _("Meeting details have been updated.") + "\n\n" + body
    _deliver_meeting_channels(
        meeting,
        participant,
        notification_type="MEETING_UPDATED",
        title=_("Meeting updated"),
        message=message,
        link="/dashboard/my-meetings/",
        ntype=NotificationType.MEETING_UPDATED,
    )


@transaction.atomic
def notify_meeting_cancellation(
    meeting: Meeting,
    participant: MeetingParticipant,
) -> None:
    body = _meeting_message_body(meeting, include_online=False)
    message = _("A meeting has been cancelled.") + "\n\n" + body
    _deliver_meeting_channels(
        meeting,
        participant,
        notification_type="MEETING_CANCELLED",
        title=_("Meeting cancelled"),
        message=message,
        link="/dashboard/my-meetings/",
        ntype=NotificationType.MEETING_CANCELLED,
    )


@transaction.atomic
def notify_meeting_reminder(
    meeting: Meeting,
    participant: MeetingParticipant,
) -> None:
    """Reminder before meeting — idempotent (default 24h window via management command)."""
    body = _meeting_message_body(meeting, include_online=True)
    message = _("Reminder: upcoming meeting.") + "\n\n" + body
    _deliver_meeting_channels(
        meeting,
        participant,
        notification_type="MEETING_REMINDER",
        title=_("Meeting reminder"),
        message=message,
        link="/dashboard/my-meetings/",
        ntype=NotificationType.MEETING_REMINDER,
    )


def _resolution_key(notification_type: str, resolution, member_id, channel: str) -> str:
    return f"{notification_type}:{resolution.pk}:{member_id}:{channel}"


@transaction.atomic
def notify_resolution_awaiting_signature(resolution: Resolution, member) -> None:
    user = getattr(member, "user", None)
    key = _resolution_key(
        "RESOLUTION_AWAITING_SIGNATURE",
        resolution,
        member.pk,
        NotificationChannel.ACCOUNT,
    )
    if _log_exists(key):
        return
    title = _("Resolution awaiting your approval")
    message = _(
        "Please review and approve resolution %(rid)s (version %(ver)s)."
    ) % {
        "rid": resolution.resolution_id,
        "ver": getattr(resolution.current_version, "version_number", 1),
    }
    if user is None:
        _create_log(
            meeting=resolution.meeting,
            resolution=resolution,
            recipient_user=None,
            recipient_address="",
            notification_type="RESOLUTION_AWAITING_SIGNATURE",
            channel=NotificationChannel.ACCOUNT,
            idempotency_key=key,
            status=DeliveryStatus.SKIPPED,
            failure_reason="No user",
        )
        return
    notify(
        title=title,
        message=message,
        ntype=NotificationType.RESOLUTION_AWAITING_SIGNATURE,
        user=user,
        related_object=resolution,
        link="/dashboard/my-resolutions/",
    )
    _create_log(
        meeting=resolution.meeting,
        resolution=resolution,
        recipient_user=user,
        recipient_address=getattr(user, "email", "") or "",
        notification_type="RESOLUTION_AWAITING_SIGNATURE",
        channel=NotificationChannel.ACCOUNT,
        idempotency_key=key,
        status=DeliveryStatus.SENT,
    )


@transaction.atomic
def notify_resolution_fully_signed(resolution: Resolution, user) -> None:
    key = _resolution_key(
        "RESOLUTION_FULLY_SIGNED",
        resolution,
        getattr(user, "pk", "staff"),
        NotificationChannel.ACCOUNT,
    )
    if _log_exists(key) or user is None:
        return
    notify(
        title=_("Resolution fully signed"),
        message=_("Resolution %(rid)s is fully signed.")
        % {"rid": resolution.resolution_id},
        ntype=NotificationType.RESOLUTION_FULLY_SIGNED,
        user=user,
        related_object=resolution,
    )
    _create_log(
        meeting=resolution.meeting,
        resolution=resolution,
        recipient_user=user,
        recipient_address=getattr(user, "email", "") or "",
        notification_type="RESOLUTION_FULLY_SIGNED",
        channel=NotificationChannel.ACCOUNT,
        idempotency_key=key,
        status=DeliveryStatus.SENT,
    )


@transaction.atomic
def notify_resolution_finalized(resolution: Resolution, user) -> None:
    key = _resolution_key(
        "RESOLUTION_FINALIZED",
        resolution,
        getattr(user, "pk", "staff"),
        NotificationChannel.ACCOUNT,
    )
    if _log_exists(key) or user is None:
        return
    notify(
        title=_("Resolution finalized"),
        message=_("Resolution %(rid)s has been finalized.")
        % {"rid": resolution.resolution_id},
        ntype=NotificationType.RESOLUTION_FINALIZED,
        user=user,
        related_object=resolution,
    )
    _create_log(
        meeting=resolution.meeting,
        resolution=resolution,
        recipient_user=user,
        recipient_address=getattr(user, "email", "") or "",
        notification_type="RESOLUTION_FINALIZED",
        channel=NotificationChannel.ACCOUNT,
        idempotency_key=key,
        status=DeliveryStatus.SENT,
    )


@transaction.atomic
def notify_resolution_new_version(resolution: Resolution, member) -> None:
    user = getattr(member, "user", None)
    version = resolution.current_version
    ver_num = getattr(version, "version_number", 0)
    key = (
        f"RESOLUTION_NEW_VERSION:{resolution.pk}:{member.pk}:"
        f"{ver_num}:{NotificationChannel.ACCOUNT}"
    )
    if _log_exists(key) or user is None:
        return
    notify(
        title=_("New resolution version"),
        message=_("A new version of resolution %(rid)s is available for review.")
        % {"rid": resolution.resolution_id},
        ntype=NotificationType.RESOLUTION_NEW_VERSION,
        user=user,
        related_object=resolution,
        link="/dashboard/my-resolutions/",
    )
    _create_log(
        meeting=resolution.meeting,
        resolution=resolution,
        recipient_user=user,
        recipient_address=getattr(user, "email", "") or "",
        notification_type="RESOLUTION_NEW_VERSION",
        channel=NotificationChannel.ACCOUNT,
        idempotency_key=key,
        status=DeliveryStatus.SENT,
    )
