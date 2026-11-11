from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.platform.api.billing_views import (
    AuditEventViewSet,
    FormChoicesView,
    PlanViewSet,
    QuotationViewSet,
    SubscriptionViewSet,
    UsageViewSet,
)
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
router.register("plans", PlanViewSet, basename="platform-plan")
router.register("subscriptions", SubscriptionViewSet, basename="platform-subscription")
router.register("quotations", QuotationViewSet, basename="platform-quotation")
router.register("usage", UsageViewSet, basename="platform-usage")
router.register("audit-log", AuditEventViewSet, basename="platform-audit-log")

urlpatterns = [
    path("demo-requests/", DemoRequestView.as_view(), name="demo-request"),
    path("contact-messages/", ContactMessageView.as_view(), name="contact-message"),
    path("dashboard/", DashboardView.as_view(), name="platform-dashboard"),
    path("choices/", FormChoicesView.as_view(), name="platform-choices"),
    *router.urls,
]
