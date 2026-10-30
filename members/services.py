import secrets
import string
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import IntegrityError, connection, transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from accounts.models import Role, User
from core.email import send_email
from core.models import SiteSettings
from members.models import (
    ApplicationDocumentRequest,
    ApplicationEvent,
    ApplicationStatus,
    Member,
    MemberApplication,
    MemberStatus,
)
from members.transitions import TransitionError, assert_transition_allowed, record_event


STATUS_TOKEN_TIMEOUT = getattr(settings, "APPLICATION_STATUS_TOKEN_TIMEOUT", 3600)
STATUS_LOOKUP_COOLDOWN = 60
STATUS_LOOKUP_MAX_PER_HOUR = 5


def generate_member_id():
    year = timezone.now().year
    prefix = f"ZF-{year}-"
    qs = Member.objects.filter(member_id__startswith=prefix)
    if connection.features.has_select_for_update:
        qs = qs.select_for_update()
    last = qs.order_by("-member_id").values_list("member_id", flat=True).first()
    if last:
        seq = int(last.split("-")[-1]) + 1
    else:
        seq = 1
    return f"{prefix}{seq:05d}"


def _create_member(**kwargs):
    """Insert a Member, retrying if two approvals take the same member ID."""
    from members.transitions import TransitionError

    last_error = None
    for _ in range(5):
        try:
            with transaction.atomic():
                kwargs["member_id"] = generate_member_id()
                return Member.objects.create(**kwargs)
        except IntegrityError as exc:
            last_error = exc
            if "member_id" not in str(exc):
                raise
    raise TransitionError("Could not allocate a unique member ID. Please try again.") from last_error


def _account_for_applicant(application, *, temp_password):
    """Return ``(user, created_new_account)`` for an approved applicant."""
    from members.transitions import TransitionError

    account_email = application.email or f"member.{application.phone}@members.zarrah.local"
    existing = User.objects.filter(email__iexact=account_email).first()
    if existing:
        if Member.objects.filter(user=existing).exists():
            if application.email:
                raise TransitionError("An account with this email is already a member.")
            raise TransitionError(
                "A login already exists for this phone number. Add an email address before approving."
            )
        updates = []
        if existing.role in (Role.DONOR, Role.MEMBER):
            existing.role = Role.MEMBER
            updates.append("role")
        if not existing.is_active:
            existing.is_active = True
            updates.append("is_active")
        if not existing.is_active_member:
            existing.is_active_member = True
            updates.append("is_active_member")
        if updates:
            updates.append("updated_at")
            existing.save(update_fields=updates)
        return existing, False

    user = User.objects.create_user(
        email=account_email,
        password=temp_password,
        name=application.full_name,
        role=Role.MEMBER,
        email_verified=timezone.now() if application.email else None,
    )
    return user, True


def generate_temp_password(length=12):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_reference_code():
    from members.models import _generate_reference_code

    return _generate_reference_code()


@transaction.atomic
def approve_application(application, reviewer, *, membership_type=None, skip_status_check=False):
    if not skip_status_check:
        assert_transition_allowed(application.status, ApplicationStatus.APPROVED)

    if application.status == ApplicationStatus.APPROVED:
        raise TransitionError("Application is already approved.")

    temp_password = generate_temp_password()
    name_parts = application.full_name.split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    # Email is optional on the application (login currently requires an
    # email — phone-only login is a planned future enhancement). When the
    # applicant didn't provide one, use a non-mailable placeholder derived
    # from their phone number so a login account can still be created; the
    # admin/reviewer must then set a real email or communicate the temporary
    # password to the member directly.
    user, created_account = _account_for_applicant(application, temp_password=temp_password)

    present_address = application.present_address
    if application.permanent_same_as_present:
        permanent_address = present_address
    else:
        permanent_address = application.permanent_address

    member = _create_member(
        user=user,
        membership_type=membership_type,
        first_name=first_name,
        last_name=last_name,
        phone=application.phone,
        gender=application.gender,
        date_of_birth=application.date_of_birth,
        blood_group=application.blood_group,
        nid_number=application.identity_number,
        present_address=present_address or application.full_foreign_address or "",
        permanent_address=permanent_address,
        district=application.present_district or application.expat_city or application.country or "N/A",
        upazila=application.present_upazila,
        occupation=application.occupation,
        organization=application.organization,
        education=application.education,
        status=MemberStatus.APPROVED,
        joined_at=timezone.now(),
        approved_by=reviewer,
        approved_at=timezone.now(),
        emergency_name=application.emergency_name,
        emergency_phone=application.emergency_phone,
        emergency_relation=application.emergency_relation,
    )

    application.status = ApplicationStatus.APPROVED
    application.reviewed_by = reviewer
    application.reviewed_at = timezone.now()
    application.save()

    # Fee ledger is required for operational consistency; failure rolls back approval.
    from members.billing import seed_ledger_for_new_member

    seed_ledger_for_new_member(member, actor=reviewer)

    login_url = f"{settings.SITE_URL}/login/"
    if application.email:
        foundation = SiteSettings.load().localized_name("en")
        if created_account:
            credentials = (
                f"Email: {application.email}\n"
                f"Temporary password: {temp_password}\n\n"
                f"Please log in at {login_url} and change your password.\n\n"
            )
        else:
            credentials = (
                f"Your existing account ({application.email}) is now linked to this membership. "
                f"Log in at {login_url} with your current password.\n\n"
            )
        send_email(
            subject=f"Welcome to {foundation}",
            message=(
                f"Dear {application.full_name},\n\n"
                f"Your membership application has been approved.\n"
                f"Member ID: {member.member_id}\n"
                f"{credentials}"
                f"{foundation}"
            ),
            recipient_list=[application.email],
            fail_silently=True,
        )

    # Additive: registration + running-month fee notice (email/SMS/in-app).
    try:
        from members.fee_notifications import notify_membership_approved_payment_due

        notify_membership_approved_payment_due(member)
    except Exception:
        pass

    return member


