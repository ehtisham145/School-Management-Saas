from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.classroom.api.views import (
    AssessmentViewSet,
    ClassroomViewSet,
    ExamDraftViewSet,
    ExamOptionsView,
    ExamPatternViewSet,
    ExamSourceView,
    ExamViewSet,
    LessonPlanViewSet,
    PaperDesignView,
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
router.register("exam-patterns", ExamPatternViewSet, basename="classroom-exam-pattern")
router.register("exam-drafts", ExamDraftViewSet, basename="classroom-exam-draft")
router.register("exams", ExamViewSet, basename="classroom-exam")

urlpatterns = [
    path("workspace/", WorkspaceView.as_view(), name="classroom-workspace"),
    path("setup/", SetupView.as_view(), name="classroom-setup"),
    path("upgrade-request/", UpgradeRequestView.as_view(), name="classroom-upgrade-request"),
    path("exam-options/", ExamOptionsView.as_view(), name="classroom-exam-options"),
    path("exam-sources/", ExamSourceView.as_view(), name="classroom-exam-sources"),
    path("paper-design/", PaperDesignView.as_view(), name="classroom-paper-design"),
    *router.urls,
]
