from django.contrib.auth import authenticate, login, logout
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.api.serializers import (
    EmailOTPLoginVerifySerializer,
    EmailOTPRequestSerializer,
    LoginSerializer,
    SwitchSchoolSerializer,
)
from apps.accounts.models import User
from apps.accounts.services import request_email_otp, verify_email_otp
from apps.tenancy.selectors import (
    get_switchable_membership,
    is_locked_out_by_inactive_school,
    list_active_memberships,
)


def _serialize_memberships(memberships):
    return [
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


def _active_memberships(request):
    """Activates the membership automatically when the user has only one school."""
    memberships = list(list_active_memberships(request.user))
    if len(memberships) == 1:
        request.session["active_membership_id"] = memberships[0].id
    return memberships


def _session_payload(request):
    return {
        "is_platform_admin": request.user.is_platform_admin,
        "school_inactive": is_locked_out_by_inactive_school(request.user),
        "memberships": _serialize_memberships(_active_memberships(request)),
    }


def _login_response(request):
    return Response(_session_payload(request))


# The public sign-in endpoints skip session authentication: an old session in the
# browser must never stop someone from signing in.


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
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

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
        return _login_response(request)


class EmailOTPRequestView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "email_code"

    def post(self, request):
        serializer = EmailOTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.filter(email=serializer.validated_data["email"]).first()
        if user is not None:
            request_email_otp(user, "login")

        return Response(status=204)


class EmailOTPVerifyView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "email_code"

    def post(self, request):
        serializer = EmailOTPLoginVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.filter(email=serializer.validated_data["email"]).first()
        if user is None or not verify_email_otp(user, "login", serializer.validated_data["code"]):
            return Response(
                {"error": {"code": "invalid_credentials", "message": "Invalid email or code."}},
                status=401,
            )

        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return _login_response(request)


class MeView(APIView):
    def get(self, request):
        payload = _session_payload(request)
        active_id = request.session.get("active_membership_id")
        active_ids = {m["membership_id"] for m in payload["memberships"]}
        return Response(
            {
                "username": request.user.username,
                "email": request.user.email,
                "full_name": request.user.get_full_name(),
                "active_membership_id": active_id if active_id in active_ids else None,
                **payload,
            }
        )


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response(status=204)
