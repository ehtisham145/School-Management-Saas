from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.api.serializers import (
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    SetPasswordSerializer,
    SwitchSchoolSerializer,
    TeacherSignupRequestSerializer,
    TeacherSignupVerifySerializer,
)
from apps.accounts.models import User
from apps.accounts.services import request_email_otp, set_password, verify_email_otp
from apps.audit.services import client_ip
from apps.core.permissions import TrustedOrigin
from apps.platform.selectors import get_active_trial
from apps.platform.services import complete_teacher_signup, request_teacher_signup_code
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
                "kind": m.school.kind,
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


def _trial_payload(user):
    trial = get_active_trial(user)
    if trial is None:
        return None
    days_left = max((trial.ends_on - timezone.localdate()).days, 0)
    return {"ends_on": trial.ends_on.isoformat(), "days_left": days_left}


def _session_payload(request):
    return {
        "username": request.user.username,
        "is_platform_admin": request.user.is_platform_admin,
        "school_inactive": is_locked_out_by_inactive_school(request.user),
        "memberships": _serialize_memberships(_active_memberships(request)),
        "trial": _trial_payload(request.user),
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
    permission_classes = [TrustedOrigin]
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


class TeacherSignupRequestView(APIView):
    """Step one of a free trial: checks the details and emails a code. Answers the same for
    an email that already has an account, so the response can't be used to find accounts."""

    authentication_classes = []
    permission_classes = [TrustedOrigin]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "teacher_signup"

    def post(self, request):
        serializer = TeacherSignupRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not serializer.validated_data.get("website"):
            request_teacher_signup_code(serializer.validated_data["email"])
        return Response(status=204)


class TeacherSignupVerifyView(APIView):
    """Step two: a correct code creates the account and starts the trial."""

    authentication_classes = []
    permission_classes = [TrustedOrigin]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "email_code"

    def post(self, request):
        serializer = TeacherSignupVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = complete_teacher_signup(
            full_name=data["full_name"],
            email=data["email"],
            password=data["password"],
            code=data["code"],
            ip_address=client_ip(request),
        )
        if user is None:
            return Response(
                {"error": {"code": "invalid_code", "message": "Invalid or expired code."}},
                status=401,
            )

        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return Response(_session_payload(request), status=201)


class PasswordResetRequestView(APIView):
    """Anyone can ask for a code: a brand-new staff account with no password yet, or someone who
    forgot theirs. Silent for an unknown email, so the response can't be used to find accounts."""

    authentication_classes = []
    permission_classes = [TrustedOrigin]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "email_code"

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.filter(email__iexact=serializer.validated_data["email"]).first()
        if user is not None:
            request_email_otp(user, "password_reset")

        return Response(status=204)


class PasswordResetConfirmView(APIView):
    """The code proves the mailbox; the new password replaces whatever the account had (or had
    none of) before. Signs the user in straight away, same as a normal login."""

    authentication_classes = []
    permission_classes = [TrustedOrigin]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "email_code"

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = User.objects.filter(email__iexact=data["email"]).first()
        if user is None or not verify_email_otp(user, "password_reset", data["code"]):
            return Response(
                {"error": {"code": "invalid_credentials", "message": "Invalid email or code."}},
                status=401,
            )

        password_serializer = SetPasswordSerializer(
            data={"password": data["password"]}, context={"user": user}
        )
        password_serializer.is_valid(raise_exception=True)

        set_password(user, password_serializer.validated_data["password"])
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
