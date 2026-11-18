"""The individual teacher's workspace API. Thin: reads use selectors, writes use services."""

from dataclasses import asdict

from django.http import HttpResponse
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from apps.classroom import selectors, services
from apps.classroom.api.serializers import (
    AssessmentFilterSerializer,
    AssessmentSerializer,
    AttendanceQuerySerializer,
    AttendanceSaveSerializer,
    ClassroomSerializer,
    LessonGenerateSerializer,
    LessonPlanFilterSerializer,
    LessonPlanSerializer,
    MarkSheetRowSerializer,
    MarksSaveSerializer,
    ParentMessageSerializer,
    ReportCardQuerySerializer,
    RosterRowSerializer,
    SetupSerializer,
    StudentsAddSerializer,
    StudentSerializer,
    UpgradeRequestSerializer,
)
from apps.classroom.documents import render_report_card_pdf
from apps.classroom.entitlements import get_workspace_access
from apps.classroom.exceptions import ProRequired, ServiceUnavailable, WorkspaceReadOnly
from apps.core.policies import can
from apps.integrations.pdf.renderer import PdfUnavailable
from apps.tenancy.models import School

PPTX_TYPE = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


class LessonAiThrottle(UserRateThrottle):
    scope = "lesson_ai"


class IndividualTeacherWorkspace(BasePermission):
    """Only the teacher of a private workspace. Once a plan ends, the workspace is read-only."""

    def has_permission(self, request, view):
        school = getattr(request, "school", None)
        if (
            not request.user.is_authenticated
            or school is None
            or school.kind != School.Kind.INDIVIDUAL
            or not can(request.role, "classroom.use")
        ):
            return False

        request.workspace_access = get_workspace_access(school)
        allowed = getattr(view, "allowed_when_read_only", False)
        if (
            request.workspace_access.read_only
            and request.method not in SAFE_METHODS
            and not allowed
        ):
            raise WorkspaceReadOnly()
        return True


class WorkspaceMixin:
    permission_classes = [IndividualTeacherWorkspace]
    lookup_value_regex = r"\d+"
    pagination_class = None

    @property
    def school(self):
        return self.request.school

    @property
    def access(self):
        return self.request.workspace_access

    def get_serializer_context(self):
        return {"request": self.request, "view": self, "school": self.school}

    def valid(self, serializer_class, data, **kwargs):
        serializer = serializer_class(data=data, context=self.get_serializer_context(), **kwargs)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data


class WorkspaceView(WorkspaceMixin, APIView):
    def get(self, request):
        access = self.access
        profile = selectors.get_teacher_profile(self.school, request.user)
        pending = selectors.get_pending_upgrade(self.school)
        return Response(
            {
                "teacher_name": request.user.get_full_name(),
                "access": {
                    "tier": access.tier,
                    "read_only": access.read_only,
                    "ends_on": access.ends_on,
                    "days_left": access.days_left,
                },
                "limits": asdict(access.limits),
                "usage": selectors.get_workspace_usage(self.school),
                "profile": profile
                and {"subject": profile.subject, "grade_levels": profile.grade_levels},
                "pending_upgrade": pending and {"plan": pending.plan},
            }
        )


class SetupView(WorkspaceMixin, APIView):
    def post(self, request):
        data = self.valid(SetupSerializer, request.data)
        services.complete_setup(self.school, request.user, **data)
        return Response(data, status=201)


class UpgradeRequestView(WorkspaceMixin, APIView):
    # An ended trial must still be able to ask for a plan.
    allowed_when_read_only = True

    def post(self, request):
        data = self.valid(UpgradeRequestSerializer, request.data)
        upgrade = services.request_upgrade(self.school, **data)
        return Response(UpgradeRequestSerializer(upgrade).data, status=201)


