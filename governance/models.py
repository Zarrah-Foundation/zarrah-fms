"""Governance meetings, resolutions, signatures, and public sharing models."""

from __future__ import annotations

import math
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import get_language

from core.validators import ImageFileValidator, MaxFileSizeValidator


class EligibilityMode(models.TextChoices):
    LINKED_GROUPS = "LINKED_GROUPS", "Linked member groups"
    ALL_APPROVED = "ALL_APPROVED", "All approved members"


class MeetingStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SCHEDULED = "SCHEDULED", "Scheduled"
    INVITATIONS_SENT = "INVITATIONS_SENT", "Invitations sent"
    IN_PROGRESS = "IN_PROGRESS", "In progress"
    COMPLETED = "COMPLETED", "Completed"
    FINALIZED = "FINALIZED", "Finalized"
    ARCHIVED = "ARCHIVED", "Archived"
    CANCELLED = "CANCELLED", "Cancelled"


class MeetingMode(models.TextChoices):
    OFFLINE = "OFFLINE", "Offline"
    ONLINE = "ONLINE", "Online"
    HYBRID = "HYBRID", "Hybrid"


class ParticipantStatus(models.TextChoices):
    INVITED = "INVITED", "Invited"
    ACCEPTED = "ACCEPTED", "Accepted"
    DECLINED = "DECLINED", "Declined"
    ATTENDED = "ATTENDED", "Present"
    ABSENT = "ABSENT", "Absent"


class GuestStatus(models.TextChoices):
    INVITED = "INVITED", "Invited"
    ACCEPTED = "ACCEPTED", "Accepted"
    DECLINED = "DECLINED", "Declined"
    PRESENT = "PRESENT", "Present"
    ABSENT = "ABSENT", "Absent"


class AgendaItemStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    DISCUSSED = "DISCUSSED", "Discussed"
    DEFERRED = "DEFERRED", "Deferred"
    CLOSED = "CLOSED", "Closed"


class ResolutionStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    READY_FOR_SIGNING = "READY_FOR_SIGNING", "Ready for signing"
    PARTIALLY_SIGNED = "PARTIALLY_SIGNED", "Partially signed"
    FULLY_SIGNED = "FULLY_SIGNED", "Fully signed"
    FINALIZED = "FINALIZED", "Finalized"
    WITHDRAWN = "WITHDRAWN", "Withdrawn"


class NotificationChannel(models.TextChoices):
    ACCOUNT = "ACCOUNT", "Account"
    EMAIL = "EMAIL", "Email"
    SMS = "SMS", "SMS"


class DeliveryStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    SENT = "SENT", "Sent"
    FAILED = "FAILED", "Failed"
    SKIPPED = "SKIPPED", "Skipped"


def _prefer_bn(lang: str | None = None) -> bool:
    code = (lang or get_language() or "bn").lower()
    return code.startswith("bn")


class MeetingType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=64, unique=True)
    name_en = models.CharField(max_length=150)
    name_bn = models.CharField(max_length=150, blank=True, default="")
    description_en = models.TextField(blank=True, default="")
    description_bn = models.TextField(blank=True, default="")
    quorum_numerator = models.PositiveSmallIntegerField(default=2)
    quorum_denominator = models.PositiveSmallIntegerField(default=3)
    eligibility_mode = models.CharField(
        max_length=20,
        choices=EligibilityMode.choices,
        default=EligibilityMode.LINKED_GROUPS,
    )
    reminder_hours_before = models.PositiveIntegerField(
        default=24,
        help_text="Default reminder lead time in hours (0 disables type default).",
    )
    reminder_enabled = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    eligibility_groups = models.ManyToManyField(
        "members.MemberGroup",
        blank=True,
        related_name="meeting_types",
    )

    class Meta:
        ordering = ["display_order", "name_en"]

    def __str__(self) -> str:
        return self.name_en or self.slug

    def required_quorum(self, eligible_count: int) -> int:
        """Constitutional quorum: ceil(eligible * numerator / denominator)."""
        n = int(eligible_count or 0)
        if n <= 0:
            return 0
        den = int(self.quorum_denominator or 0)
        if den <= 0:
            return 0
        num = int(self.quorum_numerator or 0)
        return int(math.ceil(n * num / den))

    def localized_name(self, lang: str | None = None) -> str:
        if _prefer_bn(lang):
            return (self.name_bn or self.name_en or self.slug).strip()
        return (self.name_en or self.name_bn or self.slug).strip()


