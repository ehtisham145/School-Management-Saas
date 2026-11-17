import re

import pytest
from django.core import mail

from apps.accounts.models import User
from apps.tenancy.models import Membership

REQUEST_URL = "/api/auth/password/reset/request/"
CONFIRM_URL = "/api/auth/password/reset/confirm/"
STRONG = "Blue-river-2026!"

pytestmark = pytest.mark.django_db


def _new_staff(school, role=Membership.Role.SCHOOL_ADMIN, username="school-a.admin"):
    """A staff account as the Super Admin creates it: no password, only an email."""
    user = User.objects.create_user(username=username, email=f"{username}@example.com")
    Membership.objects.create(school=school, user=user, role=role)
    return user


def _request_code(client, email):
    client.post(REQUEST_URL, {"email": email})
    return re.search(r"code is: (\d{6})", mail.outbox[-1].body).group(1)


def test_request_sends_code_for_existing_user(api_client):
    User.objects.create_user(username="parent1", password="x" * 12, email="parent1@example.com")

    response = api_client.post(REQUEST_URL, {"email": "parent1@example.com"})

    assert response.status_code == 204
    assert len(mail.outbox) == 1


def test_request_is_silent_for_unknown_email(api_client):
    response = api_client.post(REQUEST_URL, {"email": "nobody@example.com"})

    assert response.status_code == 204
    assert len(mail.outbox) == 0


def test_confirm_sets_the_first_password_for_new_staff(api_client, two_schools):
    user = _new_staff(two_schools[0])
    code = _request_code(api_client, user.email)

    response = api_client.post(CONFIRM_URL, {"email": user.email, "code": code, "password": STRONG})

    assert response.status_code == 200
    assert len(response.data["memberships"]) == 1
    user.refresh_from_db()
    assert user.check_password(STRONG)
    assert api_client.get("/api/auth/me/").status_code == 200


def test_confirm_replaces_an_existing_password(api_client, two_schools):
    user = User.objects.create_user(
        username="teacher1", password="Old-password-99", email="teacher1@example.com"
    )
    Membership.objects.create(school=two_schools[0], user=user, role=Membership.Role.TEACHER)
    code = _request_code(api_client, user.email)

    response = api_client.post(CONFIRM_URL, {"email": user.email, "code": code, "password": STRONG})

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.check_password(STRONG)
    assert not user.check_password("Old-password-99")


def test_confirm_rejects_an_invalid_code(api_client, two_schools):
    user = _new_staff(two_schools[0])
    _request_code(api_client, user.email)

    response = api_client.post(
        CONFIRM_URL, {"email": user.email, "code": "000000", "password": STRONG}
    )

    assert response.status_code == 401
    assert response.data["error"]["code"] == "invalid_credentials"
    user.refresh_from_db()
    assert not user.has_usable_password()


def test_confirm_rejects_an_unknown_email(api_client):
    response = api_client.post(
        CONFIRM_URL, {"email": "nobody@example.com", "code": "123456", "password": STRONG}
    )

    assert response.status_code == 401


@pytest.mark.parametrize(
    "password",
    [
        "short1!",  # under 10 characters
        "password123",  # a common password
        "4829173650",  # numbers only
        "school-a.admin1",  # too close to the username
    ],
)
def test_confirm_rejects_weak_passwords(api_client, two_schools, password):
    user = _new_staff(two_schools[0])
    code = _request_code(api_client, user.email)

    response = api_client.post(
        CONFIRM_URL, {"email": user.email, "code": code, "password": password}
    )

    assert response.status_code == 400
    assert "password" in response.data["error"]["fields"]
    user.refresh_from_db()
    assert not user.has_usable_password()


def test_a_platform_admin_without_a_password_can_reset_one(api_client):
    user = User.objects.create_user(
        username="owner", email="owner@example.com", is_platform_admin=True
    )
    code = _request_code(api_client, user.email)

    response = api_client.post(CONFIRM_URL, {"email": user.email, "code": code, "password": STRONG})

    assert response.status_code == 200
    assert response.data["is_platform_admin"] is True
