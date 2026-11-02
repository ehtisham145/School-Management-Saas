import pytest

from apps.core.policies import POLICIES, can
from apps.tenancy.models import Membership

Role = Membership.Role


# Parameterize Property is used when we want to test a function by passing
# it two different in order to see its result
@pytest.mark.parametrize("role", Role.values)
def test_every_role_can_view_school(role):
    assert can(role, "school.view")


def test_only_school_admin_can_manage_members():
    allowed = {role for role in Role.values if can(role, "members.manage")}
    assert allowed == {Role.SCHOOL_ADMIN}


@pytest.mark.parametrize("role", [Role.TEACHER, Role.STUDENT, Role.PARENT])
def test_non_management_roles_cannot_view_members(role):
    assert not can(role, "members.view")


def test_no_role_is_denied():
    # A logged-in user without an active school has request.role = None.
    for action in POLICIES:
        assert not can(None, action)


def test_unknown_action_is_denied():
    assert not can(Role.SCHOOL_ADMIN, "does.not.exist")


# When we to test multiple cases on a single function in pytest then
# we use @pytest keyword because it test mutiple test cases on a single function
