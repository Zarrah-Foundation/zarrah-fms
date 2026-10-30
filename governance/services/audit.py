"""Governance activity logging via audit.ActivityLog."""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def log_governance(
    actor,
    action: str,
    entity: str,
    entity_id,
    description: str,
    old: Optional[dict[str, Any]] = None,
    new: Optional[dict[str, Any]] = None,
):
    """
    Persist a governance audit row.

    Skips silently when ``actor`` is missing or unauthenticated (ActivityLog.user
    is required).
    """
    if actor is None or not getattr(actor, "is_authenticated", False):
        return None

    from audit.models import ActivityLog

    try:
        return ActivityLog.objects.create(
            user=actor,
            action=str(action)[:100],
            entity=str(entity)[:100],
            entity_id=str(entity_id) if entity_id is not None else None,
            description=description or "",
            old_values=old,
            new_values=new,
        )
    except Exception:
        logger.exception(
            "Failed to write governance ActivityLog action=%s entity=%s id=%s",
            action,
            entity,
            entity_id,
        )
        return None
