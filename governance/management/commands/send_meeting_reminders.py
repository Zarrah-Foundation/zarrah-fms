"""Send meeting reminder notifications (cron-compatible, idempotent)."""

from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from governance.models import Meeting, MeetingStatus, ParticipantStatus
from governance.notifications import notify_meeting_reminder


class Command(BaseCommand):
    help = (
        "Send meeting reminders to invited/accepted participants. "
        "Default lead time is 24 hours; overridable per meeting or meeting type. "
        "Idempotent via MeetingNotificationLog keys."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--hours",
            type=int,
            default=None,
            help="Override reminder lead time in hours (default: per meeting/type).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List meetings that would receive reminders without sending.",
        )

    def handle(self, *args, **options):
        override_hours = options.get("hours")
        dry_run = options.get("dry_run", False)
        now = timezone.now()

        qs = Meeting.objects.filter(
            status__in=(
                MeetingStatus.SCHEDULED,
                MeetingStatus.INVITATIONS_SENT,
            ),
            reminder_enabled=True,
        ).select_related("meeting_type")

        sent = skipped = 0
        for meeting in qs:
            hours = override_hours
            if hours is None:
                if not meeting.meeting_type.reminder_enabled:
                    continue
                hours = meeting.effective_reminder_hours
            if not hours or hours <= 0:
                continue

            window_start = meeting.starts_at - timedelta(hours=hours)
            window_end = window_start + timedelta(hours=1)
            if not (window_start <= now < window_end):
                continue

            participants = meeting.participants.filter(
                status__in=(ParticipantStatus.INVITED, ParticipantStatus.ACCEPTED)
            ).select_related("member__user")

            for participant in participants:
                if dry_run:
                    self.stdout.write(
                        f"Would remind {participant.member.member_id} "
                        f"for {meeting.reference_id}"
                    )
                    sent += 1
                    continue
                notify_meeting_reminder(meeting, participant)
                sent += 1

        action = "Would send" if dry_run else "Sent"
        self.stdout.write(
            self.style.SUCCESS(f"{action} {sent} reminder(s); skipped {skipped}.")
        )
