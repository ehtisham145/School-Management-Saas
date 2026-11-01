import pytest
from rest_framework.test import APIClient

from apps.tenancy.models import School


@pytest.fixture
def two_schools(db):
    return (
        School.objects.create(name_en="School A", name_ar="مدرسة أ", code="school-a"),
        School.objects.create(name_en="School B", name_ar="مدرسة ب", code="school-b"),
    )


@pytest.fixture
def api_client():
    return APIClient()
