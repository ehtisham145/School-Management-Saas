"""Every write of the teacher's workspace. Limits are checked under a lock on the workspace,
so two requests at once can't pass a plan's limit."""

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.classroom.exceptions import (
    AiQuotaReached,
    PlanLimitReached,
    ProRequired,
    ServiceUnavailable,
)
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
from apps.classroom.selectors import get_workspace_usage, list_parent_emails
from apps.classroom.tasks import send_parent_message_task
from apps.integrations.ai.lesson_provider import LessonAiUnavailable, generate_lesson_content
from apps.tenancy.models import School

NAME_TAKEN = "You already have this class for this subject."
NUMBER_TAKEN = "Another student in this class has this ID."


def _lock_workspace(school):
    School.objects.select_for_update().get(pk=school.pk)


def _check_limit(limit, used, adding=1):
    if limit is not None and used + adding > limit:
        raise PlanLimitReached()


def _require_pro(access):
    if not access.limits.pro_features:
        raise ProRequired()


def delete_record(record):
    record.delete()


# --- Setup


@transaction.atomic
def complete_setup(school, user, *, subject, grade_levels):
    profile, _ = TeacherProfile.objects.update_or_create(
        user=user,
        defaults={"school": school, "subject": subject, "grade_levels": grade_levels},
    )
    return profile


# --- Classes and students


def _class_taken(school, name, subject, exclude=None):
    classes = Classroom.objects.filter(school=school, name__iexact=name, subject__iexact=subject)
    if exclude is not None:
        classes = classes.exclude(pk=exclude.pk)
    return classes.exists()


@transaction.atomic
def create_classroom(school, access, **fields):
    _lock_workspace(school)
    _check_limit(access.limits.classes, get_workspace_usage(school)["classes"])
    if _class_taken(school, fields["name"], fields.get("subject", "")):
        raise ValidationError({"name": NAME_TAKEN})
    return Classroom.objects.create(school=school, **fields)


def update_classroom(school, classroom, **fields):
    name = fields.get("name", classroom.name)
    subject = fields.get("subject", classroom.subject)
    if _class_taken(school, name, subject, exclude=classroom):
        raise ValidationError({"name": NAME_TAKEN})
    for field, value in fields.items():
        setattr(classroom, field, value)
    try:
        with transaction.atomic():
            classroom.save(update_fields=[*fields, "updated_at"])
    except IntegrityError as error:
        raise ValidationError({"name": NAME_TAKEN}) from error
    return classroom


@transaction.atomic
def add_students(school, access, classroom, rows):
    _lock_workspace(school)
    _check_limit(access.limits.students, get_workspace_usage(school)["students"], len(rows))
    numbers = [row.get("student_number", "") for row in rows]
    taken = set(
        Student.objects.filter(
            school=school, classroom=classroom, student_number__in=[n for n in numbers if n]
        ).values_list("student_number", flat=True)
    )
    if taken:
        raise ValidationError(
            {
                "students": [
                    {"student_number": [NUMBER_TAKEN]} if number in taken else {}
                    for number in numbers
                ]
            }
        )
    return Student.objects.bulk_create(
        [Student(school=school, classroom=classroom, **row) for row in rows]
    )


def update_student(student, **fields):
    number = fields.get("student_number")
    if (
        number
        and Student.objects.filter(
            school_id=student.school_id,
            classroom_id=student.classroom_id,
            student_number=number,
        )
        .exclude(pk=student.pk)
        .exists()
    ):
        raise ValidationError({"student_number": NUMBER_TAKEN})
    for field, value in fields.items():
        setattr(student, field, value)
    try:
        with transaction.atomic():
            student.save(update_fields=[*fields, "updated_at"])
    except IntegrityError as error:
        raise ValidationError({"student_number": NUMBER_TAKEN}) from error
    return student


# --- Attendance


def save_attendance(school, classroom, day, records):
    student_ids = {record["student"] for record in records}
    known = set(
        Student.objects.filter(school=school, classroom=classroom, id__in=student_ids).values_list(
            "id", flat=True
        )
    )
    if known != student_ids:
        raise ValidationError({"records": "Some students are not in this class."})

    AttendanceRecord.objects.bulk_create(
        [
            AttendanceRecord(
                school=school,
                classroom=classroom,
                student_id=record["student"],
                date=day,
                status=record["status"],
            )
            for record in records
        ],
        update_conflicts=True,
        unique_fields=["student", "date"],
        update_fields=["status", "updated_at"],
    )


# --- Lesson plans


def _check_plan_classroom(school, classroom):
    if classroom is not None and classroom.school_id != school.id:
        raise ValidationError({"classroom": "Class not found."})


@transaction.atomic
def create_lesson_plan(school, access, **fields):
    _lock_workspace(school)
    _check_plan_classroom(school, fields.get("classroom"))
    _check_limit(access.limits.lesson_plans, get_workspace_usage(school)["lesson_plans"])
    return LessonPlan.objects.create(school=school, **fields)


