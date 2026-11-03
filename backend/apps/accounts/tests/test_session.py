import re

from django.core import mail
from django_otp.oath import totp as generate_totp
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.accounts.models import User
from apps.tenancy.models import Membership

Role = Membership.Role
PASSWORD = "correct-pass123"  # noqa: S105


def _user(username="user1", email=""):
    return User.objects.create_user(username=username, password=PASSWORD, email=email)


def _login(client, username="user1"):
    return client.post("/api/auth/login/", {"username": username, "password": PASSWORD})


def _confirmed_device(user):
    return TOTPDevice.objects.create(user=user, name="default", confirmed=True)


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


def test_totp_verify_activates_the_only_school(api_client, two_schools):
    school_a, _ = two_schools
    user = _user()
    device = _confirmed_device(user)
    membership = Membership.objects.create(school=school_a, user=user, role=Role.PRINCIPAL)

    assert _login(api_client).data == {"requires_2fa": True}
    response = api_client.post(
        "/api/auth/2fa/verify/", {"token": f"{generate_totp(device.bin_key):06d}"}
    )

    assert response.status_code == 200
    assert api_client.session["active_membership_id"] == membership.id


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


def test_email_otp_cannot_skip_2fa(api_client, two_schools):
    school_a, _ = two_schools
    user = _user(email="admin@example.com")
    _confirmed_device(user)
    Membership.objects.create(school=school_a, user=user, role=Role.SCHOOL_ADMIN)

    code = _email_code(api_client, user.email)
    response = api_client.post("/api/auth/email-otp/verify/", {"email": user.email, "code": code})

    assert response.data == {"requires_2fa": True}
    assert "_auth_user_id" not in api_client.session
    assert api_client.get("/api/auth/me/").status_code == 403


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
