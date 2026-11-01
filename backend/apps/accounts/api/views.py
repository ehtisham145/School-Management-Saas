from django.contrib.auth import authenticate, login, logout
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.serializers import LoginSerializer, SwitchSchoolSerializer
from apps.tenancy.selectors import get_switchable_membership, list_active_memberships


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


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            return Response(
                {
                    "error": {
                        "code": "invalid_credentials",
                        "message": "Invalid username or password.",
                    }
                },
                status=401,
            )

        login(request, user)
        memberships = list_active_memberships(user)
        return Response(
            {
                "memberships": [
                    {
                        "membership_id": m.id,
                        "role": m.role,
                        "school": {
                            "id": m.school_id,
                            "code": m.school.code,
                            "name_en": m.school.name_en,
                            "name_ar": m.school.name_ar,
                        },
                    }
                    for m in memberships
                ]
            }
        )


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response(status=204)