def update_lesson_plan(school, plan, **fields):
    _check_plan_classroom(school, fields.get("classroom"))
    for field, value in fields.items():
        setattr(plan, field, value)
    plan.save(update_fields=[*fields, "updated_at"])
    return plan


@transaction.atomic
def record_presentation_export(school, access, plan):
    _lock_workspace(school)
    _check_limit(
        access.limits.presentation_exports, get_workspace_usage(school)["presentation_exports"]
    )
    return PresentationExport.objects.create(school=school, lesson_plan=plan)


def _check_ai_allowance(school, access):
    usage = get_workspace_usage(school, ai_since=access.ai_since)
    if usage["ai_used"] >= access.limits.ai_lessons:
        raise AiQuotaReached()
    # No point making a draft that could never be saved.
    _check_limit(access.limits.lesson_plans, usage["lesson_plans"])


def generate_lesson_draft(school, access, *, topic, subject, grade, language, classroom=None):
    """Returns a draft for the teacher to read and edit. Nothing is saved but the count.

    Only the topic, subject and grade go to the AI provider, never any student data.
    """
    _check_plan_classroom(school, classroom)
    _check_ai_allowance(school, access)

    # Outside any transaction: the provider can take many seconds to answer.
    try:
        content = generate_lesson_content(
            topic=topic, subject=subject, grade=grade, language=language
        )
    except LessonAiUnavailable as error:
        raise ServiceUnavailable() from error

    with transaction.atomic():
        _lock_workspace(school)
        _check_ai_allowance(school, access)
        AIGeneration.objects.create(school=school)
    return {
        **content,
        "classroom": classroom.pk if classroom else None,
        "subject": subject,
        "grade": grade,
    }


# --- Assessments and marks


def create_assessment(school, classroom, **fields):
    return Assessment.objects.create(school=school, classroom=classroom, **fields)


@transaction.atomic
def update_assessment(school, assessment, **fields):
    new_max = fields.get("max_marks")
    if (
        new_max is not None
        and Mark.objects.filter(school=school, assessment=assessment, value__gt=new_max).exists()
    ):
        raise ValidationError({"max_marks": "Some marks are higher than this."})
    for field, value in fields.items():
        setattr(assessment, field, value)
    assessment.save(update_fields=[*fields, "updated_at"])
    return assessment


@transaction.atomic
def save_marks(school, assessment, rows):
    """A blank value clears that student's mark."""
    student_ids = {row["student"] for row in rows}
    known = set(
        Student.objects.filter(
            school=school, classroom_id=assessment.classroom_id, id__in=student_ids
        ).values_list("id", flat=True)
    )
    if known != student_ids:
        raise ValidationError({"marks": "Some students are not in this class."})
    if any(row["value"] is not None and row["value"] > assessment.max_marks for row in rows):
        raise ValidationError({"marks": "A mark can't be higher than the maximum."})

    cleared = [row["student"] for row in rows if row["value"] is None]
    if cleared:
        Mark.objects.filter(school=school, assessment=assessment, student_id__in=cleared).delete()

    Mark.objects.bulk_create(
        [
            Mark(
                school=school,
                assessment=assessment,
                student_id=row["student"],
                value=row["value"],
            )
            for row in rows
            if row["value"] is not None
        ],
        update_conflicts=True,
        unique_fields=["assessment", "student"],
        update_fields=["value", "updated_at"],
    )


# --- Teacher Pro


@transaction.atomic
def send_parent_message(school, access, classroom, *, subject, body):
    _require_pro(access)
    recipients = list_parent_emails(school, classroom)
    if not recipients:
        raise ValidationError({"classroom": "No student in this class has a parent email."})

    message = ParentMessage.objects.create(
        school=school,
        classroom=classroom,
        subject=subject,
        body=body,
        recipient_count=len(recipients),
    )
    transaction.on_commit(
        lambda: send_parent_message_task.delay(school.id, message.id), robust=True
    )
    return message


# --- Upgrade


@transaction.atomic
def request_upgrade(school, *, plan, note=""):
    _lock_workspace(school)
    pending = UpgradeRequest.objects.filter(
        school=school, status=UpgradeRequest.Status.PENDING
    ).first()
    if pending:
        pending.plan = plan
        pending.note = note
        pending.save(update_fields=["plan", "note", "updated_at"])
        return pending
    return UpgradeRequest.objects.create(school=school, plan=plan, note=note)


def complete_upgrade_requests(school):
    UpgradeRequest.objects.filter(school=school, status=UpgradeRequest.Status.PENDING).update(
        status=UpgradeRequest.Status.COMPLETED,
        completed_at=timezone.now(),
        updated_at=timezone.now(),
    )