def reject_application(application, reviewer, reason="", *, skip_status_check=False):
    if not skip_status_check:
        assert_transition_allowed(application.status, ApplicationStatus.REJECTED)
    application.status = ApplicationStatus.REJECTED
    application.rejection_reason = reason
    application.reviewed_by = reviewer
    application.reviewed_at = timezone.now()
    application.save()

    # Additive: notify applicant when a linked user exists. Never break rejection.
    try:
        from audit.notifications import NotificationType, notify
        from accounts.models import User

        user = None
        if application.email:
            user = User.objects.filter(email__iexact=application.email).first()
        if user:
            msg = "Your membership application was not approved."
            if reason:
                msg = f"{msg} Reason: {reason}"
            notify(
                title="Membership application update",
                message=msg,
                ntype=NotificationType.MEMBERSHIP_REJECTED,
                user=user,
                related_object=application,
            )
    except Exception:
        pass


@transaction.atomic
def create_member_manual(*, first_name, last_name, phone, district, present_address,
                         email=None, membership_type=None, creator=None):
    """Create a Member and its linked login account (manual dashboard entry).

    Prefer admin application form + transition_application for new work.
    Kept for backward compatibility with any remaining callers.
    """
    from members.transitions import TransitionError

    temp_password = generate_temp_password()
    account_email = email or f"member.{phone}@members.zarrah.local"
    if User.objects.filter(email__iexact=account_email).exists():
        if email:
            raise TransitionError("A login account with this email already exists.")
        raise TransitionError("A login already exists for this phone number. Enter an email address.")
    full_name = (f"{first_name} {last_name}").strip()

    user = User.objects.create_user(
        email=account_email,
        password=temp_password,
        name=full_name,
        role=Role.MEMBER,
        email_verified=timezone.now() if email else None,
    )

    member = _create_member(
        user=user,
        membership_type=membership_type,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        present_address=present_address,
        district=district or "N/A",
        status=MemberStatus.APPROVED,
        joined_at=timezone.now(),
        approved_by=creator,
        approved_at=timezone.now(),
    )
    try:
        from members.billing import seed_ledger_for_new_member

        seed_ledger_for_new_member(member, actor=creator)
    except Exception:
        pass
    try:
        from members.fee_notifications import notify_membership_approved_payment_due

        notify_membership_approved_payment_due(member)
    except Exception:
        pass
    return member


@transaction.atomic
def create_application_as_admin(form, *, creator, membership_type=None, auto_approve=False):
    """Save MemberApplication from admin form; optionally approve immediately.

    Administrative path: does not run the public email-verification registration workflow.
    """
    application = form.save(commit=False)
    application.status = ApplicationStatus.PENDING
    application._audit_user = creator
    # Auto-approve creates a member immediately — skip staff "new application" review notice.
    if auto_approve:
        application._skip_new_application_notification = True
    application.save()
    record_event(
        application,
        ApplicationEvent.Action.ADMIN_CREATED,
        actor=creator,
        message="Application created by administrator",
        metadata={"auto_approve": bool(auto_approve)},
    )
    member = None
    if auto_approve:
        from members.transitions import transition_application

        member = transition_application(
            application,
            ApplicationStatus.APPROVED,
            creator,
            membership_type=membership_type,
        )
        try:
            from members.fee_notifications import notify_admin_member_created

            notify_admin_member_created(member, actor=creator)
        except Exception:
            pass
    return application, member


def _status_lookup_cd_key(email):
    return f"app_status_lookup_cd:{(email or '').strip().lower()}"


def _status_lookup_hr_key(email):
    return f"app_status_lookup_hr:{(email or '').strip().lower()}"


def can_request_status_lookup(email):
    email = (email or "").strip().lower()
    if not email:
        return False, 0, "invalid"
    wait = cache.get(_status_lookup_cd_key(email))
    if wait:
        return False, int(wait), "cooldown"
    count = cache.get(_status_lookup_hr_key(email)) or 0
    if count >= STATUS_LOOKUP_MAX_PER_HOUR:
        return False, 3600, "hourly_limit"
    return True, 0, None


def mark_status_lookup_attempt(email):
    email = (email or "").strip().lower()
    cache.set(_status_lookup_cd_key(email), STATUS_LOOKUP_COOLDOWN, STATUS_LOOKUP_COOLDOWN)
    hourly = cache.get(_status_lookup_hr_key(email)) or 0
    cache.set(_status_lookup_hr_key(email), hourly + 1, 3600)


def find_application_for_status_lookup(reference_code, email):
    """Return matching application or None. Caller must not leak existence."""
    code = (reference_code or "").strip().upper()
    email_norm = (email or "").strip().lower()
    if not code or not email_norm:
        return None
    return (
        MemberApplication.objects.filter(reference_code__iexact=code)
        .exclude(email__isnull=True)
        .exclude(email="")
        .filter(email__iexact=email_norm)
        .first()
    )


def issue_status_token(application):
    token = secrets.token_urlsafe(32)
    application.status_token = token
    application.status_token_expiry = timezone.now() + timedelta(seconds=STATUS_TOKEN_TIMEOUT)
    application.save(update_fields=["status_token", "status_token_expiry", "updated_at"])
    return token


def send_status_lookup_email(application, absolute_url):
    foundation = SiteSettings.load().localized_name()
    send_email(
        subject=_("Your membership application status - %(name)s") % {"name": foundation},
        message=_(
            "Use this one-time link to view your application status (expires soon):\n\n%(url)s\n\n"
            "Reference: %(ref)s\n\n%(name)s"
        )
        % {"url": absolute_url, "ref": application.reference_code, "name": foundation},
        recipient_list=[application.email],
        fail_silently=True,
    )


def consume_status_token(token):
    """Validate one-time token; clear it and return application or None."""
    if not token:
        return None
    application = MemberApplication.objects.filter(status_token=token).first()
    if not application:
        return None
    if not application.status_token_expiry or application.status_token_expiry < timezone.now():
        application.status_token = None
        application.status_token_expiry = None
        application.save(update_fields=["status_token", "status_token_expiry", "updated_at"])
        return None
    application.status_token = None
    application.status_token_expiry = None
    application.save(update_fields=["status_token", "status_token_expiry", "updated_at"])
    record_event(
        application,
        ApplicationEvent.Action.STATUS_LOOKUP,
        message="Applicant opened status via one-time token",
    )
    return application


@transaction.atomic
def request_missing_documents(application, actor, items, *, admin_message=""):
    """Create admin-requested document slots. ``items``: list of {label, instruction}."""
    created = []
    for item in items:
        label = (item.get("label") or "").strip()
        if not label:
            continue
        doc = ApplicationDocumentRequest.objects.create(
            application=application,
            document_label=label,
            instruction=(item.get("instruction") or "").strip(),
            created_by=actor,
        )
        created.append(doc)
        record_event(
            application,
            ApplicationEvent.Action.DOCUMENT_REQUESTED,
            actor=actor,
            message=label,
            metadata={"request_id": str(doc.pk), "instruction": doc.instruction},
        )
    if admin_message:
        application.admin_message = admin_message
        application._audit_user = actor
        application.save(update_fields=["admin_message", "updated_at"])
        record_event(
            application,
            ApplicationEvent.Action.ADMIN_MESSAGE,
            actor=actor,
            message=admin_message,
        )
    elif created and application.status == ApplicationStatus.PENDING:
        from members.transitions import transition_application

        transition_application(application, ApplicationStatus.UNDER_REVIEW, actor)
    return created


@transaction.atomic
def upload_requested_document(doc_request, uploaded_file):
    """Satisfy an open ApplicationDocumentRequest. Raises ValueError if not allowed."""
    if doc_request.is_satisfied:
        raise ValueError("This document request has already been satisfied.")
    application = doc_request.application
    doc_request.uploaded_file = uploaded_file
    doc_request.is_satisfied = True
    doc_request.satisfied_at = timezone.now()
    doc_request.full_clean()
    doc_request.save()
    record_event(
        application,
        ApplicationEvent.Action.DOCUMENT_UPLOADED,
        message=doc_request.document_label,
        metadata={"request_id": str(doc_request.pk)},
    )
    return doc_request
