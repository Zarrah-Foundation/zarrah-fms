"""Centralized membership application status transitions + audit events."""

from django.db import transaction
from django.utils import timezone

from members.models import ApplicationEvent, ApplicationStatus, MemberApplication

ALLOWED_TRANSITIONS = {
    ApplicationStatus.PENDING: {
        ApplicationStatus.UNDER_REVIEW,
        ApplicationStatus.APPROVED,
        ApplicationStatus.REJECTED,
    },
    ApplicationStatus.UNDER_REVIEW: {
        ApplicationStatus.APPROVED,
        ApplicationStatus.REJECTED,
    },
    ApplicationStatus.REJECTED: {
        ApplicationStatus.UNDER_REVIEW,
        ApplicationStatus.APPROVED,
    },
    ApplicationStatus.APPROVED: set(),
}


class TransitionError(ValueError):
    """Raised when a status transition is not allowed."""


def assert_transition_allowed(current, new_status):
    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        raise TransitionError(
            f"Cannot transition application from {current} to {new_status}."
        )


def record_event(application, action, *, actor=None, message="", metadata=None):
    return ApplicationEvent.objects.create(
        application=application,
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        message=message or "",
        metadata=metadata,
    )


@transaction.atomic
def transition_application(
    application,
    new_status,
    actor,
    *,
    reason="",
    admin_message=None,
    review_note=None,
    membership_type=None,
):
    """Move an application to ``new_status`` if allowed; return Member on approve."""
    assert_transition_allowed(application.status, new_status)
    old_status = application.status
    application._audit_user = actor

    if admin_message is not None:
        application.admin_message = admin_message
    if review_note is not None:
        application.review_note = review_note

    member = None
    if new_status == ApplicationStatus.APPROVED:
        from members.services import approve_application

        member = approve_application(
            application,
            actor,
            membership_type=membership_type,
            skip_status_check=True,
        )
        record_event(
            application,
            ApplicationEvent.Action.APPROVED,
            actor=actor,
            message=f"{old_status} → {ApplicationStatus.APPROVED}",
            metadata={"from": old_status, "to": ApplicationStatus.APPROVED},
        )
    elif new_status == ApplicationStatus.REJECTED:
        from members.services import reject_application

        reject_application(application, actor, reason=reason, skip_status_check=True)
        record_event(
            application,
            ApplicationEvent.Action.REJECTED,
            actor=actor,
            message=reason or f"{old_status} → {ApplicationStatus.REJECTED}",
            metadata={"from": old_status, "to": ApplicationStatus.REJECTED, "reason": reason},
        )
    else:
        application.status = new_status
        application.reviewed_by = actor
        application.reviewed_at = timezone.now()
        update_fields = ["status", "reviewed_by", "reviewed_at", "updated_at"]
        if admin_message is not None:
            update_fields.append("admin_message")
        if review_note is not None:
            update_fields.append("review_note")
        application.save(update_fields=update_fields)
        record_event(
            application,
            ApplicationEvent.Action.STATUS_CHANGE,
            actor=actor,
            message=f"{old_status} → {new_status}",
            metadata={"from": old_status, "to": new_status},
        )

    return member
