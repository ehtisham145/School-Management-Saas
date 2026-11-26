"""The individual teacher's workspace API. Thin: reads use selectors, writes use services."""

from dataclasses import asdict

from django.http import HttpResponse
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from apps.classroom import exams, selectors, services
from apps.classroom.api.serializers import (
    AssessmentFilterSerializer,
    AssessmentSerializer,
    AttendanceQuerySerializer,
    AttendanceSaveSerializer,
    ClassroomSerializer,
    ExamDetailSerializer,
    ExamDraftCreateSerializer,
    ExamDraftSerializer,
    ExamFileQuerySerializer,
    ExamFilterSerializer,
    ExamPatternSerializer,
    ExamQuestionsSerializer,
    ExamRegenerateSerializer,
    ExamSectionsSerializer,
    ExamSerializer,
    ExamSourceUploadSerializer,
    ExamThemeSerializer,
    LessonGenerateSerializer,
    LessonPlanFilterSerializer,
    LessonPlanSerializer,
    MarkSheetRowSerializer,
    MarksSaveSerializer,
    ParentMessageSerializer,
    ProfileQuerySerializer,
    ReportCardQuerySerializer,
    RosterRowSerializer,
    SetupSerializer,
    SourceDocumentSerializer,
    StudentProfileSerializer,
    StudentsAddSerializer,
    StudentSerializer,
    UpgradeRequestSerializer,
)
from apps.classroom.documents import render_report_card_pdf
from apps.classroom.entitlements import get_workspace_access
from apps.classroom.exam_documents import build_paper, render_paper_pdf
from apps.classroom.exceptions import (
    ProRequired,
    SchoolPlanOnly,
    ServiceUnavailable,
    WorkspaceReadOnly,
)
from apps.core.policies import can
from apps.integrations.pdf.renderer import PdfUnavailable
from apps.tenancy.models import School

PPTX_TYPE = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PLAN_SECTIONS = (
    "title",
    "subject",
    "grade",
    "objectives",
    "materials",
    "activities",
    "assessment",
    "homework",
)


class LessonAiThrottle(UserRateThrottle):
    scope = "lesson_ai"


class ExamAiThrottle(UserRateThrottle):
    scope = "exam_ai"


class ExamUploadThrottle(UserRateThrottle):
    scope = "exam_upload"


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


class ClassesEnabled(BasePermission):
    """Classes and what is built on them belong to the school plan (ADR-0027). Runs after
    IndividualTeacherWorkspace, which sets workspace_access."""

    def has_permission(self, request, view):
        if not request.workspace_access.classes_enabled:
            raise SchoolPlanOnly()
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
                "usage": selectors.get_workspace_usage(self.school, ai_since=access.ai_since),
                "profile": profile
                and {"subject": profile.subject, "grade_levels": profile.grade_levels},
                "pending_upgrade": pending and {"plan": pending.plan},
                "features": {"classes": access.classes_enabled},
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


CLASS_FEATURES = [IndividualTeacherWorkspace, ClassesEnabled]


