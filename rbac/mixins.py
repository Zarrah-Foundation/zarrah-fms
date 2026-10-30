"""Class-based-view guard for action permissions."""

from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied

from rbac.permissions import has_action


class ActionRequiredMixin(AccessMixin):
    """Require a single ``<module>.<action>`` permission for a CBV.

    Set ``permission_module`` (required) and optionally ``permission_action``
    (defaults to ``"view"``). Anonymous users are redirected to login;
    authenticated users lacking the permission receive a 403.
    """

    permission_module = None
    permission_action = "view"

    def get_permission_module(self):
        if self.permission_module is None:
            raise ValueError(
                f"{self.__class__.__name__} is missing 'permission_module'."
            )
        return self.permission_module

    def get_permission_action(self):
        return self.permission_action

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied(self.get_permission_denied_message())
        return super().handle_no_permission()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not has_action(request.user, self.get_permission_module(), self.get_permission_action()):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)
