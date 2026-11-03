from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from apps.accounts.selectors import needs_2fa_setup
from apps.core.policies import can


class TwoFactorSetupRequired(PermissionDenied):
    default_code = "2fa_setup_required"
    default_detail = "Set up two-factor authentication to continue."


class HasPolicy(BasePermission):
    """Views map each action to a policy; an unmapped action is denied."""

    def has_permission(self, request, view):
        action = getattr(view, "policies", {}).get(view.action)
        if action is None or not can(request.role, action):
            return False
        if needs_2fa_setup(request.user):
            raise TwoFactorSetupRequired()
        return True
