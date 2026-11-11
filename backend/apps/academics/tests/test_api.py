from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.academics.models import AcademicYear
from apps.accounts.models import User
from apps.tenancy.models import Membership

Role = Membership.Role
YEARS_URL = "/api/academics/years/"
VALID_YEAR = {"name": "2026-2027", "start_date": "2026-08-01", "end_date": "2027-06-30"}


def _client_for(school, username, role):
    user = User.objects.create_user(username=username, password="x" * 12)
    membership = Membership.objects.create(school=school, user=user, role=role)
    client = APIClient()
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")
    session = client.session
    session["active_membership_id"] = membership.id
    session.save()
    return client


def _year(school, name="2026-2027", is_current=False):
    return AcademicYear.objects.create(
        school=school,
        name=name,
        start_date=date(2026, 8, 1),
        end_date=date(2027, 6, 30),
        is_current=is_current,
    )


def test_anonymous_user_cannot_list_years(api_client, two_schools):
    response = api_client.get(YEARS_URL)

    assert response.status_code == 403


def test_list_returns_only_own_school_years(two_schools):
    school_a, school_b = two_schools
    own = _year(school_a)
    other = _year(school_b)
    client = _client_for(school_a, "teacher_a", Role.TEACHER)

    response = client.get(YEARS_URL)

    ids = [row["id"] for row in response.data["results"]]
    assert response.status_code == 200
    assert own.id in ids
    assert other.id not in ids


def test_other_school_year_returns_404(two_schools):
    school_a, school_b = two_schools
    other = _year(school_b)
    client = _client_for(school_a, "admin_a", Role.SCHOOL_ADMIN)

    assert client.get(f"{YEARS_URL}{other.id}/").status_code == 404
    assert client.patch(f"{YEARS_URL}{other.id}/", {"name": "x"}).status_code == 404
    assert client.post(f"{YEARS_URL}{other.id}/set-current/").status_code == 404


def test_admin_creates_year_in_own_school(two_schools):
    school_a, school_b = two_schools
    client = _client_for(school_a, "admin_a", Role.SCHOOL_ADMIN)

    response = client.post(YEARS_URL, {**VALID_YEAR, "school": school_b.id})

    assert response.status_code == 201
    assert AcademicYear.objects.get(id=response.data["id"]).school == school_a


@pytest.mark.parametrize("role", [Role.PRINCIPAL, Role.TEACHER, Role.STUDENT, Role.PARENT])
def test_only_admin_can_create_year(two_schools, role):
    school_a, _ = two_schools
    client = _client_for(school_a, "member_a", role)

    response = client.post(YEARS_URL, VALID_YEAR)

    assert response.status_code == 403


def test_duplicate_name_returns_400(two_schools):
    school_a, _ = two_schools
    _year(school_a)
    client = _client_for(school_a, "admin_a", Role.SCHOOL_ADMIN)

    response = client.post(YEARS_URL, VALID_YEAR)

    assert response.status_code == 400


def test_end_before_start_returns_400(two_schools):
    school_a, _ = two_schools
    client = _client_for(school_a, "admin_a", Role.SCHOOL_ADMIN)

    response = client.post(YEARS_URL, {**VALID_YEAR, "end_date": "2026-01-01"})

    assert response.status_code == 400


def test_is_current_cannot_be_set_directly(two_schools):
    school_a, _ = two_schools
    client = _client_for(school_a, "admin_a", Role.SCHOOL_ADMIN)

    response = client.post(YEARS_URL, {**VALID_YEAR, "is_current": True})

    assert response.status_code == 201
    assert response.data["is_current"] is False


def test_set_current_switches_year(two_schools):
    school_a, _ = two_schools
    old = _year(school_a, name="2025-2026", is_current=True)
    new = _year(school_a, name="2026-2027")
    client = _client_for(school_a, "admin_a", Role.SCHOOL_ADMIN)

    response = client.post(f"{YEARS_URL}{new.id}/set-current/")

    old.refresh_from_db()
    assert response.status_code == 200
    assert response.data["is_current"] is True
    assert not old.is_current


def test_teacher_cannot_set_current_year(two_schools):
    school_a, _ = two_schools
    year = _year(school_a)
    client = _client_for(school_a, "teacher_a", Role.TEACHER)

    response = client.post(f"{YEARS_URL}{year.id}/set-current/")

    assert response.status_code == 403


def test_delete_is_not_allowed(two_schools):
    school_a, _ = two_schools
    year = _year(school_a)
    client = _client_for(school_a, "admin_a", Role.SCHOOL_ADMIN)

    response = client.delete(f"{YEARS_URL}{year.id}/")

    assert response.status_code == 403
    assert AcademicYear.objects.filter(id=year.id).exists()
