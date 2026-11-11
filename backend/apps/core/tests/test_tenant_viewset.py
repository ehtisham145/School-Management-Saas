from rest_framework import serializers
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.accounts.models import User
from apps.core.views import TenantScopedViewSet
from apps.tenancy.models import Membership

Role = Membership.Role


class MembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Membership
        fields = ["id", "user", "role"]


class MembershipViewSet(TenantScopedViewSet):
    queryset = Membership.objects.all()
    serializer_class = MembershipSerializer
    policies = {
        "list": "members.view",
        "retrieve": "members.view",
        "create": "members.manage",
    }


def _member(school, username, role):
    user = User.objects.create_user(username=username, password="x" * 12)
    return Membership.objects.create(school=school, user=user, role=role)


def _call(method, actions, membership, pk=None, data=None):
    request = getattr(APIRequestFactory(), method)("/", data=data, format="json")
    force_authenticate(request, user=membership.user)
    request.school = membership.school
    request.role = membership.role
    kwargs = {"pk": pk} if pk else {}
    return MembershipViewSet.as_view(actions)(request, **kwargs)


def test_list_returns_only_own_school(two_schools):
    school_a, school_b = two_schools
    admin_a = _member(school_a, "admin_a", Role.SCHOOL_ADMIN)
    member_b = _member(school_b, "member_b", Role.TEACHER)

    response = _call("get", {"get": "list"}, admin_a)

    ids = [row["id"] for row in response.data["results"]]
    assert response.status_code == 200
    assert admin_a.id in ids
    assert member_b.id not in ids


def test_other_school_record_returns_404(two_schools):
    school_a, school_b = two_schools
    admin_a = _member(school_a, "admin_a", Role.SCHOOL_ADMIN)
    member_b = _member(school_b, "member_b", Role.TEACHER)

    response = _call("get", {"get": "retrieve"}, admin_a, pk=member_b.id)

    assert response.status_code == 404


def test_role_without_policy_gets_403(two_schools):
    school_a, _ = two_schools
    teacher = _member(school_a, "teacher_a", Role.TEACHER)

    response = _call("get", {"get": "list"}, teacher)

    assert response.status_code == 403


def test_action_missing_from_policies_is_denied(two_schools):
    school_a, _ = two_schools
    admin_a = _member(school_a, "admin_a", Role.SCHOOL_ADMIN)

    response = _call("delete", {"delete": "destroy"}, admin_a, pk=admin_a.id)

    assert response.status_code == 403
    assert Membership.objects.filter(id=admin_a.id).exists()


def test_create_uses_logged_in_school_not_request_data(two_schools):
    school_a, school_b = two_schools
    admin_a = _member(school_a, "admin_a", Role.SCHOOL_ADMIN)
    new_user = User.objects.create_user(username="new_user", password="x" * 12)

    response = _call(
        "post",
        {"post": "create"},
        admin_a,
        data={"user": new_user.id, "role": Role.TEACHER, "school": school_b.id},
    )

    assert response.status_code == 201
    assert Membership.objects.get(user=new_user).school == school_a
