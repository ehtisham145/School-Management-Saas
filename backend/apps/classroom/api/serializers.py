from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from apps.classroom import exams
from apps.classroom.models import (
    Assessment,
    AttendanceRecord,
    Classroom,
    Exam,
    ExamDraft,
    ExamPattern,
    LessonPlan,
    ParentMessage,
    SourceDocument,
    Student,
    UpgradeRequest,
)

MAX_STUDENTS_AT_ONCE = 200
MAX_MARK = Decimal("9999.99")


def _not_in_future(value):
    if value > timezone.localdate():
        raise serializers.ValidationError("This date is in the future.")
    return value


def _tidy(value):
    """Removes extra spaces, so "Grade  5" and "Grade 5" are the same class."""
    return " ".join(value.split())


def _unique_students(rows, field):
    students = [row["student"] for row in rows]
    if len(students) != len(set(students)):
        raise serializers.ValidationError({field: "A student appears more than once."})


class WorkspaceClassroomField(serializers.PrimaryKeyRelatedField):
    """Only the teacher's own classes can be chosen."""

    def get_queryset(self):
        return Classroom.objects.filter(school=self.context["school"])


class SetupSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=100)
    grade_levels = serializers.CharField(max_length=100)


class ClassroomSerializer(serializers.ModelSerializer):
    student_count = serializers.SerializerMethodField()
    assessment_count = serializers.SerializerMethodField()
    attendance_taken_today = serializers.SerializerMethodField()

    class Meta:
        model = Classroom
        fields = [
            "id",
            "name",
            "subject",
            "grade",
            "student_count",
            "assessment_count",
            "attendance_taken_today",
        ]
        # The service gives the friendly message for a class that is already there.
        validators = []

    def validate_name(self, value):
        value = _tidy(value)
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def validate_subject(self, value):
        return _tidy(value)

    def validate_grade(self, value):
        return _tidy(value)

    def get_student_count(self, classroom) -> int:
        return getattr(classroom, "student_count", 0)

    def get_assessment_count(self, classroom) -> int:
        return getattr(classroom, "assessment_count", 0)

    def get_attendance_taken_today(self, classroom) -> bool:
        return getattr(classroom, "attendance_taken_today", False)


class StudentSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Student
        fields = [
            "id",
            "classroom",
            "first_name",
            "last_name",
            "father_name",
            "student_number",
            "full_name",
            "parent_email",
        ]
        read_only_fields = ["classroom"]
        # The service checks a repeated student ID and gives a friendly message.
        validators = []

    def validate_first_name(self, value):
        value = _tidy(value)
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def validate_last_name(self, value):
        return _tidy(value)

    def validate_father_name(self, value):
        return _tidy(value)

    def validate_student_number(self, value):
        return value.strip()


class StudentInputSerializer(StudentSerializer):
    class Meta(StudentSerializer.Meta):
        fields = ["first_name", "last_name", "father_name", "student_number", "parent_email"]


class StudentsAddSerializer(serializers.Serializer):
    students = StudentInputSerializer(many=True, min_length=1, max_length=MAX_STUDENTS_AT_ONCE)

    def validate_students(self, rows):
        numbers = [row.get("student_number", "") for row in rows]
        repeated = {n for n in numbers if n and numbers.count(n) > 1}
        if repeated:
            raise serializers.ValidationError(
                [
                    {"student_number": ["This ID is used twice in the list."]}
                    if number in repeated
                    else {}
                    for number in numbers
                ]
            )
        return rows


class ProfileQuerySerializer(serializers.Serializer):
    period = serializers.ChoiceField(choices=["month", "90days", "all"], default="month")


def _percent_field():
    return serializers.DecimalField(max_digits=5, decimal_places=1, allow_null=True)


class ProfileDaySerializer(serializers.Serializer):
    date = serializers.DateField()
    status = serializers.CharField()


class ProfileAttendanceSerializer(serializers.Serializer):
    present = serializers.IntegerField()
    absent = serializers.IntegerField()
    late = serializers.IntegerField()
    excused = serializers.IntegerField()
    total = serializers.IntegerField()
    rate = _percent_field()
    days = ProfileDaySerializer(many=True)


class ProfileMarkSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    date = serializers.DateField()
    max_marks = serializers.DecimalField(max_digits=6, decimal_places=2)
    value = serializers.DecimalField(max_digits=6, decimal_places=2, allow_null=True)
    percent = _percent_field()
    class_average_percent = _percent_field()


