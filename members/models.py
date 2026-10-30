import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.choices import DonationStatus, PaymentMethod
from core.validators import (
    ALLOWED_CONTENT_TYPES,
    ALLOWED_EXTENSIONS,
    FileTypeValidator,
    ImageFileValidator,
    MaxFileSizeValidator,
)


class MemberStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    SUSPENDED = "SUSPENDED", "Suspended"


class ApplicationStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"


class IdentityType(models.TextChoices):
    NID = "NID", "NID"
    BIRTH_REGISTRATION = "BIRTH_REGISTRATION", "Birth Registration"
    PASSPORT = "PASSPORT", "Passport"


class Gender(models.TextChoices):
    MALE = "MALE", _("Male")
    FEMALE = "FEMALE", _("Female")
    OTHER = "OTHER", _("Hijra")


class MaritalStatus(models.TextChoices):
    SINGLE = "SINGLE", _("Single")
    MARRIED = "MARRIED", _("Married")
    DIVORCED = "DIVORCED", _("Divorced")
    WIDOWED = "WIDOWED", _("Widowed")


class BloodGroup(models.TextChoices):
    A_POS = "A+", "A+"
    A_NEG = "A-", "A-"
    B_POS = "B+", "B+"
    B_NEG = "B-", "B-"
    AB_POS = "AB+", "AB+"
    AB_NEG = "AB-", "AB-"
    O_POS = "O+", "O+"
    O_NEG = "O-", "O-"


class Religion(models.TextChoices):
    ISLAM = "ISLAM", _("Islam")
    HINDU = "HINDU", _("Hindu")
    CHRISTIAN = "CHRISTIAN", _("Christian")
    BUDDHIST = "BUDDHIST", _("Buddhist")
    OTHER = "OTHER", _("Other")


class EducationType(models.TextChoices):
    GENERAL = "GENERAL", _("General Education")
    QAUMI = "QAUMI", _("Qaumi Madrasah")
    ALIA = "ALIA", _("Alia Madrasah")
    TECHNICAL = "TECHNICAL", _("Technical / Vocational")


class EducationStatus(models.TextChoices):
    CURRENT = "CURRENT", _("Currently Studying")
    COMPLETED = "COMPLETED", _("Completed")


class MembershipType(models.Model):
    """CMS-managed membership category (e.g. General, Life, Founder)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name_bn = models.CharField(max_length=150, verbose_name=_("Name (Bangla)"))
    name_en = models.CharField(max_length=150, verbose_name=_("Name (English)"))
    slug = models.SlugField(unique=True)
    description_bn = models.TextField(blank=True, default="")
    description_en = models.TextField(blank=True, default="")
    fee_amount = models.FloatField(default=0, help_text=_("Default annual/one-time fee in BDT."))
    is_lifetime = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "name_en"]

    def __str__(self):
        return self.name_en

    def label(self, lang="en"):
        return self.name_bn if lang == "bn" else self.name_en


class MemberGroup(models.Model):
    """Reusable named cohort of members for election eligibility and other targeting."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name_bn = models.CharField(max_length=150, blank=True, default="")
    name_en = models.CharField(max_length=150)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name_en"]
        verbose_name = _("Member group")
        verbose_name_plural = _("Member groups")

    def __str__(self):
        return self.name_en


class MemberGroupMembership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(
        MemberGroup, on_delete=models.CASCADE, related_name="memberships"
    )
    member = models.ForeignKey(
        "Member", on_delete=models.CASCADE, related_name="group_memberships"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["group", "member"],
                name="uniq_member_group_membership",
            )
        ]
        indexes = [
            models.Index(fields=["group", "member"]),
        ]
        verbose_name = _("Member group membership")
        verbose_name_plural = _("Member group memberships")

    def __str__(self):
        return f"{self.member_id} ∈ {self.group_id}"