class Meeting(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference_id = models.CharField(max_length=40, unique=True, editable=False)
    meeting_type = models.ForeignKey(
        MeetingType,
        on_delete=models.PROTECT,
        related_name="meetings",
    )
    title_bn = models.CharField(max_length=300)
    title_en = models.CharField(max_length=300, blank=True, default="")
    description_bn = models.TextField(blank=True, default="")
    description_en = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=MeetingStatus.choices,
        default=MeetingStatus.DRAFT,
        db_index=True,
    )
    mode = models.CharField(
        max_length=20,
        choices=MeetingMode.choices,
        default=MeetingMode.OFFLINE,
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(blank=True, null=True)
    timezone = models.CharField(max_length=64, default="Asia/Dhaka")
    venue_name = models.CharField(max_length=200, blank=True, default="")
    venue_address = models.TextField(blank=True, default="")
    room_details = models.CharField(max_length=200, blank=True, default="")
    online_platform = models.CharField(max_length=100, blank=True, default="")
    meeting_url = models.URLField(blank=True, default="")
    meeting_id_code = models.CharField(max_length=100, blank=True, default="")
    meeting_password = models.CharField(max_length=100, blank=True, default="")
    joining_instructions = models.TextField(blank=True, default="")
    reminder_enabled = models.BooleanField(default=True)
    reminder_hours_before = models.PositiveIntegerField(blank=True, null=True)
    eligible_frozen_at = models.DateTimeField(blank=True, null=True)
    participants_frozen_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_meetings",
    )

    class Meta:
        ordering = ["-starts_at", "-created_at"]
        indexes = [
            models.Index(fields=["status", "starts_at"]),
        ]

    def __str__(self) -> str:
        return self.reference_id

    def localized_title(self, lang: str | None = None) -> str:
        if _prefer_bn(lang):
            return (self.title_bn or self.title_en).strip()
        return (self.title_en or self.title_bn).strip()

    @property
    def effective_reminder_hours(self) -> int:
        if self.reminder_hours_before is not None:
            return int(self.reminder_hours_before)
        return int(self.meeting_type.reminder_hours_before or 0)


class MeetingEligibleMember(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    meeting = models.ForeignKey(
        Meeting,
        on_delete=models.CASCADE,
        related_name="eligible_members",
    )
    member = models.ForeignKey(
        "members.Member",
        on_delete=models.CASCADE,
        related_name="meeting_eligibilities",
    )
    frozen_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("meeting", "member"),
                name="uniq_meeting_eligible_member",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.meeting_id}:{self.member_id}"


class MeetingParticipant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    meeting = models.ForeignKey(
        Meeting,
        on_delete=models.CASCADE,
        related_name="participants",
    )
    member = models.ForeignKey(
        "members.Member",
        on_delete=models.CASCADE,
        related_name="meeting_participations",
    )
    source_group = models.ForeignKey(
        "members.MemberGroup",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    status = models.CharField(
        max_length=20,
        choices=ParticipantStatus.choices,
        default=ParticipantStatus.INVITED,
        db_index=True,
    )
    invited_at = models.DateTimeField(blank=True, null=True)
    responded_at = models.DateTimeField(blank=True, null=True)
    attendance_marked_at = models.DateTimeField(blank=True, null=True)
    attendance_marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("meeting", "member"),
                name="uniq_meeting_participant",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.meeting_id}:{self.member_id}:{self.status}"


