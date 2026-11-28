from datetime import timedelta

import pytest
from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from django.utils import timezone

from apps.browser_agent import agent, services
from apps.browser_agent.models import BrowserTask
from apps.browser_agent.tasks import fail_stale_tasks_task, run_browser_task_job

pytestmark = pytest.mark.django_db
Status = BrowserTask.Status


def new_task(teacher):
    return services.create_task(teacher.school, user=teacher.user, goal="Find hours")


def test_the_browser_task_is_never_retried_or_acked_late():
    assert run_browser_task_job.acks_late is False
    assert run_browser_task_job.reject_on_worker_lost is False
    assert run_browser_task_job.max_retries == 0
    assert not getattr(run_browser_task_job, "autoretry_for", ())
    assert run_browser_task_job.queue == "browser"
    assert run_browser_task_job.soft_time_limit == settings.BROWSER_AGENT_SOFT_TIME_LIMIT
    assert run_browser_task_job.time_limit == settings.BROWSER_AGENT_HARD_TIME_LIMIT


def test_a_queued_task_is_claimed_and_run_once(sara, monkeypatch):
    runs = []
    monkeypatch.setattr(agent, "run_task", lambda task: runs.append(task.pk))
    task = new_task(sara)

    run_browser_task_job.apply(args=(sara.school.pk, task.pk))
    run_browser_task_job.apply(args=(sara.school.pk, task.pk))  # delivered twice

    assert runs == [task.pk]
    task.refresh_from_db()
    assert task.status == Status.RUNNING
    assert task.started_at is not None


@pytest.mark.parametrize("status", [Status.RUNNING, Status.DONE, Status.FAILED, Status.CANCELLED])
def test_a_task_that_is_not_queued_is_refused(sara, monkeypatch, status):
    runs = []
    monkeypatch.setattr(agent, "run_task", lambda task: runs.append(task.pk))
    task = new_task(sara)
    BrowserTask.objects.filter(pk=task.pk).update(status=status)

    run_browser_task_job.apply(args=(sara.school.pk, task.pk))

    assert runs == []


def test_a_task_of_another_workspace_is_not_claimed(sara, omar, monkeypatch):
    runs = []
    monkeypatch.setattr(agent, "run_task", lambda task: runs.append(task.pk))
    task = new_task(sara)

    run_browser_task_job.apply(args=(omar.school.pk, task.pk))

    assert runs == []


def test_a_crash_marks_the_task_failed_and_is_not_retried(sara, monkeypatch):
    calls = []

    def crash(task):
        calls.append(task.pk)
        raise RuntimeError("boom")

    monkeypatch.setattr(agent, "run_task", crash)
    task = new_task(sara)

    result = run_browser_task_job.apply(args=(sara.school.pk, task.pk))

    assert result.successful()
    assert calls == [task.pk]
    task.refresh_from_db()
    assert (task.status, task.failure_reason) == (Status.FAILED, "internal_error")


def test_the_soft_time_limit_marks_the_task_failed(sara, monkeypatch):
    def too_slow(task):
        raise SoftTimeLimitExceeded()

    monkeypatch.setattr(agent, "run_task", too_slow)
    task = new_task(sara)

    run_browser_task_job.apply(args=(sara.school.pk, task.pk))

    task.refresh_from_db()
    assert (task.status, task.failure_reason) == (Status.FAILED, "time_limit")


def test_stale_tasks_are_failed_and_fresh_ones_left_alone(sara, omar):
    now = timezone.now()
    old_start = now - timedelta(seconds=settings.BROWSER_AGENT_HARD_TIME_LIMIT + 600)
    abandoned = new_task(sara)
    BrowserTask.objects.filter(pk=abandoned.pk).update(status=Status.RUNNING, started_at=old_start)
    never_started = new_task(omar)
    BrowserTask.objects.filter(pk=never_started.pk).update(created_at=now - timedelta(hours=2))
    fresh = new_task(sara)
    BrowserTask.objects.filter(pk=fresh.pk).update(status=Status.RUNNING, started_at=now)

    fail_stale_tasks_task.apply()

    reasons = dict(BrowserTask.objects.values_list("pk", "failure_reason"))
    assert reasons[abandoned.pk] == "worker_lost"
    assert reasons[never_started.pk] == "not_started"
    assert BrowserTask.objects.get(pk=fresh.pk).status == Status.RUNNING
