from django.urls import path

from apps.accounts.api.views import LoginView, LogoutView, SwitchSchoolView

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("switch-school/", SwitchSchoolView.as_view(), name="switch-school"),
]
