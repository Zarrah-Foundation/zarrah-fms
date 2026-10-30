import hashlib
import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class VoteStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    ACTIVE = "ACTIVE", "Active"
    CLOSED = "CLOSED", "Closed"


class Vote(models.Model):
    """
    Deprecated legacy simple poll.

    Prefer :class:`Election` for new voting. Product UI no longer writes here.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=300)
    description = models.TextField(null=True, blank=True)
    options = models.JSONField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=VoteStatus.choices)
    created_by = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class VoteRecord(models.Model):
    """Deprecated legacy ballot linking user to choice (not secret)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vote = models.ForeignKey(Vote, on_delete=models.CASCADE, related_name="records")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    option_id = models.CharField(max_length=100)
    weight = models.IntegerField(default=1)
    vote_hash = models.CharField(max_length=64)

    class Meta:
        unique_together = [("vote", "user")]

    def save(self, *args, **kwargs):
        self.vote_hash = hashlib.sha256(
            f"{self.vote_id}:{self.user_id}:{self.option_id}:{settings.SECRET_KEY}".encode()
        ).hexdigest()
        super().save(*args, **kwargs)

    def verify_hash(self):
        expected = hashlib.sha256(
            f"{self.vote_id}:{self.user_id}:{self.option_id}:{settings.SECRET_KEY}".encode()
        ).hexdigest()
        return self.vote_hash == expected

    def __str__(self):
        return f"{self.user} -> {self.option_id}"


# ---------------------------------------------------------------------------
# Production election engine
# ---------------------------------------------------------------------------


class ElectionType(models.TextChoices):
    GENERAL = "GENERAL", _("General")
    ADVISORY_COUNCIL = "ADVISORY_COUNCIL", _("Advisory Council")
    YES_NO = "YES_NO", _("Yes / No")
    MULTI_CHOICE = "MULTI_CHOICE", _("Multi Choice")


class ElectionStatus(models.TextChoices):
    DRAFT = "DRAFT", _("Draft")
    SCHEDULED = "SCHEDULED", _("Scheduled")
    OPEN = "OPEN", _("Open")
    CLOSED = "CLOSED", _("Closed")
    FINALIZED = "FINALIZED", _("Finalized")
    CANCELLED = "CANCELLED", _("Cancelled")


class EligibilityMode(models.TextChoices):
    ALL_APPROVED = "ALL_APPROVED", _("All approved members")
    BY_MEMBERSHIP_TYPES = "BY_MEMBERSHIP_TYPES", _("Selected membership types")
    BY_GROUPS = "BY_GROUPS", _("Selected member groups")


