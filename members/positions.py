"""Organizational position assignment services."""

from __future__ import annotations

from datetime import date
from typing import Optional

from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone
from django.utils.translation import get_language

from members.models import Member, MemberPositionAssignment, OrganizationalPosition


def _today() -> date:
    return timezone.localdate()


def effective_assignments(
    member: Member,
    *,
    on_date: Optional[date] = None,
) -> QuerySet[MemberPositionAssignment]:
    """Assignments active and date-effective on ``on_date`` (default today)."""
    on_date = on_date or _today()
    return (
        MemberPositionAssignment.objects.filter(
            member=member,
            is_active=True,
            start_date__lte=on_date,
        )
        .filter(Q(end_date__isnull=True) | Q(end_date__gte=on_date))
        .select_related("position")
        .order_by("-is_primary", "start_date", "position__display_order")
    )


def primary_assignment(
    member: Member,
    *,
    on_date: Optional[date] = None,
) -> Optional[MemberPositionAssignment]:
    qs = effective_assignments(member, on_date=on_date)
    primary = qs.filter(is_primary=True).first()
    if primary is not None:
        return primary
    return qs.first()


def format_position_label(
    assignment: Optional[MemberPositionAssignment],
    *,
    lang: Optional[str] = None,
) -> str:
    """Return ``Position — Council`` for documents/UI."""
    if assignment is None:
        return ""
    lang = (lang or get_language() or "en").split("-")[0].lower()
    pos = assignment.position
    title = pos.localized_name(lang)
    council = str(pos.get_council_body_display())
    label = f"{title} — {council}".strip(" —")
    return label[:150]


def member_position_snapshot(member: Member, *, lang: Optional[str] = None) -> str:
    """Designation string for resolution signature snapshots."""
    assignment = primary_assignment(member)
    label = format_position_label(assignment, lang=lang)
    if label:
        return label
    mtype = getattr(member, "membership_type", None)
    if mtype is not None:
        fallback = getattr(mtype, "name_en", "") or getattr(mtype, "name_bn", "")
        if fallback:
            return str(fallback)[:150]
    return (member.occupation or "")[:150]


def _log(
    actor,
    action: str,
    assignment: MemberPositionAssignment,
    description: str,
    *,
    old=None,
    new=None,
    reason: str = "",
):
    if actor is None or not getattr(actor, "is_authenticated", False):
        return
    from audit.models import ActivityLog

    ActivityLog.objects.create(
        user=actor,
        action=action[:100],
        entity="MemberPositionAssignment",
        entity_id=str(assignment.pk),
        description=description,
        old_values=old,
        new_values=new,
        reason=(reason or "")[:2000],
    )


@transaction.atomic
def assign_position(
    member: Member,
    position: OrganizationalPosition,
    *,
    start_date: date,
    end_date: Optional[date] = None,
    is_primary: bool = False,
    notes: str = "",
    actor=None,
    reason: str = "",
) -> MemberPositionAssignment:
    if not position.is_active:
        raise ValueError("Cannot assign an inactive position.")
    if end_date and end_date < start_date:
        raise ValueError("End date cannot be before start date.")
    if is_primary and not position.is_primary_eligible:
        raise ValueError("This position cannot be marked primary.")

    if is_primary:
        MemberPositionAssignment.objects.filter(
            member=member, is_primary=True, is_active=True
        ).update(is_primary=False)

    assignment = MemberPositionAssignment.objects.create(
        member=member,
        position=position,
        start_date=start_date,
        end_date=end_date,
        is_active=True,
        is_primary=bool(is_primary),
        notes=(notes or "")[:2000],
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
    )
    _log(
        actor,
        "POSITION_ASSIGN",
        assignment,
        f"Assigned {position.name_en} to {member.member_id}",
        new={
            "position": position.name_en,
            "council": position.council_body,
            "start_date": str(start_date),
            "end_date": str(end_date) if end_date else None,
            "is_primary": assignment.is_primary,
        },
        reason=reason,
    )
    return assignment


@transaction.atomic
def update_assignment(
    assignment: MemberPositionAssignment,
    *,
    start_date: Optional[date] = None,
    end_date=...,
    is_primary: Optional[bool] = None,
    notes: Optional[str] = None,
    actor=None,
    reason: str = "",
) -> MemberPositionAssignment:
    assignment = (
        MemberPositionAssignment.objects.select_for_update()
        .select_related("position", "member")
        .get(pk=assignment.pk)
    )
    old = {
        "start_date": str(assignment.start_date),
        "end_date": str(assignment.end_date) if assignment.end_date else None,
        "is_primary": assignment.is_primary,
        "notes": assignment.notes,
    }
    if start_date is not None:
        assignment.start_date = start_date
    if end_date is not ...:
        assignment.end_date = end_date
    if assignment.end_date and assignment.end_date < assignment.start_date:
        raise ValueError("End date cannot be before start date.")
    if is_primary is not None:
        if is_primary and not assignment.position.is_primary_eligible:
            raise ValueError("This position cannot be marked primary.")
        if is_primary:
            MemberPositionAssignment.objects.filter(
                member=assignment.member, is_primary=True, is_active=True
            ).exclude(pk=assignment.pk).update(is_primary=False)
        assignment.is_primary = is_primary
    if notes is not None:
        assignment.notes = notes[:2000]
    assignment.save()
    _log(
        actor,
        "POSITION_UPDATE",
        assignment,
        f"Updated position assignment for {assignment.member.member_id}",
        old=old,
        new={
            "start_date": str(assignment.start_date),
            "end_date": str(assignment.end_date) if assignment.end_date else None,
            "is_primary": assignment.is_primary,
            "notes": assignment.notes,
        },
        reason=reason,
    )
    return assignment


@transaction.atomic
def end_position(
    assignment: MemberPositionAssignment,
    *,
    end_date: Optional[date] = None,
    actor=None,
    reason: str = "",
) -> MemberPositionAssignment:
    assignment = MemberPositionAssignment.objects.select_for_update().get(pk=assignment.pk)
    old = {
        "is_active": assignment.is_active,
        "end_date": str(assignment.end_date) if assignment.end_date else None,
        "is_primary": assignment.is_primary,
    }
    assignment.end_date = end_date or _today()
    assignment.is_active = False
    assignment.is_primary = False
    assignment.save(update_fields=["end_date", "is_active", "is_primary", "updated_at"])
    _log(
        actor,
        "POSITION_END",
        assignment,
        f"Ended position for {assignment.member.member_id}",
        old=old,
        new={
            "is_active": False,
            "end_date": str(assignment.end_date),
            "is_primary": False,
        },
        reason=reason,
    )
    return assignment


@transaction.atomic
def set_primary_assignment(
    assignment: MemberPositionAssignment,
    *,
    actor=None,
    reason: str = "",
) -> MemberPositionAssignment:
    return update_assignment(
        assignment,
        is_primary=True,
        actor=actor,
        reason=reason or "Set as primary organizational position.",
    )
