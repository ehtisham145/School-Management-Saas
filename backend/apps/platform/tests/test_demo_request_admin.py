import pytest
from django.contrib.admin.sites import site
from rest_framework.test import APIClient

from apps.platform.models import DemoRequest
from apps.tenancy.models import School

Status = DemoRequest.Status
MANAGE_URL = "/api/platform/manage/demo-requests/"
SUMMARY_URL = f"{MANAGE_URL}summary/"
PUBLIC_URL = "/api/platform/demo-requests/"


def _demo(**overrides):
    return DemoRequest.objects.create(
        **{"name": "Sara", "school_name": "Al Noor", "email": "sara@example.com", **overrides}
    )


def _detail(demo):
    return f"{MANAGE_URL}{demo.id}/"


def test_a_public_submission_reaches_the_inbox_as_new(platform_client, api_client):
    api_client.post(
        PUBLIC_URL,
        {"name": "Sara", "school_name": "Al Noor", "email": "sara@example.com", "plan": "basic"},
    )

    response = platform_client.get(MANAGE_URL)

    assert response.status_code == 200
    assert response.data["count"] == 1
    row = response.data["results"][0]
    assert row["school_name"] == "Al Noor"
    assert row["status"] == Status.NEW
    assert row["admin_notes"] == ""
    assert row["converted_school_code"] is None


def test_list_shows_newest_first_and_is_paginated(platform_client):
    demos = [_demo(name=f"Lead {i}") for i in range(27)]

    response = platform_client.get(MANAGE_URL)

    assert response.data["count"] == 27
    assert len(response.data["results"]) == 25
    assert response.data["results"][0]["id"] == demos[-1].id


def test_list_filters_by_status(platform_client):
    _demo()
    contacted = _demo(status=Status.CONTACTED)

    response = platform_client.get(MANAGE_URL, {"status": Status.CONTACTED})

    assert [row["id"] for row in response.data["results"]] == [contacted.id]


def test_list_rejects_an_unknown_status(platform_client):
    assert platform_client.get(MANAGE_URL, {"status": "lost"}).status_code == 400


@pytest.mark.parametrize("term", ["hala", "riyadh acad", "hala@acad", "9665"])
def test_list_searches_contact_fields(platform_client, term):
    _demo()
    match = _demo(
        name="Hala",
        school_name="Riyadh Academy",
        email="hala@academy.example",
        phone="+966501234567",
    )

    response = platform_client.get(MANAGE_URL, {"search": term})

    assert [row["id"] for row in response.data["results"]] == [match.id]


def test_list_query_count_does_not_grow_with_requests(
    platform_client, django_assert_max_num_queries
):
    school = School.objects.create(name_en="S", name_ar="S", code="s")
    for _ in range(10):
        _demo(status=Status.CONVERTED, converted_school=school)

    with django_assert_max_num_queries(6):
        assert platform_client.get(MANAGE_URL).status_code == 200


def test_retrieve_returns_one_request(platform_client):
    demo = _demo(message="We have 400 students.")

    response = platform_client.get(_detail(demo))

    assert response.status_code == 200
    assert response.data["message"] == "We have 400 students."


def test_retrieve_a_missing_request_is_404(platform_client):
    assert platform_client.get(f"{MANAGE_URL}999/").status_code == 404


@pytest.mark.parametrize("status", [Status.CONTACTED, Status.DEMO_SCHEDULED, Status.REJECTED])
def test_status_can_move_along_the_pipeline(platform_client, status):
    demo = _demo()

    response = platform_client.patch(_detail(demo), {"status": status}, format="json")

    assert response.status_code == 200
    assert response.data["status"] == status
    demo.refresh_from_db()
    assert demo.status == status
    assert demo.is_handled is True


def test_a_rejected_request_can_be_reopened(platform_client):
    demo = _demo(status=Status.REJECTED)

    response = platform_client.patch(_detail(demo), {"status": Status.NEW}, format="json")

    assert response.status_code == 200
    demo.refresh_from_db()
    assert demo.is_handled is False


def test_notes_are_saved_without_touching_the_status(platform_client):
    demo = _demo(status=Status.CONTACTED)

    response = platform_client.patch(_detail(demo), {"admin_notes": "Call Sunday."}, format="json")

    assert response.status_code == 200
    demo.refresh_from_db()
    assert demo.admin_notes == "Call Sunday."
    assert demo.status == Status.CONTACTED


