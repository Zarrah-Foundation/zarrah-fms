"""Member-centric membership fee summaries (contiguous paid-through semantics)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Count, OuterRef, Prefetch, Q, Subquery

from core.choices import DonationStatus
from members.billing import (
    add_months,
    current_year_month,
    ensure_ledger_months,
    get_or_create_autopay,
    member_join_period,
    paid_through,
    period_tuple,
)
from members.fee_settings import get_monthly_fee_amount, get_registration_fee_amount
from members.models import (
    MembershipAutoPay,
    MembershipFee,
    MembershipFeePayment,
    MembershipRegistrationFee,
)
from members.periods import format_fee_period, format_fee_period_short


@dataclass
class MemberFeeSummary:
    member: object
    monthly_fee: Decimal
    paid_through: tuple[int, int] | None
    pending_months: int
    pending_amount: Decimal
    paid_months: int
    autopay_enabled: bool
    autopay_mode: str
    last_payment: MembershipFeePayment | None
    next_due: tuple[int, int] | None
    current_year: int
    current_month: int
    registration_fee_amount: Decimal = Decimal("0")
    registration_fee_status: str = ""
    fee_start: tuple[int, int] | None = None

    @property
    def paid_through_label(self) -> str:
        if not self.paid_through:
            return ""
        return format_fee_period(*self.paid_through)

    @property
    def paid_through_label_short(self) -> str:
        if not self.paid_through:
            return ""
        return format_fee_period_short(*self.paid_through)

    @property
    def next_due_label(self) -> str:
        if not self.next_due:
            return ""
        return format_fee_period(*self.next_due)

    @property
    def autopay_label(self) -> str:
        return "ON" if self.autopay_enabled else "OFF"

    @property
    def registration_fee_paid(self) -> bool:
        return self.registration_fee_status == DonationStatus.COMPLETED

    @property
    def fee_start_label(self) -> str:
        if not self.fee_start:
            return ""
        return format_fee_period(*self.fee_start)

    @property
    def fee_start_label_short(self) -> str:
        if not self.fee_start:
            return ""
        return format_fee_period_short(*self.fee_start)


def _next_due_from_paid_through(pt: tuple[int, int] | None, cy: int, cm: int) -> tuple[int, int] | None:
    if pt is None:
        return (cy, cm)
    ny, nm = add_months(pt[0], pt[1], 1)
    return (ny, nm)


def _paid_through_from_set(member, paid: set) -> tuple[int, int] | None:
    """Contiguous paid-through using a prefetched set of (year, month)."""
    if not paid:
        return None
    start_y, start_m = member_join_period(member)
    max_paid = max(paid)
    y, m = start_y, start_m
    last = None
    while (y, m) <= max_paid:
        if (y, m) not in paid:
            break
        last = (y, m)
        y, m = add_months(y, m, 1)
    return period_tuple(*last) if last else None


def _registration_info(member):
    try:
        reg = member.registration_fee
    except MembershipRegistrationFee.DoesNotExist:
        reg = None
    if reg is None:
        return Decimal(str(get_registration_fee_amount())), DonationStatus.PENDING
    return Decimal(str(reg.amount)), reg.status


def summarize_member_fees(member, *, ensure_ledger: bool = True) -> MemberFeeSummary:
    """Build a fee summary for one member. Optionally ensure ledger through current month."""
    cy, cm = current_year_month()
    if ensure_ledger:
        ensure_ledger_months(member, cy, cm)

    monthly = Decimal(str(get_monthly_fee_amount()))
    fees_qs = MembershipFee.objects.filter(member=member)
    paid_count = fees_qs.filter(status=DonationStatus.COMPLETED).count()
    # Pending only for periods up to current month (future prepaid months are not pending).
    pending_qs = fees_qs.filter(status=DonationStatus.PENDING).filter(
        Q(year__lt=cy) | Q(year=cy, month__lte=cm)
    )
    pending_count = pending_qs.count()
    pending_amount = sum(
        (Decimal(str(f.amount)) for f in pending_qs.only("amount")),
        Decimal("0"),
    )
    if pending_count and pending_amount == 0:
        pending_amount = monthly * pending_count
    pt = paid_through(member)
    autopay = get_or_create_autopay(member)
    last_payment = (
        MembershipFeePayment.objects.filter(
            member=member, status=DonationStatus.COMPLETED
        )
        .order_by("-created_at")
        .first()
    )
    reg_amount, reg_status = _registration_info(member)
    return MemberFeeSummary(
        member=member,
        monthly_fee=monthly,
        paid_through=pt,
        pending_months=pending_count,
        pending_amount=pending_amount,
        paid_months=paid_count,
        autopay_enabled=bool(autopay.is_enabled),
        autopay_mode=autopay.mode or "",
        last_payment=last_payment,
        next_due=_next_due_from_paid_through(pt, cy, cm),
        current_year=cy,
        current_month=cm,
        registration_fee_amount=reg_amount,
        registration_fee_status=reg_status,
        fee_start=member_join_period(member),
    )


def annotate_members_for_fee_list(qs):
    """Annotate a Member queryset for the admin fee list (avoids N+1 pending counts)."""
    cy, cm = current_year_month()
    pending_filter = Q(membership_fees__status=DonationStatus.PENDING) & (
        Q(membership_fees__year__lt=cy) | Q(membership_fees__year=cy, membership_fees__month__lte=cm)
    )
    paid_filter = Q(membership_fees__status=DonationStatus.COMPLETED)
    last_pay = (
        MembershipFeePayment.objects.filter(
            member_id=OuterRef("pk"), status=DonationStatus.COMPLETED
        )
        .order_by("-created_at")
        .values("created_at")[:1]
    )
    return qs.annotate(
        pending_months_count=Count("membership_fees", filter=pending_filter, distinct=True),
        paid_months_count=Count("membership_fees", filter=paid_filter, distinct=True),
        last_payment_at=Subquery(last_pay),
    ).select_related("user", "membership_type", "auto_pay", "registration_fee").prefetch_related(
        Prefetch(
            "membership_fees",
            queryset=MembershipFee.objects.filter(status=DonationStatus.COMPLETED).only(
                "id", "member_id", "year", "month", "status"
            ),
            to_attr="_completed_fees_cached",
        ),
        Prefetch(
            "fee_payments",
            queryset=MembershipFeePayment.objects.filter(
                status=DonationStatus.COMPLETED
            ).order_by("-created_at"),
            to_attr="_completed_payments_cached",
        ),
    )


def summaries_for_members(members) -> dict:
    """Return {member.pk: MemberFeeSummary} without ensuring ledger (list view)."""
    cy, cm = current_year_month()
    monthly = Decimal(str(get_monthly_fee_amount()))
    result = {}
    for member in members:
        pending = int(getattr(member, "pending_months_count", 0) or 0)
        paid = int(getattr(member, "paid_months_count", 0) or 0)
        completed = getattr(member, "_completed_fees_cached", None)
        if completed is not None:
            paid_set = {(f.year, f.month) for f in completed}
            pt = _paid_through_from_set(member, paid_set)
        else:
            pt = paid_through(member)
        try:
            autopay = member.auto_pay
        except MembershipAutoPay.DoesNotExist:
            autopay = None
        payments = getattr(member, "_completed_payments_cached", None)
        if payments is not None:
            last_payment = payments[0] if payments else None
        else:
            last_at = getattr(member, "last_payment_at", None)
            last_payment = None
            if last_at:
                last_payment = (
                    MembershipFeePayment.objects.filter(
                        member=member, status=DonationStatus.COMPLETED, created_at=last_at
                    ).first()
                )
        reg_amount, reg_status = _registration_info(member)
        result[member.pk] = MemberFeeSummary(
            member=member,
            monthly_fee=monthly,
            paid_through=pt,
            pending_months=pending,
            pending_amount=monthly * pending,
            paid_months=paid,
            autopay_enabled=bool(getattr(autopay, "is_enabled", False)),
            autopay_mode=getattr(autopay, "mode", "") or "",
            last_payment=last_payment,
            next_due=_next_due_from_paid_through(pt, cy, cm),
            current_year=cy,
            current_month=cm,
            registration_fee_amount=reg_amount,
            registration_fee_status=reg_status,
            fee_start=member_join_period(member),
        )
    return result
