from django.conf import settings
from rest_framework.permissions import BasePermission

from apps.core.policies import can


class TrustedOrigin(BasePermission):
    """For public sign-in endpoints, which have no session and so no CSRF check.

    Without this, a form on another website could sign a visitor in to the attacker's
    account. Browsers always send Origin on such a request. Clients with no Origin aren't
    browsers, so they carry no visitor's cookies to abuse.
    """

    message = "This request came from another website."

    def has_permission(self, request, view):
        origin = request.headers.get("Origin")
        if origin is None:
            return True
        own_origin = f"{request.scheme}://{request.get_host()}"
        return origin.lower() in {
            own_origin.lower(),
            *map(str.lower, settings.CSRF_TRUSTED_ORIGINS),
        }


class HasPolicy(BasePermission):
    """Views map each action to a policy; an unmapped action is denied."""

    def has_permission(self, request, view):
        action = getattr(view, "policies", {}).get(view.action)
        return action is not None and can(request.role, action)
