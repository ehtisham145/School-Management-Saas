"""Every workspace read takes the workspace first, so one teacher can never reach another's
tasks. The few platform-wide reads (budget, concurrency, stale tasks) are named as such
and return only counts or totals."""

from decimal import Decimal

from django.db.models import Q, Sum

from apps.browser_agent.models import AgentConsent, BrowserStep, BrowserTask

# Failures on our side. Those tasks don't use up the teacher's allowance.
SYSTEM_FAILURES = frozenset(
    {
        "internal_error",
        "worker_lost",
        "not_started",
        "provider_error",
        "not_configured",
        "model_not_priced",
        "no_time_left",
    }
)


def count_tasks_toward_allowance(school, *, since=None):
    """Tasks that use up the allowance: every task since `since` (all of them when None),
    except those that failed on our side (SYSTEM_FAILURES, or the browser not starting)."""
    tasks = BrowserTask.objects.filter(school=school)
    if since is not None:
        tasks = tasks.filter(created_at__date__gte=since)
    ours = Q(status=BrowserTask.Status.FAILED) & (
        Q(failure_reason__in=SYSTEM_FAILURES) | Q(failure_reason__startswith="browser_")
    )
    return tasks.exclude(ours).count()


def has_consent(school, user, version):
    return AgentConsent.objects.filter(school=school, user=user, version=version).exists()


def get_active_task(school, user):
    return list_tasks(school, user=user).filter(status__in=BrowserTask.ACTIVE).first()


def get_task(school, task_id, *, user=None):
    """The task in this workspace (and of this user, when given), or None."""
    tasks = BrowserTask.objects.filter(school=school, pk=task_id)
    if user is not None:
        tasks = tasks.filter(created_by=user)
    return tasks.first()


def list_tasks(school, *, user=None):
    tasks = BrowserTask.objects.filter(school=school)
    if user is not None:
        tasks = tasks.filter(created_by=user)
    return tasks


def list_steps(school, task_id):
    return BrowserStep.objects.filter(school=school, task_id=task_id).order_by("number")


def get_task_status(school_id, task_id):
    return (
        BrowserTask.objects.filter(school_id=school_id, pk=task_id)
        .values_list("status", flat=True)
        .first()
    )


def count_active_tasks_of_user(user):
    return BrowserTask.objects.filter(created_by=user, status__in=BrowserTask.ACTIVE).count()


def count_active_tasks_on_platform():
    return BrowserTask.objects.filter(status__in=BrowserTask.ACTIVE).count()


def platform_spend_since(day) -> Decimal:
    total = BrowserTask.objects.filter(created_at__date__gte=day).aggregate(total=Sum("cost_usd"))[
        "total"
    ]
    return total or Decimal("0")


def list_stale_tasks(started_before, queued_before):
    """Tasks a dead worker left behind: running/awaiting since before `started_before`,
    or still queued since before `queued_before`."""
    return BrowserTask.objects.filter(
        status__in=(BrowserTask.Status.RUNNING, BrowserTask.Status.AWAITING_USER),
        started_at__lt=started_before,
    ) | BrowserTask.objects.filter(status=BrowserTask.Status.QUEUED, created_at__lt=queued_before)
