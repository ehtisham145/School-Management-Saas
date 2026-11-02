from rest_framework.permissions import BasePermission

from apps.core.policies import can


class HasPolicy(BasePermission):
    """Views map each action to a policy; an unmapped action is denied."""

    def has_permission(self, request, view):
        action = getattr(view, "policies", {}).get(view.action)
        return action is not None and can(request.role, action)


# Here we are verifying the permissions for every single role
