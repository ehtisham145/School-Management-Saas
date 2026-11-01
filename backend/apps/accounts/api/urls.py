from django.urls import path

from apps.accounts.api.views import (
    EmailOTPRequestView,
    EmailOTPVerifyView,
    LoginView,
    LogoutView,
    SwitchSchoolView,
    TOTPConfirmView,
    TOTPResetConfirmView,
    TOTPResetRequestView,
    TOTPSetupView,
    TOTPVerifyView,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("switch-school/", SwitchSchoolView.as_view(), name="switch-school"),
    path("2fa/setup/", TOTPSetupView.as_view(), name="2fa-setup"),
    path("2fa/confirm/", TOTPConfirmView.as_view(), name="2fa-confirm"),
    path("2fa/verify/", TOTPVerifyView.as_view(), name="2fa-verify"),
    path("2fa/reset/request/", TOTPResetRequestView.as_view(), name="2fa-reset-request"),
    path("2fa/reset/confirm/", TOTPResetConfirmView.as_view(), name="2fa-reset-confirm"),
    path("email-otp/request/", EmailOTPRequestView.as_view(), name="email-otp-request"),
    path("email-otp/verify/", EmailOTPVerifyView.as_view(), name="email-otp-verify"),
]
