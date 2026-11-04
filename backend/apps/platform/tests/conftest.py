import pytest
from django_otp.oath import totp as generate_totp
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.tenancy.models import Membership

PASSWORD = "correct-pass123"  # noqa: S105


def signed_in_with_2fa(user):
    device = TOTPDevice.objects.create(user=user, name="default", confirmed=True)
    client = APIClient()
    client.post("/api/auth/login/", {"username": user.username, "password": PASSWORD})
    response = client.post(
        "/api/auth/2fa/verify/", {"token": f"{generate_totp(device.bin_key):06d}"}
    )
    assert response.status_code == 200
    return client


@pytest.fixture
def platform_client(db):
    user = User.objects.create_user("platform", password=PASSWORD, is_platform_admin=True)
    return signed_in_with_2fa(user)


@pytest.fixture
def school_admin_client(two_schools):
    user = User.objects.create_user("head", password=PASSWORD)
    Membership.objects.create(school=two_schools[0], user=user, role=Membership.Role.SCHOOL_ADMIN)
    return signed_in_with_2fa(user)


@pytest.fixture
def unverified_platform_client(db):
    """The kind of session a password-only Django admin login creates."""
    user = User.objects.create_user("platform2", password=PASSWORD, is_platform_admin=True)
    TOTPDevice.objects.create(user=user, name="default", confirmed=True)
    client = APIClient()
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")
    return client
