from django_otp.oath import totp as generate_totp
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.tenancy.models import Membership, School
from apps.tenancy.selectors import is_locked_out_by_inactive_school

Role = Membership.Role
PASSWORD = "correct-pass123"  # noqa: S105


def _member(school, username="teacher", role=Role.TEACHER):
    user = User.objects.create_user(username, password=PASSWORD)
    membership = Membership.objects.create(school=school, user=user, role=role)
    return user, membership


def _deactivate(school):
    School.objects.filter(pk=school.pk).update(is_active=False)


def _login(client, user):
    return client.post("/api/auth/login/", {"username": user.username, "password": PASSWORD})


def test_login_reports_a_deactivated_school_and_offers_no_membership(two_schools):
    school_a, _ = two_schools
    user, _ = _member(school_a)
    _deactivate(school_a)

    response = _login(APIClient(), user)

    assert response.status_code == 200
    assert response.data["memberships"] == []
    assert response.data["school_inactive"] is True


def test_login_is_normal_for_an_active_school(two_schools):
    user, membership = _member(two_schools[0])

    response = _login(APIClient(), user)

    assert [m["membership_id"] for m in response.data["memberships"]] == [membership.id]
    assert response.data["school_inactive"] is False


def test_user_without_any_school_is_not_reported_as_inactive(db):
    user = User.objects.create_user("loner", password=PASSWORD)

    assert _login(APIClient(), user).data["school_inactive"] is False


def test_a_suspended_membership_is_not_reported_as_inactive_school(two_schools):
    school_a, _ = two_schools
    user, membership = _member(school_a)
    membership.status = Membership.Status.SUSPENDED
    membership.save()
    _deactivate(school_a)

    assert is_locked_out_by_inactive_school(user) is False


def test_user_with_another_active_school_keeps_using_it(two_schools):
    school_a, school_b = two_schools
    user, _ = _member(school_a)
    other = Membership.objects.create(school=school_b, user=user, role=Role.PARENT)
    _deactivate(school_a)
    client = APIClient()

    response = _login(client, user)

    assert [m["membership_id"] for m in response.data["memberships"]] == [other.id]
    assert response.data["school_inactive"] is False
    assert client.session["active_membership_id"] == other.id


def test_deactivating_ends_tenant_access_for_a_signed_in_user(two_schools):
    school_a, _ = two_schools
    user, _ = _member(school_a)
    client = APIClient()
    _login(client, user)
    assert client.get("/api/auth/me/").data["active_membership_id"] is not None
    assert client.get("/api/academics/years/").status_code == 200

    _deactivate(school_a)

    me = client.get("/api/auth/me/")
    assert me.data["active_membership_id"] is None
    assert me.data["memberships"] == []
    assert me.data["school_inactive"] is True
    assert client.get("/api/academics/years/").status_code == 403


def test_cannot_switch_into_a_deactivated_school(two_schools):
    school_a, school_b = two_schools
    user, membership = _member(school_a)
    Membership.objects.create(school=school_b, user=user, role=Role.PARENT)
    _deactivate(school_a)
    client = APIClient()
    _login(client, user)

    response = client.post("/api/auth/switch-school/", {"membership_id": membership.id})

    assert response.status_code == 404


def test_school_admin_of_a_deactivated_school_is_not_asked_to_set_up_2fa(two_schools):
    school_a, _ = two_schools
    user, _ = _member(school_a, role=Role.SCHOOL_ADMIN)
    _deactivate(school_a)

    assert _login(APIClient(), user).data["requires_2fa_setup"] is False


def test_2fa_login_also_reports_a_deactivated_school(two_schools):
    school_a, _ = two_schools
    user, _ = _member(school_a, role=Role.SCHOOL_ADMIN)
    device = TOTPDevice.objects.create(user=user, name="default", confirmed=True)
    _deactivate(school_a)
    client = APIClient()

    assert _login(client, user).data == {"requires_2fa": True}
    response = client.post(
        "/api/auth/2fa/verify/", {"token": f"{generate_totp(device.bin_key):06d}"}
    )

    assert response.data["memberships"] == []
    assert response.data["school_inactive"] is True


def test_reactivating_restores_access(two_schools):
    school_a, _ = two_schools
    user, membership = _member(school_a)
    _deactivate(school_a)
    School.objects.filter(pk=school_a.pk).update(is_active=True)

    response = _login(APIClient(), user)

    assert [m["membership_id"] for m in response.data["memberships"]] == [membership.id]


def test_platform_admin_with_a_deactivated_school_still_signs_in(two_schools):
    school_a, _ = two_schools
    user = User.objects.create_user("platform", password=PASSWORD, is_platform_admin=True)
    Membership.objects.create(school=school_a, user=user, role=Role.TEACHER)
    device = TOTPDevice.objects.create(user=user, name="default", confirmed=True)
    _deactivate(school_a)
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/auth/2fa/verify/", {"token": f"{generate_totp(device.bin_key):06d}"}
    )

    assert response.data["is_platform_admin"] is True
    assert client.get("/api/platform/schools/").status_code == 200


def test_me_includes_profile_details(two_schools):
    user = User.objects.create_user(
        "sara", password=PASSWORD, email="sara@example.com", first_name="Sara", last_name="Ali"
    )
    client = APIClient()
    _login(client, user)

    response = client.get("/api/auth/me/")

    assert response.data["username"] == "sara"
    assert response.data["email"] == "sara@example.com"
    assert response.data["full_name"] == "Sara Ali"
