import uuid

from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class ContactMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    email = models.EmailField()
    subject = models.CharField(max_length=300)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["is_read"]), models.Index(fields=["created_at"])]

    def __str__(self):
        return f"{self.subject} — {self.name}"


class VolunteerStatus(models.TextChoices):
    NEW = "NEW", _("New")
    CONTACTED = "CONTACTED", _("Contacted")
    ACTIVE = "ACTIVE", _("Active")
    REJECTED = "REJECTED", _("Rejected")


class Volunteer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    area_of_interest = models.CharField(max_length=200, blank=True, default="")
    message = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=VolunteerStatus.choices, default=VolunteerStatus.NEW)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status"]), models.Index(fields=["created_at"])]

    def __str__(self):
        return self.name


class Testimonial(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author_name = models.CharField(max_length=200)
    designation = models.CharField(max_length=200, blank=True, default="")
    content_bn = models.TextField(blank=True, default="")
    content_en = models.TextField(blank=True, default="")
    photo = models.ImageField(upload_to="community/testimonials/", null=True, blank=True)
    display_order = models.PositiveIntegerField(default=0, db_index=True)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order", "-created_at"]

    def __str__(self):
        return self.author_name


class FAQ(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question_bn = models.CharField(max_length=300, blank=True, default="")
    question_en = models.CharField(max_length=300, blank=True, default="")
    answer_bn = models.TextField(blank=True, default="")
    answer_en = models.TextField(blank=True, default="")
    display_order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order"]
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self):
        return self.question_en or self.question_bn


class PartnerRelationshipType(models.TextChoices):
    ORGANIZATIONAL_SUPPORTER = (
        "ORGANIZATIONAL_SUPPORTER",
        _("Organization supporting our work"),
    )
    ELIGIBILITY_PLATFORM = (
        "ELIGIBILITY_PLATFORM",
        _("Nonprofit eligibility platform"),
    )
    TECHNOLOGY_BENEFIT = (
        "TECHNOLOGY_BENEFIT",
        _("Nonprofit technology/service benefit"),
    )
    PARTNER = "PARTNER", _("Partner")


class Partner(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    logo = models.ImageField(upload_to="community/partners/", null=True, blank=True)
    url = models.URLField(blank=True, default="")
    relationship_type = models.CharField(
        max_length=40,
        choices=PartnerRelationshipType.choices,
        default=PartnerRelationshipType.TECHNOLOGY_BENEFIT,
        db_index=True,
    )
    description_en = models.CharField(max_length=300, blank=True, default="")
    description_bn = models.CharField(max_length=300, blank=True, default="")
    display_order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name = _("Partner / supporter")
        verbose_name_plural = _("Partners & supporters")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def localized_description(self, lang=None):
        from django.utils.translation import get_language

        lang = lang or get_language()
        if (lang or "").startswith("bn"):
            return self.description_bn or self.description_en
        return self.description_en or self.description_bn

    @property
    def localized_relationship_type(self):
        from django.utils.translation import get_language

        labels = {
            PartnerRelationshipType.ORGANIZATIONAL_SUPPORTER: (
                "Organization supporting our work",
                "আমাদের কাজকে সহায়তা করা সংস্থা",
            ),
            PartnerRelationshipType.ELIGIBILITY_PLATFORM: (
                "Nonprofit eligibility platform",
                "অলাভজনক যোগ্যতা প্ল্যাটফর্ম",
            ),
            PartnerRelationshipType.TECHNOLOGY_BENEFIT: (
                "Nonprofit technology/service benefit",
                "অলাভজনক প্রযুক্তি/সেবা সুবিধা",
            ),
            PartnerRelationshipType.PARTNER: ("Partner", "অংশীদার"),
        }
        pair = labels.get(self.relationship_type)
        if not pair:
            return self.get_relationship_type_display()
        return pair[1] if (get_language() or "").startswith("bn") else pair[0]

    @property
    def public_url(self):
        url = (self.url or "").strip()
        if url.lower().startswith(("http://", "https://")):
            return url
        return ""

    @property
    def logo_is_usable(self):
        field = self.logo
        name = getattr(field, "name", "") or ""
        if not name.strip():
            return False
        try:
            return bool(field.storage.exists(name))
        except Exception:
            return True

    @property
    def initials(self):
        parts = [p for p in (self.name or "").split() if p]
        if not parts:
            return "Z"
        if len(parts) == 1:
            return parts[0][:2].upper()
        return f"{parts[0][0]}{parts[-1][0]}".upper()


class LeadershipRole(models.TextChoices):
    CHAIRMAN = "CHAIRMAN", _("Chairman")
    SECRETARY = "SECRETARY", _("Secretary")
    VICE_CHAIRMAN = "VICE_CHAIRMAN", _("Vice Chairman")
    TREASURER = "TREASURER", _("Treasurer")
    COMMITTEE = "COMMITTEE", _("Committee Member")


class LeadershipPerson(models.Model):
    """Public About-page leadership profiles (Chairman, Secretary, committee)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=30, choices=LeadershipRole.choices, db_index=True)
    name = models.CharField(max_length=200)
    role_label_bn = models.CharField(max_length=150, blank=True, default="")
    role_label_en = models.CharField(max_length=150, blank=True, default="")
    bio_bn = models.TextField(blank=True, default="")
    bio_en = models.TextField(blank=True, default="")
    photo = models.ImageField(
        upload_to="community/leadership/",
        null=True,
        blank=True,
    )
    display_order = models.PositiveIntegerField(default=0, db_index=True)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "role", "name"]
        verbose_name = _("Leadership person")
        verbose_name_plural = _("Leadership people")

    def __str__(self):
        return f"{self.name} ({self.get_role_display()})"

    def localized_role(self, lang=None):
        from django.utils.translation import get_language

        lang = lang or get_language()
        if lang == "bn":
            return self.role_label_bn or self.role_label_en or self.get_role_display()
        return self.role_label_en or self.role_label_bn or self.get_role_display()

    def localized_bio(self, lang=None):
        from django.utils.translation import get_language

        lang = lang or get_language()
        if lang == "bn":
            return self.bio_bn or self.bio_en
        return self.bio_en or self.bio_bn

    def as_card_dict(self):
        """Shape expected by About leadership card templates / |bl filter."""
        return {
            "name": self.name,
            "role_en": self.role_label_en or self.get_role_display(),
            "role_bn": self.role_label_bn or self.get_role_display(),
            "bio_en": self.bio_en,
            "bio_bn": self.bio_bn,
            "photo": self.photo if self.photo else None,
        }
