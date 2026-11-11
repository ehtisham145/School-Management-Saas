from rest_framework.test import APIClient

from apps.platform.models import DemoRequest
from apps.platform.selectors import RECENT_LIMIT
from apps.tenancy.models import School

DASHBOARD_URL = "/api/platform/dashboard/"


def _demo(**overrides):
    return DemoRequest.objects.create(
        **{"name": "Sara", "school_name": "Al Noor", "email": "sara@example.com", **overrides}
    )


def test_dashboard_is_empty_without_data(platform_client):
    response = platform_client.get(DASHBOARD_URL)

    assert response.status_code == 200
    assert response.data["schools"] == {"total": 0, "active": 0, "inactive": 0}
    assert response.data["demo_requests"]["total"] == 0
    assert response.data["demo_requests"]["by_status"]["new"] == 0
    assert response.data["recent_schools"] == []
    assert response.data["recent_demo_requests"] == []


def test_dashboard_counts_schools_and_requests(platform_client, two_schools):
    School.objects.filter(pk=two_schools[1].pk).update(is_active=False)
    _demo()
    _demo(status=DemoRequest.Status.CONTACTED)

    response = platform_client.get(DASHBOARD_URL)

    assert response.data["schools"] == {"total": 2, "active": 1, "inactive": 1}
    assert response.data["demo_requests"]["total"] == 2
    assert response.data["demo_requests"]["by_status"]["new"] == 1
    assert response.data["demo_requests"]["by_status"]["contacted"] == 1


def test_dashboard_lists_only_the_latest_records(platform_client):
    School.objects.bulk_create(
        School(name_en=f"S{i}", name_ar=f"S{i}", code=f"s{i}") for i in range(RECENT_LIMIT + 2)
    )
    demos = [_demo(name=f"Lead {i}") for i in range(RECENT_LIMIT + 2)]

    response = platform_client.get(DASHBOARD_URL)

    assert len(response.data["recent_schools"]) == RECENT_LIMIT
    assert len(response.data["recent_demo_requests"]) == RECENT_LIMIT
    assert response.data["recent_demo_requests"][0]["id"] == demos[-1].id


def test_dashboard_is_read_only(platform_client):
    assert platform_client.post(DASHBOARD_URL).status_code == 405


def test_dashboard_is_denied_to_everyone_else(two_schools, school_admin_client):
    for client in (APIClient(), school_admin_client):
        assert client.get(DASHBOARD_URL).status_code == 403
