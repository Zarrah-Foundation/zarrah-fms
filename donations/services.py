import logging
import uuid

from django.conf import settings
from django.db import transaction as db_transaction
from django.utils import timezone

from core.choices import DonationStatus, PaymentMethod
from core.email import send_email
from core.models import SiteSettings
from donations.gateways import get_gateway
from donations.money import amounts_equal, normalize_currency, to_money
from donations.receipts import generate_receipt_pdf, receipt_filename

logger = logging.getLogger(__name__)


class DonationCompletionError(Exception):
    """Raised when gateway donation completion is refused."""


@db_transaction.atomic
def create_manual_donation(
    *,
    amount,
    category,
    donor_name="",
    donor_phone="",
    donor_email="",
    payment_method=PaymentMethod.CASH,
    is_anonymous=False,
    message="",
    user=None,
    recorded_by=None,
):
    """Record an offline/manual donation (cash, bank, mobile wallet).

    Creates a completed Donation + Transaction and posts Finance Income once.
    Not a gateway completion path.
    """
    from donations.models import Donation, Transaction

    if payment_method == PaymentMethod.SSLCOMMERZ:
        raise DonationCompletionError(
            "SSLCommerz donations cannot be recorded as offline/manual."
        )

    if not donor_name and not is_anonymous:
        donor_name = "Anonymous"

    txn = Transaction.objects.create(
        session_id=f"MANUAL-{uuid.uuid4().hex}",
        tran_id=generate_tran_id(),
        amount=float(to_money(amount)),
        currency="BDT",
        status=DonationStatus.COMPLETED,
        gateway=payment_method,
        cus_name=donor_name or "Anonymous",
        cus_email=donor_email or None,
        cus_phone=donor_phone or None,
        validated_on=timezone.now(),
    )
    donation = Donation.objects.create(
        donor_name=donor_name or "Anonymous",
        donor_email=donor_email or None,
        donor_phone=donor_phone or None,
        user=user,
        amount=float(to_money(amount)),
        currency="BDT",
        category=category,
        message=message or None,
        payment_method=payment_method,
        status=DonationStatus.COMPLETED,
        transaction=txn,
        is_anonymous=is_anonymous,
    )
    try:
        assign_receipt_number(donation)
        donation.save(update_fields=["receipt_number", "updated_at"])
    except Exception:
        logger.exception("Manual donation receipt assignment failed")
    _post_donation_income(donation)
    return donation


def init_payment(donation, request, method=None):
    """Start checkout via the selected gateway (SSLCommerz by default)."""
    gateway = get_gateway(method or donation.payment_method or PaymentMethod.SSLCOMMERZ)
    return gateway.init_payment(donation, request)


def validate_transaction(val_id, tran_id, amount, method=None, *, currency="BDT"):
    gateway = get_gateway(method or PaymentMethod.SSLCOMMERZ)
    return gateway.validate_transaction(
        val_id, tran_id, amount, currency=currency
    )


def generate_tran_id():
    return f"ZF{uuid.uuid4().hex[:16].upper()}"


def generate_receipt_number():
    """Unique receipt number: ZFR-YYYYMMDD-XXXXXX."""
    stamp = timezone.localtime().strftime("%Y%m%d")
    suffix = uuid.uuid4().hex[:6].upper()
    return f"ZFR-{stamp}-{suffix}"


def assign_receipt_number(donation):
    if donation.receipt_number:
        return donation.receipt_number
    for _ in range(5):
        number = generate_receipt_number()
        if not type(donation).objects.filter(receipt_number=number).exists():
            donation.receipt_number = number
            return number
    donation.receipt_number = f"ZFR-{uuid.uuid4().hex[:12].upper()}"
    return donation.receipt_number


def _admin_recipients():
    site = SiteSettings.load()
    recipients = []
    if site.primary_email:
        recipients.append(site.primary_email)
    admin_email = getattr(settings, "ADMIN_EMAIL", "") or ""
    if admin_email and admin_email not in recipients:
        recipients.append(admin_email)
    return recipients


