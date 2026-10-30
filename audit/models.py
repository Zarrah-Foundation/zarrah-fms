import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from accounts.models import Role


class ActivityLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="activities"
    )
    action = models.CharField(max_length=100)
    entity = models.CharField(max_length=100)
    entity_id = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, null=True, blank=True)
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)
    reason = models.TextField(
        blank=True,
        default="",
        help_text="Required for sensitive official field changes.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.action} - {self.entity}"


class LoginHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="login_history"
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, null=True, blank=True)
    logged_in_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["logged_in_at"]),
        ]
        verbose_name_plural = "login histories"

    def __str__(self):
        return f"{self.user} at {self.logged_in_at}"


class NotificationType(models.TextChoices):
    NEW_APPLICATION = "NEW_APPLICATION", "New Member Application"
    MEMBERSHIP_APPROVED = "MEMBERSHIP_APPROVED", "Membership Approved"
    MEMBERSHIP_REJECTED = "MEMBERSHIP_REJECTED", "Membership Rejected"
    NEW_DONATION = "NEW_DONATION", "New Donation"
    LARGE_DONATION = "LARGE_DONATION", "Large Donation"
    PAYMENT_FAILED = "PAYMENT_FAILED", "Payment Failed"
    FEE_DUE = "FEE_DUE", "Membership Fee Due"
    FEE_PAID = "FEE_PAID", "Membership Fee Paid"
    NEW_CONTACT_MESSAGE = "NEW_CONTACT_MESSAGE", "New Contact Message"
    VOLUNTEER_REGISTRATION = "VOLUNTEER_REGISTRATION", "Volunteer Registration"
    NEWS_PENDING_REVIEW = "NEWS_PENDING_REVIEW", "News Pending Review"
    FINANCE_ENTRY = "FINANCE_ENTRY", "Finance Entry Added"
    ROLE_ASSIGNED = "ROLE_ASSIGNED", "Role Assigned"
    USER_CREATED = "USER_CREATED", "User Created"
    SYSTEM_WARNING = "SYSTEM_WARNING", "System Warning"
    ELECTION_OPENED = "ELECTION_OPENED", "Election Opened"
    ELECTION_CLOSING_SOON = "ELECTION_CLOSING_SOON", "Election Closing Soon"
    ELECTION_RESULTS = "ELECTION_RESULTS", "Election Results"
    MEETING_INVITATION = "MEETING_INVITATION", "Meeting Invitation"
    MEETING_UPDATED = "MEETING_UPDATED", "Meeting Updated"
    MEETING_CANCELLED = "MEETING_CANCELLED", "Meeting Cancelled"
    MEETING_REMINDER = "MEETING_REMINDER", "Meeting Reminder"
    RESOLUTION_AWAITING_SIGNATURE = (
        "RESOLUTION_AWAITING_SIGNATURE",
        "Resolution Awaiting Signature",
    )
    RESOLUTION_FULLY_SIGNED = "RESOLUTION_FULLY_SIGNED", "Resolution Fully Signed"
    RESOLUTION_FINALIZED = "RESOLUTION_FINALIZED", "Resolution Finalized"
    RESOLUTION_NEW_VERSION = "RESOLUTION_NEW_VERSION", "Resolution New Version"
    GENERAL = "GENERAL", "General"


class NotificationPriority(models.TextChoices):
    LOW = "LOW", "Low"
    NORMAL = "NORMAL", "Normal"
    HIGH = "HIGH", "High"
    CRITICAL = "CRITICAL", "Critical"


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=300)
    message = models.TextField()
    type = models.CharField(max_length=50)
    priority = models.CharField(
        max_length=20,
        choices=NotificationPriority.choices,
        default=NotificationPriority.NORMAL,
        db_index=True,
    )
    icon = models.CharField(
        max_length=80,
        blank=True,
        default="",
        help_text="Bootstrap Icons class; auto-derived from type when blank.",
    )
    link = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="Optional target URL opened when the notification is clicked.",
    )
    target_role = models.CharField(
        max_length=50, choices=Role.choices, null=True, blank=True
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    # Optional related object ("Related Object" in the spec).
    content_type = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, null=True, blank=True
    )
    object_id = models.CharField(max_length=64, null=True, blank=True)
    related_object = GenericForeignKey("content_type", "object_id")

    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["user"]),
            models.Index(fields=["target_role"]),
            models.Index(fields=["is_read"]),
            models.Index(fields=["priority"]),
        ]

    def __str__(self):
        return self.title

    def mark_read(self):
        if not self.is_read:
            from django.utils import timezone

            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])


class NotificationRead(models.Model):
    """Per-user read receipt for role-broadcast notifications (user=NULL rows)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.ForeignKey(
        Notification, on_delete=models.CASCADE, related_name="reads"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_reads",
    )
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["notification", "user"], name="uniq_notification_read_per_user"
            )
        ]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["notification", "user"]),
        ]

    def __str__(self):
        return f"Read {self.notification_id} by {self.user_id}"
