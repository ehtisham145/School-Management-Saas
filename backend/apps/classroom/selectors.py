"""Every read takes the workspace first, so one teacher can never reach another's data."""

from datetime import date

from django.db.models import Count, IntegerField, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.classroom.models import (
    AIGeneration,
    Assessment,
    AttendanceRecord,
    Classroom,
    LessonPlan,
    Mark,
    ParentMessage,
    PresentationExport,
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


def get_workspace_usage(school):
    """All the counts for the overview and the plan limits, in one query."""
    month_start = timezone.localdate().replace(day=1)
    return (
        School.objects.filter(pk=school.pk)
        .annotate(
            classes=_count_of(Classroom.objects.all()),
            students=_count_of(Student.objects.all()),
            lesson_plans=_count_of(LessonPlan.objects.all()),
            presentation_exports=_count_of(PresentationExport.objects.all()),
            assessments=_count_of(Assessment.objects.all()),
            attendance_records=_count_of(AttendanceRecord.objects.all()),
            ai_this_month=_count_of(AIGeneration.objects.filter(created_at__date__gte=month_start)),
        )
        .values(
            "classes",
            "students",
            "lesson_plans",
            "presentation_exports",
            "assessments",
            "attendance_records",
            "ai_this_month",
        )
        .get()
    )


def get_teacher_profile(school, user):
    return TeacherProfile.objects.filter(school=school, user=user).first()


def get_pending_upgrade(school):
    return UpgradeRequest.objects.filter(
        school=school, status=UpgradeRequest.Status.PENDING
    ).first()


def list_classrooms(school):
    return Classroom.objects.filter(school=school).annotate(student_count=Count("students"))


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
