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
            # The same class name can be used once for each subject.
            models.UniqueConstraint(
                "school",
                Lower("name"),
                Lower("subject"),
                name="unique_classroom_name_subject",
            ),
        ]

    def __str__(self):
        return self.name


class Student(TenantModel):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name="students")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    father_name = models.CharField(max_length=100, blank=True)
    # The school's own ID for the student. Optional, but used once per class.
    student_number = models.CharField(max_length=30, blank=True)
    parent_email = models.EmailField(blank=True)

    class Meta:
        ordering = ["first_name", "last_name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["classroom", "student_number"],
                condition=~Q(student_number=""),
                name="unique_student_number_per_class",
            ),
        ]
        indexes = [
            models.Index(
                fields=["school", "classroom", "first_name", "last_name"],
                name="student_roster_idx",
            ),
        ]

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

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
    """One AI lesson plan or AI test. Each kind has its own allowance."""

    class Kind(models.TextChoices):
        LESSON = "lesson", "Lesson plan"
        EXAM = "exam", "Test"

    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.LESSON)
    lesson_plan = models.ForeignKey(
        LessonPlan, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        indexes = [
            models.Index(fields=["school", "created_at"], name="ai_generation_month_idx"),
            models.Index(fields=["school", "kind", "created_at"], name="ai_generation_kind_idx"),
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


class SourceDocument(TenantModel):
    """The text of a PDF a teacher uploaded to make a test. The file itself is never kept.

    The same file uploaded again within a day is read from here, not parsed again."""

    sha256 = models.CharField(max_length=64)
    filename = models.CharField(max_length=255)
    page_count = models.PositiveSmallIntegerField()
    # The text of each page, in order. A page with no text is "".
    pages = models.JSONField(default=list)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["school", "sha256"], name="one_source_per_file"),
        ]
        indexes = [models.Index(fields=["updated_at"], name="source_document_age_idx")]


class ExamPattern(TenantModel):
    """A test layout the teacher saved: sections of question kind, count, marks and level."""

    name = models.CharField(max_length=100)
    sections = models.JSONField()

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint("school", Lower("name"), name="unique_exam_pattern_name"),
        ]

    def __str__(self):
        return self.name


class PaperDesign(TenantModel):
    """How every test paper and answer key of the workspace looks: color, text size,
    columns and the name line. One per workspace, set on the Paper design page."""

    theme = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["school"], name="one_paper_design_per_workspace"),
        ]


class ExamDraft(TenantModel):
    """Questions the AI wrote, waiting for the teacher to review. Deleted after a day."""

    class Status(models.TextChoices):
        PENDING = "pending", "Being written"
        READY = "ready", "Ready to review"
        FAILED = "failed", "Failed"

    document = models.ForeignKey(SourceDocument, on_delete=models.CASCADE, related_name="drafts")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    # What the teacher asked for: title, subject, grade, language, classroom, pages, sections.
    settings = models.JSONField()
    questions = models.JSONField(default=list)
    requested = models.PositiveSmallIntegerField()
    error = models.CharField(max_length=40, blank=True)
    regenerations = models.PositiveSmallIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["school", "status", "created_at"], name="exam_draft_status_idx"),
        ]


class Exam(TenantModel):
    """A test paper the teacher saved, printed or downloaded with its answer key."""

    class Source(models.TextChoices):
        MANUAL = "manual", "Written by the teacher"
        AI = "ai", "Generated with AI"

    class Language(models.TextChoices):
        ENGLISH = "en", "English"
        ARABIC = "ar", "Arabic"

    classroom = models.ForeignKey(
        Classroom, null=True, blank=True, on_delete=models.SET_NULL, related_name="exams"
    )
    title = models.CharField(max_length=200)
    subject = models.CharField(max_length=100, blank=True)
    grade = models.CharField(max_length=50, blank=True)
    language = models.CharField(max_length=2, choices=Language.choices, default=Language.ENGLISH)
    exam_date = models.DateField(null=True, blank=True)
    duration_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    instructions = models.TextField(max_length=1000, blank=True)
    # How the paper looks: color, font size, columns and the name line.
    theme = models.JSONField(default=dict)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.MANUAL)

    class Meta:
        ordering = ["-updated_at", "-id"]
        indexes = [models.Index(fields=["school", "-updated_at"], name="exam_recent_idx")]

    def __str__(self):
        return self.title


class ExamQuestion(TenantModel):
    class Kind(models.TextChoices):
        MCQ = "mcq", "Multiple choice"
        TRUE_FALSE = "true_false", "True or false"
        FILL_BLANK = "fill_blank", "Fill in the blank"
        SHORT_ANSWER = "short_answer", "Short answer"

    class Difficulty(models.TextChoices):
        EASY = "easy", "Easy"
        MEDIUM = "medium", "Medium"
        HARD = "hard", "Hard"

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="questions")
    position = models.PositiveSmallIntegerField()
    kind = models.CharField(max_length=20, choices=Kind.choices)
    text = models.TextField(max_length=1000)
    # Multiple choice only: the choices, and the index of the right one.
    options = models.JSONField(default=list, blank=True)
    correct_option = models.PositiveSmallIntegerField(null=True, blank=True)
    # "true" or "false", the missing word, or a model answer, by kind.
    answer = models.TextField(max_length=1000, blank=True)
    explanation = models.TextField(max_length=1000, blank=True)
    marks = models.DecimalField(max_digits=5, decimal_places=2)
    difficulty = models.CharField(
        max_length=10, choices=Difficulty.choices, default=Difficulty.MEDIUM
    )
    source_page = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["position", "id"]
        constraints = [
            models.UniqueConstraint(fields=["exam", "position"], name="one_question_per_position"),
            models.CheckConstraint(
                condition=Q(marks__gt=Decimal("0")), name="exam_question_marks_positive"
            ),
        ]


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
