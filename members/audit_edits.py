"""Structured member/application field edits with immutable ActivityLog history."""

from __future__ import annotations

from typing import Any, Iterable

from django.db import transaction

SENSITIVE_MEMBER_FIELDS = frozenset(
    {
        "first_name",
        "last_name",
        "nid_number",
        "date_of_birth",
        "member_id",
        "status",
        "membership_type",
        "approved_at",
        "approved_by",
        "joined_at",
        "signature_image",
        "is_founder",
    }
)

SENSITIVE_APPLICATION_FIELDS = frozenset(
    {
        "bangla_name",
        "english_name",
        "identity_number",
        "identity_type",
        "date_of_birth",
        "status",
        "reviewed_by",
        "reviewed_at",
        "rejection_reason",
    }
)

MINOR_MEMBER_FIELDS = frozenset(
    {
        "phone",
        "present_address",
        "permanent_address",
        "district",
        "upazila",
        "occupation",
        "organization",
        "education",
        "blood_group",
        "gender",
        "emergency_name",
        "emergency_phone",
        "emergency_relation",
    }
)


def _serialize(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "pk"):
        return str(value.pk)
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    return str(value)


def compute_field_diffs(instance, cleaned: dict[str, Any], fields: Iterable[str]) -> dict[str, dict]:
    diffs: dict[str, dict] = {}
    for field in fields:
        if field not in cleaned:
            continue
        old = getattr(instance, field, None)
        new = cleaned[field]
        old_s, new_s = _serialize(old), _serialize(new)
        if old_s != new_s:
            diffs[field] = {"old": old_s, "new": new_s}
    return diffs


def requires_reason(diffs: dict[str, dict], sensitive_fields: frozenset) -> bool:
    return any(field in sensitive_fields for field in diffs)


@transaction.atomic
def apply_model_edits(
    instance,
    cleaned: dict[str, Any],
    *,
    actor,
    entity: str,
    reason: str = "",
    sensitive_fields: frozenset = SENSITIVE_MEMBER_FIELDS,
    fields: Iterable[str] | None = None,
    request=None,
):
    """
    Apply cleaned field values, writing one ActivityLog row with field diffs.

    Raises ValueError when sensitive fields change without a meaningful reason.
    """
    field_list = list(fields) if fields is not None else list(cleaned.keys())
    diffs = compute_field_diffs(instance, cleaned, field_list)
    if not diffs:
        return instance

    reason = (reason or "").strip()
    if requires_reason(diffs, sensitive_fields) and len(reason) < 3:
        raise ValueError(
            "A reason is required when changing sensitive official fields."
        )

    old_values = {k: v["old"] for k, v in diffs.items()}
    new_values = {k: v["new"] for k, v in diffs.items()}

    for field in diffs:
        setattr(instance, field, cleaned[field])
    instance._audit_user = actor
    instance.save()

    from accounts.signals import get_client_ip
    from audit.models import ActivityLog

    ip = get_client_ip(request) if request is not None else None
    ua = ""
    if request is not None:
        ua = (request.META.get("HTTP_USER_AGENT") or "")[:500]

    ActivityLog.objects.create(
        user=actor,
        action="FIELD_EDIT",
        entity=entity[:100],
        entity_id=str(instance.pk),
        description=f"Updated {len(diffs)} field(s) on {entity}",
        old_values=old_values,
        new_values=new_values,
        reason=reason[:2000],
        ip_address=ip,
        user_agent=ua,
    )
    return instance