class StudentProfileSerializer(serializers.Serializer):
    period = serializers.CharField()
    start = serializers.DateField(allow_null=True)
    end = serializers.DateField()
    attendance = ProfileAttendanceSerializer()
    marks = ProfileMarkSerializer(many=True)
    average_percent = _percent_field()


class AttendanceQuerySerializer(serializers.Serializer):
    date = serializers.DateField(required=False)

    def validate_date(self, value):
        return _not_in_future(value)


class AttendanceRowSerializer(serializers.Serializer):
    student = serializers.IntegerField()
    status = serializers.ChoiceField(choices=AttendanceRecord.Status.choices)


class AttendanceSaveSerializer(serializers.Serializer):
    date = serializers.DateField()
    records = AttendanceRowSerializer(many=True, min_length=1, max_length=1000)

    def validate_date(self, value):
        return _not_in_future(value)

    def validate(self, attrs):
        _unique_students(attrs["records"], "records")
        return attrs


class RosterRowSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    status = serializers.CharField(allow_null=True)

    class Meta:
        model = Student
        fields = ["id", "full_name", "status"]


class LessonPlanSerializer(serializers.ModelSerializer):
    classroom = WorkspaceClassroomField(required=False, allow_null=True)
    classroom_name = serializers.CharField(source="classroom.name", read_only=True, default=None)

    class Meta:
        model = LessonPlan
        fields = [
            "id",
            "classroom",
            "classroom_name",
            "title",
            "subject",
            "grade",
            "lesson_date",
            "objectives",
            "materials",
            "activities",
            "assessment",
            "homework",
            "source",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]


class LessonPlanFilterSerializer(serializers.Serializer):
    search = serializers.CharField(required=False, max_length=100)
    classroom = serializers.IntegerField(required=False)


class LessonGenerateSerializer(serializers.Serializer):
    topic = serializers.CharField(max_length=200)
    subject = serializers.CharField(max_length=100)
    grade = serializers.CharField(max_length=50)
    language = serializers.ChoiceField(choices=["en", "ar"])
    classroom = WorkspaceClassroomField(required=False, allow_null=True)


class AssessmentSerializer(serializers.ModelSerializer):
    classroom = WorkspaceClassroomField()
    max_marks = serializers.DecimalField(
        max_digits=6, decimal_places=2, min_value=Decimal("0.01"), max_value=MAX_MARK
    )
    marked = serializers.SerializerMethodField()

    class Meta:
        model = Assessment
        fields = ["id", "classroom", "title", "max_marks", "date", "marked"]

    def get_marked(self, assessment) -> int:
        return getattr(assessment, "marked", 0)


class AssessmentFilterSerializer(serializers.Serializer):
    classroom = serializers.IntegerField(required=False)


class MarkRowSerializer(serializers.Serializer):
    student = serializers.IntegerField()
    value = serializers.DecimalField(
        max_digits=6,
        decimal_places=2,
        min_value=Decimal("0"),
        max_value=MAX_MARK,
        allow_null=True,
    )


class MarksSaveSerializer(serializers.Serializer):
    marks = MarkRowSerializer(many=True, min_length=1, max_length=1000)

    def validate(self, attrs):
        _unique_students(attrs["marks"], "marks")
        return attrs


class MarkSheetRowSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    value = serializers.DecimalField(max_digits=6, decimal_places=2, allow_null=True)

    class Meta:
        model = Student
        fields = ["id", "full_name", "value"]


class ParentMessageSerializer(serializers.ModelSerializer):
    classroom = WorkspaceClassroomField()
    classroom_name = serializers.CharField(source="classroom.name", read_only=True)

    class Meta:
        model = ParentMessage
        fields = [
            "id",
            "classroom",
            "classroom_name",
            "subject",
            "body",
            "recipient_count",
            "created_at",
        ]
        read_only_fields = ["recipient_count", "created_at"]
        extra_kwargs = {"body": {"max_length": 3000}}


class UpgradeRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = UpgradeRequest
        fields = ["id", "plan", "note", "status", "created_at"]
        read_only_fields = ["status", "created_at"]


class ReportCardQuerySerializer(serializers.Serializer):
    language = serializers.ChoiceField(choices=["en", "ar"], required=False, default="en")


# --- Tests made from a PDF


