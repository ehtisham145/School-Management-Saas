import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.tenancy.models import Membership

PASSWORD = "correct-pass123"  # noqa: S105


def signed_in(user):
    client = APIClient()
    response = client.post("/api/auth/login/", {"username": user.username, "password": PASSWORD})
    assert response.status_code == 200
    return client


@pytest.fixture
def platform_client(db):
    user = User.objects.create_user("platform", password=PASSWORD, is_platform_admin=True)
    return signed_in(user)


@pytest.fixture
def school_admin_client(two_schools):
    user = User.objects.create_user("head", password=PASSWORD)
    Membership.objects.create(school=two_schools[0], user=user, role=Membership.Role.SCHOOL_ADMIN)
    return signed_in(user)
