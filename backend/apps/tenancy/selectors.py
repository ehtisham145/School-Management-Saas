from apps.tenancy.models import Membership


def get_switchable_membership(user, membership_id):
    return (
        Membership.objects.filter(
            id=membership_id,
            user=user,
            status=Membership.Status.ACTIVE,
        )
        .select_related("school")
        .first()
    )


def list_active_memberships(user):
    return Membership.objects.filter(user=user, status=Membership.Status.ACTIVE).select_related(
        "school"
    )