class Election(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title_bn = models.CharField(max_length=300, blank=True, default="")
    title_en = models.CharField(max_length=300)
    description_bn = models.TextField(blank=True, default="")
    description_en = models.TextField(blank=True, default="")
    election_type = models.CharField(
        max_length=30,
        choices=ElectionType.choices,
        default=ElectionType.GENERAL,
    )
    status = models.CharField(
        max_length=20,
        choices=ElectionStatus.choices,
        default=ElectionStatus.DRAFT,
        db_index=True,
    )
    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    window_hours = models.PositiveIntegerField(
        default=48,
        help_text=_("Default open window in hours (Advisory Council uses 48)."),
    )
    total_seats = models.PositiveIntegerField(
        default=1,
        help_text=_(
            "Seats to fill for ranked elections. Also the max rank count (N) for Borda scoring."
        ),
    )
    quorum_numerator = models.PositiveIntegerField(default=2)
    quorum_denominator = models.PositiveIntegerField(default=3)
    allow_self_vote = models.BooleanField(
        default=False,
        help_text=_("When false, voters cannot rank/select themselves as a candidate."),
    )
    auto_candidates = models.BooleanField(
        default=False,
        help_text=_(
            "When true (default for Advisory Council), every eligible APPROVED member "
            "becomes a candidate at OPEN. No self-nomination."
        ),
    )
    eligibility_mode = models.CharField(
        max_length=30,
        choices=EligibilityMode.choices,
        default=EligibilityMode.ALL_APPROVED,
        db_index=True,
    )
    # Legacy flag — kept for migrations; eligibility_mode is authoritative.
    eligible_approved_members_only = models.BooleanField(
        default=True,
        help_text=_("Legacy: prefer eligibility_mode=ALL_APPROVED."),
    )
    membership_types = models.ManyToManyField(
        "members.MembershipType",
        blank=True,
        related_name="elections",
        help_text=_("Used when eligibility mode is BY_MEMBERSHIP_TYPES."),
    )
    member_groups = models.ManyToManyField(
        "members.MemberGroup",
        blank=True,
        related_name="elections",
        help_text=_("Used when eligibility mode is BY_GROUPS."),
    )
    # MULTI_CHOICE configuration
    allow_multiple_selections = models.BooleanField(
        default=False,
        help_text=_("For MULTI_CHOICE: allow selecting more than one option."),
    )
    max_selections = models.PositiveIntegerField(
        default=1,
        help_text=_("For MULTI_CHOICE: maximum options a voter may select."),
    )
    results_published = models.BooleanField(default=False)
    electorate_frozen_at = models.DateTimeField(null=True, blank=True)
    candidates_locked = models.BooleanField(
        default=False,
        help_text=_("Set true after first ballot; prevents roster changes."),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_elections",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Election")
        verbose_name_plural = _("Elections")

    def __str__(self):
        return self.title_en or self.title_bn

    def localized_title(self, lang=None):
        from django.utils.translation import get_language

        lang = lang or get_language() or "en"
        if str(lang).startswith("bn") and self.title_bn:
            return self.title_bn
        return self.title_en or self.title_bn

    def localized_description(self, lang=None):
        from django.utils.translation import get_language

        lang = lang or get_language() or "en"
        if str(lang).startswith("bn") and self.description_bn:
            return self.description_bn
        return self.description_en or self.description_bn

    @property
    def quorum_ratio(self) -> float:
        if not self.quorum_denominator:
            return 2.0 / 3.0
        return self.quorum_numerator / self.quorum_denominator

    @property
    def is_ranked(self) -> bool:
        return self.election_type in (
            ElectionType.ADVISORY_COUNCIL,
            ElectionType.GENERAL,
        )

    @property
    def is_choice(self) -> bool:
        return self.election_type in (ElectionType.YES_NO, ElectionType.MULTI_CHOICE)

    def configuration_locked(self) -> bool:
        """Ballot structure / eligibility locked once open with freeze or ballots exist."""
        if self.status in (
            ElectionStatus.OPEN,
            ElectionStatus.CLOSED,
            ElectionStatus.FINALIZED,
            ElectionStatus.CANCELLED,
        ):
            return True
        if self.electorate_frozen_at:
            return True
        if self.ballots.exists():
            return True
        return False


class ElectionElectorate(models.Model):
    """Immutable eligible voter snapshot frozen at OPEN."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    election = models.ForeignKey(
        Election, on_delete=models.CASCADE, related_name="electorate"
    )
    member = models.ForeignKey(
        "members.Member",
        on_delete=models.CASCADE,
        related_name="election_electorate_rows",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="election_electorate_rows",
    )
    frozen_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["election", "member"],
                name="uniq_election_electorate_member",
            ),
            models.UniqueConstraint(
                fields=["election", "user"],
                name="uniq_election_electorate_user",
            ),
        ]
        indexes = [
            models.Index(fields=["election", "user"]),
            models.Index(fields=["election", "member"]),
        ]
        verbose_name = _("Election electorate")
        verbose_name_plural = _("Election electorate")

    def __str__(self):
        return f"{self.user_id} @ {self.election_id}"


class ElectionCandidate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    election = models.ForeignKey(
        Election, on_delete=models.CASCADE, related_name="candidates"
    )
    member = models.ForeignKey(
        "members.Member",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="election_candidacies",
    )
    name = models.CharField(max_length=200)
    is_founder_candidate = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["election", "member"],
                name="uniq_election_candidate_member",
                condition=models.Q(member__isnull=False),
            )
        ]
        verbose_name = _("Election Candidate")
        verbose_name_plural = _("Election Candidates")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.member_id:
            from voting.services import is_founder_member

            self.is_founder_candidate = is_founder_member(self.member)
            if not self.name:
                self.name = f"{self.member.first_name} {self.member.last_name}".strip()
        super().save(*args, **kwargs)


class ElectionQuestion(models.Model):
    """Question for YES_NO / MULTI_CHOICE elections."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    election = models.ForeignKey(
        Election, on_delete=models.CASCADE, related_name="questions"
    )
    question_bn = models.CharField(max_length=500, blank=True, default="")
    question_en = models.CharField(max_length=500)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "question_en"]

    def __str__(self):
        return self.question_en

    def localized_question(self, lang=None):
        from django.utils.translation import get_language

        lang = lang or get_language() or "en"
        if str(lang).startswith("bn") and self.question_bn:
            return self.question_bn
        return self.question_en or self.question_bn


