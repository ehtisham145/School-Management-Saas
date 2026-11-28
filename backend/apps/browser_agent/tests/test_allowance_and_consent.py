from datetime import timedelta

import pytest
from django.utils import timezone

from apps.browser_agent import services
from apps.browser_agent.models import AgentConsent, BrowserTask
from apps.browser_agent.tests.teachers import Teacher

pytestmark = pytest.mark.django_db
TASKS = "/api/browser-agent/tasks/"
STATUS = "/api/browser-agent/status/"
CONSENT = "/api/browser-agent/consent/"
Status = BrowserTask.Status


@pytest.fixture(autouse=True)
def no_celery(monkeypatch):
    monkeypatch.setattr(services, "_enqueue", lambda task: None)


@pytest.fixture(autouse=True)
def many_at_once(settings):
    settings.BROWSER_AGENT_MAX_RUNNING_PER_USER = 100


def start(teacher):
    return teacher.client.post(TASKS, {"goal": "Find hours"}, format="json")


def finished(teacher, count, *, status=Status.DONE, reason="", days_ago=0):
    for _ in range(count):
        task = services.create_task(teacher.school, user=teacher.user, goal="Earlier")
        created = timezone.now() - timedelta(days=days_ago)
        BrowserTask.objects.filter(pk=task.pk).update(
            status=status, failure_reason=reason, created_at=created
        )


# ---------------------------------------------------------------- allowance


def test_the_trial_gets_five_tasks():
    trial = Teacher("Tala", trial=True)
    for _ in range(5):
        assert start(trial).status_code == 202

    response = start(trial)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "agent_quota_reached"


@pytest.mark.parametrize(("code", "limit"), [("teacher", 20), ("teacher_pro", 60)])
def test_paid_plans_get_their_monthly_tasks(code, limit):
    teacher = Teacher(f"Paid{limit}", subscribed=False)
    teacher.subscribe(code=code)
    finished(teacher, limit - 1)

    assert start(teacher).status_code == 202
    assert start(teacher).json()["error"]["code"] == "agent_quota_reached"


def test_a_paid_plan_starts_again_each_month(sara):
    finished(sara, 20, days_ago=40)

    assert start(sara).status_code == 202


def test_the_trial_counts_every_task_of_the_trial():
    trial = Teacher("Tamer", trial=True)
    finished(trial, 5, days_ago=40)

    assert start(trial).status_code == 403


@pytest.mark.parametrize(
    "reason",
    ["internal_error", "worker_lost", "not_started", "provider_error", "browser_launch_failed"],
)
def test_failures_on_our_side_dont_use_up_the_allowance(reason):
    trial = Teacher("Tariq", trial=True)
    finished(trial, 5, status=Status.FAILED, reason=reason)

    assert start(trial).status_code == 202


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        (Status.DONE, ""),
        (Status.CANCELLED, "cancelled_by_user"),
        (Status.LIMIT_REACHED, "max_steps"),
        (Status.FAILED, "too_many_strikes"),
        (Status.FAILED, "start_url_blocked_domain"),
    ],
)
def test_everything_else_uses_up_the_allowance(status, reason):
    trial = Teacher("Tahir", trial=True)
    finished(trial, 5, status=status, reason=reason)

    assert start(trial).status_code == 403


def test_another_workspace_does_not_use_my_allowance(omar):
    trial = Teacher("Tuba", trial=True)
    finished(omar, 30)

    assert start(trial).status_code == 202


# ---------------------------------------------------------------- consent


def test_no_task_without_consent():
    teacher = Teacher("Nadia", consented=False)

    response = start(teacher)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "consent_required"
    assert BrowserTask.objects.count() == 0


def test_consent_is_given_for_the_current_notice_only():
    teacher = Teacher("Nabil", consented=False)

    old = teacher.client.post(CONSENT, {"version": "2020-01-01"}, format="json")
    assert old.status_code == 403
    assert teacher.client.post(CONSENT, {"version": services.CONSENT_VERSION}, format="json")
    assert AgentConsent.objects.filter(user=teacher.user).count() == 1

    assert start(teacher).status_code == 202


def test_giving_consent_twice_keeps_one_record():
    teacher = Teacher("Noha", consented=False)
    for _ in range(2):
        response = teacher.client.post(CONSENT, {"version": services.CONSENT_VERSION})
        assert response.status_code == 204
    assert AgentConsent.objects.count() == 1


def test_consent_in_one_workspace_is_not_consent_in_another(sara):
    other = Teacher("Nour", consented=False)
    assert not AgentConsent.objects.filter(school=other.school).exists()
    assert start(other).json()["error"]["code"] == "consent_required"


# ---------------------------------------------------------------- status


def test_status_tells_the_page_what_it_needs():
    trial = Teacher("Salma", trial=True, consented=False)
    finished(trial, 2)

    body = trial.client.get(STATUS).json()

    assert body == {
        "consent_version": services.CONSENT_VERSION,
        "consent_given": False,
        "allowance": {"used": 2, "limit": 5, "left": 3, "period": "trial"},
        "active_task": None,
    }


def test_status_shows_the_running_task(sara):
    task = services.create_task(sara.school, user=sara.user, goal="Running one")

    body = sara.client.get(STATUS).json()

    assert body["consent_given"] is True
    assert body["active_task"]["id"] == task.pk
    assert body["allowance"]["period"] == "month"


def test_status_and_consent_follow_the_same_access_rules(settings, school_teacher):
    assert school_teacher.client.get(STATUS).status_code == 403
    settings.BROWSER_AGENT_ENABLED = False
    trial = Teacher("Samir", trial=True)
    assert trial.client.get(STATUS).json()["error"]["code"] == "browser_agent_disabled"
    assert trial.client.post(CONSENT, {"version": services.CONSENT_VERSION}).status_code == 403
