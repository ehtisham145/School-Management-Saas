from decimal import Decimal

import pytest
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle

from apps.browser_agent import services
from apps.browser_agent.models import BrowserTask

pytestmark = pytest.mark.django_db
TASKS = "/api/browser-agent/tasks/"
Status = BrowserTask.Status


@pytest.fixture(autouse=True)
def queued(monkeypatch):
    """Records what would go to Celery instead of starting a browser."""
    sent = []
    monkeypatch.setattr(services, "_enqueue", lambda task: sent.append(task.pk))
    return sent


def start(teacher, goal="Find the opening hours", **extra):
    return teacher.client.post(TASKS, {"goal": goal, **extra}, format="json")


def error_code(response):
    return response.json()["error"]["code"]


def test_a_task_is_saved_and_queued(sara, queued, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        response = start(sara, start_url="https://example.com")

    assert response.status_code == 202
    body = response.json()
    assert (body["status"], body["goal"]) == ("queued", "Find the opening hours")
    assert "cost_usd" not in body and "input_tokens" not in body
    assert queued == [body["id"]]
    task = BrowserTask.objects.get()
    assert (task.school, task.created_by) == (sara.school, sara.user)


def test_bad_input_is_refused(sara):
    assert start(sara, goal="").status_code == 400
    assert start(sara, start_url="file:///etc/passwd").status_code == 400
    assert start(sara, goal="x" * 2001).status_code == 400


def test_the_feature_switch_closes_every_endpoint(sara, settings):
    settings.BROWSER_AGENT_ENABLED = False
    response = start(sara)
    assert (response.status_code, error_code(response)) == (403, "browser_agent_disabled")
    assert sara.client.get(TASKS).status_code == 403


def test_only_the_teacher_of_an_individual_workspace_may_use_it(school_teacher):
    assert start(school_teacher).status_code == 403
    assert APIClient().post(TASKS, {"goal": "x"}, format="json").status_code == 403


def test_a_workspace_whose_plan_ended_can_not_start_tasks(lapsed):
    response = start(lapsed)
    assert (response.status_code, error_code(response)) == (403, "workspace_read_only")
    assert lapsed.client.get(TASKS).status_code == 200


def test_another_workspaces_task_is_not_found(sara, omar):
    task = services.create_task(sara.school, user=sara.user, goal="Mine")

    assert omar.client.get(f"{TASKS}{task.pk}/").status_code == 404
    assert omar.client.post(f"{TASKS}{task.pk}/cancel/").status_code == 404
    assert omar.client.get(TASKS).json()["results"] == []
    assert BrowserTask.objects.get(pk=task.pk).status == Status.QUEUED


def test_the_owner_sees_a_task_with_its_steps(sara):
    task = services.create_task(sara.school, user=sara.user, goal="Mine")
    services.record_step(task, number=1, action="goto", domain="example.com", verdict="ok")

    body = sara.client.get(f"{TASKS}{task.pk}/").json()

    assert body["steps"] == [
        {
            "number": 1,
            "action": "goto",
            "domain": "example.com",
            "verdict": "ok",
            "note": "",
            "duration_ms": 0,
        }
    ]
    assert [item["id"] for item in sara.client.get(TASKS).json()["results"]] == [task.pk]


def test_cancel_ends_an_active_task_and_leaves_a_finished_one(sara):
    task = services.create_task(sara.school, user=sara.user, goal="Mine")

    response = sara.client.post(f"{TASKS}{task.pk}/cancel/")
    assert response.json()["status"] == "cancelled"

    services.finish_task(task, status=Status.DONE)  # no effect: already ended
    assert BrowserTask.objects.get(pk=task.pk).status == Status.CANCELLED


def test_one_running_task_per_teacher(sara):
    assert start(sara).status_code == 202

    response = start(sara)
    assert (response.status_code, error_code(response)) == (409, "task_already_running")

    BrowserTask.objects.update(status=Status.DONE)
    assert start(sara).status_code == 202


def test_the_platform_wide_cap(sara, omar, settings):
    settings.BROWSER_AGENT_MAX_RUNNING_TOTAL = 1
    assert start(omar).status_code == 202

    response = start(sara)
    assert (response.status_code, error_code(response)) == (503, "browser_agent_busy")


def test_the_monthly_budget_refuses_new_tasks(sara, omar, settings):
    settings.BROWSER_AGENT_MONTHLY_BUDGET_USD = Decimal("1.00")
    spent = services.create_task(omar.school, user=omar.user, goal="Earlier")
    BrowserTask.objects.filter(pk=spent.pk).update(status=Status.DONE, cost_usd=Decimal("1.00"))

    response = start(sara)

    assert (response.status_code, error_code(response)) == (503, "browser_agent_budget_reached")
    assert "limit for this month" in response.json()["error"]["message"]


def test_starting_tasks_is_throttled(sara, settings, monkeypatch):
    monkeypatch.setattr(ScopedRateThrottle, "THROTTLE_RATES", {"browser_agent": "2/hour"})
    settings.BROWSER_AGENT_MAX_RUNNING_PER_USER = 100

    assert start(sara).status_code == 202
    assert start(sara).status_code == 202
    assert start(sara).status_code == 429
    # Reading is not throttled.
    assert sara.client.get(TASKS).status_code == 200
