from rest_framework.test import APIClient

from apps.audit.models import AuditEvent
from apps.platform.tests.test_api import SCHOOLS_URL, VALID_SCHOOL

AUDIT_URL = "/api/platform/audit-log/"


def test_school_actions_are_logged_with_actor_and_ip(platform_client, two_schools):
    created = platform_client.post(SCHOOLS_URL, VALID_SCHOOL, REMOTE_ADDR="203.0.113.7")
    platform_client.post(f"{SCHOOLS_URL}{created.data['id']}/deactivate/")
    platform_client.post(f"{SCHOOLS_URL}{created.data['id']}/activate/")

    response = platform_client.get(AUDIT_URL)

    actions = [row["action"] for row in response.data["results"]]
    assert actions == ["school.activated", "school.deactivated", "school.created"]
    created_event = response.data["results"][-1]
    assert created_event["actor_label"] == "owner@lessonlab.example"
    assert created_event["ip_address"] == "203.0.113.7"
    assert created_event["school"]["code"] == "alnoor"
    assert created_event["target_type"] == "school"


def test_deactivating_an_inactive_school_logs_nothing(platform_client, two_schools):
    school_b = two_schools[1]
    platform_client.post(f"{SCHOOLS_URL}{school_b.pk}/deactivate/")
    platform_client.post(f"{SCHOOLS_URL}{school_b.pk}/deactivate/")

    assert AuditEvent.objects.filter(action="school.deactivated").count() == 1


def test_demo_request_changes_are_logged(platform_client, demo_request):
    platform_client.patch(
        f"/api/platform/manage/demo-requests/{demo_request.pk}/",
        {"status": "contacted"},
        format="json",
    )

    event = AuditEvent.objects.get(action="demo_request.updated")
    assert event.details == {"status": ["new", "contacted"], "notes_changed": False}
    assert event.target_label == "Al Noor School"


def test_audit_log_filters(platform_client, two_schools):
    platform_client.post(f"{SCHOOLS_URL}{two_schools[0].pk}/deactivate/")
    platform_client.post(f"{SCHOOLS_URL}{two_schools[1].pk}/deactivate/")
    platform_client.post(f"{SCHOOLS_URL}{two_schools[1].pk}/activate/")

    by_action = platform_client.get(f"{AUDIT_URL}?action=school.activated")
    by_school = platform_client.get(f"{AUDIT_URL}?school={two_schools[0].pk}")
    by_search = platform_client.get(AUDIT_URL, {"search": "School B"})

    assert by_action.data["count"] == 1
    assert by_school.data["count"] == 1
    assert by_search.data["count"] == 2


def test_unknown_filter_values_are_refused(platform_client):
    assert platform_client.get(f"{AUDIT_URL}?action=school.deleted").status_code == 400


def test_audit_log_is_read_only(platform_client, two_schools):
    platform_client.post(f"{SCHOOLS_URL}{two_schools[0].pk}/deactivate/")
    event = AuditEvent.objects.get()

    assert platform_client.post(AUDIT_URL, {"action": "school.created"}).status_code == 405
    assert platform_client.delete(f"{AUDIT_URL}{event.pk}/").status_code == 404
    assert platform_client.patch(f"{AUDIT_URL}{event.pk}/", {}).status_code == 404
    assert AuditEvent.objects.count() == 1


def test_audit_log_is_denied_to_everyone_else(school_admin_client, two_schools):
    for client in (APIClient(), school_admin_client):
        assert client.get(AUDIT_URL).status_code == 403