def test_notes_can_be_cleared_and_have_a_limit(platform_client):
    demo = _demo(admin_notes="Old")

    assert (
        platform_client.patch(_detail(demo), {"admin_notes": ""}, format="json").status_code == 200
    )
    too_long = platform_client.patch(_detail(demo), {"admin_notes": "x" * 2001}, format="json")

    assert too_long.status_code == 400
    assert "admin_notes" in too_long.data["error"]["fields"]


def test_converted_cannot_be_set_by_hand(platform_client):
    demo = _demo()

    response = platform_client.patch(_detail(demo), {"status": Status.CONVERTED}, format="json")

    assert response.status_code == 400
    assert "status" in response.data["error"]["fields"]
    demo.refresh_from_db()
    assert demo.status == Status.NEW


def test_a_converted_request_keeps_its_status_but_accepts_notes(platform_client):
    school = School.objects.create(name_en="S", name_ar="S", code="linked")
    demo = _demo(status=Status.CONVERTED, converted_school=school)

    moved = platform_client.patch(_detail(demo), {"status": Status.NEW}, format="json")
    noted = platform_client.patch(
        _detail(demo), {"status": Status.CONVERTED, "admin_notes": "Live."}, format="json"
    )

    assert moved.status_code == 400
    assert noted.status_code == 200
    assert noted.data["converted_school_code"] == "linked"


def test_an_unknown_status_is_rejected(platform_client):
    response = platform_client.patch(_detail(_demo()), {"status": "lost"}, format="json")

    assert response.status_code == 400
    assert "status" in response.data["error"]["fields"]


def test_contact_details_cannot_be_changed(platform_client):
    demo = _demo()

    response = platform_client.patch(
        _detail(demo), {"email": "new@example.com", "name": "Changed"}, format="json"
    )

    assert response.status_code == 200
    demo.refresh_from_db()
    assert demo.email == "sara@example.com"
    assert demo.name == "Sara"


def test_only_reading_and_patching_are_available(platform_client):
    demo = _demo()
    body = {"name": "X", "school_name": "Y", "email": "x@example.com"}

    assert platform_client.post(MANAGE_URL, body).status_code == 405
    assert platform_client.put(_detail(demo), body).status_code == 405
    assert platform_client.delete(_detail(demo)).status_code == 405
    assert DemoRequest.objects.filter(pk=demo.pk).exists()


def test_summary_counts_every_status(platform_client):
    _demo()
    _demo()
    _demo(status=Status.REJECTED)

    response = platform_client.get(SUMMARY_URL)

    assert response.status_code == 200
    assert response.data == {
        "total": 3,
        "by_status": {
            "new": 2,
            "contacted": 0,
            "demo_scheduled": 0,
            "converted": 0,
            "rejected": 1,
        },
    }


def test_everyone_else_is_denied(two_schools, school_admin_client, unverified_platform_client):
    demo = _demo(email="private@example.com")

    for client in (APIClient(), school_admin_client, unverified_platform_client):
        assert client.get(MANAGE_URL).status_code == 403
        assert client.get(SUMMARY_URL).status_code == 403
        assert client.get(_detail(demo)).status_code == 403
        assert (
            client.patch(_detail(demo), {"status": Status.REJECTED}, format="json").status_code
            == 403
        )

    demo.refresh_from_db()
    assert demo.status == Status.NEW


def test_the_public_form_stays_write_only(db, api_client):
    _demo()

    assert api_client.get(PUBLIC_URL).status_code == 405


def test_public_form_cannot_set_the_status_or_notes(db, api_client):
    response = api_client.post(
        PUBLIC_URL,
        {
            "name": "Sara",
            "school_name": "Al Noor",
            "email": "sara@example.com",
            "status": Status.CONVERTED,
            "admin_notes": "injected",
        },
    )

    assert response.status_code == 201
    demo = DemoRequest.objects.get()
    assert demo.status == Status.NEW
    assert demo.admin_notes == ""


def test_django_admin_cannot_change_the_status(rf):
    readonly = site._registry[DemoRequest].get_readonly_fields(rf.get("/"))

    assert "status" in readonly
    assert "admin_notes" not in readonly
