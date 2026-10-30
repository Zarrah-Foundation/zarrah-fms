"""Meeting notification idempotency via MeetingNotificationLog keys."""

from unittest.mock import patch

from django.test import TestCase

from governance.models import DeliveryStatus, MeetingNotificationLog, NotificationChannel
from governance.notifications import notify_meeting_invitation
from governance.services.participants import add_participants_from_members
from governance.tests.helpers import create_approved_member, create_meeting


class MeetingNotificationIdempotencyTests(TestCase):
    def setUp(self):
        self.meeting = create_meeting()
        self.user, self.member = create_approved_member(1)
        self.participant = add_participants_from_members(
            self.meeting, [self.member]
        )[0]

    @patch("governance.notifications.notify")
    def test_duplicate_invitation_does_not_double_send_account_channel(self, mock_notify):
        notify_meeting_invitation(self.meeting, self.participant)
        notify_meeting_invitation(self.meeting, self.participant)

        self.assertEqual(mock_notify.call_count, 1)

        acct_key = f"MEETING_INVITATION:{self.meeting.pk}:{self.participant.pk}:ACCOUNT"
        logs = MeetingNotificationLog.objects.filter(idempotency_key=acct_key)
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first().channel, NotificationChannel.ACCOUNT)
        self.assertEqual(logs.first().status, DeliveryStatus.SENT)

    @patch("governance.notifications.notify")
    def test_account_log_prevents_resend_even_if_first_failed(self, mock_notify):
        acct_key = f"MEETING_INVITATION:{self.meeting.pk}:{self.participant.pk}:ACCOUNT"
        MeetingNotificationLog.objects.create(
            meeting=self.meeting,
            recipient_user=self.user,
            notification_type="MEETING_INVITATION",
            channel=NotificationChannel.ACCOUNT,
            idempotency_key=acct_key,
            status=DeliveryStatus.SENT,
        )

        notify_meeting_invitation(self.meeting, self.participant)
        mock_notify.assert_not_called()
        self.assertEqual(
            MeetingNotificationLog.objects.filter(idempotency_key=acct_key).count(),
            1,
        )

    @patch("governance.notifications.notify")
    def test_idempotency_key_is_stable_per_participant(self, mock_notify):
        notify_meeting_invitation(self.meeting, self.participant)
        notify_meeting_invitation(self.meeting, self.participant)
        expected = f"MEETING_INVITATION:{self.meeting.pk}:{self.participant.pk}:ACCOUNT"
        self.assertTrue(
            MeetingNotificationLog.objects.filter(idempotency_key=expected).exists()
        )
        self.assertEqual(mock_notify.call_count, 1)
