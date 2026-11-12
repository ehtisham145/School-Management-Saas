from apps.tenancy.models import Membership

STAFF_ROLES = (
    Membership.Role.SCHOOL_ADMIN,
    Membership.Role.PRINCIPAL,
    Membership.Role.TEACHER,
)


def needs_password_setup(user):
    """True for staff created without a password, such as a new School Admin.

    They sign in once with an email code and must then choose a password.
    Parents and students keep signing in without one.
    """
    if user.has_usable_password():
        return False
    return (
        user.is_platform_admin
        or Membership.objects.filter(user=user, role__in=STAFF_ROLES).exists()
    )
