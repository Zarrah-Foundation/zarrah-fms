"""Function-based-view guards for action permissions.

``role_required`` in ``dashboard.views`` is intentionally left in place; this
is an additive, more granular alternative — nothing that used the old helper
needs to change.
"""

from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from rbac.permissions import has_action


def require_action(module, action):
    """Decorator: require ``<module>.<action>`` for a view.

    Anonymous users are sent to login; authenticated users without the
    permission get a 403.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not has_action(request.user, module, action):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator
