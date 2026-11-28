from apps.tenancy.models import Membership, School


def _usable_memberships(user):
    """A deactivated school takes its memberships out of use, without changing them."""
    return Membership.objects.filter(
        user=user, status=Membership.Status.ACTIVE, school__is_active=True
    )


def get_switchable_membership(user, membership_id):
    return _usable_memberships(user).filter(id=membership_id).select_related("school").first()


def list_active_memberships(user):
    return _usable_memberships(user).select_related("school")


def is_individual_workspace(school):
    return school is not None and school.kind == School.Kind.INDIVIDUAL


def get_individual_teacher_membership(school_id):
    """The active teacher of an active individual workspace, or None."""
    return (
        _usable_memberships_of_school(school_id)
        .filter(role=Membership.Role.TEACHER, school__kind=School.Kind.INDIVIDUAL)
        .select_related("school", "user")
        .first()
    )


def _usable_memberships_of_school(school_id):
    return Membership.objects.filter(
        school_id=school_id, status=Membership.Status.ACTIVE, school__is_active=True
    )


def is_locked_out_by_inactive_school(user):
    """True when the user belongs to schools, but all of them are deactivated."""
    memberships = Membership.objects.filter(user=user, status=Membership.Status.ACTIVE)
    return memberships.exists() and not memberships.filter(school__is_active=True).exists()
