from django.db.models import Count, OuterRef, Q, Subquery

from apps.accounts.models import User
from apps.platform.models import DemoRequest
from apps.tenancy.models import Membership, School

RECENT_LIMIT = 5


def is_email_registered(email):
    """True when a user account or a school already has this email, in any letter case."""
    return (
        User.objects.filter(email__iexact=email).exists()
        or School.objects.filter(email__iexact=email).exists()
    )


def list_schools(*, status=None, search=""):
    first_admin = Membership.objects.filter(
        school=OuterRef("pk"), role=Membership.Role.SCHOOL_ADMIN
    ).order_by("id")
    schools = School.objects.annotate(
        member_count=Count("membership"),
        school_admin_email=Subquery(first_admin.values("user__email")[:1]),
    )

    if status:
        schools = schools.filter(is_active=status == "active")
    if search:
        schools = schools.filter(
            Q(name_en__icontains=search)
            | Q(name_ar__icontains=search)
            | Q(code__icontains=search)
            | Q(city__icontains=search)
        )
    return schools.order_by("-created_at", "-id")


def get_school_counts():
    return School.objects.aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(is_active=True)),
        inactive=Count("id", filter=Q(is_active=False)),
    )


def list_demo_requests(*, status=None, search=""):
    demos = DemoRequest.objects.select_related("converted_school")

    if status:
        demos = demos.filter(status=status)
    if search:
        demos = demos.filter(
            Q(name__icontains=search)
            | Q(school_name__icontains=search)
            | Q(email__icontains=search)
            | Q(phone__icontains=search)
        )
    return demos.order_by("-created_at", "-id")


def get_demo_request_counts():
    """Every status is present, including those with no requests yet."""
    counts = dict(DemoRequest.objects.order_by().values_list("status").annotate(count=Count("id")))
    by_status = {status: counts.get(status, 0) for status in DemoRequest.Status.values}
    return {"total": sum(by_status.values()), "by_status": by_status}


def get_dashboard_overview():
    return {
        "schools": get_school_counts(),
        "demo_requests": get_demo_request_counts(),
        "recent_schools": list_schools()[:RECENT_LIMIT],
        "recent_demo_requests": list_demo_requests()[:RECENT_LIMIT],
    }
