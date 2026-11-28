from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.browser_agent.api.views import BrowserTaskViewSet, ConsentView, StatusView

router = SimpleRouter()
router.register("tasks", BrowserTaskViewSet, basename="browser-agent-task")

urlpatterns = [
    path("status/", StatusView.as_view(), name="browser-agent-status"),
    path("consent/", ConsentView.as_view(), name="browser-agent-consent"),
    *router.urls,
]
