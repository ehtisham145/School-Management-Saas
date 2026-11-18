from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from apps.classroom.models import (
    Assessment,
    AttendanceRecord,
    Classroom,
    LessonPlan,
    ParentMessage,
    Student,
    UpgradeRequest,
)

MAX_STUDENTS_AT_ONCE = 200
MAX_MARK = Decimal("9999.99")


def _not_in_future(value):
    if value > timezone.localdate():
        raise serializers.ValidationError("This date is in the future.")
    return value


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

    class Meta:
        model = Classroom
        fields = ["id", "name", "subject", "grade", "student_count"]
        # The service gives the friendly message for a name that is already used.
        validators = []

    def get_student_count(self, classroom) -> int:
        return getattr(classroom, "student_count", 0)


class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ["id", "classroom", "full_name", "parent_email"]
        read_only_fields = ["classroom"]


class StudentInputSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    parent_email = serializers.EmailField(required=False, allow_blank=True, default="")


class StudentsAddSerializer(serializers.Serializer):
    students = StudentInputSerializer(many=True, min_length=1, max_length=MAX_STUDENTS_AT_ONCE)


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
        read_only_fields = ["source", "updated_at"]


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