class ClassroomViewSet(WorkspaceMixin, viewsets.GenericViewSet):
    serializer_class = ClassroomSerializer

    def get_queryset(self):
        return selectors.list_classrooms(self.school)

    def _classroom(self, pk):
        return selectors.get_classroom(self.school, pk)

    def list(self, request):
        return Response(self.get_serializer(self.get_queryset(), many=True).data)

    def create(self, request):
        data = self.valid(ClassroomSerializer, request.data)
        classroom = services.create_classroom(self.school, self.access, **data)
        return Response(self.get_serializer(classroom).data, status=201)

    def retrieve(self, request, pk=None):
        return Response(self.get_serializer(self._classroom(pk)).data)

    def partial_update(self, request, pk=None):
        classroom = self._classroom(pk)
        data = self.valid(ClassroomSerializer, request.data, partial=True)
        services.update_classroom(self.school, classroom, **data)
        return Response(self.get_serializer(classroom).data)

    def destroy(self, request, pk=None):
        services.delete_record(self._classroom(pk))
        return Response(status=204)

    @action(detail=True, methods=["get"])
    def students(self, request, pk=None):
        students = selectors.list_students(self.school, self._classroom(pk))
        return Response(StudentSerializer(students, many=True).data)

    @students.mapping.post
    def add_students(self, request, pk=None):
        data = self.valid(StudentsAddSerializer, request.data)
        students = services.add_students(
            self.school, self.access, self._classroom(pk), data["students"]
        )
        return Response(StudentSerializer(students, many=True).data, status=201)

    @action(detail=True, methods=["get"])
    def attendance(self, request, pk=None):
        query = self.valid(AttendanceQuerySerializer, request.query_params)
        day = query.get("date") or timezone.localdate()
        roster = selectors.get_attendance_roster(self.school, self._classroom(pk), day)
        return Response({"date": day, "students": RosterRowSerializer(roster, many=True).data})

    @attendance.mapping.put
    def save_attendance(self, request, pk=None):
        data = self.valid(AttendanceSaveSerializer, request.data)
        services.save_attendance(self.school, self._classroom(pk), data["date"], data["records"])
        return Response(status=204)

    @action(detail=True, methods=["get"])
    def gradebook(self, request, pk=None):
        book = selectors.get_gradebook(self.school, self._classroom(pk))
        return Response(
            {
                "assessments": [
                    {
                        "id": assessment.id,
                        "title": assessment.title,
                        "max_marks": str(assessment.max_marks),
                        "date": assessment.date,
                    }
                    for assessment in book["assessments"]
                ],
                "students": [
                    {
                        "id": student.id,
                        "full_name": student.full_name,
                        "marks": {
                            str(assessment_id): str(value)
                            for assessment_id, value in book["marks"].get(student.id, {}).items()
                        },
                    }
                    for student in book["students"]
                ],
            }
        )


class StudentViewSet(WorkspaceMixin, viewsets.GenericViewSet):
    serializer_class = StudentSerializer

    def _student(self, pk):
        return selectors.get_student(self.school, pk)

    def partial_update(self, request, pk=None):
        student = self._student(pk)
        data = self.valid(StudentSerializer, request.data, partial=True)
        return Response(self.get_serializer(services.update_student(student, **data)).data)

    def destroy(self, request, pk=None):
        services.delete_record(self._student(pk))
        return Response(status=204)

    @action(detail=True, methods=["get"], url_path="report-card")
    def report_card(self, request, pk=None):
        if not self.access.limits.pro_features:
            raise ProRequired()
        query = self.valid(ReportCardQuerySerializer, request.query_params)
        student = self._student(pk)
        try:
            pdf = render_report_card_pdf(
                student=student,
                teacher_name=request.user.get_full_name(),
                report=selectors.get_report_card(self.school, student),
                language=query["language"],
            )
        except PdfUnavailable as error:
            raise ServiceUnavailable() from error

        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="report-card-{student.id}.pdf"'
        return response


class LessonPlanPagination(PageNumberPagination):
    page_size = 20


