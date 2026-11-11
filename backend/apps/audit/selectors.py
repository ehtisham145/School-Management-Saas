from django.db.models import Q

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
