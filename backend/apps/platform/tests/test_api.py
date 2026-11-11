import re

from django.core import mail
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.tenancy.models import Membership, School

Role = Membership.Role
SCHOOLS_URL = "/api/platform/schools/"
PASSWORD = "correct-pass123"  # noqa: S105
VALID_SCHOOL = {
    "name_en": "Al Noor School",
    "name_ar": "مدرسة النور",
    "code": "alnoor",
    "admin_email": "head@alnoor.example",
    "admin_name": "Sara Ahmed",
    "admin_phone": "0501234567",
    "school_type": "mixed",
    "education_stages": ["primary", "intermediate"],
    "email": "office@alnoor.example",
    "phone": "0112345678",
    "region": "riyadh",
    "city": "Riyadh",
    "address": "King Fahd Road",
    "cr_number": "1010123456",
    "moe_license_number": "778899",
    "estimated_students": 450,
}


def _platform_client(username="platform"):
    User.objects.create_user(username, password=PASSWORD, is_platform_admin=True)
    client = APIClient()
    response = client.post("/api/auth/login/", {"username": username, "password": PASSWORD})
    assert response.status_code == 200
    return client


def test_anonymous_user_is_denied(db):
    assert APIClient().get(SCHOOLS_URL).status_code == 403


def test_school_admin_is_denied(two_schools):
    school_a, _ = two_schools
    user = User.objects.create_user("head", password=PASSWORD)
    Membership.objects.create(school=school_a, user=user, role=Role.SCHOOL_ADMIN)
    client = APIClient()
    client.post("/api/auth/login/", {"username": "head", "password": PASSWORD})

    assert client.get(SCHOOLS_URL).status_code == 403
    assert client.post(SCHOOLS_URL, VALID_SCHOOL).status_code == 403
    assert not School.objects.filter(code="alnoor").exists()


def test_platform_admin_signs_in_with_a_password_alone(db):
    User.objects.create_user("platform", password=PASSWORD, is_platform_admin=True)
    client = APIClient()

    response = client.post("/api/auth/login/", {"username": "platform", "password": PASSWORD})

    assert response.status_code == 200
    assert response.data["is_platform_admin"] is True
    assert client.get(SCHOOLS_URL).status_code == 200


def test_list_returns_all_schools_with_member_counts(two_schools):
    school_a, _ = two_schools
    user = User.objects.create_user("teacher", password=PASSWORD)
    Membership.objects.create(school=school_a, user=user, role=Role.TEACHER)
    client = _platform_client()

    response = client.get(SCHOOLS_URL)

    counts = {row["code"]: row["member_count"] for row in response.data["results"]}
    assert response.status_code == 200
    assert counts == {"school-a": 1, "school-b": 0}
    assert "admin_email" not in response.data["results"][0]


def test_list_is_paginated(db):
    School.objects.bulk_create(
        School(name_en=f"S{i}", name_ar=f"S{i}", code=f"s{i}") for i in range(30)
    )
    client = _platform_client()

    response = client.get(f"{SCHOOLS_URL}?page=2")

    assert response.data["count"] == 30
    assert len(response.data["results"]) == 5


def test_create_makes_school_admin_and_sends_welcome_email(db, django_capture_on_commit_callbacks):
    client = _platform_client()

    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(SCHOOLS_URL, VALID_SCHOOL)

    assert response.status_code == 201
    assert response.data["code"] == "alnoor"
    assert response.data["member_count"] == 1
    assert "admin_email" not in response.data

    admin = User.objects.get(email=VALID_SCHOOL["admin_email"])
    assert not admin.has_usable_password()
    membership = Membership.objects.get(user=admin)
    assert membership.school.code == "alnoor"
    assert membership.role == Role.SCHOOL_ADMIN

    assert [message.to for message in mail.outbox] == [[VALID_SCHOOL["admin_email"]]]
    assert "Al Noor School" in mail.outbox[0].body


def test_new_admin_signs_in_with_an_email_code(db, django_capture_on_commit_callbacks):
    platform = _platform_client()
    with django_capture_on_commit_callbacks(execute=True):
        platform.post(SCHOOLS_URL, VALID_SCHOOL)
    email = VALID_SCHOOL["admin_email"]
    client = APIClient()

    client.post("/api/auth/email-otp/request/", {"email": email})
    code = re.search(r"\b\d{6}\b", mail.outbox[-1].body).group()
    response = client.post("/api/auth/email-otp/verify/", {"email": email, "code": code})

    assert response.status_code == 200
    assert len(response.data["memberships"]) == 1
    assert client.get("/api/academics/years/").status_code == 200


def test_new_admin_cannot_see_other_schools(two_schools, django_capture_on_commit_callbacks):
    platform = _platform_client()
    with django_capture_on_commit_callbacks(execute=True):
        platform.post(SCHOOLS_URL, VALID_SCHOOL)
    admin = User.objects.get(email=VALID_SCHOOL["admin_email"])
    client = APIClient()
    client.force_login(admin, backend="django.contrib.auth.backends.ModelBackend")

    assert client.get(SCHOOLS_URL).status_code == 403


def test_create_refuses_an_admin_email_that_already_has_an_account(two_schools):
    school_a, _ = two_schools
    existing = User.objects.create_user("old", password=PASSWORD, email="HEAD@alnoor.example")
    Membership.objects.create(school=school_a, user=existing, role=Role.TEACHER)
    client = _platform_client()

    response = client.post(SCHOOLS_URL, VALID_SCHOOL)

    assert response.status_code == 400
    assert "admin_email" in response.data["error"]["fields"]
    assert Membership.objects.filter(user=existing).count() == 1
    assert not School.objects.filter(code="alnoor").exists()


def test_duplicate_code_returns_400_even_with_different_case(two_schools):
    client = _platform_client()

    response = client.post(SCHOOLS_URL, {**VALID_SCHOOL, "code": "SCHOOL-A"})

    assert response.status_code == 400
    assert "code" in response.data["error"]["fields"]
    assert not User.objects.filter(email=VALID_SCHOOL["admin_email"]).exists()


def test_code_is_saved_in_lowercase(db):
    client = _platform_client()

    response = client.post(SCHOOLS_URL, {**VALID_SCHOOL, "code": "AlNoor"})

    assert response.status_code == 201
    assert School.objects.filter(code="alnoor").exists()


def test_invalid_fields_return_400(db):
    client = _platform_client()

    response = client.post(
        SCHOOLS_URL,
        {
            "name_en": "",
            "name_ar": "English only",
            "code": "has spaces",
            "admin_email": "not-an-email",
        },
    )

    assert response.status_code == 400
    assert {"name_en", "name_ar", "code", "admin_email"} <= set(response.data["error"]["fields"])


def test_username_clash_rolls_back_the_school(db):
    User.objects.create_user("alnoor.admin", password=PASSWORD)
    client = _platform_client()

    response = client.post(SCHOOLS_URL, VALID_SCHOOL)

    assert response.status_code == 400
    assert not School.objects.filter(code="alnoor").exists()


def test_update_and_delete_are_not_available(two_schools):
    school_a, _ = two_schools
    client = _platform_client()

    assert client.patch(f"{SCHOOLS_URL}{school_a.id}/", {"name_en": "x"}).status_code == 404
    assert client.delete(f"{SCHOOLS_URL}{school_a.id}/").status_code == 404
    assert School.objects.filter(id=school_a.id).exists()
