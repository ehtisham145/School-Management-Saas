from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.classroom.api.views import (
    AssessmentViewSet,
    ClassroomViewSet,
    LessonPlanViewSet,
    ParentMessageViewSet,
    SetupView,
    StudentViewSet,
    UpgradeRequestView,
    WorkspaceView,
)

router = SimpleRouter()
router.register("classes", ClassroomViewSet, basename="classroom-class")
router.register("students", StudentViewSet, basename="classroom-student")
router.register("lesson-plans", LessonPlanViewSet, basename="classroom-lesson-plan")
router.register("assessments", AssessmentViewSet, basename="classroom-assessment")
router.register("messages", ParentMessageViewSet, basename="classroom-message")

urlpatterns = [
    path("workspace/", WorkspaceView.as_view(), name="classroom-workspace"),
    path("setup/", SetupView.as_view(), name="classroom-setup"),
    path("upgrade-request/", UpgradeRequestView.as_view(), name="classroom-upgrade-request"),
    *router.urls,
]
