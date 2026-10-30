"""Template helpers for conditional, permission-aware UI."""

from django import template

from rbac.permissions import has_action, has_module_access

register = template.Library()


@register.simple_tag(takes_context=True)
def can(context, module, action):
    """Usage: ``{% can "members" "approve" as can_approve %}``."""
    request = context.get("request")
    if request is None:
        return False
    return has_action(request.user, module, action)


@register.simple_tag(takes_context=True)
def can_access(context, module):
    """True if the user holds any permission in ``module``."""
    request = context.get("request")
    if request is None:
        return False
    return has_module_access(request.user, module)