class ClassroomViewSet(WorkspaceMixin, viewsets.GenericViewSet):
    permission_classes = CLASS_FEATURES
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
    permission_classes = CLASS_FEATURES
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

    @action(detail=True, methods=["get"])
    def profile(self, request, pk=None):
        query = self.valid(ProfileQuerySerializer, request.query_params)
        student = self._student(pk)
        profile = selectors.get_student_profile(self.school, student, period=query["period"])
        return Response(
            {
                "student": {
                    **self.get_serializer(student).data,
                    "classroom_name": student.classroom.name,
                },
                **StudentProfileSerializer(profile).data,
            }
        )

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
        """A draft only. The teacher edits it and saves it with a normal create."""
        data = self.valid(LessonGenerateSerializer, request.data)
        return Response(services.generate_lesson_draft(self.school, self.access, **data))

    @action(detail=True, methods=["get"])
    def presentation(self, request, pk=None):
        # Imported here so the rest of the API still runs if python-pptx is missing.
        from apps.integrations.slides.lesson_deck import build_lesson_deck

        plan = self._plan(pk)
        services.record_presentation_export(self.school, self.access, plan)
        deck = build_lesson_deck(
            {field: getattr(plan, field) for field in PLAN_SECTIONS},
            watermark=self.access.tier in ("trial", "expired"),
            teacher_name=request.user.get_full_name(),
        )
        return self._file(plan, deck, PPTX_TYPE, "pptx")

    @action(detail=True, methods=["get"])
    def document(self, request, pk=None):
        """The lesson plan as a Word file. Not counted against any limit."""
        # Imported here so the rest of the API still runs if python-docx is missing.
        from apps.integrations.word.lesson_document import build_lesson_document

        plan = self._plan(pk)
        document = build_lesson_document(
            {
                **{field: getattr(plan, field) for field in PLAN_SECTIONS},
                "classroom": plan.classroom.name if plan.classroom else "",
                "date": plan.lesson_date.strftime("%d/%m/%Y") if plan.lesson_date else "",
                "teacher": request.user.get_full_name(),
            },
            watermark=self.access.tier in ("trial", "expired"),
        )
        return self._file(plan, document, DOCX_TYPE, "docx")

    @staticmethod
    def _file(plan, content, content_type, extension):
        name = slugify(plan.title) or f"lesson-{plan.id}"
        response = HttpResponse(content, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{name}.{extension}"'
        return response


class AssessmentViewSet(WorkspaceMixin, viewsets.GenericViewSet):
    permission_classes = CLASS_FEATURES
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
    permission_classes = CLASS_FEATURES
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


# --- Tests made from a PDF


class ExamOptionsView(WorkspaceMixin, APIView):
    """What the test maker offers: ready patterns, paper colors and its limits."""

    def get(self, request):
        return Response(
            {
                "presets": exams.PRESETS,
                "themes": [{"key": key, **colors} for key, colors in exams.THEMES.items()],
                "font_sizes": list(exams.FONT_SIZES),
                "limits": {
                    "max_pdf_mb": exams.MAX_PDF_BYTES // (1024 * 1024),
                    "max_pdf_pages": exams.MAX_PDF_PAGES,
                    "max_sections": exams.MAX_SECTIONS,
                    "max_section_questions": exams.MAX_SECTION_QUESTIONS,
                    "max_ai_questions": exams.MAX_AI_QUESTIONS,
                    "max_exam_questions": exams.MAX_EXAM_QUESTIONS,
                    "max_regenerations": exams.MAX_REGENERATIONS,
                },
            }
        )


class PaperDesignView(WorkspaceMixin, APIView):
    """The look of every test paper and answer key: color, text size, columns, name line."""

    def get(self, request):
        return Response(selectors.get_paper_design(self.school))

    def put(self, request):
        # Partial: a field left out keeps its saved value.
        data = self.valid(ExamThemeSerializer, request.data, partial=True)
        return Response(services.save_paper_design(self.school, data))


class ExamSourceView(WorkspaceMixin, APIView):
    """Takes a PDF and keeps only its text. Says which pages have text to choose from."""

    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [ExamUploadThrottle]

    def post(self, request):
        data = self.valid(ExamSourceUploadSerializer, request.data)
        document = services.save_exam_source(self.school, upload=data["file"])
        return Response(SourceDocumentSerializer(document).data, status=201)


def _without(data, *keys):
    return {key: value for key, value in data.items() if key not in keys}


class ExamPatternViewSet(WorkspaceMixin, viewsets.GenericViewSet):
    serializer_class = ExamPatternSerializer

    def _pattern(self, pk):
        return selectors.get_exam_pattern(self.school, pk)

    def list(self, request):
        patterns = selectors.list_exam_patterns(self.school)
        return Response(self.get_serializer(patterns, many=True).data)

    def create(self, request):
        data = self.valid(ExamPatternSerializer, request.data)
        pattern = services.create_exam_pattern(self.school, **data)
        return Response(self.get_serializer(pattern).data, status=201)

    def partial_update(self, request, pk=None):
        pattern = self._pattern(pk)
        data = self.valid(ExamPatternSerializer, _without(request.data, "sections"), partial=True)
        if "sections" in request.data:
            data.update(self.valid(ExamSectionsSerializer, {"sections": request.data["sections"]}))
        pattern = services.update_exam_pattern(self.school, pattern, **data)
        return Response(self.get_serializer(pattern).data)

    def destroy(self, request, pk=None):
        services.delete_record(self._pattern(pk))
        return Response(status=204)


class ExamDraftViewSet(WorkspaceMixin, viewsets.GenericViewSet):
    """AI drafts. One is written in the background; the app asks for it until it's ready."""

    serializer_class = ExamDraftSerializer

    def get_throttles(self):
        if self.action == "create":
            return [ExamAiThrottle()]
        return super().get_throttles()

    def create(self, request):
        data = self.valid(ExamDraftCreateSerializer, request.data)
        draft = services.start_exam_draft(
            self.school, self.access, document=data.pop("source"), **data
        )
        # Without a task queue (a laptop), the draft is already written by now.
        draft.refresh_from_db()
        return Response(self.get_serializer(draft).data, status=202)

    def retrieve(self, request, pk=None):
        return Response(self.get_serializer(selectors.get_exam_draft(self.school, pk)).data)

    @action(detail=True, methods=["post"], throttle_classes=[ExamAiThrottle])
    def regenerate(self, request, pk=None):
        draft = selectors.get_exam_draft(self.school, pk)
        data = self.valid(ExamRegenerateSerializer, request.data)
        return Response(services.regenerate_exam_question(self.school, draft, **data))


class ExamPagination(PageNumberPagination):
    page_size = 20


class ExamViewSet(WorkspaceMixin, viewsets.GenericViewSet):
    serializer_class = ExamSerializer
    pagination_class = ExamPagination

    def _exam(self, pk):
        return selectors.get_exam(self.school, pk)

    def _detail(self, pk):
        return ExamDetailSerializer(self._exam(pk), context=self.get_serializer_context()).data

    def list(self, request):
        filters = self.valid(ExamFilterSerializer, request.query_params)
        page = self.paginate_queryset(selectors.list_exams(self.school, **filters))
        return self.get_paginated_response(self.get_serializer(page, many=True).data)

    def create(self, request):
        data = self.valid(ExamDetailSerializer, request.data)
        exam = services.create_exam(self.school, **data)
        return Response(self._detail(exam.pk), status=201)

    def retrieve(self, request, pk=None):
        return Response(self._detail(pk))

    def partial_update(self, request, pk=None):
        exam = self._exam(pk)
        fields = _without(request.data, "questions", "draft")
        data = self.valid(ExamSerializer, fields, partial=True)
        if "questions" in request.data:
            data.update(
                self.valid(ExamQuestionsSerializer, {"questions": request.data["questions"]})
            )
        services.update_exam(self.school, exam, **data)
        return Response(self._detail(exam.pk))

    def destroy(self, request, pk=None):
        services.delete_record(self._exam(pk))
        return Response(status=204)

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        copy = services.duplicate_exam(self.school, self._exam(pk))
        return Response(self._detail(copy.pk), status=201)

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        """The paper, or its answer key, as PDF or Word. Not counted against any limit."""
        query = self.valid(ExamFileQuerySerializer, request.query_params)
        exam = self._exam(pk)
        paper = build_paper(
            exam,
            teacher_name=request.user.get_full_name(),
            answers=query["answers"],
            watermark=self.access.tier in ("trial", "expired"),
            # The Paper design page sets the look of every paper.
            theme=selectors.get_paper_design(self.school),
        )
        if query["type"] == "docx":
            # Imported here so the rest of the API still runs if python-docx is missing.
            from apps.integrations.word.exam_document import build_exam_document

            content, content_type = build_exam_document(paper), DOCX_TYPE
        else:
            try:
                content = render_paper_pdf(paper)
            except PdfUnavailable as error:
                raise ServiceUnavailable() from error
            content_type = "application/pdf"

        name = slugify(exam.title) or f"test-{exam.id}"
        if query["answers"]:
            name += "-answers"
        response = HttpResponse(content, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{name}.{query["type"]}"'
        return response
