"""Idempotent membership fee due / paid / approval notifications."""

from django.contrib.contenttypes.models import ContentType
from audit.models import Notification, NotificationType
from audit.notifications import notify, notify_roles, ADMIN_ROLES
from members.fee_settings import format_amount_bdt, get_monthly_fee_amount
from members.periods import format_fee_period, format_fee_period_list


def _related_exists(ntype, obj):
    if obj is None or obj.pk is None:
        return False
    ct = ContentType.objects.get_for_model(obj)
    return Notification.objects.filter(
        type=ntype, content_type=ct, object_id=str(obj.pk)
    ).exists()


def notify_fee_due(fee):
    """Emit FEE_DUE once per MembershipFee row (member/month)."""
    if fee is None or fee.pk is None:
        return None
    if _related_exists(NotificationType.FEE_DUE, fee):
        return None
    user = getattr(getattr(fee, "member", None), "user", None)
    if not user:
        return None
    # Stored notifications use English month labels (project notification convention).
    period = format_fee_period(fee.year, fee.month, language="en")
    return notify(
        title="Membership fee due",
        message=f"Membership fee for {period} is pending (৳{fee.amount:g}).",
        ntype=NotificationType.FEE_DUE,
        user=user,
        related_object=fee,
        link="/dashboard/my-fees/",
    )


def notify_fee_paid(payment):
    """Emit FEE_PAID once per MembershipFeePayment to the member."""
    if payment is None or payment.pk is None:
        return None
    if _related_exists(NotificationType.FEE_PAID, payment):
        return None
    user = getattr(getattr(payment, "member", None), "user", None)
    if not user:
        return None
    months = payment.months or []
    label = format_fee_period_list(months, language="en") or "selected months"
    return notify(
        title="Membership fee payment received",
        message=f"Payment of ৳{payment.amount:g} received for {label}.",
        ntype=NotificationType.FEE_PAID,
        user=user,
        related_object=payment,
        link="/dashboard/my-fees/",
    )


def notify_registration_fee_paid(reg_fee):
    if reg_fee is None or reg_fee.pk is None:
        return None
    if _related_exists(NotificationType.FEE_PAID, reg_fee):
        return None
    user = getattr(getattr(reg_fee, "member", None), "user", None)
    if not user:
        return None
    return notify(
        title="Registration fee payment received",
        message=f"Registration fee payment of ৳{reg_fee.amount:g} received.",
        ntype=NotificationType.FEE_PAID,
        user=user,
        related_object=reg_fee,
        link="/dashboard/my-fees/",
    )


def _approval_fee_message(*, language: str, registration_amount, monthly_amount, year, month):
    period_en = format_fee_period(year, month, language="en")
    period_bn = format_fee_period(year, month, language="bn")
    reg = format_amount_bdt(registration_amount, language=language)
    monthly = format_amount_bdt(monthly_amount, language=language)
    total = format_amount_bdt(
        float(registration_amount) + float(monthly_amount), language=language
    )
    if (language or "en").startswith("bn"):
        return (
            "আপনার জাররাহ ফাউন্ডেশন সদস্যপদ আবেদন অনুমোদিত হয়েছে।\n\n"
            f"রেজিস্ট্রেশন ফি: {reg}\n"
            f"{period_bn} মাসের সদস্যপদ ফি: {monthly}\n"
            f"বর্তমানে মোট পরিশোধযোগ্য: {total}\n\n"
            "পেমেন্ট সম্পন্ন করতে আপনার অ্যাকাউন্টে লগইন করুন।"
        )
    return (
        "Your Zarrah Foundation membership application has been approved.\n\n"
        f"Registration Fee: {reg}\n"
        f"Membership Fee for {period_en}: {monthly}\n"
        f"Total payable now: {total}\n\n"
        "Please log in to your account to complete your payment."
    )


def notify_membership_approved_payment_due(member, *, year=None, month=None):
    """In-app + email + optional SMS for registration + running-month fees."""
    from members.billing import current_year_month, ensure_registration_fee
    from members.models import MembershipFee

    if member is None or member.pk is None:
        return None
    user = getattr(member, "user", None)
    if not user:
        return None

    cy, cm = current_year_month()
    year = year or cy
    month = month or cm
    reg = ensure_registration_fee(member)
    fee = MembershipFee.objects.filter(member=member, year=year, month=month).first()
    monthly_amount = float(fee.amount) if fee else get_monthly_fee_amount()
    registration_amount = float(reg.amount)

    message_en = _approval_fee_message(
        language="en",
        registration_amount=registration_amount,
        monthly_amount=monthly_amount,
        year=year,
        month=month,
    )
    message_bn = _approval_fee_message(
        language="bn",
        registration_amount=registration_amount,
        monthly_amount=monthly_amount,
        year=year,
        month=month,
    )

    notification = None
    if not _related_exists(NotificationType.MEMBERSHIP_APPROVED, member):
        notification = notify(
            title="Membership approved — payment due",
            message=message_en.replace("\n\n", " ").replace("\n", " "),
            ntype=NotificationType.MEMBERSHIP_APPROVED,
            user=user,
            related_object=member,
            link="/dashboard/my-fees/",
        )

    email = getattr(user, "email", None) or ""
    if email and not email.endswith("@members.zarrah.local"):
        try:
            from core.email import send_email
            from core.models import SiteSettings

            foundation = SiteSettings.load().localized_name("en")
            body = (
                f"{message_en}\n\n"
                f"---\n\n"
                f"{message_bn}\n\n"
                f"Payment page (after login): /dashboard/my-fees/\n\n"
                f"{foundation}"
            )
            send_email(
                subject=f"Membership approved — payment due · {foundation}",
                message=body,
                recipient_list=[email],
                fail_silently=True,
            )
        except Exception:
            pass

    phone = getattr(member, "phone", None) or ""
    if phone:
        try:
            from core.sms import SMSService

            total = format_amount_bdt(registration_amount + monthly_amount)
            sms_body = (
                f"Zarrah membership approved. Reg {format_amount_bdt(registration_amount)} + "
                f"{format_fee_period(year, month, short=True, language='en')} "
                f"{format_amount_bdt(monthly_amount)} = {total}. Pay at My Fees after login."
            )
            SMSService.send_sms(phone, sms_body)
        except Exception:
            pass

    return notification


def notify_admin_member_created(member, *, actor=None):
    """Staff notice when an admin auto-approves / creates a member (not NEW_APPLICATION)."""
    try:
        from django.urls import reverse

        link = reverse("dashboard-member-detail", kwargs={"pk": member.pk})
    except Exception:
        link = ""
    actor_label = getattr(actor, "email", None) or "Administrator"
    notify_roles(
        ADMIN_ROLES + ["FINANCE_OFFICER"],
        title="Member created by administrator",
        message=f"{member.member_id} was created by {actor_label}.",
        ntype=NotificationType.USER_CREATED,
        link=link,
        related_object=member,
    )
