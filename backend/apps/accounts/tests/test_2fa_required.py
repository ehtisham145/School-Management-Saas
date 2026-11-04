from datetime import timedelta

from django.utils import timezone
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


def _wrong_code_for(device):
    good = f"{generate_totp(device.bin_key):06d}"
    return "000000" if good != "000000" else "000001"


def _wait_is_over(device):
    device.refresh_from_db()
    device.throttling_failure_timestamp = timezone.now() - timedelta(hours=1)
    device.save()


def test_right_code_during_the_wait_at_login_says_wait_and_does_not_sign_in(api_client, db):
    user = User.objects.create_user("owner", password=PASSWORD)
    device = TOTPDevice.objects.create(user=user, confirmed=True, name="default")
    _login(api_client, user)

    wrong = api_client.post("/api/auth/2fa/verify/", {"token": _wrong_code_for(device)})
    assert wrong.status_code == 401
    assert wrong.data["error"]["code"] == "invalid_token"

    good = f"{generate_totp(device.bin_key):06d}"
    response = api_client.post("/api/auth/2fa/verify/", {"token": good})

    assert response.status_code == 429
    assert response.data["error"]["code"] == "totp_wait"
    assert response.data["error"]["retry_after"] == 1
    assert response["Retry-After"] == "1"
    assert "_auth_user_id" not in api_client.session


def test_the_right_code_signs_in_once_the_wait_is_over(api_client, db):
    user = User.objects.create_user("owner", password=PASSWORD)
    device = TOTPDevice.objects.create(user=user, confirmed=True, name="default")
    _login(api_client, user)
    api_client.post("/api/auth/2fa/verify/", {"token": _wrong_code_for(device)})

    _wait_is_over(device)
    response = api_client.post(
        "/api/auth/2fa/verify/", {"token": f"{generate_totp(device.bin_key):06d}"}
    )

    assert response.status_code == 200
    assert api_client.session["_auth_user_id"] == str(user.pk)


def test_the_wait_grows_with_each_wrong_code(api_client, db):
    user = User.objects.create_user("owner", password=PASSWORD)
    device = TOTPDevice.objects.create(user=user, confirmed=True, name="default")
    _login(api_client, user)

    for _ in range(3):
        _wait_is_over(device)
        api_client.post("/api/auth/2fa/verify/", {"token": _wrong_code_for(device)})

    response = api_client.post("/api/auth/2fa/verify/", {"token": _wrong_code_for(device)})

    assert response.status_code == 429
    assert 1 < response.data["error"]["retry_after"] <= 4


def test_codes_sent_during_the_wait_do_not_make_it_longer(api_client, db):
    user = User.objects.create_user("owner", password=PASSWORD)
    device = TOTPDevice.objects.create(user=user, confirmed=True, name="default")
    _login(api_client, user)
    api_client.post("/api/auth/2fa/verify/", {"token": _wrong_code_for(device)})

    api_client.post("/api/auth/2fa/verify/", {"token": _wrong_code_for(device)})

    device.refresh_from_db()
    assert device.throttling_failure_count == 1


def test_right_code_during_the_wait_in_setup_says_wait_and_does_not_turn_on_2fa(api_client, db):
    user = User.objects.create_user("owner", password=PASSWORD)
    _login(api_client, user)
    api_client.post("/api/auth/2fa/setup/")
    device = TOTPDevice.objects.get(user=user, confirmed=False)

    wrong = api_client.post("/api/auth/2fa/confirm/", {"token": _wrong_code_for(device)})
    assert wrong.data["error"]["code"] == "invalid_token"

    good = f"{generate_totp(device.bin_key):06d}"
    response = api_client.post("/api/auth/2fa/confirm/", {"token": good})

    assert response.status_code == 429
    assert response.data["error"]["code"] == "totp_wait"
    device.refresh_from_db()
    assert device.confirmed is False


def test_setup_works_once_the_wait_is_over(api_client, db):
    user = User.objects.create_user("owner", password=PASSWORD)
    _login(api_client, user)
    api_client.post("/api/auth/2fa/setup/")
    device = TOTPDevice.objects.get(user=user, confirmed=False)
    api_client.post("/api/auth/2fa/confirm/", {"token": _wrong_code_for(device)})

    _wait_is_over(device)
    response = api_client.post(
        "/api/auth/2fa/confirm/", {"token": f"{generate_totp(device.bin_key):06d}"}
    )

    assert response.status_code == 204
    device.refresh_from_db()
    assert device.confirmed is True


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