class Member(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member_id = models.CharField(max_length=50, unique=True)
    membership_type = models.ForeignKey(
        "MembershipType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="member_profile"
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    gender = models.CharField(max_length=10, choices=Gender.choices, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    blood_group = models.CharField(max_length=10, choices=BloodGroup.choices, null=True, blank=True)
    nid_number = models.CharField(max_length=50, null=True, blank=True)
    present_address = models.TextField()
    permanent_address = models.TextField(null=True, blank=True)
    district = models.CharField(max_length=100)
    upazila = models.CharField(max_length=100, null=True, blank=True)
    occupation = models.CharField(max_length=200, null=True, blank=True)
    organization = models.CharField(max_length=200, null=True, blank=True)
    education = models.CharField(max_length=200, null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=MemberStatus.choices, default=MemberStatus.PENDING
    )
    is_founder = models.BooleanField(
        default=False,
        verbose_name=_("Founder"),
        help_text=_("Marks this member as a foundation founder for advisory elections."),
    )
    joined_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_members",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    emergency_name = models.CharField(max_length=200, null=True, blank=True)
    emergency_phone = models.CharField(max_length=20, null=True, blank=True)
    emergency_relation = models.CharField(max_length=100, null=True, blank=True)
    signature_image = models.ImageField(
        upload_to="members/signatures/",
        blank=True,
        null=True,
        validators=[MaxFileSizeValidator(2), ImageFileValidator()],
        verbose_name="Digital signature image",
        help_text="Private signature used for resolution approval snapshots.",
    )
    signature_uploaded_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["district"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return self.member_id


class MemberApplication(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # --- Personal information ---
    full_name = models.CharField(max_length=200, editable=False)
    bangla_name = models.CharField(max_length=200)
    english_name = models.CharField(max_length=200)
    father_name = models.CharField(max_length=200)
    mother_name = models.CharField(max_length=200)
    email = models.EmailField(unique=True, null=True, blank=True)
    phone = models.CharField(max_length=20, unique=True)
    gender = models.CharField(max_length=10, choices=Gender.choices)
    date_of_birth = models.DateField()
    blood_group = models.CharField(max_length=10, choices=BloodGroup.choices, null=True, blank=True)
    marital_status = models.CharField(
        max_length=20, choices=MaritalStatus.choices, default=MaritalStatus.SINGLE
    )
    religion = models.CharField(max_length=20, choices=Religion.choices, null=True, blank=True)
    photo = models.ImageField(
        upload_to="members/photos/",
        validators=[MaxFileSizeValidator(3), ImageFileValidator()],
    )

    # --- Identity ---
    identity_type = models.CharField(max_length=20, choices=IdentityType.choices)
    identity_number = models.CharField(max_length=50)
    identity_document = models.FileField(
        upload_to="members/identity/",
        validators=[
            MaxFileSizeValidator(3),
            FileTypeValidator(
                allowed_extensions=ALLOWED_EXTENSIONS,
                allowed_content_types=ALLOWED_CONTENT_TYPES,
            ),
        ],
    )

    # --- Present address (Bangladesh) ---
    present_division = models.CharField(max_length=100, null=True, blank=True)
    present_district = models.CharField(max_length=100, null=True, blank=True)
    present_upazila = models.CharField(max_length=100, null=True, blank=True)
    present_union = models.CharField(max_length=100, null=True, blank=True)
    present_address = models.TextField(
        null=True, blank=True, help_text="Village / Road / House"
    )

    # --- Permanent address ---
    permanent_same_as_present = models.BooleanField(default=False)
    permanent_division = models.CharField(max_length=100, null=True, blank=True)
    permanent_district = models.CharField(max_length=100, null=True, blank=True)
    permanent_upazila = models.CharField(max_length=100, null=True, blank=True)
    permanent_union = models.CharField(max_length=100, null=True, blank=True)
    permanent_address = models.TextField(null=True, blank=True)

    # --- Expatriates ---
    is_expat = models.BooleanField(default=False)
    country = models.CharField(max_length=100, null=True, blank=True)
    expat_state_province = models.CharField(max_length=150, null=True, blank=True)
    expat_city = models.CharField(max_length=150, null=True, blank=True)
    expat_postal_code = models.CharField(max_length=20, null=True, blank=True)
    full_foreign_address = models.TextField(null=True, blank=True)
    passport_number = models.CharField(max_length=50, null=True, blank=True)

    # --- Occupation ---
    is_student = models.BooleanField(default=False)
    occupation = models.CharField(max_length=200, null=True, blank=True)
    designation = models.CharField(max_length=150, null=True, blank=True)
    organization = models.CharField(max_length=200, null=True, blank=True)
    workplace_address = models.TextField(null=True, blank=True)

    # --- Education (fully selectable, no free text) ---
    # education_type: General / Qaumi / Alia / Technical
    # education_level: the Stage (General) / Marhala (Qaumi) / Level (Alia, Technical)
    # education_class: Class — only applicable for General stages that have one
    # education_status: Currently Studying / Completed
    # See core/education_data.py for the full bilingual option tree.
    education = models.CharField(max_length=200, editable=False, blank=True)
    education_type = models.CharField(
        max_length=20, choices=EducationType.choices, null=True, blank=True
    )
    education_level = models.CharField(max_length=100, null=True, blank=True)
    education_class = models.CharField(max_length=20, null=True, blank=True)
    education_status = models.CharField(
        max_length=20, choices=EducationStatus.choices, null=True, blank=True
    )
    education_institution = models.CharField(max_length=200, null=True, blank=True)
    education_passing_year = models.PositiveIntegerField(null=True, blank=True)
    education_result = models.CharField(max_length=100, null=True, blank=True)

    # --- Additional ---
    facebook_url = models.URLField(null=True, blank=True)
    volunteer_experience = models.TextField(null=True, blank=True)
    cv = models.FileField(
        upload_to="members/cv/",
        null=True,
        blank=True,
        validators=[
            MaxFileSizeValidator(3),
            FileTypeValidator(
                allowed_extensions=ALLOWED_EXTENSIONS,
                allowed_content_types=ALLOWED_CONTENT_TYPES,
            ),
        ],
    )
    emergency_name = models.CharField(max_length=200, null=True, blank=True)
    emergency_phone = models.CharField(max_length=20, null=True, blank=True)
    emergency_relation = models.CharField(max_length=100, null=True, blank=True)

    # --- Review workflow ---
    status = models.CharField(
        max_length=20, choices=ApplicationStatus.choices, default=ApplicationStatus.PENDING
    )
    reference_code = models.CharField(max_length=32, unique=True, null=True, blank=True, db_index=True)
    admin_message = models.TextField(blank=True, default="")
    review_note = models.TextField(blank=True, default="")
    rejection_reason = models.TextField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_applications",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    status_token = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    status_token_expiry = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.email})"

    def open_document_requests(self):
        return self.document_requests.filter(is_satisfied=False)

    def has_open_document_requests(self):
        return self.open_document_requests().exists()

    def save(self, *args, **kwargs):
        from core.education_data import EDUCATION_CLASSES, EDUCATION_STAGES

        self.full_name = self.english_name or self.bangla_name
        if self.education_level:
            stage_label = self.education_level
            for option in EDUCATION_STAGES.get(self.education_type or "", []):
                if option["value"] == self.education_level:
                    stage_label = option["en"]
                    break
            if self.education_class:
                for option in EDUCATION_CLASSES.get(self.education_level, []):
                    if option["value"] == self.education_class:
                        stage_label = f"{stage_label} — {option['en']}"
                        break
            self.education = stage_label
        if not self.reference_code:
            self.reference_code = _generate_reference_code()
        super().save(*args, **kwargs)


def _generate_reference_code():
    """Unique public reference like ZFA-YYYYMMDD-XXXX (used from model.save)."""
    import secrets

    from django.utils import timezone

    day = timezone.now().strftime("%Y%m%d")
    for _ in range(40):
        code = f"ZFA-{day}-{secrets.token_hex(2).upper()}"
        if not MemberApplication.objects.filter(reference_code=code).exists():
            return code
    return f"ZFA-{day}-{secrets.token_hex(4).upper()}"


class ApplicationDocumentRequest(models.Model):
    """Admin-requested missing document that an applicant may upload."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        MemberApplication, on_delete=models.CASCADE, related_name="document_requests"
    )
    document_label = models.CharField(max_length=200)
    instruction = models.TextField(blank=True, default="")
    uploaded_file = models.FileField(
        upload_to="members/requested_docs/",
        null=True,
        blank=True,
        validators=[
            MaxFileSizeValidator(5),
            FileTypeValidator(
                allowed_extensions=ALLOWED_EXTENSIONS,
                allowed_content_types=ALLOWED_CONTENT_TYPES,
            ),
        ],
    )
    is_satisfied = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_document_requests",
    )
    satisfied_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.document_label} ({self.application.reference_code})"


class ApplicationEvent(models.Model):
    """Immutable audit trail for membership application workflow actions."""

    class Action(models.TextChoices):
        CREATED = "CREATED", "Created"
        ADMIN_CREATED = "ADMIN_CREATED", "Admin created"
        STATUS_CHANGE = "STATUS_CHANGE", "Status change"
        DOCUMENT_REQUESTED = "DOCUMENT_REQUESTED", "Document requested"
        DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED", "Document uploaded"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        ADMIN_MESSAGE = "ADMIN_MESSAGE", "Admin message"
        STATUS_LOOKUP = "STATUS_LOOKUP", "Status lookup"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        MemberApplication, on_delete=models.CASCADE, related_name="events"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="application_events",
    )
    action = models.CharField(max_length=40, choices=Action.choices)
    message = models.TextField(blank=True, default="")
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["application", "created_at"]),
            models.Index(fields=["action"]),
        ]

    def __str__(self):
        return f"{self.action} · {self.application_id}"


class FeePaymentSource(models.TextChoices):
    MANUAL = "MANUAL", "Member checkout"
    GATEWAY = "GATEWAY", "Gateway"
    AUTO = "AUTO", "Auto-payment"
    ADMIN = "ADMIN", "Admin / Finance"


class MembershipFeeSettings(models.Model):
    """Singleton configuration for membership monthly + registration fees."""

    SINGLETON_PK = 1

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    monthly_fee_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=50,
        help_text=_("Monthly membership fee amount in BDT."),
    )
    registration_fee_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=100,
        help_text=_("One-time membership registration fee in BDT."),
    )
    fee_start_year = models.PositiveIntegerField(
        default=1,
        help_text=_(
            "Global month from which existing members become liable for monthly fees."
        ),
    )
    fee_start_month = models.PositiveSmallIntegerField(
        default=1,
        help_text=_("Month component (1–12) of the fee starting month."),
    )
    is_active = models.BooleanField(default=True)
    admin_note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Membership fee settings")
        verbose_name_plural = _("Membership fee settings")
        constraints = [
            models.CheckConstraint(
                check=models.Q(fee_start_month__gte=1) & models.Q(fee_start_month__lte=12),
                name="membership_fee_settings_month_range",
            ),
            models.CheckConstraint(
                check=models.Q(monthly_fee_amount__gte=0),
                name="membership_fee_settings_monthly_nonneg",
            ),
            models.CheckConstraint(
                check=models.Q(registration_fee_amount__gte=0),
                name="membership_fee_settings_registration_nonneg",
            ),
        ]

    def __str__(self):
        return (
            f"Monthly ৳{self.monthly_fee_amount} · Registration "
            f"৳{self.registration_fee_amount} · start "
            f"{self.fee_start_year}-{self.fee_start_month:02d}"
        )

    def save(self, *args, **kwargs):
        self.pk = self.SINGLETON_PK
        super().save(*args, **kwargs)
        from members.fee_settings import clear_fee_settings_cache

        clear_fee_settings_cache()

    @classmethod
    def load(cls):
        from members.fee_settings import (
            DEFAULT_FEE_START_MONTH,
            DEFAULT_FEE_START_YEAR,
            DEFAULT_MONTHLY_FEE_BDT,
            DEFAULT_REGISTRATION_FEE_BDT,
        )

        obj, _ = cls.objects.get_or_create(
            pk=cls.SINGLETON_PK,
            defaults={
                "monthly_fee_amount": DEFAULT_MONTHLY_FEE_BDT,
                "registration_fee_amount": DEFAULT_REGISTRATION_FEE_BDT,
                "fee_start_year": DEFAULT_FEE_START_YEAR,
                "fee_start_month": DEFAULT_FEE_START_MONTH,
                "is_active": True,
            },
        )
        return obj

    @property
    def fee_start_period(self):
        return int(self.fee_start_year), int(self.fee_start_month)


class MembershipFee(models.Model):
    """One ledger row per member per calendar month (amount from fee settings at creation)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(
        Member, on_delete=models.CASCADE, related_name="membership_fees"
    )
    year = models.IntegerField()
    month = models.PositiveSmallIntegerField(default=1)
    amount = models.FloatField(default=50)
    paid_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=DonationStatus.choices, default=DonationStatus.PENDING
    )
    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.choices, null=True, blank=True
    )
    transaction_id = models.CharField(max_length=255, null=True, blank=True)
    source = models.CharField(
        max_length=20, choices=FeePaymentSource.choices, null=True, blank=True
    )
    fee_payment = models.ForeignKey(
        "MembershipFeePayment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fees",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["member", "year", "month"],
                name="uniq_membership_fee_member_year_month",
            ),
            models.CheckConstraint(
                check=models.Q(month__gte=1) & models.Q(month__lte=12),
                name="membership_fee_month_range",
            ),
        ]
        indexes = [
            models.Index(fields=["year", "month"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["-year", "-month"]

    def __str__(self):
        return f"{self.member.member_id} - {self.year}-{self.month:02d}"

    @property
    def period_label(self):
        from members.periods import format_fee_period

        return format_fee_period(self.year, self.month)

    @property
    def period_label_short(self):
        from members.periods import format_fee_period_short

        return format_fee_period_short(self.year, self.month)

    @property
    def period_key(self):
        """Machine key YYYY-MM (forms/checkboxes only — not for display)."""
        return f"{self.year}-{self.month:02d}"


class MembershipFeePayment(models.Model):
    """Batch payment covering one or more monthly fee rows (idempotent)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(
        Member, on_delete=models.CASCADE, related_name="fee_payments"
    )
    transaction = models.OneToOneField(
        "donations.Transaction",
        on_delete=models.CASCADE,
        related_name="membership_fee_payment",
        null=True,
        blank=True,
    )
    amount = models.FloatField()
    currency = models.CharField(max_length=10, default="BDT")
    status = models.CharField(
        max_length=20, choices=DonationStatus.choices, default=DonationStatus.PENDING
    )
    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.SSLCOMMERZ
    )
    # Canonical list of {"year": int, "month": int} covered by this payment.
    months = models.JSONField(default=list)
    source = models.CharField(
        max_length=20, choices=FeePaymentSource.choices, default=FeePaymentSource.GATEWAY
    )
    notes = models.TextField(blank=True, default="")
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_fee_payments",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["member", "created_at"]),
        ]

    def __str__(self):
        return f"FeePayment {self.pk} ({self.amount})"

    @property
    def payment_purpose(self):
        return "MEMBERSHIP_FEE"

    @property
    def donor_name(self):
        return f"{self.member.first_name} {self.member.last_name}".strip() or self.member.member_id

    @property
    def donor_email(self):
        user = getattr(self.member, "user", None)
        return getattr(user, "email", None) or ""

    @property
    def donor_phone(self):
        return self.member.phone or ""

    @property
    def product_name(self):
        return "Membership fee"


class AutoPayMode(models.TextChoices):
    MOCK = "MOCK", "Sandbox / mock"
    GATEWAY = "GATEWAY", "Gateway recurring"


class MembershipAutoPay(models.Model):
    """Optional member-activated auto-payment preference (never silently enabled)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.OneToOneField(
        Member, on_delete=models.CASCADE, related_name="auto_pay"
    )
    is_enabled = models.BooleanField(default=False)
    gateway = models.CharField(
        max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.SSLCOMMERZ
    )
    mode = models.CharField(
        max_length=20, choices=AutoPayMode.choices, default=AutoPayMode.MOCK
    )
    activated_at = models.DateTimeField(null=True, blank=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    deactivated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deactivated_autopays",
    )
    next_charge_on = models.DateField(null=True, blank=True)
    # Kept nullable/unused until a documented gateway integration requires storage.
    gateway_subscription_ref = models.CharField(max_length=255, null=True, blank=True)
    payment_token = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"AutoPay {self.member.member_id} enabled={self.is_enabled}"


class MembershipBillingEvent(models.Model):
    """Immutable audit trail for membership billing actions."""

    class Action(models.TextChoices):
        LEDGER_ENSURED = "LEDGER_ENSURED", "Ledger ensured"
        PAYMENT_INITIATED = "PAYMENT_INITIATED", "Payment initiated"
        PAYMENT_COMPLETED = "PAYMENT_COMPLETED", "Payment completed"
        PAYMENT_FAILED = "PAYMENT_FAILED", "Payment failed"
        ADMIN_RECORDED = "ADMIN_RECORDED", "Admin recorded payment"
        AUTOPAY_ACTIVATED = "AUTOPAY_ACTIVATED", "Auto-pay activated"
        AUTOPAY_DEACTIVATED = "AUTOPAY_DEACTIVATED", "Auto-pay deactivated"
        AUTOPAY_FORCED_OFF = "AUTOPAY_FORCED_OFF", "Auto-pay forced off (prepaid)"
        AUTOPAY_MOCK_CHARGE = "AUTOPAY_MOCK_CHARGE", "Auto-pay mock charge"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(
        Member, on_delete=models.CASCADE, related_name="billing_events"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="membership_billing_events",
    )
    action = models.CharField(max_length=40, choices=Action.choices)
    message = models.TextField(blank=True, default="")
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["member", "created_at"])]


class MemberNote(models.Model):
    """Free-form staff note attached to a member profile."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="member_notes",
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Note on {self.member.member_id}"


class MemberDocument(models.Model):
    """Additional uploaded document attached to a member profile."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=200)
    file = models.FileField(
        upload_to="members/documents/",
        validators=[
            MaxFileSizeValidator(5),
            FileTypeValidator(
                allowed_extensions=ALLOWED_EXTENSIONS,
                allowed_content_types=ALLOWED_CONTENT_TYPES,
            ),
        ],
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_member_documents",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.member.member_id})"


class MembershipRegistrationFee(models.Model):
    """One-time membership registration fee (separate from monthly ledger)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.OneToOneField(
        Member, on_delete=models.CASCADE, related_name="registration_fee"
    )
    amount = models.FloatField()
    currency = models.CharField(max_length=10, default="BDT")
    status = models.CharField(
        max_length=20, choices=DonationStatus.choices, default=DonationStatus.PENDING
    )
    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.choices, null=True, blank=True
    )
    source = models.CharField(
        max_length=20, choices=FeePaymentSource.choices, null=True, blank=True
    )
    transaction = models.OneToOneField(
        "donations.Transaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="membership_registration_fee",
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_registration_fees",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"RegistrationFee {self.member.member_id} ({self.status})"

    @property
    def payment_purpose(self):
        return "MEMBERSHIP_REG"

    @property
    def donor_name(self):
        return f"{self.member.first_name} {self.member.last_name}".strip() or self.member.member_id

    @property
    def donor_email(self):
        user = getattr(self.member, "user", None)
        return getattr(user, "email", None) or ""

    @property
    def donor_phone(self):
        return self.member.phone or ""

    @property
    def product_name(self):
        return "Membership registration fee"


class CouncilBody(models.TextChoices):
    EXECUTIVE = "EXECUTIVE", _("Executive Council")
    ADVISORY = "ADVISORY", _("Advisory Council")
    GENERAL = "GENERAL", _("General Council")
    BOARD = "BOARD", _("Board")
    OTHER = "OTHER", _("Other")


class OrganizationalPosition(models.Model):
    """Catalog of organizational offices (Chairman, Secretary, etc.)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name_en = models.CharField(max_length=150)
    name_bn = models.CharField(max_length=150, blank=True, default="")
    council_body = models.CharField(
        max_length=20,
        choices=CouncilBody.choices,
        default=CouncilBody.GENERAL,
    )
    description_en = models.TextField(blank=True, default="")
    description_bn = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    is_primary_eligible = models.BooleanField(
        default=True,
        help_text=_("May be marked as a member's primary position."),
    )
    display_order = models.PositiveIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "name_en"]

    def __str__(self):
        return f"{self.name_en} ({self.get_council_body_display()})"

    def localized_name(self, lang: str = "en") -> str:
        if (lang or "").startswith("bn"):
            return (self.name_bn or self.name_en).strip()
        return (self.name_en or self.name_bn).strip()


class MemberPositionAssignment(models.Model):
    """Dated assignment of an organizational position to a member."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name="position_assignments",
    )
    position = models.ForeignKey(
        OrganizationalPosition,
        on_delete=models.PROTECT,
        related_name="assignments",
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_primary = models.BooleanField(default=False)
    notes = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_position_assignments",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_primary", "-start_date", "position__display_order"]
        indexes = [
            models.Index(fields=["member", "is_active"]),
            models.Index(fields=["start_date", "end_date"]),
        ]

    def __str__(self):
        return f"{self.member.member_id} — {self.position.name_en}"

    def is_effective_on(self, on_date) -> bool:
        if not self.is_active:
            return False
        if self.start_date and on_date < self.start_date:
            return False
        if self.end_date and on_date > self.end_date:
            return False
        return True

