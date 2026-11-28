"""Celery tasks for the browser agent.

The project sets CELERY_TASK_ACKS_LATE=True, so a crashed worker re-runs its task. A
browser task may already have submitted a form, so this one is acknowledged when it
starts, never retried, and claimed with an atomic queued → running update. A failure is
recorded on the task for the teacher to see; it is never silently run again.

Runs on its own "browser" queue (CELERY_TASK_ROUTES) with its own worker:
    celery -A config worker -Q browser --concurrency=2 --prefetch-multiplier=1 -n browser@%h
"""

import logging

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(
    queue="browser",
    acks_late=False,
    reject_on_worker_lost=False,
    max_retries=0,
    autoretry_for=(),
    soft_time_limit=settings.BROWSER_AGENT_SOFT_TIME_LIMIT,
    time_limit=settings.BROWSER_AGENT_HARD_TIME_LIMIT,
)
def run_browser_task_job(school_id, task_id):
    # Imported here so Celery can load this module without pulling in Playwright.
    from apps.browser_agent import services
    from apps.browser_agent.agent import run_task
    from apps.browser_agent.models import BrowserTask

    task = services.claim_task(school_id, task_id)
    if task is None:
        # Already running, finished or cancelled: a second delivery does nothing.
        logger.warning("browser_task_not_claimed", extra={"task_id": task_id})
        return
    try:
        run_task(task)
    except SoftTimeLimitExceeded:
        # run_task handles this itself; this covers the moment before its browser opens.
        services.finish_task(task, status=BrowserTask.Status.FAILED, failure_reason="time_limit")
    except Exception as error:
        logger.error(
            "browser_task_crashed", extra={"task_id": task_id, "error": type(error).__name__}
        )
        services.finish_task(
            task, status=BrowserTask.Status.FAILED, failure_reason="internal_error"
        )


@shared_task
def fail_stale_tasks_task():
    from apps.browser_agent.services import fail_stale_tasks

    fail_stale_tasks()
