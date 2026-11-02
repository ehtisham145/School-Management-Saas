from apps.tenancy.models import Membership

Role = Membership.Role

# Action -> roles allowed to perform it. An action missing here is denied.
POLICIES = {
    "school.view": frozenset(Role.values),
    "school.manage": frozenset({Role.SCHOOL_ADMIN}),
    "members.view": frozenset({Role.SCHOOL_ADMIN, Role.PRINCIPAL}),
    "members.manage": frozenset({Role.SCHOOL_ADMIN}),
}


def can(role, action):
    return role in POLICIES.get(action, frozenset())


# Here in this file we are defining the permission that what are
# are tasks are performed by this user
