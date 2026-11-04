from apps.tenancy.models import Membership


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.school = None
        request.role = None

        membership_id = request.session.get("active_membership_id")
        if membership_id and request.user.is_authenticated:
            membership = (
                Membership.objects.filter(
                    id=membership_id,
                    user=request.user,
                    status=Membership.Status.ACTIVE,
                    school__is_active=True,
                )
                .select_related("school")
                .first()
            )
            if membership:
                request.school = membership.school
                request.role = membership.role

        return self.get_response(request)
