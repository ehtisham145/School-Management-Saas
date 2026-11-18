"""An individual teacher's own classes, students, lessons and results."""

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Lower

from apps.core.models import TenantModel


class TeacherProfile(TenantModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="teacher_profile"
    )
    subject = models.CharField(max_length=100)
    grade_levels = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.user} ({self.subject})"


class Classroom(TenantModel):
    name = models.CharField(max_length=100)
    subject = models.CharField(max_length=100, blank=True)
    grade = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(
                "school", Lower("name"), name="unique_classroom_name_per_workspace"
            ),
        ]

    def __str__(self):
        return self.name


class Student(TenantModel):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name="students")
    full_name = models.CharField(max_length=150)
    parent_email = models.EmailField(blank=True)

    class Meta:
        ordering = ["full_name", "id"]
        indexes = [
            models.Index(fields=["school", "classroom", "full_name"], name="student_roster_idx"),
        ]

    def __str__(self):
        return self.full_name


class LessonPlan(TenantModel):
    class Source(models.TextChoices):
        MANUAL = "manual", "Written by the teacher"
        AI = "ai", "Generated with AI"

    classroom = models.ForeignKey(
        Classroom, null=True, blank=True, on_delete=models.SET_NULL, related_name="lesson_plans"
    )
    title = models.CharField(max_length=200)
    subject = models.CharField(max_length=100, blank=True)
    grade = models.CharField(max_length=50, blank=True)
    lesson_date = models.DateField(null=True, blank=True)
    objectives = models.TextField(max_length=5000, blank=True)
    materials = models.TextField(max_length=5000, blank=True)
    activities = models.TextField(max_length=5000, blank=True)
    assessment = models.TextField(max_length=5000, blank=True)
    homework = models.TextField(max_length=5000, blank=True)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.MANUAL)

    class Meta:
        ordering = ["-updated_at", "-id"]
        indexes = [
            models.Index(fields=["school", "-updated_at"], name="lesson_plan_recent_idx"),
        ]

    def __str__(self):
        return self.title


class PresentationExport(TenantModel):
    """One PowerPoint download. Counted against the free trial's limit."""

    lesson_plan = models.ForeignKey(
        LessonPlan, null=True, on_delete=models.SET_NULL, related_name="+"
    )


class AIGeneration(TenantModel):
    """One AI lesson plan. Counted against the monthly allowance."""

    lesson_plan = models.ForeignKey(
        LessonPlan, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        indexes = [
            models.Index(fields=["school", "created_at"], name="ai_generation_month_idx"),
        ]


class AttendanceRecord(TenantModel):
    class Status(models.TextChoices):
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"
        LATE = "late", "Late"
        EXCUSED = "excused", "Excused"

    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name="attendance")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="attendance")
    date = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["student", "date"], name="one_attendance_per_day"),
        ]
        indexes = [
            models.Index(fields=["school", "classroom", "date"], name="attendance_class_day_idx"),
        ]


class Assessment(TenantModel):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name="assessments")
    title = models.CharField(max_length=150)
    max_marks = models.DecimalField(max_digits=6, decimal_places=2)
    date = models.DateField()

    class Meta:
        ordering = ["date", "id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(max_marks__gt=Decimal("0")), name="assessment_max_marks_positive"
            ),
        ]
        indexes = [
            models.Index(fields=["school", "classroom", "date"], name="assessment_class_day_idx"),
        ]

    def __str__(self):
        return self.title


class Mark(TenantModel):
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="marks")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="marks")
    value = models.DecimalField(max_digits=6, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["assessment", "student"], name="one_mark_per_student"),
            models.CheckConstraint(condition=Q(value__gte=Decimal("0")), name="mark_not_negative"),
        ]


class ParentMessage(TenantModel):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name="messages")
    subject = models.CharField(max_length=150)
    body = models.TextField(max_length=3000)
    recipient_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["school", "-created_at"], name="parent_message_recent_idx"),
        ]

    def __str__(self):
        return self.subject


class UpgradeRequest(TenantModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"

    class Plan(models.TextChoices):
        TEACHER = "teacher", "Teacher"
        TEACHER_PRO = "teacher_pro", "Teacher Pro"

    plan = models.CharField(max_length=20, choices=Plan.choices)
    note = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["school"],
                condition=Q(status="pending"),
                name="one_pending_upgrade_per_workspace",
            ),
            models.CheckConstraint(
                condition=Q(status="pending") | Q(completed_at__gte=F("created_at")),
                name="upgrade_completed_after_request",
            ),
        ]
