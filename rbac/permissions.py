"""Runtime permission checks.

The public entry point is :func:`has_action`. It is intentionally forgiving so
the app keeps working during/after rollout:

* Superusers always pass.
* A user's effective permissions are the union of all permissions from
  (a) explicitly assigned roles (``UserRole``) and
  (b) any role whose ``legacy_role`` matches the historical
  ``accounts.User.role`` value — this preserves backward compatibility for
  every existing account with zero data migration.

Codenames are cached on the user instance for the lifetime of the request to
avoid repeated queries within a single view/template render.
"""

from rbac.models import Role, RolePermission, UserRole

_CACHE_ATTR = "_rbac_codenames_cache"
# Sentinel meaning "every permission" (superusers).
_ALL = object()


def _role_ids_for_user(user):
    role_ids = set(
        UserRole.objects.filter(user=user, role__is_active=True).values_list("role_id", flat=True)
    )
    legacy = getattr(user, "role", None)
    if legacy:
        role_ids.update(
            Role.objects.filter(is_active=True, legacy_role=legacy).values_list("id", flat=True)
        )
    return role_ids


def get_permission_codenames(user):
    """Return the set of ``<module>.<action>`` codenames a user holds.

    Returns the ``_ALL`` sentinel for superusers.
    """
    if not getattr(user, "is_authenticated", False):
        return set()
    if getattr(user, "is_superuser", False):
        return _ALL

    cached = getattr(user, _CACHE_ATTR, None)
    if cached is not None:
        return cached

    role_ids = _role_ids_for_user(user)
    codenames = set(
        RolePermission.objects.filter(role_id__in=role_ids).values_list(
            "permission__codename", flat=True
        )
    )
    setattr(user, _CACHE_ATTR, codenames)
    return codenames


def has_action(user, module, action):
    """True if ``user`` may perform ``action`` on ``module``."""
    codes = get_permission_codenames(user)
    if codes is _ALL:
        return True
    return f"{module}.{action}" in codes


def has_module_access(user, module):
    """True if the user holds *any* permission within ``module`` (menu gating)."""
    codes = get_permission_codenames(user)
    if codes is _ALL:
        return True
    prefix = f"{module}."
    return any(code.startswith(prefix) for code in codes)


def clear_cache(user):
    """Drop the per-request codename cache (call after changing assignments)."""
    if hasattr(user, _CACHE_ATTR):
        delattr(user, _CACHE_ATTR)