def _donor_email(donation):
    return (donation.donor_email or "").strip()


def notify_admin_new_donation(donation):
    recipients = _admin_recipients()
    if not recipients:
        return
    site = SiteSettings.load()
    name = site.foundation_name_en or site.site_title
    try:
        send_email(
            subject=f"[{name}] New donation — {donation.amount:g} {donation.currency}",
            message=(
                f"A new donation was received.\n\n"
                f"Donor: {donation.display_name}\n"
                f"Amount: {donation.amount:g} {donation.currency}\n"
                f"Category: {donation.category.name_en}\n"
                f"Status: {donation.get_status_display()}\n"
                f"Transaction ID: {donation.transaction_id}\n"
                f"Receipt: {donation.receipt_number or '—'}\n"
            ),
            recipient_list=recipients,
            fail_silently=True,
        )
    except Exception:
        logger.exception("Admin donation notification failed")


def send_donation_success_email(donation):
    email = _donor_email(donation)
    if not email:
        return
    site = SiteSettings.load()
    name = site.foundation_name_en or site.site_title
    try:
        send_email(
            subject=f"Donation successful — {donation.amount:g} {donation.currency}",
            message=(
                f"Dear {donation.display_name},\n\n"
                f"Thank you for your donation of {donation.amount:g} {donation.currency} "
                f"to {donation.category.name_en}.\n"
                f"Transaction ID: {donation.transaction_id}\n"
                f"Receipt Number: {donation.receipt_number or '—'}\n\n"
                f"{name}"
            ),
            recipient_list=[email],
            fail_silently=True,
        )
    except Exception:
        logger.exception("Donation success email failed")


def send_receipt_email(donation, force=False):
    email = _donor_email(donation)
    if not email:
        return False
    if donation.receipt_sent and not force:
        return True

    site = SiteSettings.load()
    name = site.foundation_name_en or site.site_title
    try:
        pdf_bytes = generate_receipt_pdf(donation)
        send_email(
            subject=f"Donation Receipt {donation.receipt_number or ''} — {name}".strip(),
            message=(
                f"Dear {donation.display_name},\n\n"
                f"Please find attached your donation receipt.\n"
                f"Receipt Number: {donation.receipt_number or '—'}\n"
                f"Transaction ID: {donation.transaction_id}\n"
                f"Amount: {donation.amount:g} {donation.currency}\n\n"
                f"{name}"
            ),
            recipient_list=[email],
            attachments=[(receipt_filename(donation), pdf_bytes, "application/pdf")],
            fail_silently=True,
        )
        donation.receipt_sent = True
        donation.save(update_fields=["receipt_sent", "updated_at"])
        return True
    except Exception:
        logger.exception("Donation receipt email failed")
        return False


def send_payment_failure_email(donation):
    email = _donor_email(donation)
    if not email:
        return
    site = SiteSettings.load()
    name = site.foundation_name_en or site.site_title
    try:
        send_email(
            subject=f"Donation payment failed — {name}",
            message=(
                f"Dear {donation.display_name},\n\n"
                f"Unfortunately your donation payment of {donation.amount:g} {donation.currency} "
                f"could not be completed.\n"
                f"Transaction ID: {donation.transaction_id or '—'}\n\n"
                f"You may try again from our donation page.\n\n"
                f"{name}"
            ),
            recipient_list=[email],
            fail_silently=True,
        )
    except Exception:
        logger.exception("Payment failure email failed")


def _post_donation_income(donation):
    try:
        from finance.donation_income import ensure_income_for_donation

        ensure_income_for_donation(donation)
    except Exception:
        logger.exception("Finance income posting failed for donation %s", donation.pk)


