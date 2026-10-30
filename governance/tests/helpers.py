"""Shared factories for governance tests."""

from __future__ import annotations

import io
import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image

from accounts.models import Role as LegacyRole
from governance.models import EligibilityMode, Meeting, MeetingStatus, MeetingType
from governance.sequences import generate_meeting_reference
from members.models import Member, MemberGroup, MemberStatus
from rbac.models import Permission, Role, RolePermission, UserRole
from rbac.permissions import clear_cache

User = get_user_model()


def ensure_rbac_seeded() -> None:
    """Seed RBAC catalog each call — TestCase rollbacks invalidate a one-shot flag."""
    from rbac.management.commands.seed_rbac import Command as SeedRbac

    SeedRbac().handle()


def png_upload(name: str = "signature.png") -> SimpleUploadedFile:
    buf = io.BytesIO()
    Image.new("RGB", (48, 24), color=(20, 120, 80)).save(buf, format="PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


def create_user(
    email: str,
    *,
    password: str = "pass12345",
    role=LegacyRole.MEMBER,
    verified: bool = True,
    is_staff: bool = False,
) -> User:
    user = User.objects.create_user(email=email, password=password, role=role)
    if verified:
        user.email_verified = timezone.now()
    user.is_staff = is_staff
    user.save(update_fields=["email_verified", "is_staff"])
    return user


def create_staff_with_permission(
    email: str,
    codename: str,
    *,
    password: str = "pass12345",
) -> User:
    """Staff user granted a single RBAC permission via an ad-hoc role."""
    ensure_rbac_seeded()
    # Ad-hoc permission for tests when WP3 registry grants are not yet seeded.
    if "." not in codename:
        raise ValueError(f"Invalid permission codename: {codename}")
    module, action = codename.split(".", 1)
    perm, _ = Permission.objects.get_or_create(
        module=module,
        action=action,
        defaults={"label": codename},
    )
    role = Role.objects.create(
        name=f"Test role {codename} {email}",
        is_system=False,
    )
    RolePermission.objects.create(role=role, permission=perm)
    user = create_user(
        email,
        password=password,
        role=LegacyRole.MEMBER,
        is_staff=True,
    )
    UserRole.objects.create(user=user, role=role)
    clear_cache(user)
    return user


def create_approved_member(
    index: int,
    *,
    signature_image=None,
    status=MemberStatus.APPROVED,
) -> tuple[User, Member]:
    user = create_user(f"gov-member-{index}@example.com")
    member_kwargs = {
        "member_id": f"GOV{index:04d}",
        "user": user,
        "first_name": f"Member{index}",
        "last_name": "Gov",
        "phone": f"0171000{index:04d}",
        "present_address": "Dhaka",
        "district": "Dhaka",
        "status": status,
    }
    if signature_image is not None:
        member_kwargs["signature_image"] = signature_image
    member = Member.objects.create(**member_kwargs)
    return user, member


def create_meeting_type(
    *,
    slug: str | None = None,
    quorum_numerator: int = 2,
    quorum_denominator: int = 3,
    eligibility_mode=EligibilityMode.LINKED_GROUPS,
    groups=None,
) -> MeetingType:
    slug = slug or f"meeting-type-{uuid.uuid4().hex[:8]}"
    mt = MeetingType.objects.create(
        slug=slug,
        name_en=f"Type {slug}",
        name_bn=f"ধরন {slug}",
        quorum_numerator=quorum_numerator,
        quorum_denominator=quorum_denominator,
        eligibility_mode=eligibility_mode,
    )
    if groups:
        mt.eligibility_groups.set(groups)
    return mt


def create_meeting(
    *,
    meeting_type: MeetingType | None = None,
    created_by=None,
    **overrides,
) -> Meeting:
    if meeting_type is None:
        meeting_type = create_meeting_type()
    defaults = {
        "reference_id": generate_meeting_reference(),
        "meeting_type": meeting_type,
        "title_bn": "পরীক্ষামূলক সভা",
        "title_en": "Test Meeting",
        "starts_at": timezone.now() + timedelta(days=1),
        "status": MeetingStatus.DRAFT,
    }
    if created_by is not None:
        defaults["created_by"] = created_by
    defaults.update(overrides)
    return Meeting.objects.create(**defaults)


def create_member_group(name: str = "Council") -> MemberGroup:
    slug = name.lower().replace(" ", "-")
    return MemberGroup.objects.create(name_en=name, slug=slug)
