from datetime import timedelta

from django.db.models import Count, IntegerField, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.accounts.models import User
from apps.classroom.models import Classroom, Student, UpgradeRequest
from apps.platform.models import DemoRequest, Plan, Quotation, Subscription
from apps.tenancy.models import Membership, School

RECENT_LIMIT = 5
# A user counts as active when they signed in within this many days.
ACTIVE_USER_DAYS = 30
Role = Membership.Role


def is_email_registered(email):
    """True when a user account or a school already has this email, in any letter case."""
    return (
        User.objects.filter(email__iexact=email).exists()
        or School.objects.filter(email__iexact=email).exists()
    )


def _schools():
    """Real schools. Individual teachers' private workspaces are not listed as schools."""
    return School.objects.filter(kind=School.Kind.SCHOOL)


def list_schools(*, status=None, search=""):
    first_admin = Membership.objects.filter(
        school=OuterRef("pk"), role=Membership.Role.SCHOOL_ADMIN
    ).order_by("id")
    schools = _schools().annotate(
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
    return _schools().aggregate(
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


# --- Plans and subscriptions


def get_current_subscription(school, today=None):
    """The subscription that covers today, even before the nightly job has expired an old one."""
    today = today or timezone.localdate()
    return (
        Subscription.objects.filter(
            school=school, status=Subscription.Status.ACTIVE, ends_on__gt=today
        )
        .select_related("plan")
        .order_by("-ends_on")
        .first()
    )


def _count_for_workspace(queryset):
    counted = (
        queryset.filter(school=OuterRef("pk"))
        .order_by()
        .values("school")
        .annotate(total=Count("pk"))
        .values("total")
    )
    return Coalesce(Subquery(counted, output_field=IntegerField()), Value(0))


def _individual_teachers():
    today = timezone.localdate()
    teacher = Membership.objects.filter(school=OuterRef("pk"), role=Role.TEACHER).order_by("id")
    current = Subscription.objects.filter(
        school=OuterRef("pk"), status=Subscription.Status.ACTIVE, ends_on__gt=today
    ).order_by("-ends_on")
    pending = UpgradeRequest.objects.filter(
        school=OuterRef("pk"), status=UpgradeRequest.Status.PENDING
    )
    return School.objects.filter(kind=School.Kind.INDIVIDUAL).annotate(
        teacher_email=Subquery(teacher.values("user__email")[:1]),
        class_count=_count_for_workspace(Classroom.objects.all()),
        student_count=_count_for_workspace(Student.objects.all()),
        plan_code=Subquery(current.values("plan__code")[:1]),
        is_trial=Subquery(current.values("is_trial")[:1]),
        ends_on=Subquery(current.values("ends_on")[:1]),
        requested_plan=Subquery(pending.values("plan")[:1]),
    )


def list_individual_teachers(*, search="", status=None):
    teachers = _individual_teachers()
    if status == "trial":
        teachers = teachers.filter(is_trial=True)
    elif status == "paid":
        teachers = teachers.filter(is_trial=False)
    elif status == "ended":
        teachers = teachers.filter(plan_code__isnull=True)
    if search:
        teachers = teachers.filter(
            Q(name_en__icontains=search) | Q(teacher_email__icontains=search)
        )
    return teachers.order_by("-created_at", "-id")


def get_individual_teacher(workspace_id):
    return get_object_or_404(_individual_teachers(), pk=workspace_id)


def get_active_trial(user):
    """The running free trial of this user's own workspace, if there is one."""
    return (
        Subscription.objects.filter(
            school__kind=School.Kind.INDIVIDUAL,
            school__membership__user=user,
            status=Subscription.Status.ACTIVE,
            is_trial=True,
        )
        .order_by("-ends_on")
        .first()
    )


def list_plans(*, active=None):
    plans = Plan.objects.annotate(
        active_subscriptions=Count(
            "subscriptions", filter=Q(subscriptions__status=Subscription.Status.ACTIVE)
        )
    )
    if active is not None:
        plans = plans.filter(is_active=active)
    return plans.order_by("monthly_price", "id")


def list_subscriptions(*, status=None, school=None, search=""):
    subscriptions = Subscription.objects.select_related("school", "plan")
    if status:
        subscriptions = subscriptions.filter(status=status)
    if school:
        subscriptions = subscriptions.filter(school_id=school)
    if search:
        subscriptions = subscriptions.filter(
            Q(school__name_en__icontains=search)
            | Q(school__name_ar__icontains=search)
            | Q(school__code__icontains=search)
        )
    return subscriptions.order_by("-starts_on", "-id")


def get_subscription_counts():
    return Subscription.objects.aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(status=Subscription.Status.ACTIVE)),
        expired=Count("id", filter=Q(status=Subscription.Status.EXPIRED)),
    )


