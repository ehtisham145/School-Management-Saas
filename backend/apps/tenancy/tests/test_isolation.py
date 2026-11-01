import pytest
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory

from apps.accounts.models import User
from apps.tenancy.middleware import TenantMiddleware
from apps.tenancy.models import Membership, School


def _add_session(request):
    SessionMiddleware(lambda r: None).process_request(request)
    request.session.save()


@pytest.fixture
def two_schools(db):
    return (
        School.objects.create(name_en="School A", name_ar="مدرسة أ", code="school-a"),
        School.objects.create(name_en="School B", name_ar="مدرسة ب", code="school-b"),
    )


@pytest.mark.django_db
def test_tenant_middleware_sets_school_from_active_membership(two_schools):
    school_a, _ = two_schools
    user = User.objects.create_user(username="teacher1", password="x" * 12)
    membership = Membership.objects.create(school=school_a, user=user, role=Membership.Role.TEACHER)

    request = RequestFactory().get("/")
    request.user = user
    _add_session(request)
    request.session["active_membership_id"] = membership.id

    TenantMiddleware(lambda r: r)(request)

    assert request.school == school_a
    assert request.role == Membership.Role.TEACHER


@pytest.mark.django_db
def test_tenant_middleware_ignores_membership_belonging_to_another_user(two_schools):
    school_a, school_b = two_schools
    user_a = User.objects.create_user(username="teacher1", password="x" * 12)
    user_b = User.objects.create_user(username="teacher2", password="x" * 12)
    membership_b = Membership.objects.create(
        school=school_b, user=user_b, role=Membership.Role.TEACHER
    )

    request = RequestFactory().get("/")
    request.user = user_a  # logged in as A
    _add_session(request)
    request.session["active_membership_id"] = membership_b.id  # session points at B's membership

    TenantMiddleware(lambda r: r)(request)

    assert request.school is None
