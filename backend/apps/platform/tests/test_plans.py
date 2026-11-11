from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.audit.models import AuditEvent
from apps.platform.models import Plan

PLANS_URL = "/api/platform/plans/"
VALID_PLAN = {
    "code": "premium",
    "name_en": "Premium",
    "name_ar": "المميزة",
    "monthly_price": "3000.00",
    "yearly_price": "30000.00",
    "max_students": 800,
}


def _plan_url(plan):
    return f"{PLANS_URL}{plan.pk}/"


def test_create_plan_stores_prices_as_decimals_and_logs_it(platform_client):
    response = platform_client.post(PLANS_URL, VALID_PLAN, format="json")

    assert response.status_code == 201
    assert response.data["monthly_price"] == "3000.00"
    assert response.data["active_subscriptions"] == 0
    plan = Plan.objects.get(code="premium")
    assert plan.yearly_price == Decimal("30000.00")
    event = AuditEvent.objects.get(action=AuditEvent.Action.PLAN_CREATED)
    assert event.target_id == plan.pk
    assert event.actor_label == "owner@lessonlab.example"


def test_code_is_lower_cased_and_must_be_unused(platform_client, basic_plan):
    response = platform_client.post(PLANS_URL, {**VALID_PLAN, "code": "BASIC"}, format="json")

    assert response.status_code == 400
    assert "code" in response.data["error"]["fields"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("monthly_price", "-1.00"),
        ("yearly_price", "1.234"),
        ("monthly_price", "1000000000.00"),
        ("name_en", "الباقة"),
        ("name_ar", "Premium"),
        ("max_students", 0),
        ("code", "not a slug"),
    ],
)
def test_create_rejects_invalid_values(platform_client, field, value):
    response = platform_client.post(PLANS_URL, {**VALID_PLAN, field: value}, format="json")

    assert response.status_code == 400
    assert field in response.data["error"]["fields"]
    assert not Plan.objects.exists()


def test_blank_student_limit_means_unlimited(platform_client):
    response = platform_client.post(PLANS_URL, {**VALID_PLAN, "max_students": None}, format="json")

    assert response.status_code == 201
    assert response.data["max_students"] is None


def test_update_changes_prices_and_records_old_and_new(platform_client, basic_plan):
    response = platform_client.patch(
        _plan_url(basic_plan), {"monthly_price": "1750.00"}, format="json"
    )

    assert response.status_code == 200
    basic_plan.refresh_from_db()
    assert basic_plan.monthly_price == Decimal("1750.00")
    event = AuditEvent.objects.get(action=AuditEvent.Action.PLAN_UPDATED)
    assert event.details == {"changes": {"monthly_price": ["1500.00", "1750.00"]}}


def test_update_without_a_real_change_logs_nothing(platform_client, basic_plan):
    platform_client.patch(_plan_url(basic_plan), {"name_en": "Basic"}, format="json")

    assert not AuditEvent.objects.filter(action=AuditEvent.Action.PLAN_UPDATED).exists()


def test_code_cannot_change(platform_client, basic_plan):
    response = platform_client.patch(_plan_url(basic_plan), {"code": "starter"}, format="json")

    assert response.status_code == 400
    basic_plan.refresh_from_db()
    assert basic_plan.code == "basic"


def test_plans_are_switched_off_not_deleted(platform_client, basic_plan):
    assert platform_client.delete(_plan_url(basic_plan)).status_code == 405

    response = platform_client.patch(_plan_url(basic_plan), {"is_active": False}, format="json")

    assert response.status_code == 200
    assert response.data["is_active"] is False


def test_list_filters_by_active_and_is_not_paginated(platform_client, basic_plan):
    Plan.objects.create(
        code="old",
        name_en="Old",
        name_ar="قديمة",
        monthly_price=1,
        yearly_price=10,
        is_active=False,
    )

    everything = platform_client.get(PLANS_URL)
    active = platform_client.get(f"{PLANS_URL}?active=true")

    assert [plan["code"] for plan in everything.data] == ["old", "basic"]
    assert [plan["code"] for plan in active.data] == ["basic"]


def test_plans_are_denied_to_everyone_else(school_admin_client, basic_plan):
    for client in (APIClient(), school_admin_client):
        assert client.get(PLANS_URL).status_code == 403
        assert client.post(PLANS_URL, VALID_PLAN, format="json").status_code == 403
        assert client.patch(_plan_url(basic_plan), {"is_active": False}).status_code == 403

    basic_plan.refresh_from_db()
    assert basic_plan.is_active is True
    assert Plan.objects.count() == 1
