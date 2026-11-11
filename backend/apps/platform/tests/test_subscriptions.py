from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.audit.models import AuditEvent
from apps.platform.models import Plan, Subscription
from apps.platform.services import add_months, expire_overdue_subscriptions, subscription_end
from apps.platform.tasks import expire_overdue_subscriptions_task
from apps.tenancy.models import School

SUBSCRIPTIONS_URL = "/api/platform/subscriptions/"


def _activate(client, school, plan, /, **extra):
    return client.post(
        SUBSCRIPTIONS_URL,
        {"school": school.pk, "plan": plan.pk, "billing_cycle": "monthly", **extra},
        format="json",
    )


def _subscription(school, plan, *, starts_on, billing_cycle="monthly", status="active"):
    return Subscription.objects.create(
        school=school,
        plan=plan,
        billing_cycle=billing_cycle,
        price=plan.price_for(billing_cycle),
        starts_on=starts_on,
        ends_on=subscription_end(starts_on, billing_cycle),
        status=status,
    )


@pytest.mark.parametrize(
    ("start", "months", "end"),
    [
        (date(2026, 1, 31), 1, date(2026, 2, 28)),
        (date(2028, 1, 31), 1, date(2028, 2, 29)),
        (date(2026, 11, 15), 2, date(2027, 1, 15)),
        (date(2026, 3, 31), 12, date(2027, 3, 31)),
        (date(2028, 2, 29), 12, date(2029, 2, 28)),
    ],
)
def test_add_months_keeps_the_day_or_uses_the_month_end(start, months, end):
    assert add_months(start, months) == end


def test_activate_uses_the_plan_price_and_logs_it(platform_client, two_schools, basic_plan):
    school = two_schools[0]

    response = _activate(platform_client, school, basic_plan, starts_on="2026-11-01")

    assert response.status_code == 201
    assert response.data["price"] == "1500.00"
    assert response.data["starts_on"] == "2026-11-01"
    assert response.data["ends_on"] == "2026-12-01"
    assert response.data["status"] == "active"
    assert response.data["school"]["code"] == school.code
    event = AuditEvent.objects.get(action=AuditEvent.Action.SUBSCRIPTION_ACTIVATED)
    assert event.school == school
    assert event.details["price"] == "1500.00"


def test_yearly_uses_the_yearly_price(platform_client, two_schools, basic_plan):
    response = _activate(
        platform_client,
        two_schools[0],
        basic_plan,
        billing_cycle="yearly",
        starts_on="2026-11-01",
    )

    assert response.data["price"] == "15000.00"
    assert response.data["ends_on"] == "2027-11-01"


def test_an_agreed_price_overrides_the_plan(platform_client, two_schools, basic_plan):
    response = _activate(platform_client, two_schools[0], basic_plan, price="1200.50")

    assert response.status_code == 201
    assert Subscription.objects.get().price == Decimal("1200.50")


def test_start_defaults_to_today(platform_client, two_schools, basic_plan):
    response = _activate(platform_client, two_schools[0], basic_plan)

    assert response.data["starts_on"] == timezone.localdate().isoformat()


def test_a_school_can_have_only_one_active_subscription(platform_client, two_schools, basic_plan):
    school = two_schools[0]
    _activate(platform_client, school, basic_plan)

    response = _activate(platform_client, school, basic_plan)

    assert response.status_code == 400
    assert "school" in response.data["error"]["fields"]
    assert Subscription.objects.filter(school=school).count() == 1


def test_inactive_school_or_plan_is_refused(platform_client, two_schools, basic_plan):
    School.objects.filter(pk=two_schools[0].pk).update(is_active=False)
    Plan.objects.create(
        code="old", name_en="Old", name_ar="قديمة", monthly_price=1, yearly_price=1, is_active=False
    )
    old = Plan.objects.get(code="old")

    inactive_school = _activate(platform_client, two_schools[0], basic_plan)
    inactive_plan = _activate(platform_client, two_schools[1], old)

    assert inactive_school.status_code == 400
    assert "school" in inactive_school.data["error"]["fields"]
    assert inactive_plan.status_code == 400
    assert "plan" in inactive_plan.data["error"]["fields"]
    assert not Subscription.objects.exists()


