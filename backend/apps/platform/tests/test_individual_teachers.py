from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.classroom.models import Classroom, Student, UpgradeRequest
from apps.platform.models import BillingCycle, Plan, Subscription
from apps.platform.services import send_trial_reminders
from apps.platform.tasks import send_trial_reminders_task
from apps.tenancy.models import Membership, School

pytestmark = pytest.mark.django_db

URL = "/api/platform/teachers/"
PASSWORD = "correct-pass123"  # noqa: S105


@pytest.fixture
def admin_client():
    User.objects.create_user("platform", password=PASSWORD, is_platform_admin=True)
    client = APIClient()
    assert (
        client.post("/api/auth/login/", {"username": "platform", "password": PASSWORD}).status_code
        == 200
    )
    return client


def _plan(code="teacher"):
    plan, _ = Plan.objects.get_or_create(
        code=code,
        defaults={"name_en": code, "name_ar": code, "monthly_price": 49, "yearly_price": 588},
    )
    return plan


def _teacher(name="Sara", *, days_left=7, is_trial=True, code="teacher"):
    workspace = School.objects.create(
        name_en=name, code=f"teacher-{name.lower()}", kind=School.Kind.INDIVIDUAL
    )
    user = User.objects.create_user(f"{name.lower()}@x.com", email=f"{name.lower()}@x.com")
    Membership.objects.create(school=workspace, user=user, role=Membership.Role.TEACHER)
    today = timezone.localdate()
    Subscription.objects.create(
        school=workspace,
        plan=_plan(code),
        billing_cycle=BillingCycle.MONTHLY,
        price=0,
        starts_on=today - timedelta(days=30),
        ends_on=today + timedelta(days=days_left),
        is_trial=is_trial,
    )
    return workspace


def _ended_trial(name="Omar", ended_days_ago=1):
    workspace = _teacher(name, days_left=-ended_days_ago)
    Subscription.objects.filter(school=workspace).update(status=Subscription.Status.EXPIRED)
    return workspace


def test_only_platform_admins_can_use_teachers(db):
    workspace = _teacher()
    user = User.objects.create_user("someone", password=PASSWORD)
    client = APIClient()
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    assert APIClient().get(URL).status_code == 403
    assert client.get(URL).status_code == 403
    assert client.post(f"{URL}{workspace.id}/extend-trial/", {"days": 7}).status_code == 403
    assert (
        client.post(f"{URL}{workspace.id}/activate-plan/", {"plan": "teacher"}).status_code == 403
    )


def test_list_shows_teachers_with_their_plan_and_usage(admin_client):
    workspace = _teacher()
    classroom = Classroom.objects.create(school=workspace, name="A")
    Student.objects.create(school=workspace, classroom=classroom, first_name="Ali")
    UpgradeRequest.objects.create(school=workspace, plan="teacher_pro")
    School.objects.create(name_en="Al Noor", code="alnoor")

    response = admin_client.get(URL)

    assert response.data["count"] == 1
    row = response.data["results"][0]
    assert row["email"] == "sara@x.com"
    assert (row["class_count"], row["student_count"]) == (1, 1)
    assert (row["plan_code"], row["is_trial"]) == ("teacher", True)
    assert row["requested_plan"] == "teacher_pro"


def test_list_query_count_does_not_grow(admin_client, django_assert_max_num_queries):
    for index in range(10):
        _teacher(f"T{index}")

    with django_assert_max_num_queries(6):
        response = admin_client.get(URL)

    assert response.data["count"] == 10


@pytest.mark.parametrize(
    ("status", "expected"), [("trial", "Sara"), ("paid", "Tariq"), ("ended", "Omar")]
)
def test_list_filters_by_status(admin_client, status, expected):
    _teacher("Sara")
    _teacher("Tariq", is_trial=False)
    _ended_trial("Omar")

    response = admin_client.get(URL, {"status": status})

    assert [row["name"] for row in response.data["results"]] == [expected]


def test_list_searches_name_and_email(admin_client):
    _teacher("Sara")
    _teacher("Tariq")

    assert admin_client.get(URL, {"search": "tariq@x"}).data["count"] == 1
    assert admin_client.get(URL, {"search": "SAR"}).data["count"] == 1


def test_an_unknown_status_is_rejected(admin_client):
    assert admin_client.get(URL, {"status": "other"}).status_code == 400


def test_a_running_trial_can_be_extended(admin_client):
    workspace = _teacher(days_left=2)

    response = admin_client.post(f"{URL}{workspace.id}/extend-trial/", {"days": 5})

    assert response.status_code == 200
    trial = Subscription.objects.get(school=workspace)
    assert trial.ends_on == timezone.localdate() + timedelta(days=7)
    assert AuditEvent.objects.filter(school=workspace).exists()


