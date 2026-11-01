from django.urls import path

from apps.accounts.api.views import SwitchSchoolView

urlpatterns = [
    path("switch-school/", SwitchSchoolView.as_view(), name="switch-school"),
]
