"""Writes for browser agent tasks. Steps keep the action kind, domain and a reason code,
never page content or typed values.

A task moves queued → running (⇄ awaiting_user) → done | failed | cancelled | limit_reached,
and never goes back: claim_task() only takes a queued task, and finish_task() only
finishes an active one, so a task can't run twice or be finished twice."""

from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone

from apps.browser_agent import budget, realtime, selectors
from apps.browser_agent.models import AgentConsent, BrowserStep, BrowserTask
from apps.classroom.entitlements import get_workspace_access

MAX_GOAL_LENGTH = 2000
# The date of the notice the teacher accepts. Change it when the notice changes, and every
# teacher is asked again (frontend: Teacher.agent.consent in messages/*.json).
CONSENT_VERSION = "2026-11-28"
MILLION = Decimal(1_000_000)
# Serialises the concurrency check across web processes (PostgreSQL advisory lock).
QUEUE_LOCK_ID = 7_201_028
# A queued task no worker picked up in this time is failed by the sweep.
QUEUED_TIMEOUT = timedelta(minutes=30)
# Grace after the hard time limit before a running task counts as abandoned.
STALE_GRACE = timedelta(minutes=2)

Status = BrowserTask.Status


class TaskInputError(ValueError):
    """The goal or start URL can't be used. `code` is safe to show and log."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


class QueueRefused(Exception):
    """A new task can't be queued now. `code` tells the app which message to show."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def estimate_cost(model, input_tokens, output_tokens) -> Decimal:
    prices = settings.BROWSER_AGENT_PRICES.get(model)
    if not prices:
        return Decimal("0")
    input_price, output_price = (Decimal(price) for price in prices)
    return (input_tokens * input_price + output_tokens * output_price) / MILLION


def create_task(school, *, user, goal, start_url=""):
    goal = (goal or "").strip()
    start_url = (start_url or "").strip()
    if not goal:
        raise TaskInputError("goal_required")
    if len(goal) > MAX_GOAL_LENGTH:
        raise TaskInputError("goal_too_long")
    if start_url and not start_url.lower().startswith(("http://", "https://")):
        raise TaskInputError("start_url_scheme")
    return BrowserTask.objects.create(
        school=school, created_by=user, goal=goal, start_url=start_url[:2000]
    )


def _lock_queue():
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [QUEUE_LOCK_ID])


def give_consent(school, user):
    AgentConsent.objects.get_or_create(school=school, user=user, version=CONSENT_VERSION)


def allowance(school):
    """(used, limit, period) of the workspace's plan. Period is "trial" or "month"."""
    access = get_workspace_access(school)
    used = selectors.count_tasks_toward_allowance(school, since=access.ai_since)
    return used, access.limits.agent_tasks, access.limits.ai_period


def queue_task(school, *, user, goal, start_url=""):
    """Check the switch, consent, budget, allowance and concurrency caps, save the task
    and queue it."""
    if not settings.BROWSER_AGENT_ENABLED:
        raise QueueRefused("browser_agent_disabled")
    if not selectors.has_consent(school, user, CONSENT_VERSION):
        raise QueueRefused("consent_required")
    if budget.is_exhausted():
        raise QueueRefused("browser_agent_budget_reached")

    with transaction.atomic():
        # Inside the lock, so two quick clicks can't both use the last try.
        _lock_queue()
        used, limit, _ = allowance(school)
        if used >= limit:
            raise QueueRefused("agent_quota_reached")
        per_user = settings.BROWSER_AGENT_MAX_RUNNING_PER_USER
        total = settings.BROWSER_AGENT_MAX_RUNNING_TOTAL
        if selectors.count_active_tasks_of_user(user) >= per_user:
            raise QueueRefused("task_already_running")
        if selectors.count_active_tasks_on_platform() >= total:
            raise QueueRefused("browser_agent_busy")
        task = create_task(school, user=user, goal=goal, start_url=start_url)
        transaction.on_commit(lambda: _enqueue(task), robust=True)
    return task


def _enqueue(task):
    # Imported here: tasks.py imports the agent, which imports this module.
    from apps.browser_agent.tasks import run_browser_task_job

    run_browser_task_job.delay(task.school_id, task.pk)


def claim_task(school_id, task_id):
    """Move a queued task to running and return it, or None if it isn't queued any more.

    The conditional update is atomic, so a task delivered twice runs once."""
    now = timezone.now()
    claimed = BrowserTask.objects.filter(
        school_id=school_id, pk=task_id, status=Status.QUEUED
    ).update(status=Status.RUNNING, started_at=now, updated_at=now)
    if not claimed:
        return None
    return BrowserTask.objects.select_related("created_by").get(pk=task_id)


def mark_running(task, *, model):
    """Record the model and make sure the task is running. False if it already ended."""
    now = timezone.now()
    started_at = task.started_at or now
    updated = BrowserTask.objects.filter(
        pk=task.pk, status__in=(Status.QUEUED, Status.RUNNING)
    ).update(status=Status.RUNNING, model=model, started_at=started_at, updated_at=now)
    if not updated:
        task.refresh_from_db()
        return False
    task.status, task.model, task.started_at = Status.RUNNING, model, started_at
    realtime.notify(task)
    return True


def record_step(
    task,
    *,
    number,
    action,
    domain,
    verdict,
    note="",
    input_tokens=0,
    output_tokens=0,
    duration_ms=0,
    model="",
):
    step = BrowserStep.objects.create(
        school_id=task.school_id,
        task=task,
        number=number,
        action=action[:20],
        domain=domain[:253],
        verdict=verdict,
        note=note[:60],
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        duration_ms=duration_ms,
    )
    cost = estimate_cost(model or task.model, input_tokens, output_tokens)
    task.steps_taken = number
    task.input_tokens += input_tokens
    task.output_tokens += output_tokens
    task.cost_usd += cost
    task.save(
        update_fields=["steps_taken", "input_tokens", "output_tokens", "cost_usd", "updated_at"]
    )
    budget.add_spend(cost)
    realtime.notify(task, step=step)
    return step


def finish_task(task, *, status, answer="", failure_reason=""):
    """End an active task. A task that already ended (for example cancelled by the teacher
    while a step ran) keeps its first ending."""
    now = timezone.now()
    answer = (answer or "")[:10000]
    failure_reason = (failure_reason or "")[:40]
    updated = BrowserTask.objects.filter(pk=task.pk, status__in=BrowserTask.ACTIVE).update(
        status=status,
        answer=answer,
        failure_reason=failure_reason,
        finished_at=now,
        updated_at=now,
    )
    if updated:
        task.status, task.answer, task.failure_reason = status, answer, failure_reason
        task.finished_at = now
    else:
        task.refresh_from_db()
    realtime.notify(task)
    return task


def cancel_task(task):
    """The teacher stops a task. A running task stops before its next step."""
    finish_task(task, status=Status.CANCELLED, failure_reason="cancelled_by_user")
    return task


def fail_stale_tasks():
    """Fail tasks a dead or overloaded worker left behind. Returns how many."""
    now = timezone.now()
    hard_limit = timedelta(seconds=settings.BROWSER_AGENT_HARD_TIME_LIMIT)
    stale = selectors.list_stale_tasks(
        started_before=now - hard_limit - STALE_GRACE, queued_before=now - QUEUED_TIMEOUT
    )
    count = 0
    for task in stale:
        reason = "not_started" if task.status == Status.QUEUED else "worker_lost"
        finish_task(task, status=Status.FAILED, failure_reason=reason)
        count += 1
    return count
