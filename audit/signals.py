import json

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from uuid import UUID
from decimal import Decimal
from datetime import date, datetime
from django.db.models import Model
from django.db.models.fields.files import FieldFile


AUDITED_MODELS = []


def register_audit_signals():
    from donations.models import Donation
    from members.models import Member, MemberApplication
    from news.models import News
    from reports.models import Report

    global AUDITED_MODELS
    AUDITED_MODELS = [Member, MemberApplication, Donation, News, Report]


def _serialize_value(value):
    if value is None:
        return None

    # UUID
    if isinstance(value, UUID):
        return str(value)

    # Date / DateTime
    if isinstance(value, (datetime, date)):
        return value.isoformat()

    # Decimal
    if isinstance(value, Decimal):
        return str(value)

    # FileField / ImageField
    if isinstance(value, FieldFile):
        return value.name if value else None

    # ForeignKey / Model instance
    if isinstance(value, Model):
        return str(value.pk)

    # JSON-safe primitive types
    if isinstance(value, (str, int, float, bool, list, dict)):
        return value

    # Fallback for any remaining unknown object
    return str(value)


def _serialize_instance(instance):
    data = {}
    for field in instance._meta.fields:
        data[field.name] = _serialize_value(
            getattr(instance, field.name)
        )
    return data


def _log_activity(user, action, instance, old_values=None, new_values=None):
    from audit.models import ActivityLog

    if user is None or not user.is_authenticated:
        return
    ActivityLog.objects.create(
        user=user,
        action=action,
        entity=instance.__class__.__name__,
        entity_id=str(instance.pk),
        description=f"{action} {instance.__class__.__name__} {instance.pk}",
        old_values=old_values,
        new_values=new_values,
    )


@receiver(post_save)
def audit_post_save(sender, instance, created, **kwargs):
    if sender.__name__ not in ("Member", "MemberApplication", "Donation", "News", "Report"):
        return
    user = getattr(instance, "_audit_user", None)
    action = "CREATE" if created else "UPDATE"
    new_values = _serialize_instance(instance)
    old_values = getattr(instance, "_old_values", None)
    _log_activity(user, action, instance, old_values=old_values, new_values=new_values)


@receiver(post_delete)
def audit_post_delete(sender, instance, **kwargs):
    if sender.__name__ not in ("Member", "MemberApplication", "Donation", "News", "Report"):
        return
    user = getattr(instance, "_audit_user", None)
    old_values = _serialize_instance(instance)
    _log_activity(user, "DELETE", instance, old_values=old_values)


register_audit_signals()


# --------------------------------------------------------------------------
# Notification emitters (additive; never raise into the saving transaction).
# --------------------------------------------------------------------------

# A donation at/above this amount also raises a "Large Donation" alert.
LARGE_DONATION_THRESHOLD = 10000


@receiver(post_save)
def emit_notifications_on_save(sender, instance, created, **kwargs):
    name = sender.__name__
    try:
        if name == "MemberApplication" and created:
            _notify_new_application(instance)
        elif name == "Donation":
            _notify_donation(instance, created)
    except Exception:
        # Notifications must never break the underlying write.
        pass


def _notify_new_application(application):
    from audit.notifications import ADMIN_ROLES, NotificationType, notify_roles
    from django.urls import reverse

    if getattr(application, "status", "PENDING") != "PENDING":
        return
    # Admin Add Member + auto-approve sets this to avoid a false "needs review" alert.
    if getattr(application, "_skip_new_application_notification", False):
        return
    try:
        link = reverse("dashboard-applications")
    except Exception:
        link = ""
    notify_roles(
        ADMIN_ROLES + ["REGIONAL_ADMIN"],
        title="New membership application",
        message=f"{application.full_name} submitted a membership application.",
        ntype=NotificationType.NEW_APPLICATION,
        link=link,
        related_object=application,
    )


def _notify_donation(donation, created):
    from audit.notifications import ADMIN_ROLES, NotificationType, notify_roles

    status = getattr(donation, "status", None)
    old_status = getattr(donation, "_old_status", None)

    # Fire once when a donation reaches its terminal state (either created that
    # way for manual entries, or transitioning from PENDING for gateway flows).
    reached_completed = status == "COMPLETED" and (created or old_status != "COMPLETED")
    reached_failed = status == "FAILED" and (created or old_status != "FAILED")

    audience = ADMIN_ROLES + ["FINANCE_OFFICER"]

    if reached_completed:
        notify_roles(
            audience,
            title="New donation received",
            message=f"{donation.display_name} donated {donation.amount:g} {donation.currency}.",
            ntype=NotificationType.NEW_DONATION,
            related_object=donation,
        )
        if donation.amount and donation.amount >= LARGE_DONATION_THRESHOLD:
            notify_roles(
                audience,
                title="Large donation received",
                message=f"{donation.display_name} donated {donation.amount:g} {donation.currency}.",
                ntype=NotificationType.LARGE_DONATION,
                related_object=donation,
            )
    elif reached_failed:
        notify_roles(
            audience,
            title="Donation payment failed",
            message=f"A payment of {donation.amount:g} {donation.currency} from {donation.display_name} failed.",
            ntype=NotificationType.PAYMENT_FAILED,
            related_object=donation,
        )


@receiver(pre_save)
def capture_old_donation_status(sender, instance, **kwargs):
    """Record the previous status so post_save can detect transitions."""
    if sender.__name__ != "Donation" or instance.pk is None:
        return
    try:
        instance._old_status = sender.objects.filter(pk=instance.pk).values_list("status", flat=True).first()
    except Exception:
        instance._old_status = None