class WorkspaceSourceField(serializers.PrimaryKeyRelatedField):
    """Only PDFs the teacher uploaded."""

    def get_queryset(self):
        return SourceDocument.objects.filter(school=self.context["school"])


class WorkspaceDraftField(serializers.PrimaryKeyRelatedField):
    """Only the teacher's own drafts that are ready and under a day old."""

    def get_queryset(self):
        return ExamDraft.objects.filter(
            school=self.context["school"],
            status=ExamDraft.Status.READY,
            created_at__gte=timezone.now() - exams.DRAFT_LIFETIME,
        )


def _marks_field(**kwargs):
    return serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=exams.MIN_MARKS,
        max_value=exams.MAX_MARKS,
        **kwargs,
    )


class ExamSourceUploadSerializer(serializers.Serializer):
    file = serializers.FileField(allow_empty_file=False)


class SourceDocumentSerializer(serializers.ModelSerializer):
    text_pages = serializers.SerializerMethodField()
    preview = serializers.SerializerMethodField()

    class Meta:
        model = SourceDocument
        fields = ["id", "filename", "page_count", "text_pages", "preview"]

    def get_text_pages(self, document) -> list[int]:
        return [number for number, text in enumerate(document.pages, start=1) if text.strip()]

    def get_preview(self, document) -> str:
        return next((text for text in document.pages if text.strip()), "")[:400]


class ExamSectionSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=exams.KINDS)
    count = serializers.IntegerField(min_value=1, max_value=exams.MAX_SECTION_QUESTIONS)
    marks = _marks_field()
    difficulty = serializers.ChoiceField(choices=exams.DIFFICULTIES, default="medium")


def _sections_field():
    return ExamSectionSerializer(many=True, min_length=1, max_length=exams.MAX_SECTIONS)


def _check_sections(sections):
    if exams.total_questions(sections) > exams.MAX_AI_QUESTIONS:
        raise serializers.ValidationError(
            f"An AI test can have up to {exams.MAX_AI_QUESTIONS} questions."
        )
    return sections


class ExamPatternSerializer(serializers.ModelSerializer):
    sections = _sections_field()

    class Meta:
        model = ExamPattern
        fields = ["id", "name", "sections", "updated_at"]
        read_only_fields = ["updated_at"]
        # The service gives the friendly message for a name that is already used.
        validators = []

    def validate_name(self, value):
        value = _tidy(value)
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def validate_sections(self, value):
        return _check_sections(value)


class ExamDraftCreateSerializer(serializers.Serializer):
    source = WorkspaceSourceField()
    page_from = serializers.IntegerField(min_value=1, max_value=exams.MAX_PDF_PAGES)
    page_to = serializers.IntegerField(min_value=1, max_value=exams.MAX_PDF_PAGES)
    title = serializers.CharField(max_length=200)
    subject = serializers.CharField(max_length=100, allow_blank=True, default="")
    grade = serializers.CharField(max_length=50, allow_blank=True, default="")
    language = serializers.ChoiceField(choices=Exam.Language.choices)
    classroom = WorkspaceClassroomField(required=False, allow_null=True)
    sections = _sections_field()

    def validate_sections(self, value):
        return _check_sections(value)

    def validate(self, attrs):
        if attrs["page_from"] > attrs["page_to"]:
            raise serializers.ValidationError(
                {"page_to": "The last page can't come before the first."}
            )
        return attrs


class ExamDraftSerializer(serializers.ModelSerializer):
    regenerations_left = serializers.SerializerMethodField()

    class Meta:
        model = ExamDraft
        fields = [
            "id",
            "status",
            "error",
            "requested",
            "questions",
            "settings",
            "regenerations_left",
            "created_at",
        ]

    def get_regenerations_left(self, draft) -> int:
        return max(exams.MAX_REGENERATIONS - draft.regenerations, 0)


class ExamRegenerateSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=exams.KINDS)
    difficulty = serializers.ChoiceField(choices=exams.DIFFICULTIES, default="medium")
    source_page = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    # The questions already in the test, so the new one is different.
    avoid = serializers.ListField(
        child=serializers.CharField(max_length=1000),
        max_length=exams.MAX_EXAM_QUESTIONS,
        default=list,
    )


class ExamQuestionSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=exams.KINDS)
    text = serializers.CharField(max_length=1000)
    options = serializers.ListField(
        child=serializers.CharField(max_length=300), max_length=6, default=list
    )
    correct_option = serializers.IntegerField(
        min_value=0, max_value=5, allow_null=True, default=None
    )
    answer = serializers.CharField(max_length=1000, allow_blank=True, default="")
    explanation = serializers.CharField(max_length=1000, allow_blank=True, default="")
    marks = _marks_field()
    difficulty = serializers.ChoiceField(choices=exams.DIFFICULTIES, default="medium")
    source_page = serializers.IntegerField(
        min_value=1, max_value=32767, allow_null=True, default=None
    )

    def validate(self, attrs):
        kind = attrs["kind"]
        if kind == exams.MCQ:
            options = attrs["options"]
            if not 2 <= len(options) <= 6:
                raise serializers.ValidationError({"options": "Give 2 to 6 choices."})
            if len({exams.normalize(option) for option in options}) != len(options):
                raise serializers.ValidationError({"options": "Each choice must be different."})
            correct = attrs["correct_option"]
            if correct is None or correct >= len(options):
                raise serializers.ValidationError({"correct_option": "Choose the right answer."})
            attrs["answer"] = ""
            return attrs

        # Only a multiple-choice question has choices.
        attrs["options"] = []
        attrs["correct_option"] = None
        if kind == exams.TRUE_FALSE and attrs["answer"] not in ("true", "false"):
            raise serializers.ValidationError({"answer": 'Choose "true" or "false".'})
        if kind == exams.FILL_BLANK:
            text = exams.UNDERSCORES.sub(exams.BLANK, attrs["text"])
            if text.count(exams.BLANK) != 1:
                raise serializers.ValidationError(
                    {"text": "Mark the missing part once, with _____."}
                )
            if not attrs["answer"].strip():
                raise serializers.ValidationError({"answer": "Write the missing word."})
            attrs["text"] = text
        return attrs


class ExamThemeSerializer(serializers.Serializer):
    color = serializers.ChoiceField(choices=list(exams.THEMES), default="navy")
    font_size = serializers.ChoiceField(choices=list(exams.FONT_SIZES), default="normal")
    columns = serializers.ChoiceField(choices=[1, 2], default=1)
    name_line = serializers.BooleanField(default=True)


class ExamSerializer(serializers.ModelSerializer):
    classroom = WorkspaceClassroomField(required=False, allow_null=True)
    classroom_name = serializers.CharField(source="classroom.name", read_only=True, default=None)
    duration_minutes = serializers.IntegerField(
        min_value=1, max_value=600, required=False, allow_null=True
    )
    theme = ExamThemeSerializer(required=False)
    question_count = serializers.IntegerField(read_only=True)
    total_marks = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)

    class Meta:
        model = Exam
        fields = [
            "id",
            "classroom",
            "classroom_name",
            "title",
            "subject",
            "grade",
            "language",
            "exam_date",
            "duration_minutes",
            "instructions",
            "theme",
            "source",
            "question_count",
            "total_marks",
            "updated_at",
        ]
        read_only_fields = ["source", "updated_at"]
        extra_kwargs = {"instructions": {"max_length": 1000}}

    def validate_title(self, value):
        value = _tidy(value)
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value


def _questions_field():
    return ExamQuestionSerializer(many=True, min_length=1, max_length=exams.MAX_EXAM_QUESTIONS)


class ExamQuestionsSerializer(serializers.Serializer):
    """The full list of questions, checked whole even in a partial update."""

    questions = _questions_field()


class ExamSectionsSerializer(serializers.Serializer):
    """The full list of sections, checked whole even in a partial update."""

    sections = _sections_field()

    def validate_sections(self, value):
        return _check_sections(value)


class ExamDetailSerializer(ExamSerializer):
    questions = _questions_field()
    # The AI draft this test was made from, if any. It is removed once the test is saved.
    draft = WorkspaceDraftField(required=False, allow_null=True, write_only=True)

    class Meta(ExamSerializer.Meta):
        fields = [*ExamSerializer.Meta.fields, "questions", "draft"]


class ExamFilterSerializer(serializers.Serializer):
    search = serializers.CharField(required=False, max_length=100)
    classroom = serializers.IntegerField(required=False)


class ExamFileQuerySerializer(serializers.Serializer):
    # Not "format": DRF reads that one to choose how to reply.
    type = serializers.ChoiceField(choices=["pdf", "docx"], default="pdf")
    answers = serializers.BooleanField(default=False)
