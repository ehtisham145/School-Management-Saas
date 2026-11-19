import re
from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.platform.models import Plan, Subscription, TeacherSignupCode
from apps.platform.selectors import get_school_counts, list_school_usage, list_schools
from apps.platform.services import TRIAL_DAYS, expire_overdue_subscriptions
from apps.tenancy.models import Membership, School

REQUEST_URL = "/api/auth/teacher-signup/request/"
VERIFY_URL = "/api/auth/teacher-signup/verify/"
DETAILS = {
    "full_name": "Sara Ahmed",
    "email": "Sara@Example.com",
    "password": "Blue-river-2026!",
    "accept_privacy": True,
}

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def run_email_tasks_now(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True


def _request_code(client, django_capture_on_commit_callbacks, **details):
    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(REQUEST_URL, {**DETAILS, **details}, format="json")
    return response


def _code():
    return re.search(r"code is: (\d{6})", mail.outbox[-1].body).group(1)


def _sign_up(client, capture, **details):
    _request_code(client, capture, **details)
    return client.post(VERIFY_URL, {**DETAILS, **details, "code": _code()}, format="json")


def test_a_code_is_emailed_and_no_account_exists_yet(
    api_client, django_capture_on_commit_callbacks
):
    response = _request_code(api_client, django_capture_on_commit_callbacks)

    assert response.status_code == 204
    assert mail.outbox[-1].to == ["sara@example.com"]
    assert not User.objects.exists()
    assert not School.objects.exists()
    # The password is never kept while the email is being confirmed.
    assert not hasattr(TeacherSignupCode.objects.get(), "password_hash")


def test_a_correct_code_creates_the_teacher_workspace_and_trial(
    api_client, django_capture_on_commit_callbacks
):
    response = _sign_up(api_client, django_capture_on_commit_callbacks)

    assert response.status_code == 201
    user = User.objects.get(email="sara@example.com")
    assert user.username == "sara@example.com"
    assert (user.first_name, user.last_name) == ("Sara", "Ahmed")
    assert user.check_password(DETAILS["password"])

    membership = Membership.objects.get(user=user)
    assert membership.role == Membership.Role.TEACHER
    assert membership.school.kind == School.Kind.INDIVIDUAL

    trial = Subscription.objects.get(school=membership.school)
    today = timezone.localdate()
    assert trial.is_trial is True
    assert trial.price == 0
    assert trial.plan.code == "teacher"
    assert trial.status == Subscription.Status.ACTIVE
    assert (trial.starts_on, trial.ends_on) == (today, today + timedelta(days=TRIAL_DAYS))

    assert response.data["trial"]["days_left"] == TRIAL_DAYS
    assert response.data["memberships"][0]["role"] == Membership.Role.TEACHER
    assert api_client.get("/api/auth/me/").data["trial"]["days_left"] == TRIAL_DAYS
    assert not TeacherSignupCode.objects.exists()

    event = AuditEvent.objects.get(action=AuditEvent.Action.SUBSCRIPTION_ACTIVATED)
    assert event.details["trial"] is True
    assert "privacy_accepted_at" in event.details


def test_the_teacher_can_sign_in_with_email_in_any_letter_case(
    api_client, django_capture_on_commit_callbacks
):
    _sign_up(api_client, django_capture_on_commit_callbacks)

    response = APIClient().post(
        "/api/auth/login/",
        {"username": "SARA@example.com", "password": DETAILS["password"]},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["trial"]["days_left"] == TRIAL_DAYS


def test_an_existing_plan_is_used_for_the_trial(api_client, django_capture_on_commit_callbacks):
    plan = Plan.objects.create(
        code="teacher", name_en="Teacher", name_ar="المعلم", monthly_price=59, yearly_price=590
    )

    _sign_up(api_client, django_capture_on_commit_callbacks)

    assert Subscription.objects.get().plan == plan
    assert Plan.objects.count() == 1


def test_two_teachers_get_separate_workspaces(api_client, django_capture_on_commit_callbacks):
    _sign_up(api_client, django_capture_on_commit_callbacks)
    _sign_up(APIClient(), django_capture_on_commit_callbacks, email="omar@example.com")

    sara = Membership.objects.get(user__email="sara@example.com")
    omar = Membership.objects.get(user__email="omar@example.com")
    assert sara.school_id != omar.school_id

    other = api_client.post("/api/auth/switch-school/", {"membership_id": omar.id}, format="json")
    assert other.status_code == 404


def test_a_wrong_code_creates_nothing_and_counts_as_an_attempt(
    api_client, django_capture_on_commit_callbacks
):
    _request_code(api_client, django_capture_on_commit_callbacks)
    wrong = "000000" if _code() != "000000" else "111111"

    response = api_client.post(VERIFY_URL, {**DETAILS, "code": wrong}, format="json")

    assert response.status_code == 401
    assert response.data["error"]["code"] == "invalid_code"
    assert not User.objects.exists()
    assert TeacherSignupCode.objects.get().attempts == 1


def test_the_code_stops_working_after_five_wrong_tries(
    api_client, django_capture_on_commit_callbacks
):
    _request_code(api_client, django_capture_on_commit_callbacks)
    code = _code()
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(5):
        api_client.post(VERIFY_URL, {**DETAILS, "code": wrong}, format="json")

    response = api_client.post(VERIFY_URL, {**DETAILS, "code": code}, format="json")

    assert response.status_code == 401
    assert not User.objects.exists()


def test_an_expired_code_is_rejected(api_client, django_capture_on_commit_callbacks):
    _request_code(api_client, django_capture_on_commit_callbacks)
    code = _code()
    TeacherSignupCode.objects.update(expires_at=timezone.now() - timedelta(seconds=1))

    response = api_client.post(VERIFY_URL, {**DETAILS, "code": code}, format="json")

    assert response.status_code == 401
    assert not User.objects.exists()


def test_a_code_cannot_be_used_without_asking_for_one(api_client):
    response = api_client.post(VERIFY_URL, {**DETAILS, "code": "123456"}, format="json")

    assert response.status_code == 401
    assert not User.objects.exists()


def test_a_registered_email_gets_the_same_answer_and_a_sign_in_reminder(
    api_client, django_capture_on_commit_callbacks
):
    User.objects.create_user(username="sara", email="sara@example.com", password="x" * 12)

    response = _request_code(api_client, django_capture_on_commit_callbacks)

    assert response.status_code == 204
    assert "already have" in mail.outbox[-1].subject
    assert not TeacherSignupCode.objects.exists()


def test_a_school_email_cannot_start_a_trial(api_client, django_capture_on_commit_callbacks):
    School.objects.create(name_en="Al Noor", code="alnoor", email="sara@example.com")

    _request_code(api_client, django_capture_on_commit_callbacks)

    assert not TeacherSignupCode.objects.exists()


def test_asking_again_straight_away_does_not_send_another_email(
    api_client, django_capture_on_commit_callbacks
):
    _request_code(api_client, django_capture_on_commit_callbacks)
    _request_code(api_client, django_capture_on_commit_callbacks)

    assert len(mail.outbox) == 1


def test_a_new_code_replaces_the_old_one_after_the_wait(
    api_client, django_capture_on_commit_callbacks
):
    _request_code(api_client, django_capture_on_commit_callbacks)
    TeacherSignupCode.objects.update(sent_at=timezone.now() - timedelta(minutes=1), attempts=3)

    _request_code(api_client, django_capture_on_commit_callbacks)

    assert len(mail.outbox) == 2
    assert TeacherSignupCode.objects.get().attempts == 0


def test_bots_that_fill_the_hidden_field_get_no_email(
    api_client, django_capture_on_commit_callbacks
):
    response = _request_code(
        api_client, django_capture_on_commit_callbacks, website="http://spam.example"
    )

    assert response.status_code == 204
    assert not mail.outbox
    assert not TeacherSignupCode.objects.exists()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("full_name", ""),
        ("full_name", "12345"),
        ("full_name", "x" * 121),
        ("email", "not-an-email"),
        ("password", "short1!"),
        ("password", "password123"),
        ("password", "4829173650"),
        ("password", "sara@example.com"),
        ("accept_privacy", False),
    ],
)
def test_invalid_details_are_rejected(api_client, field, value):
    response = api_client.post(REQUEST_URL, {**DETAILS, field: value}, format="json")

    assert response.status_code == 400
    assert field in response.data["error"]["fields"]
    assert not mail.outbox


