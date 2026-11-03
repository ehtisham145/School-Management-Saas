from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django_otp import login as otp_login
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.api.serializers import (
    EmailOTPConfirmSerializer,
    EmailOTPLoginVerifySerializer,
    EmailOTPRequestSerializer,
    LoginSerializer,
    SwitchSchoolSerializer,
    TOTPConfirmSerializer,
)
from apps.accounts.models import User
from apps.accounts.selectors import needs_2fa_setup
from apps.accounts.services import request_email_otp, verify_email_otp
from apps.tenancy.selectors import get_switchable_membership, list_active_memberships


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
        "requires_2fa_setup": needs_2fa_setup(request.user),
        "memberships": _serialize_memberships(_active_memberships(request)),
    }


def _login_response(request):
    return Response(_session_payload(request))


def _pending_2fa_user(request):
    user_id = request.session.get("pending_2fa_user_id")
    return User.objects.filter(id=user_id).first() if user_id else None


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

        if TOTPDevice.objects.filter(user=user, confirmed=True).exists():
            request.session["pending_2fa_user_id"] = user.id
            return Response({"requires_2fa": True})

        login(request, user)
        return _login_response(request)


class TOTPVerifyView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "twofa"

    def post(self, request):
        serializer = TOTPConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = _pending_2fa_user(request)
        if user is None:
            return Response(
                {"error": {"code": "no_pending_login", "message": "No 2FA login in progress."}},
                status=400,
            )

        device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
        if device is None or not device.verify_token(serializer.validated_data["token"]):
            return Response(
                {"error": {"code": "invalid_token", "message": "Invalid code."}}, status=401
            )

        del request.session["pending_2fa_user_id"]
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        otp_login(request, device)
        return _login_response(request)


class TOTPResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "twofa"

    def post(self, request):
        user = _pending_2fa_user(request)
        if user is None:
            return Response(
                {"error": {"code": "no_pending_login", "message": "No 2FA login in progress."}},
                status=400,
            )
        if not user.email:
            return Response(
                {
                    "error": {
                        "code": "no_email",
                        "message": "No email on file. Contact your school admin.",
                    }
                },
                status=400,
            )

        request_email_otp(user, "totp_reset")
        return Response(status=204)


class TOTPResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "twofa"

    def post(self, request):
        serializer = EmailOTPConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = _pending_2fa_user(request)
        if user is None:
            return Response(
                {"error": {"code": "no_pending_login", "message": "No 2FA login in progress."}},
                status=400,
            )

        if not verify_email_otp(user, "totp_reset", serializer.validated_data["code"]):
            return Response(
                {"error": {"code": "invalid_token", "message": "Invalid code."}}, status=401
            )

        TOTPDevice.objects.filter(user=user).delete()
        del request.session["pending_2fa_user_id"]
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return _login_response(request)


class EmailOTPRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "twofa"

    def post(self, request):
        serializer = EmailOTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.filter(email=serializer.validated_data["email"]).first()
        if user is not None:
            request_email_otp(user, "login")

        return Response(status=204)


class EmailOTPVerifyView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "twofa"

    def post(self, request):
        serializer = EmailOTPLoginVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.filter(email=serializer.validated_data["email"]).first()
        if user is None or not verify_email_otp(user, "login", serializer.validated_data["code"]):
            return Response(
                {"error": {"code": "invalid_credentials", "message": "Invalid email or code."}},
                status=401,
            )

        if TOTPDevice.objects.filter(user=user, confirmed=True).exists():
            request.session["pending_2fa_user_id"] = user.id
            return Response({"requires_2fa": True})

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
                "active_membership_id": active_id if active_id in active_ids else None,
                **payload,
            }
        )


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response(status=204)


class TOTPSetupView(APIView):
    def post(self, request):
        if TOTPDevice.objects.filter(user=request.user, confirmed=True).exists():
            return Response(
                {
                    "error": {
                        "code": "already_enabled",
                        "message": "2FA is already enabled. Use the reset flow to replace it.",
                    }
                },
                status=400,
            )
        # Locks the user row so a double submit can't create two pending devices.
        with transaction.atomic():
            User.objects.select_for_update().get(pk=request.user.pk)
            device = TOTPDevice.objects.filter(user=request.user, confirmed=False).first()
            if device is None:
                device = TOTPDevice.objects.create(
                    user=request.user, confirmed=False, name="default"
                )
        return Response({"otpauth_url": device.config_url, "secret": device.bin_key.hex()})


class TOTPConfirmView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "twofa"

    def post(self, request):
        serializer = TOTPConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        device = TOTPDevice.objects.filter(user=request.user, confirmed=False).first()
        if device is None:
            return Response(
                {"error": {"code": "not_found", "message": "No pending 2FA setup found."}},
                status=404,
            )

        if not device.verify_token(serializer.validated_data["token"]):
            return Response(
                {"error": {"code": "invalid_token", "message": "Invalid code."}}, status=400
            )

        device.confirmed = True
        device.save(update_fields=["confirmed"])
        otp_login(request, device)
        return Response(status=204)
