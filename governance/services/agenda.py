"""Meeting agenda items and proceedings (minutes)."""

from __future__ import annotations

import logging
from typing import Iterable, Optional
from uuid import UUID

from django.db import transaction
from django.db.models import Max

from core.html_sanitize import sanitize_html
from governance.models import Meeting, MeetingAgendaItem, MeetingProceeding
from governance.services.audit import log_governance

logger = logging.getLogger(__name__)


def _next_agenda_number(meeting: Meeting) -> int:
    current = (
        MeetingAgendaItem.objects.filter(meeting=meeting)
        .aggregate(m=Max("number"))
        .get("m")
    )
    return int(current or 0) + 1


@transaction.atomic
def add_agenda_item(
    meeting: Meeting,
    *,
    title_bn: str,
    title_en: str = "",
    description_bn: str = "",
    description_en: str = "",
    presenter_name: str = "",
    presenter_member=None,
    supporting_document=None,
    actor=None,
) -> MeetingAgendaItem:
    """Append an agenda item with auto-incremented number and display_order."""
    meeting = Meeting.objects.select_for_update().get(pk=meeting.pk)
    title_bn = (title_bn or "").strip()
    if not title_bn:
        raise ValueError("title_bn is required.")

    number = _next_agenda_number(meeting)
    item = MeetingAgendaItem.objects.create(
        meeting=meeting,
        number=number,
        display_order=number,
        title_bn=title_bn,
        title_en=(title_en or "").strip(),
        description_bn=description_bn or "",
        description_en=description_en or "",
        presenter_name=(presenter_name or "").strip(),
        presenter_member=presenter_member,
        supporting_document=supporting_document,
    )
    log_governance(
        actor,
        "AGENDA_ADD",
        "MeetingAgendaItem",
        item.pk,
        f"Added agenda item {number} on {meeting.reference_id}",
        new={"number": number, "title_bn": title_bn},
    )
    return item


@transaction.atomic
def update_agenda_item(
    item: MeetingAgendaItem,
    *,
    actor=None,
    **fields,
) -> MeetingAgendaItem:
    """Update allowed agenda fields for an item belonging to its meeting."""
    item = MeetingAgendaItem.objects.select_for_update().select_related("meeting").get(
        pk=item.pk
    )
    allowed = {
        "title_bn",
        "title_en",
        "description_bn",
        "description_en",
        "presenter_name",
        "presenter_member",
        "supporting_document",
        "status",
        "notes",
    }
    updates = []
    old = {}
    new = {}
    for key, value in fields.items():
        if key not in allowed:
            raise ValueError(f"Field '{key}' cannot be updated on agenda items.")
        if key in ("title_bn", "title_en", "presenter_name") and value is not None:
            value = str(value).strip()
        if key == "title_bn" and not value:
            raise ValueError("title_bn is required.")
        old[key] = getattr(item, key)
        setattr(item, key, value)
        new[key] = value
        updates.append(key)

    if not updates:
        return item

    updates.append("updated_at")
    item.save(update_fields=updates)
    log_governance(
        actor,
        "AGENDA_UPDATE",
        "MeetingAgendaItem",
        item.pk,
        f"Updated agenda item {item.number} on {item.meeting.reference_id}",
        old=old,
        new=new,
    )
    return item


@transaction.atomic
def delete_agenda_item(item: MeetingAgendaItem, *, actor=None) -> None:
    """Delete an agenda item and renumber remaining items on the meeting."""
    item = MeetingAgendaItem.objects.select_for_update().select_related("meeting").get(
        pk=item.pk
    )
    meeting = item.meeting
    number = item.number
    pk = item.pk
    item.delete()
    reorder_agenda(
        meeting,
        list(
            MeetingAgendaItem.objects.filter(meeting=meeting)
            .order_by("display_order", "number")
            .values_list("pk", flat=True)
        ),
        actor=actor,
        audit=False,
    )
    log_governance(
        actor,
        "AGENDA_DELETE",
        "MeetingAgendaItem",
        pk,
        f"Deleted agenda item {number} on {meeting.reference_id}",
    )


@transaction.atomic
def reorder_agenda(
    meeting: Meeting,
    ordered_ids: Iterable[UUID | str],
    *,
    actor=None,
    audit: bool = True,
) -> list[MeetingAgendaItem]:
    """
    Reorder agenda items for ``meeting``.

    ``ordered_ids`` must be a complete permutation of this meeting's agenda
    item PKs. Foreign items raise ``ValueError`` (IDOR / ownership guard).
    """
    meeting = Meeting.objects.select_for_update().get(pk=meeting.pk)
    ids = [str(i) for i in ordered_ids]
    existing = {
        str(pk): item
        for pk, item in (
            (str(i.pk), i)
            for i in MeetingAgendaItem.objects.select_for_update().filter(meeting=meeting)
        )
    }
    if set(ids) != set(existing.keys()):
        raise ValueError(
            "Agenda reorder list must include exactly this meeting's agenda items."
        )
    if len(ids) != len(set(ids)):
        raise ValueError("Agenda reorder list contains duplicates.")

    # Two-phase update avoids uniq_meeting_agenda_number collisions mid-reorder.
    offset = 10_000
    for index, item_id in enumerate(ids, start=1):
        item = existing[item_id]
        item.number = offset + index
        item.display_order = offset + index
        item.save(update_fields=["number", "display_order", "updated_at"])

    updated: list[MeetingAgendaItem] = []
    for index, item_id in enumerate(ids, start=1):
        item = existing[item_id]
        item.number = index
        item.display_order = index
        item.save(update_fields=["number", "display_order", "updated_at"])
        updated.append(item)

    if audit:
        log_governance(
            actor,
            "AGENDA_REORDER",
            "Meeting",
            meeting.pk,
            f"Reordered agenda for {meeting.reference_id}",
            new={"order": ids},
        )
    return updated


@transaction.atomic
def save_proceedings(
    meeting: Meeting,
    *,
    content_bn: str = "",
    content_en: str = "",
    actor=None,
) -> MeetingProceeding:
    """Create or update sanitized meeting minutes (Bangla primary)."""
    meeting = Meeting.objects.select_for_update().get(pk=meeting.pk)
    bn = sanitize_html(content_bn or "")
    en = sanitize_html(content_en or "")
    proceeding, _created = MeetingProceeding.objects.select_for_update().get_or_create(
        meeting=meeting,
        defaults={
            "content_bn": bn,
            "content_en": en,
            "updated_by": actor if getattr(actor, "is_authenticated", False) else None,
        },
    )
    if not _created:
        proceeding.content_bn = bn
        proceeding.content_en = en
        if getattr(actor, "is_authenticated", False):
            proceeding.updated_by = actor
        proceeding.save(
            update_fields=["content_bn", "content_en", "updated_by", "updated_at"]
        )

    log_governance(
        actor,
        "PROCEEDINGS_SAVE",
        "Meeting",
        meeting.pk,
        f"Saved proceedings for {meeting.reference_id}",
    )
    return proceeding