def test_the_password_is_checked_again_with_the_code(
    api_client, django_capture_on_commit_callbacks
):
    _request_code(api_client, django_capture_on_commit_callbacks)

    response = api_client.post(
        VERIFY_URL, {**DETAILS, "password": "password123", "code": _code()}, format="json"
    )

    assert response.status_code == 400
    assert not User.objects.exists()


def test_the_trial_ends_after_seven_days(api_client, django_capture_on_commit_callbacks):
    _sign_up(api_client, django_capture_on_commit_callbacks)
    today = timezone.localdate()

    assert expire_overdue_subscriptions(today + timedelta(days=TRIAL_DAYS - 1)) == 0
    assert expire_overdue_subscriptions(today + timedelta(days=TRIAL_DAYS)) == 1

    assert Subscription.objects.get().status == Subscription.Status.EXPIRED
    assert api_client.get("/api/auth/me/").data["trial"] is None


def test_workspaces_are_not_counted_as_schools(api_client, django_capture_on_commit_callbacks):
    School.objects.create(name_en="Al Noor", code="alnoor")
    _sign_up(api_client, django_capture_on_commit_callbacks)

    assert [school.code for school in list_schools()] == ["alnoor"]
    assert [school.code for school in list_school_usage()] == ["alnoor"]
    assert get_school_counts()["total"] == 1


def test_people_without_a_trial_have_none_in_their_session(api_client, two_schools):
    user = User.objects.create_user(username="teacher1", password="correct-pass123")
    Membership.objects.create(school=two_schools[0], user=user, role=Membership.Role.TEACHER)

    response = api_client.post(
        "/api/auth/login/",
        {"username": "teacher1", "password": "correct-pass123"},
        format="json",
    )

    assert response.data["trial"] is None


def _trials_from(ip_address, count, *, hours_ago=1):
    events = AuditEvent.objects.bulk_create(
        AuditEvent(
            action=AuditEvent.Action.SUBSCRIPTION_ACTIVATED,
            target_type="subscription",
            target_id=index,
            ip_address=ip_address,
            details={"trial": True},
        )
        for index in range(count)
    )
    AuditEvent.objects.filter(pk__in=[event.pk for event in events]).update(
        created_at=timezone.now() - timedelta(hours=hours_ago)
    )


def test_a_fourth_trial_from_one_network_in_a_day_is_refused(
    api_client, django_capture_on_commit_callbacks
):
    _trials_from("127.0.0.1", 3)

    response = _sign_up(api_client, django_capture_on_commit_callbacks)

    assert response.status_code == 429
    assert response.data["error"]["code"] == "trial_signup_limit"
    assert not User.objects.filter(email="sara@example.com").exists()
    assert not School.objects.exists()


def test_older_trials_and_other_networks_do_not_count(
    api_client, django_capture_on_commit_callbacks
):
    _trials_from("127.0.0.1", 3, hours_ago=25)
    _trials_from("10.0.0.9", 5)

    response = _sign_up(api_client, django_capture_on_commit_callbacks)

    assert response.status_code == 201
