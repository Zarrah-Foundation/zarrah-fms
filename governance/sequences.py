"""DB-safe sequence allocation for meeting references and resolution IDs."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from governance.models import SequenceCounter

MEETING_SEQUENCE_KEY = "meeting_reference"
RESOLUTION_SEQUENCE_KEY = "resolution_id"


@transaction.atomic
def next_sequence(key: str, *, year: int = 0, month: int = 0) -> int:
    """
    Atomically allocate the next integer for ``key`` / period.

    Uses ``select_for_update`` so concurrent callers never share a value.
    Consumed numbers are never recycled.
    """
    key = (key or "").strip()
    if not key:
        raise ValueError("Sequence key is required.")

    counter, _ = SequenceCounter.objects.select_for_update().get_or_create(
        key=key,
        year=year,
        month=month,
        defaults={"last_value": 0},
    )
    # Re-fetch under lock in case get_or_create raced without a lock on create path.
    counter = SequenceCounter.objects.select_for_update().get(pk=counter.pk)
    counter.last_value += 1
    counter.save(update_fields=["last_value", "updated_at"])
    return counter.last_value


def generate_meeting_reference() -> str:
    """Allocate ``MTG-{YYYY}-{#####}`` (immutable once assigned to a Meeting)."""
    year = timezone.localdate().year
    seq = next_sequence(MEETING_SEQUENCE_KEY, year=year, month=0)
    return f"MTG-{year}-{seq:05d}"


def generate_resolution_id() -> str:
    """Allocate ``ZF-{YYYY}-{MM}-{###}`` (immutable once assigned to a Resolution)."""
    when = timezone.localdate()
    seq = next_sequence(
        RESOLUTION_SEQUENCE_KEY,
        year=when.year,
        month=when.month,
    )
    return f"ZF-{when.year}-{when.month:02d}-{seq:03d}"
