from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.serializers import SwitchSchoolSerializer
from apps.tenancy.selectors import get_switchable_membership


class SwitchSchoolView(APIView):
    def post(self, request):
        serializer = SwitchSchoolSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        membership = get_switchable_membership(
            request.user, serializer.validated_data["membership_id"]
        )
        if membership is None:
            return Response(
                {"error": {"code": "not_found", "message": "Membership not found."}},
                status=404,
            )

        request.session["active_membership_id"] = membership.id
        return Response(
            {
                "membership_id": membership.id,
                "role": membership.role,
                "school": {
                    "id": membership.school_id,
                    "code": membership.school.code,
                    "name_en": membership.school.name_en,
                    "name_ar": membership.school.name_ar,
                },
            }
        )