class LessonPlanViewSet(WorkspaceMixin, viewsets.GenericViewSet):
    serializer_class = LessonPlanSerializer
    pagination_class = LessonPlanPagination

    def _plan(self, pk):
        return selectors.get_lesson_plan(self.school, pk)

    def list(self, request):
        filters = self.valid(LessonPlanFilterSerializer, request.query_params)
        page = self.paginate_queryset(selectors.list_lesson_plans(self.school, **filters))
        return self.get_paginated_response(self.get_serializer(page, many=True).data)

    def create(self, request):
        data = self.valid(LessonPlanSerializer, request.data)
        plan = services.create_lesson_plan(self.school, self.access, **data)
        return Response(self.get_serializer(plan).data, status=201)

    def retrieve(self, request, pk=None):
        return Response(self.get_serializer(self._plan(pk)).data)

    def partial_update(self, request, pk=None):
        plan = self._plan(pk)
        data = self.valid(LessonPlanSerializer, request.data, partial=True)
        return Response(
            self.get_serializer(services.update_lesson_plan(self.school, plan, **data)).data
        )

    def destroy(self, request, pk=None):
        services.delete_record(self._plan(pk))
        return Response(status=204)

    @action(detail=False, methods=["post"], throttle_classes=[LessonAiThrottle])
    def generate(self, request):
        data = self.valid(LessonGenerateSerializer, request.data)
        plan = services.generate_lesson_plan(self.school, self.access, **data)
        return Response(self.get_serializer(plan).data, status=201)

    @action(detail=True, methods=["get"])
    def presentation(self, request, pk=None):
        # Imported here so the rest of the API still runs if python-pptx is missing.
        from apps.integrations.slides.lesson_deck import build_lesson_deck

        plan = self._plan(pk)
        services.record_presentation_export(self.school, self.access, plan)
        deck = build_lesson_deck(
            {
                field: getattr(plan, field)
                for field in (
                    "title",
                    "subject",
                    "grade",
                    "objectives",
                    "materials",
                    "activities",
                    "assessment",
                    "homework",
                )
            },
            watermark=self.access.tier in ("trial", "expired"),
        )
        name = slugify(plan.title) or f"lesson-{plan.id}"
        response = HttpResponse(deck, content_type=PPTX_TYPE)
        response["Content-Disposition"] = f'attachment; filename="{name}.pptx"'
        return response


class AssessmentViewSet(WorkspaceMixin, viewsets.GenericViewSet):
    serializer_class = AssessmentSerializer

    def _assessment(self, pk):
        return selectors.get_assessment(self.school, pk)

    def list(self, request):
        filters = self.valid(AssessmentFilterSerializer, request.query_params)
        assessments = selectors.list_assessments(self.school, **filters)
        return Response(self.get_serializer(assessments, many=True).data)

    def create(self, request):
        data = self.valid(AssessmentSerializer, request.data)
        classroom = data.pop("classroom")
        assessment = services.create_assessment(self.school, classroom, **data)
        return Response(self.get_serializer(assessment).data, status=201)

    def partial_update(self, request, pk=None):
        assessment = self._assessment(pk)
        data = self.valid(AssessmentSerializer, request.data, partial=True)
        data.pop("classroom", None)
        services.update_assessment(self.school, assessment, **data)
        return Response(self.get_serializer(assessment).data)

    def destroy(self, request, pk=None):
        services.delete_record(self._assessment(pk))
        return Response(status=204)

    @action(detail=True, methods=["get"])
    def marks(self, request, pk=None):
        assessment = self._assessment(pk)
        sheet = selectors.get_marks_sheet(self.school, assessment)
        return Response(
            {
                "assessment": self.get_serializer(assessment).data,
                "students": MarkSheetRowSerializer(sheet, many=True).data,
            }
        )

    @marks.mapping.put
    def save_marks(self, request, pk=None):
        data = self.valid(MarksSaveSerializer, request.data)
        services.save_marks(self.school, self._assessment(pk), data["marks"])
        return Response(status=204)


class ParentMessagePagination(PageNumberPagination):
    page_size = 20


class ParentMessageViewSet(WorkspaceMixin, viewsets.GenericViewSet):
    serializer_class = ParentMessageSerializer
    pagination_class = ParentMessagePagination

    def list(self, request):
        page = self.paginate_queryset(selectors.list_parent_messages(self.school))
        return self.get_paginated_response(self.get_serializer(page, many=True).data)

    def create(self, request):
        if not self.access.limits.pro_features:
            raise ProRequired()
        data = self.valid(ParentMessageSerializer, request.data)
        classroom = data.pop("classroom")
        message = services.send_parent_message(self.school, self.access, classroom, **data)
        return Response(self.get_serializer(message).data, status=201)
