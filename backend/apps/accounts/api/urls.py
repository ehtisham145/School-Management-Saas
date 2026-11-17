from django.urls import path

from apps.accounts.api.views import (
    LoginView,
    LogoutView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    SwitchSchoolView,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path("switch-school/", SwitchSchoolView.as_view(), name="switch-school"),
    path(
        "password/reset/request/", PasswordResetRequestView.as_view(), name="password-reset-request"
    ),
    path(
        "password/reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"
    ),
]