class MeetingGuest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    meeting = models.ForeignKey(
        Meeting,
        on_delete=models.CASCADE,
        related_name="guests",
    )
    full_name = models.CharField(max_length=200)
    organization = models.CharField(max_length=200, blank=True, default="")
    designation = models.CharField(max_length=150, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=30, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=GuestStatus.choices,
        default=GuestStatus.INVITED,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.full_name


class MeetingAgendaItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    meeting = models.ForeignKey(
        Meeting,
        on_delete=models.CASCADE,
        related_name="agenda_items",
    )
    number = models.PositiveIntegerField(default=1)
    title_bn = models.CharField(max_length=300)
    title_en = models.CharField(max_length=300, blank=True, default="")
    description_bn = models.TextField(blank=True, default="")
    description_en = models.TextField(blank=True, default="")
    presenter_name = models.CharField(max_length=200, blank=True, default="")
    presenter_member = models.ForeignKey(
        "members.Member",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    supporting_document = models.FileField(
        upload_to="meetings/agenda/",
        blank=True,
        null=True,
        validators=[MaxFileSizeValidator(10)],
    )
    display_order = models.PositiveIntegerField(default=0, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=AgendaItemStatus.choices,
        default=AgendaItemStatus.PENDING,
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=("meeting", "number"),
                name="uniq_meeting_agenda_number",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.number}. {self.title_bn}"


class MeetingProceeding(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    meeting = models.OneToOneField(
        Meeting,
        on_delete=models.CASCADE,
        related_name="proceeding",
    )
    content_bn = models.TextField(blank=True, default="")
    content_en = models.TextField(blank=True, default="")
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Proceedings {self.meeting_id}"


class Resolution(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resolution_id = models.CharField(max_length=40, unique=True, editable=False)
    meeting = models.ForeignKey(
        Meeting,
        on_delete=models.CASCADE,
        related_name="resolutions",
    )
    agenda_item = models.ForeignKey(
        MeetingAgendaItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolutions",
    )
    title_bn = models.CharField(max_length=300)
    title_en = models.CharField(max_length=300, blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=ResolutionStatus.choices,
        default=ResolutionStatus.DRAFT,
        db_index=True,
    )
    current_version = models.ForeignKey(
        "ResolutionVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    finalized_at = models.DateTimeField(blank=True, null=True)
    finalized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_resolutions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.resolution_id


class ResolutionVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resolution = models.ForeignKey(
        Resolution,
        on_delete=models.CASCADE,
        related_name="versions",
    )
    version_number = models.PositiveIntegerField(default=1)
    title_bn = models.CharField(max_length=300)
    title_en = models.CharField(max_length=300, blank=True, default="")
    content_bn = models.TextField()
    content_en = models.TextField(blank=True, default="")
    decision_bn = models.TextField(blank=True, default="")
    decision_en = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="")
    change_reason = models.CharField(max_length=300, blank=True, default="")
    is_frozen = models.BooleanField(default=False)
    previous_version = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="next_versions",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version_number"]
        constraints = [
            models.UniqueConstraint(
                fields=("resolution", "version_number"),
                name="uniq_resolution_version_number",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.resolution_id} v{self.version_number}"


class ResolutionSigner(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resolution = models.ForeignKey(
        Resolution,
        on_delete=models.CASCADE,
        related_name="signers",
    )
    version = models.ForeignKey(
        ResolutionVersion,
        on_delete=models.CASCADE,
        related_name="signers",
    )
    member = models.ForeignKey(
        "members.Member",
        on_delete=models.CASCADE,
        related_name="resolution_sign_requests",
    )
    selected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    selected_at = models.DateTimeField(default=timezone.now)
    is_required = models.BooleanField(default=True)
    signed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("version", "member"),
                name="uniq_resolution_version_signer",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.resolution_id}:{self.member_id}"


class ResolutionSignature(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    signer = models.OneToOneField(
        ResolutionSigner,
        on_delete=models.PROTECT,
        related_name="signature",
    )
    version = models.ForeignKey(
        ResolutionVersion,
        on_delete=models.PROTECT,
        related_name="signatures",
    )
    member = models.ForeignKey(
        "members.Member",
        on_delete=models.PROTECT,
        related_name="resolution_signatures",
    )
    signer_name = models.CharField(max_length=200)
    signer_designation = models.CharField(max_length=150, blank=True, default="")
    member_id_snapshot = models.CharField(max_length=40)
    signature_image = models.ImageField(
        upload_to="resolutions/signatures/",
        validators=[MaxFileSizeValidator(2), ImageFileValidator()],
    )
    signed_at = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=300, blank=True, default="")
    confirmation_text = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Historical signature snapshots are immutable once persisted.
        if self._state.adding:
            return super().save(*args, **kwargs)
        raise ValueError(
            "Resolution signatures cannot be edited, replaced, or withdrawn."
        )

    def delete(self, *args, **kwargs):
        raise ValueError(
            "Resolution signatures cannot be deleted or withdrawn."
        )

    def __str__(self) -> str:
        return f"{self.member_id_snapshot} @ {self.signed_at}"


class ResolutionPublicShare(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resolution = models.OneToOneField(
        Resolution,
        on_delete=models.CASCADE,
        related_name="public_share",
    )
    token = models.CharField(max_length=64, unique=True, db_index=True)
    is_enabled = models.BooleanField(default=False)
    password_hash = models.CharField(max_length=128, blank=True, default="")
    expires_at = models.DateTimeField(blank=True, null=True)
    revoked_at = models.DateTimeField(blank=True, null=True)
    show_signer_details = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Share {self.resolution_id}"

    @property
    def requires_password(self) -> bool:
        return bool(self.password_hash)

    def is_accessible(self) -> bool:
        if not self.is_enabled or self.revoked_at is not None:
            return False
        if self.expires_at is not None and self.expires_at <= timezone.now():
            return False
        return True


class MeetingNotificationLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    meeting = models.ForeignKey(
        Meeting,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notification_logs",
    )
    resolution = models.ForeignKey(
        Resolution,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notification_logs",
    )
    recipient_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    recipient_address = models.CharField(max_length=255, blank=True, default="")
    notification_type = models.CharField(max_length=50, db_index=True)
    channel = models.CharField(max_length=20, choices=NotificationChannel.choices)
    idempotency_key = models.CharField(max_length=255, unique=True)
    status = models.CharField(
        max_length=20,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.PENDING,
    )
    failure_reason = models.TextField(blank=True, default="")
    sent_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["notification_type", "channel"]),
        ]

    def __str__(self) -> str:
        return self.idempotency_key


class SequenceCounter(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(max_length=64, db_index=True)
    year = models.PositiveIntegerField(default=0)
    month = models.PositiveSmallIntegerField(default=0)
    last_value = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("key", "year", "month"),
                name="uniq_sequence_counter_key_period",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.key}:{self.year}-{self.month}={self.last_value}"
