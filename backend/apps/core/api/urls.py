from django.urls import path

from apps.core.api.views import HealthView

urlpatterns = [
    path("", HealthView.as_view(), name="health"),
]
