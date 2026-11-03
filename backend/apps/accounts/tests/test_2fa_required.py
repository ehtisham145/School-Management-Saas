from django_otp.oath import totp as generate_totp
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.accounts.models import User
from apps.tenancy.models import Membership

Role = Membership.Role
PASSWORD = "correct-pass123"  # noqa: S105
YEARS_URL = "/api/academics/years/"


def _login(client, user):
    return client.post("/api/auth/login/", {"username": user.username, "password": PASSWORD})


def _set_up_2fa(client, user):
    client.post("/api/auth/2fa/setup/")
    device = TOTPDevice.objects.get(user=user, confirmed=False)
    token = f"{generate_totp(device.bin_key):06d}"
    return client.post("/api/auth/2fa/confirm/", {"token": token})


def test_school_admin_without_device_must_set_up_2fa(api_client, two_schools):
    school_a, _ = two_schools
    user = User.objects.create_user("head", password=PASSWORD)
    Membership.objects.create(school=school_a, user=user, role=Role.SCHOOL_ADMIN)

    response = _login(api_client, user)

    assert response.status_code == 200
    assert response.data["requires_2fa_setup"] is True
    assert api_client.get("/api/auth/me/").data["requires_2fa_setup"] is True

    blocked = api_client.get(YEARS_URL)
    assert blocked.status_code == 403
    assert blocked.data["error"]["code"] == "2fa_setup_required"


def test_school_admin_gets_access_after_2fa_setup(api_client, two_schools):
    school_a, _ = two_schools
    user = User.objects.create_user("head", password=PASSWORD)
    Membership.objects.create(school=school_a, user=user, role=Role.SCHOOL_ADMIN)
    _login(api_client, user)

    assert _set_up_2fa(api_client, user).status_code == 204

    assert api_client.get("/api/auth/me/").data["requires_2fa_setup"] is False
    assert api_client.get(YEARS_URL).status_code == 200


def test_teacher_does_not_need_2fa(api_client, two_schools):
    school_a, _ = two_schools
    user = User.objects.create_user("teacher", password=PASSWORD)
    Membership.objects.create(school=school_a, user=user, role=Role.TEACHER)

    response = _login(api_client, user)

    assert response.data["requires_2fa_setup"] is False
    assert api_client.get(YEARS_URL).status_code == 200


def test_suspended_school_admin_role_does_not_force_2fa(api_client, two_schools):
    school_a, school_b = two_schools
    user = User.objects.create_user("user1", password=PASSWORD)
    Membership.objects.create(
        school=school_a, user=user, role=Role.SCHOOL_ADMIN, status=Membership.Status.SUSPENDED
    )
    Membership.objects.create(school=school_b, user=user, role=Role.TEACHER)

    assert _login(api_client, user).data["requires_2fa_setup"] is False


def test_platform_admin_flag_is_returned(api_client, db):
    user = User.objects.create_user("platform", password=PASSWORD, is_platform_admin=True)

    response = _login(api_client, user)

    assert response.data["is_platform_admin"] is True
    assert response.data["requires_2fa_setup"] is True
    assert response.data["memberships"] == []


def test_regular_user_is_not_platform_admin(api_client, two_schools):
    school_a, _ = two_schools
    user = User.objects.create_user("teacher", password=PASSWORD)
    Membership.objects.create(school=school_a, user=user, role=Role.TEACHER)

    assert _login(api_client, user).data["is_platform_admin"] is False


def test_reset_removes_device_and_requires_new_setup(api_client, two_schools, mailoutbox):
    school_a, _ = two_schools
    user = User.objects.create_user("head", password=PASSWORD, email="head@example.com")
    TOTPDevice.objects.create(user=user, name="default", confirmed=True)
    Membership.objects.create(school=school_a, user=user, role=Role.SCHOOL_ADMIN)
    assert _login(api_client, user).data == {"requires_2fa": True}

    api_client.post("/api/auth/2fa/reset/request/")
    code = "".join(c for c in mailoutbox[-1].body.split("\n")[0] if c.isdigit())
    response = api_client.post("/api/auth/2fa/reset/confirm/", {"code": code})

    assert response.data["requires_2fa_setup"] is True
    assert api_client.get(YEARS_URL).data["error"]["code"] == "2fa_setup_required"


def test_setup_is_rejected_when_2fa_is_already_on(api_client, db):
    user = User.objects.create_user("head", password=PASSWORD)
    TOTPDevice.objects.create(user=user, name="default", confirmed=True)
    api_client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    response = api_client.post("/api/auth/2fa/setup/")

    assert response.status_code == 400
    assert response.data["error"]["code"] == "already_enabled"


def test_repeated_setup_keeps_the_same_pending_device(api_client, db):
    user = User.objects.create_user("head", password=PASSWORD)
    api_client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    first = api_client.post("/api/auth/2fa/setup/")
    second = api_client.post("/api/auth/2fa/setup/")

    assert first.data["secret"] == second.data["secret"]
    assert TOTPDevice.objects.filter(user=user).count() == 1


def test_setup_requires_login(api_client, db):
    assert api_client.post("/api/auth/2fa/setup/").status_code == 403
    assert api_client.post("/api/auth/2fa/confirm/", {"token": "123456"}).status_code == 403
