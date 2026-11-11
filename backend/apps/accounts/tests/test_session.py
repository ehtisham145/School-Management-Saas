import re

from django.core import mail
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.tenancy.models import Membership

Role = Membership.Role
PASSWORD = "correct-pass123"  # noqa: S105


def _user(username="user1", email=""):
    return User.objects.create_user(username=username, password=PASSWORD, email=email)


def _login(client, username="user1"):
    return client.post("/api/auth/login/", {"username": username, "password": PASSWORD})


def test_login_activates_the_only_school(api_client, two_schools):
    school_a, _ = two_schools
    membership = Membership.objects.create(school=school_a, user=_user(), role=Role.TEACHER)

    _login(api_client)

    assert api_client.session["active_membership_id"] == membership.id
    assert api_client.get("/api/academics/years/").status_code == 200


def test_login_does_not_pick_a_school_when_user_has_several(api_client, two_schools):
    school_a, school_b = two_schools
    user = _user()
    Membership.objects.create(school=school_a, user=user, role=Role.TEACHER)
    Membership.objects.create(school=school_b, user=user, role=Role.PARENT)

    response = _login(api_client)

    assert len(response.data["memberships"]) == 2
    assert "active_membership_id" not in api_client.session
    assert api_client.get("/api/academics/years/").status_code == 403


def _email_code(client, email):
    client.post("/api/auth/email-otp/request/", {"email": email})
    return re.search(r"\b\d{6}\b", mail.outbox[-1].body).group()


def test_email_otp_activates_the_only_school(api_client, two_schools):
    school_a, _ = two_schools
    user = _user(email="parent@example.com")
    membership = Membership.objects.create(school=school_a, user=user, role=Role.PARENT)

    code = _email_code(api_client, user.email)
    api_client.post("/api/auth/email-otp/verify/", {"email": user.email, "code": code})

    assert api_client.session["active_membership_id"] == membership.id


def test_school_admin_signs_in_with_an_email_code_alone(api_client, two_schools):
    school_a, _ = two_schools
    user = _user(email="admin@example.com")
    Membership.objects.create(school=school_a, user=user, role=Role.SCHOOL_ADMIN)

    code = _email_code(api_client, user.email)
    response = api_client.post("/api/auth/email-otp/verify/", {"email": user.email, "code": code})

    assert response.status_code == 200
    assert "requires_2fa" not in response.data
    assert "requires_2fa_setup" not in response.data
    assert api_client.get("/api/academics/years/").status_code == 200


def test_me_requires_login(api_client, db):
    response = api_client.get("/api/auth/me/")

    assert response.status_code == 403
    assert response.data["error"]["code"] == "not_authenticated"


def test_me_returns_memberships_and_active_school(api_client, two_schools):
    school_a, _ = two_schools
    membership = Membership.objects.create(school=school_a, user=_user(), role=Role.TEACHER)
    _login(api_client)

    response = api_client.get("/api/auth/me/")

    assert response.status_code == 200
    assert response.data["username"] == "user1"
    assert response.data["active_membership_id"] == membership.id
    assert response.data["memberships"][0]["role"] == Role.TEACHER


def test_me_has_no_active_school_until_one_is_chosen(api_client, two_schools):
    school_a, school_b = two_schools
    user = _user()
    Membership.objects.create(school=school_a, user=user, role=Role.TEACHER)
    Membership.objects.create(school=school_b, user=user, role=Role.PARENT)
    _login(api_client)

    response = api_client.get("/api/auth/me/")

    assert response.data["active_membership_id"] is None
    assert len(response.data["memberships"]) == 2


def test_me_moves_to_remaining_school_after_suspension(api_client, two_schools):
    school_a, school_b = two_schools
    user = _user()
    suspended = Membership.objects.create(school=school_a, user=user, role=Role.TEACHER)
    remaining = Membership.objects.create(school=school_b, user=user, role=Role.PARENT)
    _login(api_client)
    api_client.post("/api/auth/switch-school/", {"membership_id": suspended.id})

    suspended.status = Membership.Status.SUSPENDED
    suspended.save()

    assert api_client.get("/api/auth/me/").data["active_membership_id"] == remaining.id


def test_me_has_no_active_school_when_all_memberships_are_suspended(api_client, two_schools):
    school_a, _ = two_schools
    membership = Membership.objects.create(school=school_a, user=_user(), role=Role.TEACHER)
    _login(api_client)

    membership.status = Membership.Status.SUSPENDED
    membership.save()

    response = api_client.get("/api/auth/me/")

    assert response.data["active_membership_id"] is None
    assert response.data["memberships"] == []


def test_errors_use_the_standard_format(api_client, two_schools):
    school_a, _ = two_schools
    Membership.objects.create(school=school_a, user=_user(), role=Role.SCHOOL_ADMIN)
    _login(api_client)

    not_found = api_client.get("/api/academics/years/999999/")
    invalid = api_client.post("/api/academics/years/", {"name": ""})

    assert not_found.status_code == 404
    assert not_found.data["error"]["code"] == "not_found"
    assert invalid.status_code == 400
    assert invalid.data["error"]["code"] == "validation_error"
    assert "name" in invalid.data["error"]["fields"]


def test_login_works_when_browser_still_has_an_old_session(two_schools):
    school_a, _ = two_schools
    Membership.objects.create(school=school_a, user=_user(), role=Role.TEACHER)
    client = APIClient(enforce_csrf_checks=True)
    assert _login(client).status_code == 200

    # Real CSRF checks are on and no token is sent, as with an expired cookie.
    response = _login(client)

    assert response.status_code == 200
    assert client.get("/api/academics/years/").status_code == 200


def test_login_as_another_user_replaces_the_old_session(two_schools):
    school_a, school_b = two_schools
    first = Membership.objects.create(school=school_a, user=_user("first"), role=Role.TEACHER)
    second = Membership.objects.create(school=school_b, user=_user("second"), role=Role.TEACHER)
    client = APIClient(enforce_csrf_checks=True)

    _login(client, "first")
    assert client.session["active_membership_id"] == first.id
    _login(client, "second")

    assert client.session["active_membership_id"] == second.id
    assert client.get("/api/auth/me/").data["username"] == "second"


def test_wrong_password_with_an_old_session_still_fails(two_schools):
    school_a, _ = two_schools
    Membership.objects.create(school=school_a, user=_user(), role=Role.TEACHER)
    client = APIClient(enforce_csrf_checks=True)
    _login(client)

    response = client.post("/api/auth/login/", {"username": "user1", "password": "wrong-pass-123"})

    assert response.status_code == 401
    assert response.data["error"]["code"] == "invalid_credentials"


def test_logout_still_requires_a_csrf_token(two_schools):
    school_a, _ = two_schools
    Membership.objects.create(school=school_a, user=_user(), role=Role.TEACHER)
    client = APIClient(enforce_csrf_checks=True)
    _login(client)

    assert client.post("/api/auth/logout/").status_code == 403
