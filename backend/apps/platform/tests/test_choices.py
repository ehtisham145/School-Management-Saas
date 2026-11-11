from rest_framework.test import APIClient

from apps.platform.models import DemoRequest, Plan
from apps.tenancy.models import School

CHOICES_URL = "/api/platform/choices/"


def test_choices_list_only_what_a_form_can_use(platform_client, two_schools, basic_plan):
    School.objects.filter(pk=two_schools[1].pk).update(is_active=False)
    Plan.objects.create(
        code="old", name_en="Old", name_ar="قديمة", monthly_price=1, yearly_price=1, is_active=False
    )
    open_request = DemoRequest.objects.create(name="A", school_name="Open", email="a@x.example")
    DemoRequest.objects.create(
        name="B", school_name="Done", email="b@x.example", status="converted"
    )
    DemoRequest.objects.create(name="C", school_name="No", email="c@x.example", status="rejected")

    response = platform_client.get(CHOICES_URL)

    assert response.status_code == 200
    assert [school["code"] for school in response.data["schools"]] == ["school-a"]
    assert [demo["id"] for demo in response.data["demo_requests"]] == [open_request.pk]
    assert response.data["plans"] == [
        {
            "id": basic_plan.pk,
            "code": "basic",
            "name_en": "Basic",
            "name_ar": "الأساسية",
            "monthly_price": "1500.00",
            "yearly_price": "15000.00",
            "max_students": 300,
        }
    ]


def test_choices_are_denied_to_everyone_else(school_admin_client):
    for client in (APIClient(), school_admin_client):
        assert client.get(CHOICES_URL).status_code == 403