class ElectionOption(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(
        ElectionQuestion, on_delete=models.CASCADE, related_name="options"
    )
    label_bn = models.CharField(max_length=200, blank=True, default="")
    label_en = models.CharField(max_length=200)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "label_en"]

    def __str__(self):
        return self.label_en

    def localized_label(self, lang=None):
        from django.utils.translation import get_language

        lang = lang or get_language() or "en"
        if str(lang).startswith("bn") and self.label_bn:
            return self.label_bn
        return self.label_en or self.label_bn


class ElectionParticipation(models.Model):
    """Tracks WHO voted without storing their choices (ballot secrecy)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    election = models.ForeignKey(
        Election, on_delete=models.CASCADE, related_name="participations"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="election_participations",
    )
    voted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["election", "user"],
                name="uniq_election_participation_user",
            )
        ]
        indexes = [
            models.Index(fields=["election", "voted_at"]),
        ]
        verbose_name = _("Election Participation")
        verbose_name_plural = _("Election Participations")

    def __str__(self):
        return f"{self.user_id} @ {self.election_id}"


class ElectionBallot(models.Model):
    """Anonymous ballot — no user FK (secrecy)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    election = models.ForeignKey(
        Election, on_delete=models.CASCADE, related_name="ballots"
    )
    ballot_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["election", "submitted_at"]),
        ]
        verbose_name = _("Election Ballot")
        verbose_name_plural = _("Election Ballots")

    def __str__(self):
        return str(self.ballot_token)


class ElectionBallotPreference(models.Model):
    """Ranked preference on an anonymous ballot."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ballot = models.ForeignKey(
        ElectionBallot, on_delete=models.CASCADE, related_name="preferences"
    )
    candidate = models.ForeignKey(
        ElectionCandidate, on_delete=models.CASCADE, related_name="preferences"
    )
    rank = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["ballot", "rank"],
                name="uniq_ballot_rank",
            ),
            models.UniqueConstraint(
                fields=["ballot", "candidate"],
                name="uniq_ballot_candidate",
            ),
        ]
        ordering = ["rank"]
        verbose_name = _("Ballot Preference")
        verbose_name_plural = _("Ballot Preferences")

    def __str__(self):
        return f"rank={self.rank} candidate={self.candidate_id}"


class ElectionBallotChoice(models.Model):
    """Selected option(s) on an anonymous YES_NO / MULTI_CHOICE ballot."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ballot = models.ForeignKey(
        ElectionBallot, on_delete=models.CASCADE, related_name="choices"
    )
    option = models.ForeignKey(
        ElectionOption, on_delete=models.CASCADE, related_name="ballot_choices"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["ballot", "option"],
                name="uniq_ballot_option",
            ),
        ]
        verbose_name = _("Ballot Choice")
        verbose_name_plural = _("Ballot Choices")

    def __str__(self):
        return f"option={self.option_id}"


class ElectionAdminAction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    election = models.ForeignKey(
        Election, on_delete=models.CASCADE, related_name="admin_actions"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="election_admin_actions",
    )
    action = models.CharField(max_length=50)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Election Admin Action")
        verbose_name_plural = _("Election Admin Actions")

    def __str__(self):
        return f"{self.action} @ {self.election_id}"