@pytest.mark.parametrize(
    "extra",
    [
        {"billing_cycle": "weekly"},
        {"price": "-5"},
        {"starts_on": "2020-01-01"},
        {"plan": 999999},
        {"school": 999999},
    ],
)
def test_activate_rejects_invalid_input(platform_client, two_schools, basic_plan, extra):
    response = _activate(platform_client, two_schools[0], basic_plan, **extra)

    assert response.status_code == 400
    assert not Subscription.objects.exists()


def test_expire_ends_it_and_frees_the_school(platform_client, two_schools, basic_plan):
    school = two_schools[0]
    subscription_id = _activate(platform_client, school, basic_plan).data["id"]

    response = platform_client.post(f"{SUBSCRIPTIONS_URL}{subscription_id}/expire/")

    assert response.status_code == 200
    assert response.data["status"] == "expired"
    assert response.data["expired_at"] is not None
    assert AuditEvent.objects.filter(
        action=AuditEvent.Action.SUBSCRIPTION_EXPIRED, details={"reason": "manual"}
    ).exists()
    assert _activate(platform_client, school, basic_plan).status_code == 201


def test_expiring_twice_is_refused(platform_client, two_schools, basic_plan):
    subscription_id = _activate(platform_client, two_schools[0], basic_plan).data["id"]
    platform_client.post(f"{SUBSCRIPTIONS_URL}{subscription_id}/expire/")

    response = platform_client.post(f"{SUBSCRIPTIONS_URL}{subscription_id}/expire/")

    assert response.status_code == 400


def test_daily_job_expires_only_overdue_subscriptions(two_schools, basic_plan):
    today = date(2026, 11, 11)
    overdue = _subscription(two_schools[0], basic_plan, starts_on=date(2026, 10, 11))
    current = _subscription(two_schools[1], basic_plan, starts_on=date(2026, 10, 12))

    with_count = expire_overdue_subscriptions(today=today)

    overdue.refresh_from_db()
    current.refresh_from_db()
    assert with_count == 1
    assert overdue.status == Subscription.Status.EXPIRED
    assert current.status == Subscription.Status.ACTIVE
    event = AuditEvent.objects.get(action=AuditEvent.Action.SUBSCRIPTION_EXPIRED)
    assert event.actor is None
    assert event.details == {"reason": "ended"}


def test_daily_task_runs_the_job(two_schools, basic_plan):
    _subscription(two_schools[0], basic_plan, starts_on=timezone.localdate() - timedelta(days=40))

    assert expire_overdue_subscriptions_task.delay().get() == 1


def test_list_filters_and_counts(platform_client, two_schools, basic_plan):
    school_a, school_b = two_schools
    _subscription(school_a, basic_plan, starts_on=date(2026, 1, 1), status="expired")
    _subscription(school_a, basic_plan, starts_on=date(2026, 6, 1))
    _subscription(school_b, basic_plan, starts_on=date(2026, 7, 1))

    active = platform_client.get(f"{SUBSCRIPTIONS_URL}?status=active")
    for_a = platform_client.get(f"{SUBSCRIPTIONS_URL}?school={school_a.pk}")
    searched = platform_client.get(f"{SUBSCRIPTIONS_URL}?search=school-b")
    summary = platform_client.get(f"{SUBSCRIPTIONS_URL}summary/")

    assert active.data["count"] == 2
    assert for_a.data["count"] == 2
    assert searched.data["count"] == 1
    assert summary.data == {"total": 3, "active": 2, "expired": 1}


def test_subscriptions_are_denied_to_everyone_else(school_admin_client, two_schools, basic_plan):
    subscription = _subscription(two_schools[0], basic_plan, starts_on=date(2026, 11, 1))

    for client in (APIClient(), school_admin_client):
        assert client.get(SUBSCRIPTIONS_URL).status_code == 403
        assert _activate(client, two_schools[1], basic_plan).status_code == 403
        assert client.post(f"{SUBSCRIPTIONS_URL}{subscription.pk}/expire/").status_code == 403

    subscription.refresh_from_db()
    assert subscription.status == Subscription.Status.ACTIVE
    assert Subscription.objects.count() == 1


def test_subscriptions_cannot_be_edited_or_deleted(platform_client, two_schools, basic_plan):
    subscription = _subscription(two_schools[0], basic_plan, starts_on=date(2026, 11, 1))
    url = f"{SUBSCRIPTIONS_URL}{subscription.pk}/"

    assert platform_client.patch(url, {"price": "1"}, format="json").status_code == 405
    assert platform_client.delete(url).status_code == 405
