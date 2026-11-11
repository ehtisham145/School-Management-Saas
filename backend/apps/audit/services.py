import ipaddress
from dataclasses import dataclass

from django.conf import settings
from django.db import transaction

from apps.audit.models import AuditEvent

Action = AuditEvent.Action


@dataclass(frozen=True)
class Actor:
    """Who did something and from where. `user` is None for scheduled jobs."""

    user: object = None
    ip_address: str | None = None

    @property
    def user_id(self):
        return getattr(self.user, "id", None)


SYSTEM = Actor()


def client_ip(request):
    """The caller's IP address.

    Behind Caddy, REMOTE_ADDR is the proxy, so production reads X-Forwarded-For, which
    Caddy sets itself and never takes from the client (staging/caddy/Caddyfile).
    """
    if settings.TRUST_X_FORWARDED_FOR:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        candidate = forwarded.split(",")[0].strip()
    else:
        candidate = request.META.get("REMOTE_ADDR", "")
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return None


def actor_from_request(request):
    return Actor(user=request.user, ip_address=client_ip(request))


def _label(user):
    if user is None:
        return ""
    return user.email or user.username


def record_event(actor, action, target, *, label="", school=None, details=None):
    """Adds one entry to the audit log.

    Runs inside the caller's transaction, so the entry exists only if the change does.
    """
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError("record_event must run inside the transaction that makes the change")
    return AuditEvent.objects.create(
        actor=actor.user,
        actor_label=_label(actor.user),
        action=action,
        target_type=target._meta.model_name,
        target_id=target.pk,
        target_label=(label or str(target))[:300],
        school=school,
        ip_address=actor.ip_address,
        details=details or {},
    )
