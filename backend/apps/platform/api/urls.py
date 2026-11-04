from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.platform.api.views import (
    ContactMessageView,
    DashboardView,
    DemoRequestAdminViewSet,
    DemoRequestView,
    SchoolViewSet,
)

router = SimpleRouter()
router.register("schools", SchoolViewSet, basename="platform-school")
router.register("manage/demo-requests", DemoRequestAdminViewSet, basename="platform-demo-request")

urlpatterns = [
    path("demo-requests/", DemoRequestView.as_view(), name="demo-request"),
    path("contact-messages/", ContactMessageView.as_view(), name="contact-message"),
    path("dashboard/", DashboardView.as_view(), name="platform-dashboard"),
    *router.urls,
]