def _assert_gateway_validation(donation, *, val_id, validation_data):
    """Service-layer invariant: gateway completion requires verified payload."""
    if not validation_data or not isinstance(validation_data, dict):
        raise DonationCompletionError(
            "Gateway validation data is required to complete this donation."
        )
    status = (validation_data.get("status") or "").upper()
    if status not in ("VALID", "VALIDATED"):
        raise DonationCompletionError("Gateway validation status is not VALID.")

    txn = donation.transaction
    if txn is None:
        raise DonationCompletionError("Donation has no transaction.")

    remote_tran = validation_data.get("tran_id")
    if not remote_tran or str(remote_tran) != str(txn.tran_id):
        raise DonationCompletionError("Validated tran_id does not match donation.")

    if not amounts_equal(validation_data.get("amount"), donation.amount):
        raise DonationCompletionError("Validated amount does not match donation.")
    if not amounts_equal(validation_data.get("amount"), txn.amount):
        raise DonationCompletionError("Validated amount does not match transaction.")

    expected_currency = normalize_currency(donation.currency or txn.currency)
    remote_currency = normalize_currency(
        validation_data.get("currency"), default=expected_currency
    )
    # If gateway omits currency, accept when expected is BDT; otherwise require match.
    if validation_data.get("currency") and remote_currency != expected_currency:
        raise DonationCompletionError("Validated currency does not match donation.")

    if not val_id and not validation_data.get("val_id"):
        raise DonationCompletionError("val_id is required for gateway completion.")


@db_transaction.atomic
def complete_donation(donation, val_id=None, validation_data=None):
    """Complete a gateway-validated donation (idempotent).

    Offline/manual donations must use :func:`create_manual_donation` instead.
    Calling this without verified ``validation_data`` is rejected.
    """
    from donations.models import Donation, Transaction

    locked = (
        Donation.objects.select_for_update()
        .select_related("transaction", "category")
        .get(pk=donation.pk)
    )
    if locked.status == DonationStatus.COMPLETED:
        _post_donation_income(locked)
        return locked

    if locked.payment_method == PaymentMethod.SSLCOMMERZ or (
        locked.transaction
        and locked.transaction.gateway == PaymentMethod.SSLCOMMERZ
    ):
        _assert_gateway_validation(
            locked, val_id=val_id, validation_data=validation_data
        )
    else:
        # Non-SSLCommerz online paths are not implemented; refuse generic completion.
        raise DonationCompletionError(
            "Unsupported payment method for gateway completion. "
            "Use create_manual_donation for offline recording."
        )

    txn = Transaction.objects.select_for_update().get(pk=locked.transaction_id)
    txn.val_id = val_id or validation_data.get("val_id")
    txn.bank_tran_id = validation_data.get("bank_tran_id")
    txn.card_type = validation_data.get("card_type")
    card_no = validation_data.get("card_no") or ""
    txn.card_no = card_no if ("*" in str(card_no) or len(str(card_no)) <= 4) else ""
    txn.card_issuer = validation_data.get("card_issuer")
    txn.risk_level = validation_data.get("risk_level")
    txn.validated_on = timezone.now()
    txn.status = DonationStatus.COMPLETED
    txn.save()

    assign_receipt_number(locked)
    locked.status = DonationStatus.COMPLETED
    locked.save()

    send_donation_success_email(locked)
    send_receipt_email(locked)
    notify_admin_new_donation(locked)
    _post_donation_income(locked)

    return locked


@db_transaction.atomic
def mark_donation_failed(donation, notify=True):
    from donations.models import Donation

    locked = Donation.objects.select_for_update().select_related("transaction").get(
        pk=donation.pk
    )
    if locked.status == DonationStatus.COMPLETED:
        return locked
    locked.status = DonationStatus.FAILED
    locked.save(update_fields=["status", "updated_at"])
    txn = locked.transaction
    txn.status = DonationStatus.FAILED
    txn.save(update_fields=["status", "updated_at"])
    if notify:
        send_payment_failure_email(locked)
    return locked
