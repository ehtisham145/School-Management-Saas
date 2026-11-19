from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from apps.audit.models import AuditEvent


def list_audit_events(*, action=None, target_type=None, school=None, search=""):
    events = AuditEvent.objects.select_related("school")

    if action:
        events = events.filter(action=action)
    if target_type:
        events = events.filter(target_type=target_type)
    if school:
        events = events.filter(school_id=school)
    if search:
        events = events.filter(Q(actor_label__icontains=search) | Q(target_label__icontains=search))
    return events.order_by("-created_at", "-id")


def count_trials_started_from(ip_address, *, hours=24):
    """Free trials started from one network in the last day, for the sign-up limit."""
    if not ip_address:
        return 0
    return AuditEvent.objects.filter(
        action=AuditEvent.Action.SUBSCRIPTION_ACTIVATED,
        ip_address=ip_address,
        details__trial=True,
        created_at__gte=timezone.now() - timedelta(hours=hours),
    ).count()
