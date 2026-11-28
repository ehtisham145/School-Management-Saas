from decimal import Decimal

import pytest
from django.core.management import CommandError, call_command

from apps.browser_agent import selectors, services
from apps.browser_agent.management.commands import run_browser_task
from apps.browser_agent.models import BrowserTask
from apps.tenancy.models import Membership, School
from apps.tenancy.selectors import get_individual_teacher_membership

pytestmark = pytest.mark.django_db


def test_create_task_checks_the_goal_and_start_url(sara):
    task = services.create_task(
        sara.school, user=sara.user, goal="  Find hours  ", start_url="https://example.com"
    )
    assert (task.goal, task.status, task.school) == ("Find hours", "queued", sara.school)

    for goal, url, code in [
        ("", "", "goal_required"),
        ("x" * 2001, "", "goal_too_long"),
        ("Find", "file:///etc/passwd", "start_url_scheme"),
        ("Find", "javascript:alert(1)", "start_url_scheme"),
    ]:
        with pytest.raises(services.TaskInputError) as error:
            services.create_task(sara.school, user=sara.user, goal=goal, start_url=url)
        assert error.value.code == code


def test_estimate_cost_uses_the_price_table():
    assert services.estimate_cost("gpt-4o-mini", 1_000_000, 1_000_000) == Decimal("0.75")
    assert services.estimate_cost("unknown-model", 1_000_000, 1_000_000) == Decimal("0")


def test_one_workspace_can_not_read_another_workspaces_tasks(sara, omar):
    task = services.create_task(sara.school, user=sara.user, goal="Find hours")
    services.record_step(task, number=1, action="goto", domain="example.com", verdict="ok")

    assert selectors.get_task(omar.school, task.pk) is None
    assert list(selectors.list_tasks(omar.school)) == []
    assert list(selectors.list_steps(omar.school, task.pk)) == []

    assert selectors.get_task(sara.school, task.pk) == task
    assert list(selectors.list_tasks(sara.school, user=sara.user)) == [task]
    assert selectors.list_steps(sara.school, task.pk).count() == 1


def test_individual_teacher_membership_lookup(sara):
    assert get_individual_teacher_membership(sara.school.pk) == sara.membership

    school = School.objects.create(name_en="Real school", code="real-school")
    Membership.objects.create(school=school, user=sara.user, role=Membership.Role.TEACHER)
    assert get_individual_teacher_membership(school.pk) is None

    sara.school.is_active = False
    sara.school.save()
    assert get_individual_teacher_membership(sara.school.pk) is None


def test_command_refuses_when_the_feature_is_off(sara, settings):
    settings.BROWSER_AGENT_ENABLED = False
    with pytest.raises(CommandError, match="BROWSER_AGENT_ENABLED"):
        call_command("run_browser_task", "Find hours", "--workspace", str(sara.school.pk))


def test_command_refuses_an_unknown_workspace(db, settings):
    settings.BROWSER_AGENT_ENABLED = True
    with pytest.raises(CommandError, match="No active individual teacher workspace"):
        call_command("run_browser_task", "Find hours", "--workspace", "999999")


def test_command_runs_a_task_and_prints_the_answer(sara, settings, monkeypatch, capsys):
    settings.BROWSER_AGENT_ENABLED = True

    def fake_run(task, **kwargs):
        return services.finish_task(task, status=BrowserTask.Status.DONE, answer="9am to 5pm")

    monkeypatch.setattr(run_browser_task, "run_task", fake_run)
    call_command("run_browser_task", "Find hours", "--workspace", str(sara.school.pk))

    output = capsys.readouterr().out
    assert "Status: done" in output
    assert "9am to 5pm" in output
    assert BrowserTask.objects.get().created_by == sara.user
