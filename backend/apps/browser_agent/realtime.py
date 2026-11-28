"""Pushes task updates to the teacher's open socket (consumers.py).

Payloads carry the status, counters and the step's action kind, domain and reason code.
Never page content or typed values. The answer is sent only when the task ends, and only
to the task's own group, which only its owner can join."""

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


def group_name(task_id):
    return f"browser_task_{task_id}"


def task_payload(task):
    from apps.browser_agent.models import BrowserTask

    data = {
        "id": task.pk,
        "status": str(task.status),
        "steps_taken": task.steps_taken,
        "failure_reason": task.failure_reason,
    }
    if task.status in BrowserTask.FINISHED:
        data["answer"] = task.answer
    return data


def step_payload(step):
    return {
        "number": step.number,
        "action": step.action,
        "domain": step.domain,
        "verdict": str(step.verdict),
        "note": step.note,
        "duration_ms": step.duration_ms,
    }


def notify(task, *, step=None):
    """Best effort: a broken channel layer never stops a task."""
    try:
        layer = get_channel_layer()
        if layer is None:
            return
        message = {"type": "task.update", "task": task_payload(task)}
        if step is not None:
            message["step"] = step_payload(step)
        async_to_sync(layer.group_send)(group_name(task.pk), message)
    except Exception as error:
        logger.warning(
            "browser_agent_notify_failed",
            extra={"task_id": task.pk, "error": type(error).__name__},
        )
