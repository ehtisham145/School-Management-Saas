from django.urls import path

from apps.accounts.api.views import (
    EmailOTPRequestView,
    EmailOTPVerifyView,
    LoginView,
    LogoutView,
    MeView,
    SetPasswordView,
    SwitchSchoolView,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path("password/set/", SetPasswordView.as_view(), name="password-set"),
    path("switch-school/", SwitchSchoolView.as_view(), name="switch-school"),
    path("email-otp/request/", EmailOTPRequestView.as_view(), name="email-otp-request"),
    path("email-otp/verify/", EmailOTPVerifyView.as_view(), name="email-otp-verify"),
]