def test_an_ended_trial_can_be_reopened(admin_client):
    workspace = _ended_trial()

    response = admin_client.post(f"{URL}{workspace.id}/extend-trial/", {"days": 3})

    assert response.status_code == 200
    trial = Subscription.objects.get(school=workspace)
    assert trial.status == Subscription.Status.ACTIVE
    assert trial.expired_at is None
    assert trial.ends_on == timezone.localdate() + timedelta(days=3)


@pytest.mark.parametrize("days", [0, 31, "x"])
def test_extension_days_are_limited(admin_client, days):
    workspace = _teacher()

    assert (
        admin_client.post(f"{URL}{workspace.id}/extend-trial/", {"days": days}).status_code == 400
    )


def test_a_paid_teacher_cannot_get_a_trial_extension(admin_client):
    workspace = _teacher(is_trial=False)

    assert admin_client.post(f"{URL}{workspace.id}/extend-trial/", {"days": 3}).status_code == 400


@pytest.mark.parametrize("code", ["teacher", "teacher_pro"])
def test_activating_a_plan_replaces_the_trial(admin_client, code):
    workspace = _teacher()
    UpgradeRequest.objects.create(school=workspace, plan=code)

    response = admin_client.post(f"{URL}{workspace.id}/activate-plan/", {"plan": code})

    assert response.status_code == 200
    assert (response.data["plan_code"], response.data["is_trial"]) == (code, False)
    assert response.data["requested_plan"] is None
    active = Subscription.objects.get(school=workspace, status=Subscription.Status.ACTIVE)
    assert active.plan.code == code
    assert active.is_trial is False
    assert active.price == active.plan.monthly_price
    assert Subscription.objects.filter(school=workspace).count() == 2
    assert UpgradeRequest.objects.get().status == UpgradeRequest.Status.COMPLETED


def test_activating_needs_a_teacher_plan(admin_client):
    workspace = _teacher()

    assert (
        admin_client.post(f"{URL}{workspace.id}/activate-plan/", {"plan": "basic"}).status_code
        == 400
    )


def test_real_schools_are_not_teachers(admin_client):
    school = School.objects.create(name_en="Al Noor", code="alnoor")

    assert admin_client.post(f"{URL}{school.id}/extend-trial/", {"days": 3}).status_code == 404
    assert (
        admin_client.post(f"{URL}{school.id}/activate-plan/", {"plan": "teacher"}).status_code
        == 404
    )


# --- Reminder emails


def _run_reminders(capture, today=None):
    with capture(execute=True):
        return send_trial_reminders(today)


def test_a_reminder_goes_out_two_days_before_the_end_only_once(django_capture_on_commit_callbacks):
    _teacher(days_left=2)

    assert _run_reminders(django_capture_on_commit_callbacks) == 1
    assert _run_reminders(django_capture_on_commit_callbacks) == 0

    assert len(mail.outbox) == 1
    assert "in 2 days" in mail.outbox[0].subject
    assert mail.outbox[0].to == ["sara@x.com"]


def test_a_second_reminder_goes_out_on_the_last_day(django_capture_on_commit_callbacks):
    _teacher(days_left=2)
    _run_reminders(django_capture_on_commit_callbacks)

    tomorrow = timezone.localdate() + timedelta(days=1)
    assert _run_reminders(django_capture_on_commit_callbacks, tomorrow) == 1

    assert "tomorrow" in mail.outbox[-1].subject


def test_no_reminder_is_sent_early_or_to_a_paid_teacher(django_capture_on_commit_callbacks):
    _teacher("Sara", days_left=5)
    _teacher("Tariq", days_left=1, is_trial=False)

    assert _run_reminders(django_capture_on_commit_callbacks) == 0
    assert not mail.outbox


def test_an_email_goes_out_when_the_trial_has_ended(django_capture_on_commit_callbacks):
    _ended_trial()

    assert _run_reminders(django_capture_on_commit_callbacks) == 1
    assert _run_reminders(django_capture_on_commit_callbacks) == 0

    assert "has ended" in mail.outbox[0].subject


def test_a_teacher_who_upgraded_gets_no_ended_email(django_capture_on_commit_callbacks):
    workspace = _ended_trial()
    Subscription.objects.create(
        school=workspace,
        plan=_plan(),
        billing_cycle=BillingCycle.MONTHLY,
        price=49,
        starts_on=timezone.localdate(),
        ends_on=timezone.localdate() + timedelta(days=30),
    )

    assert _run_reminders(django_capture_on_commit_callbacks) == 0


def test_a_trial_that_ended_long_ago_gets_no_email(django_capture_on_commit_callbacks):
    _ended_trial(ended_days_ago=10)

    assert _run_reminders(django_capture_on_commit_callbacks) == 0


def test_the_scheduled_task_runs_the_reminders(django_capture_on_commit_callbacks):
    _teacher(days_left=2)

    with django_capture_on_commit_callbacks(execute=True):
        assert send_trial_reminders_task() == 1
