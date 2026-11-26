"""Every read takes the workspace first, so one teacher can never reach another's data."""

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import (
    Avg,
    Count,
    DecimalField,
    Exists,
    IntegerField,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.classroom.exams import DEFAULT_THEME, DRAFT_LIFETIME, PENDING_TIMEOUT
from apps.classroom.models import (
    AIGeneration,
    Assessment,
    AttendanceRecord,
    Classroom,
    Exam,
    ExamDraft,
    ExamPattern,
    ExamQuestion,
    LessonPlan,
    Mark,
    PaperDesign,
    ParentMessage,
    PresentationExport,
    SourceDocument,
    Student,
    TeacherProfile,
    UpgradeRequest,
)
from apps.tenancy.models import School


def _count_of(queryset):
    counted = (
        queryset.filter(school=OuterRef("pk"))
        .order_by()
        .values("school")
        .annotate(total=Count("pk"))
        .values("total")
    )
    return Coalesce(Subquery(counted, output_field=IntegerField()), Value(0))


def get_workspace_usage(school, *, ai_since: date | None = None):
    """All the counts for the overview and the plan limits, in one query.

    AI lesson plans and AI tests are counted from ai_since (the start of the month on a
    paid plan), or all of them during the trial."""
    ai = AIGeneration.objects.all()
    if ai_since is not None:
        ai = ai.filter(created_at__date__gte=ai_since)
    return (
        School.objects.filter(pk=school.pk)
        .annotate(
            classes=_count_of(Classroom.objects.all()),
            students=_count_of(Student.objects.all()),
            lesson_plans=_count_of(LessonPlan.objects.all()),
            presentation_exports=_count_of(PresentationExport.objects.all()),
            assessments=_count_of(Assessment.objects.all()),
            attendance_records=_count_of(AttendanceRecord.objects.all()),
            exams=_count_of(Exam.objects.all()),
            ai_used=_count_of(ai.filter(kind=AIGeneration.Kind.LESSON)),
            ai_exams_used=_count_of(ai.filter(kind=AIGeneration.Kind.EXAM)),
        )
        .values(
            "classes",
            "students",
            "lesson_plans",
            "presentation_exports",
            "assessments",
            "attendance_records",
            "exams",
            "ai_used",
            "ai_exams_used",
        )
        .get()
    )


def get_teacher_profile(school, user):
    return TeacherProfile.objects.filter(school=school, user=user).first()


def get_pending_upgrade(school):
    return UpgradeRequest.objects.filter(
        school=school, status=UpgradeRequest.Status.PENDING
    ).first()


def _count_per_classroom(queryset):
    counted = (
        queryset.filter(classroom=OuterRef("pk"))
        .order_by()
        .values("classroom")
        .annotate(total=Count("pk"))
        .values("total")
    )
    return Coalesce(Subquery(counted, output_field=IntegerField()), Value(0))


def list_classrooms(school):
    """Each class with its counts, and whether today's attendance is taken, in one query."""
    today = timezone.localdate()
    return Classroom.objects.filter(school=school).annotate(
        student_count=_count_per_classroom(Student.objects.filter(school=school)),
        assessment_count=_count_per_classroom(Assessment.objects.filter(school=school)),
        attendance_taken_today=Exists(
            AttendanceRecord.objects.filter(school=school, classroom=OuterRef("pk"), date=today)
        ),
    )


def get_classroom(school, classroom_id):
    return get_object_or_404(list_classrooms(school), pk=classroom_id)


def list_students(school, classroom):
    return Student.objects.filter(school=school, classroom=classroom)


def get_student(school, student_id):
    return get_object_or_404(
        Student.objects.filter(school=school).select_related("classroom"), pk=student_id
    )


def get_attendance_roster(school, classroom, day: date):
    """Every student of the class, with their status that day, if one was saved."""
    status = AttendanceRecord.objects.filter(
        school=school, student=OuterRef("pk"), date=day
    ).values("status")[:1]
    return list_students(school, classroom).annotate(status=Subquery(status))


def get_attendance_summary(school, classroom, *, start: date, end: date):
    return (
        AttendanceRecord.objects.filter(
            school=school, classroom=classroom, date__gte=start, date__lte=end
        )
        .order_by()
        .values("status")
        .annotate(total=Count("id"))
    )


def list_lesson_plans(school, *, search="", classroom=None):
    plans = LessonPlan.objects.filter(school=school).select_related("classroom")
    if classroom:
        plans = plans.filter(classroom_id=classroom)
    if search:
        plans = plans.filter(Q(title__icontains=search) | Q(subject__icontains=search))
    return plans


def get_lesson_plan(school, plan_id):
    return get_object_or_404(list_lesson_plans(school), pk=plan_id)


def list_assessments(school, *, classroom=None):
    assessments = Assessment.objects.filter(school=school).annotate(marked=Count("marks"))
    if classroom:
        assessments = assessments.filter(classroom_id=classroom)
    return assessments


def get_assessment(school, assessment_id):
    return get_object_or_404(list_assessments(school), pk=assessment_id)


def get_marks_sheet(school, assessment):
    """Every student of the class, with their mark for this assessment, if any."""
    value = Mark.objects.filter(
        school=school, assessment=assessment, student=OuterRef("pk")
    ).values("value")[:1]
    return list_students(school, assessment.classroom).annotate(value=Subquery(value))


def get_gradebook(school, classroom):
    """Students, assessments and marks in three queries, however large the class is."""
    assessments = list(Assessment.objects.filter(school=school, classroom=classroom))
    students = list(list_students(school, classroom))
    marks = Mark.objects.filter(school=school, assessment__classroom=classroom).values_list(
        "student_id", "assessment_id", "value"
    )
    by_student = {}
    for student_id, assessment_id, value in marks:
        by_student.setdefault(student_id, {})[assessment_id] = value
    return {"assessments": assessments, "students": students, "marks": by_student}


def get_report_card(school, student):
    marks = (
        Mark.objects.filter(school=school, student=student)
        .select_related("assessment")
        .order_by("assessment__date", "assessment_id")
    )
    attendance = (
        AttendanceRecord.objects.filter(school=school, student=student)
        .order_by()
        .values("status")
        .annotate(total=Count("id"))
    )
    return {"marks": list(marks), "attendance": {row["status"]: row["total"] for row in attendance}}


def list_parent_messages(school):
    return ParentMessage.objects.filter(school=school).select_related("classroom")


def list_parent_emails(school, classroom):
    return list(
        list_students(school, classroom)
        .exclude(parent_email="")
        .order_by()
        .values_list("parent_email", flat=True)
        .distinct()
    )


PROFILE_PERIODS = {"month": 30, "90days": 90, "all": None}
HUNDRED = Decimal("100")


def _percent(part, whole):
    if not whole:
        return None
    return (Decimal(part) * HUNDRED / Decimal(whole)).quantize(Decimal("0.1"), ROUND_HALF_UP)


def get_student_profile(school, student, *, period="month"):
    """Attendance and marks of one student, in two queries.

    Late and excused days count as attended in the rate; only absent days count against it.
    """
    today = timezone.localdate()
    days = PROFILE_PERIODS[period]
    start = today - timedelta(days=days - 1) if days else None

    records = AttendanceRecord.objects.filter(school=school, student=student)
    if start:
        records = records.filter(date__gte=start)
    attendance = list(records.order_by("-date").values("date", "status"))
    counts = {status: 0 for status in AttendanceRecord.Status.values}
    for record in attendance:
        counts[record["status"]] += 1
    attended = len(attendance) - counts[AttendanceRecord.Status.ABSENT]

    mark = Mark.objects.filter(school=school, assessment=OuterRef("pk"), student=student)
    assessments = (
        Assessment.objects.filter(school=school, classroom_id=student.classroom_id)
        .annotate(
            value=Subquery(
                mark.values("value")[:1],
                output_field=DecimalField(max_digits=6, decimal_places=2),
            ),
            class_average=Avg("marks__value"),
        )
        .order_by("-date", "-id")
    )
    if start:
        assessments = assessments.filter(date__gte=start)

    marks, earned, possible = [], Decimal("0"), Decimal("0")
    for assessment in assessments:
        if assessment.value is not None:
            earned += assessment.value
            possible += assessment.max_marks
        marks.append(
            {
                "id": assessment.id,
                "title": assessment.title,
                "date": assessment.date,
                "max_marks": assessment.max_marks,
                "value": assessment.value,
                "percent": _percent(assessment.value, assessment.max_marks)
                if assessment.value is not None
                else None,
                "class_average_percent": _percent(assessment.class_average, assessment.max_marks)
                if assessment.class_average is not None
                else None,
            }
        )

    return {
        "period": period,
        "start": start,
        "end": today,
        "attendance": {
            **counts,
            "total": len(attendance),
            "rate": _percent(attended, len(attendance)),
            "days": attendance,
        },
        "marks": marks,
        "average_percent": _percent(earned, possible),
    }


# --- Tests made from a PDF


def get_source_document(school, document_id):
    return get_object_or_404(SourceDocument.objects.filter(school=school), pk=document_id)


def find_source_document(school, sha256):
    return SourceDocument.objects.filter(school=school, sha256=sha256).first()


def list_exam_patterns(school):
    return ExamPattern.objects.filter(school=school)


def get_exam_pattern(school, pattern_id):
    return get_object_or_404(list_exam_patterns(school), pk=pattern_id)


def count_exams_in_progress(school):
    """AI tests still being written. They hold a place in the allowance until they finish."""
    return ExamDraft.objects.filter(
        school=school,
        status=ExamDraft.Status.PENDING,
        created_at__gte=timezone.now() - PENDING_TIMEOUT,
    ).count()


def get_exam_draft(school, draft_id):
    """A draft from the last day. Older ones are gone, even before the clean-up runs."""
    drafts = ExamDraft.objects.filter(
        school=school, created_at__gte=timezone.now() - DRAFT_LIFETIME
    ).select_related("document")
    return get_object_or_404(drafts, pk=draft_id)


def _exam_totals(exams):
    return exams.annotate(
        question_count=Count("questions"),
        total_marks=Coalesce(
            Sum("questions__marks"),
            Value(0),
            output_field=DecimalField(max_digits=8, decimal_places=2),
        ),
    )


def list_exams(school, *, search="", classroom=None):
    # Ordered here: a query with totals doesn't use the model's default order.
    exams = _exam_totals(Exam.objects.filter(school=school).select_related("classroom")).order_by(
        "-updated_at", "-id"
    )
    if classroom:
        exams = exams.filter(classroom_id=classroom)
    if search:
        exams = exams.filter(Q(title__icontains=search) | Q(subject__icontains=search))
    return exams


def get_paper_design(school):
    """The workspace's paper design, with the defaults for anything not chosen yet."""
    theme = PaperDesign.objects.filter(school=school).values_list("theme", flat=True).first() or {}
    return {**DEFAULT_THEME, **theme}


def get_exam(school, exam_id):
    """The test with its questions in order, in two queries."""
    questions = ExamQuestion.objects.filter(school=school).order_by("position", "id")
    return get_object_or_404(
        list_exams(school).prefetch_related(Prefetch("questions", queryset=questions)),
        pk=exam_id,
    )
