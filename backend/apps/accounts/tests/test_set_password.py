import re

import pytest
from django.core import mail

from apps.accounts.models import User
from apps.tenancy.models import Membership

SET_URL = "/api/auth/password/set/"
STRONG = "Blue-river-2026!"

pytestmark = pytest.mark.django_db


def _new_staff(school, role=Membership.Role.SCHOOL_ADMIN, username="school-a.admin"):
    """A staff account as the Super Admin creates it: no password, only an email."""
    user = User.objects.create_user(username=username, email=f"{username}@example.com")
    Membership.objects.create(school=school, user=user, role=role)
    return user


def _sign_in_with_email_code(client, email):
    client.post("/api/auth/email-otp/request/", {"email": email})
    code = re.search(r"code is: (\d{6})", mail.outbox[-1].body).group(1)
    return client.post("/api/auth/email-otp/verify/", {"email": email, "code": code})


@pytest.mark.parametrize(
    "role", [Membership.Role.SCHOOL_ADMIN, Membership.Role.PRINCIPAL, Membership.Role.TEACHER]
)
def test_staff_without_a_password_are_asked_to_set_one(api_client, two_schools, role):
    user = _new_staff(two_schools[0], role)

    response = _sign_in_with_email_code(api_client, user.email)

    assert response.status_code == 200
    assert response.data["needs_password"] is True


def test_parents_without_a_password_are_not_asked(api_client, two_schools):
    user = _new_staff(two_schools[0], Membership.Role.PARENT, username="parent1")

    response = _sign_in_with_email_code(api_client, user.email)

    assert response.data["needs_password"] is False
    assert api_client.post(SET_URL, {"password": STRONG}).status_code == 409


def test_setting_the_password_keeps_the_session_and_enables_password_login(api_client, two_schools):
    user = _new_staff(two_schools[0])
    _sign_in_with_email_code(api_client, user.email)

    response = api_client.post(SET_URL, {"password": STRONG})

    assert response.status_code == 200
    assert response.data["needs_password"] is False
    assert len(response.data["memberships"]) == 1
    assert api_client.get("/api/auth/me/").status_code == 200

    fresh = type(api_client)()
    login = fresh.post("/api/auth/login/", {"username": user.username, "password": STRONG})
    assert login.status_code == 200
    assert login.data["needs_password"] is False


def test_me_reports_the_missing_password_until_it_is_set(api_client, two_schools):
    user = _new_staff(two_schools[0])
    _sign_in_with_email_code(api_client, user.email)

    assert api_client.get("/api/auth/me/").data["needs_password"] is True
    api_client.post(SET_URL, {"password": STRONG})
    assert api_client.get("/api/auth/me/").data["needs_password"] is False


@pytest.mark.parametrize(
    "password",
    [
        "short1!",  # under 10 characters
        "password123",  # a common password
        "4829173650",  # numbers only
        "school-a.admin1",  # too close to the username
    ],
)
def test_weak_passwords_are_rejected(api_client, two_schools, password):
    user = _new_staff(two_schools[0])
    _sign_in_with_email_code(api_client, user.email)

    response = api_client.post(SET_URL, {"password": password})

    assert response.status_code == 400
    assert "password" in response.data["error"]["fields"]
    user.refresh_from_db()
    assert not user.has_usable_password()


def test_a_password_cannot_be_replaced_through_this_endpoint(api_client, two_schools):
    user = User.objects.create_user(username="teacher1", password="Old-password-99")
    Membership.objects.create(school=two_schools[0], user=user, role=Membership.Role.TEACHER)
    api_client.force_login(user)

    response = api_client.post(SET_URL, {"password": STRONG})

    assert response.status_code == 409
    assert response.data["error"]["code"] == "password_already_set"
    user.refresh_from_db()
    assert user.check_password("Old-password-99")


def test_signed_out_visitors_cannot_set_a_password(api_client, two_schools):
    _new_staff(two_schools[0])

    response = api_client.post(SET_URL, {"password": STRONG})

    assert response.status_code == 403
    assert not User.objects.get(username="school-a.admin").has_usable_password()


def test_a_platform_admin_without_a_password_is_asked_too(api_client):
    user = User.objects.create_user(
        username="owner", email="owner@example.com", is_platform_admin=True
    )

    response = _sign_in_with_email_code(api_client, user.email)

    assert response.data["needs_password"] is True
    assert api_client.post(SET_URL, {"password": STRONG}).status_code == 200