# --- Quotations


def _quotations():
    return Quotation.objects.select_related("school", "demo_request", "plan").prefetch_related(
        "items"
    )


def get_quotation(quotation_id):
    return _quotations().filter(pk=quotation_id).first()


def list_quotations(*, status=None, search=""):
    quotations = _quotations()
    if status:
        quotations = quotations.filter(status=status)
    if search:
        quotations = quotations.filter(
            Q(number__icontains=search)
            | Q(recipient_organization__icontains=search)
            | Q(recipient_name__icontains=search)
            | Q(recipient_email__icontains=search)
        )
    return quotations.order_by("-created_at", "-id")


def get_quotation_counts():
    counts = dict(Quotation.objects.order_by().values_list("status").annotate(count=Count("id")))
    by_status = {status: counts.get(status, 0) for status in Quotation.Status.values}
    return {"total": sum(by_status.values()), "by_status": by_status}


# --- Usage


def _role_count(*roles):
    return Count(
        "membership",
        filter=Q(membership__status=Membership.Status.ACTIVE, membership__role__in=roles),
    )


def list_school_usage(*, search="", status=None):
    """Per school: active members by role, recent sign-ins and the current plan."""
    since = timezone.now() - timedelta(days=ACTIVE_USER_DAYS)
    current = Subscription.objects.filter(
        school=OuterRef("pk"), status=Subscription.Status.ACTIVE
    ).select_related("plan")

    schools = _schools().annotate(
        students=_role_count(Role.STUDENT),
        teachers=_role_count(Role.TEACHER),
        parents=_role_count(Role.PARENT),
        staff=_role_count(Role.SCHOOL_ADMIN, Role.PRINCIPAL),
        active_users=Count(
            "membership",
            filter=Q(
                membership__status=Membership.Status.ACTIVE,
                membership__user__last_login__gte=since,
            ),
        ),
        plan_code=Subquery(current.values("plan__code")[:1]),
        plan_name_en=Subquery(current.values("plan__name_en")[:1]),
        plan_name_ar=Subquery(current.values("plan__name_ar")[:1]),
        plan_max_students=Subquery(current.values("plan__max_students")[:1]),
        subscription_ends_on=Subquery(current.values("ends_on")[:1]),
    )
    if status:
        schools = schools.filter(is_active=status == "active")
    if search:
        schools = schools.filter(
            Q(name_en__icontains=search) | Q(name_ar__icontains=search) | Q(code__icontains=search)
        )
    return schools.order_by("name_en", "id")


def get_usage_totals():
    since = timezone.now() - timedelta(days=ACTIVE_USER_DAYS)
    active = Q(status=Membership.Status.ACTIVE)
    members = Membership.objects.filter(
        active, school__is_active=True, school__kind=School.Kind.SCHOOL
    ).aggregate(
        students=Count("id", filter=Q(role=Role.STUDENT)),
        teachers=Count("id", filter=Q(role=Role.TEACHER)),
        parents=Count("id", filter=Q(role=Role.PARENT)),
        staff=Count("id", filter=Q(role__in=[Role.SCHOOL_ADMIN, Role.PRINCIPAL])),
        active_users=Count("user", filter=Q(user__last_login__gte=since), distinct=True),
    )
    return {
        "active_schools": _schools().filter(is_active=True).count(),
        "active_subscriptions": Subscription.objects.filter(
            status=Subscription.Status.ACTIVE
        ).count(),
        "active_user_days": ACTIVE_USER_DAYS,
        **members,
    }


# --- Form choices


def get_form_choices():
    """Everything the subscription and quotation forms offer, in one small payload."""
    open_statuses = [
        DemoRequest.Status.NEW,
        DemoRequest.Status.CONTACTED,
        DemoRequest.Status.DEMO_SCHEDULED,
    ]
    return {
        "schools": list(
            School.objects.filter(is_active=True)
            .order_by("name_en", "id")
            .values("id", "code", "name_en", "name_ar", "email")
        ),
        "demo_requests": list(
            DemoRequest.objects.filter(status__in=open_statuses)
            .order_by("-created_at", "-id")
            .values("id", "name", "school_name", "email")
        ),
        "plans": list(
            Plan.objects.filter(is_active=True)
            .order_by("monthly_price", "id")
            .values(
                "id", "code", "name_en", "name_ar", "monthly_price", "yearly_price", "max_students"
            )
        ),
    }
