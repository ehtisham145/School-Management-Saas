import pytest

from apps.accounts.models import User
from apps.tenancy.models import Membership


@pytest.mark.django_db
def test_switch_school_succeeds_for_own_active_membership(api_client, two_schools):
    school_a, _ = two_schools
    user = User.objects.create_user(username="parent1", password="x" * 12)
    membership = Membership.objects.create(school=school_a, user=user, role=Membership.Role.PARENT)

    api_client.force_authenticate(user=user)
    response = api_client.post("/api/auth/switch-school/", {"membership_id": membership.id})

    assert response.status_code == 200
    assert response.data["school"]["id"] == school_a.id
    assert api_client.session["active_membership_id"] == membership.id


@pytest.mark.django_db
def test_switch_school_rejects_another_users_membership(api_client, two_schools):
    school_a, school_b = two_schools
    user_a = User.objects.create_user(username="parent1", password="x" * 12)
    user_b = User.objects.create_user(username="parent2", password="x" * 12)
    membership_b = Membership.objects.create(
        school=school_b, user=user_b, role=Membership.Role.PARENT
    )

    api_client.force_authenticate(user=user_a)
    response = api_client.post("/api/auth/switch-school/", {"membership_id": membership_b.id})

    assert response.status_code == 404
    assert "active_membership_id" not in api_client.session


@pytest.mark.django_db
def test_switch_school_rejects_suspended_membership(api_client, two_schools):
    school_a, _ = two_schools
    user = User.objects.create_user(username="parent1", password="x" * 12)
    membership = Membership.objects.create(
        school=school_a,
        user=user,
        role=Membership.Role.PARENT,
        status=Membership.Status.SUSPENDED,
    )

    api_client.force_authenticate(user=user)
    response = api_client.post("/api/auth/switch-school/", {"membership_id": membership.id})

    assert response.status_code == 404


def test_login_succeeds_with_correct_credentials(api_client, two_schools):
    school_a, _ = two_schools
    user = User.objects.create_user(username="teacher1", password="correct-pass123")
    Membership.objects.create(school=school_a, user=user, role=Membership.Role.TEACHER)

    response = api_client.post(
        "/api/auth/login/", {"username": "teacher1", "password": "correct-pass123"}
    )

    assert response.status_code == 200
    assert response.data["memberships"][0]["school"]["id"] == school_a.id


@pytest.mark.django_db
def test_login_fails_with_wrong_password(api_client):
    User.objects.create_user(username="teacher1", password="correct-pass123")

    response = api_client.post(
        "/api/auth/login/", {"username": "teacher1", "password": "wrong-pass"}
    )

    assert response.status_code == 401
    assert response.data["error"]["code"] == "invalid_credentials"


@pytest.mark.django_db
def test_login_fails_with_unknown_username(api_client):
    response = api_client.post("/api/auth/login/", {"username": "ghost", "password": "whatever123"})

    assert response.status_code == 401
    assert response.data["error"]["code"] == "invalid_credentials"


def test_logout_requires_login_again(api_client, two_schools):
    school_a, _ = two_schools
    user = User.objects.create_user(username="teacher1", password="correct-pass123")
    membership = Membership.objects.create(school=school_a, user=user, role=Membership.Role.TEACHER)

    api_client.post("/api/auth/login/", {"username": "teacher1", "password": "correct-pass123"})
    api_client.post("/api/auth/logout/")

    response = api_client.post("/api/auth/switch-school/", {"membership_id": membership.id})

    assert response.status_code in (401, 403)
