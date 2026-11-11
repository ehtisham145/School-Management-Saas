from datetime import date, timedelta

from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.platform.models import Subscription
from apps.tenancy.models import Membership, School

USAGE_URL = "/api/platform/usage/"
Role = Membership.Role


def _members(school, role, count, *, prefix, signed_in_days_ago=None, status="ACTIVE"):
    last_login = (
        timezone.now() - timedelta(days=signed_in_days_ago)
        if signed_in_days_ago is not None
        else None
    )
    for i in range(count):
        user = User.objects.create_user(f"{prefix}{i}", last_login=last_login)
        Membership.objects.create(school=school, user=user, role=role, status=status)


def _row(response, school):
    return next(row for row in response.data["results"] if row["id"] == school.pk)


def test_usage_counts_active_members_by_role(platform_client, two_schools):
    school_a, school_b = two_schools
    _members(school_a, Role.STUDENT, 3, prefix="s", signed_in_days_ago=2)
    _members(school_a, Role.STUDENT, 1, prefix="gone", status="SUSPENDED")
    _members(school_a, Role.TEACHER, 2, prefix="t", signed_in_days_ago=45)
    _members(school_a, Role.PARENT, 4, prefix="p")
    _members(school_a, Role.PRINCIPAL, 1, prefix="pr", signed_in_days_ago=1)
    _members(school_b, Role.STUDENT, 1, prefix="b")

    response = platform_client.get(USAGE_URL)

    row = _row(response, school_a)
    assert response.status_code == 200
    assert (row["students"], row["teachers"], row["parents"], row["staff"]) == (3, 2, 4, 1)
    # Only members who signed in within 30 days.
    assert row["active_users"] == 4
    assert _row(response, school_b)["students"] == 1


def test_usage_shows_the_current_plan_and_the_student_limit(
    platform_client, two_schools, basic_plan
):
    school_a = two_schools[0]
    Subscription.objects.create(
        school=school_a,
        plan=basic_plan,
        billing_cycle="monthly",
        price=basic_plan.monthly_price,
        starts_on=date(2026, 11, 1),
        ends_on=date(2026, 12, 1),
    )
    basic_plan.max_students = 2
    basic_plan.save()
    _members(school_a, Role.STUDENT, 3, prefix="s")

    response = platform_client.get(USAGE_URL)

    row = _row(response, school_a)
    assert row["plan"] == {
        "code": "basic",
        "name_en": "Basic",
        "name_ar": "الأساسية",
        "max_students": 2,
    }
    assert row["subscription_ends_on"] == "2026-12-01"
    assert row["over_student_limit"] is True
    assert _row(response, two_schools[1])["plan"] is None


def test_an_expired_subscription_is_not_the_current_plan(platform_client, two_schools, basic_plan):
    Subscription.objects.create(
        school=two_schools[0],
        plan=basic_plan,
        billing_cycle="monthly",
        price=1,
        starts_on=date(2026, 1, 1),
        ends_on=date(2026, 2, 1),
        status="expired",
    )

    assert _row(platform_client.get(USAGE_URL), two_schools[0])["plan"] is None


def test_usage_filters(platform_client, two_schools):
    School.objects.filter(pk=two_schools[1].pk).update(is_active=False)

    active = platform_client.get(f"{USAGE_URL}?status=active")
    searched = platform_client.get(f"{USAGE_URL}?search=school-b")

    assert [row["code"] for row in active.data["results"]] == ["school-a"]
    assert [row["code"] for row in searched.data["results"]] == ["school-b"]


def test_usage_summary_counts_only_active_schools(platform_client, two_schools, basic_plan):
    school_a, school_b = two_schools
    _members(school_a, Role.STUDENT, 2, prefix="s", signed_in_days_ago=1)
    _members(school_b, Role.STUDENT, 5, prefix="b")
    School.objects.filter(pk=school_b.pk).update(is_active=False)

    response = platform_client.get(f"{USAGE_URL}summary/")

    assert response.data["active_schools"] == 1
    assert response.data["students"] == 2
    assert response.data["active_users"] == 2
    assert response.data["active_user_days"] == 30


def test_usage_query_count_does_not_grow_with_schools(
    platform_client, django_assert_max_num_queries
):
    School.objects.bulk_create(
        School(name_en=f"S{i}", name_ar=f"S{i}", code=f"s{i}") for i in range(20)
    )

    # Session, user, page count and page rows.
    with django_assert_max_num_queries(5):
        assert platform_client.get(USAGE_URL).status_code == 200


def test_usage_is_denied_to_everyone_else(school_admin_client):
    for client in (APIClient(), school_admin_client):
        assert client.get(USAGE_URL).status_code == 403
        assert client.get(f"{USAGE_URL}summary/").status_code == 403
