from django.core.validators import URLValidator
from rest_framework import serializers

from apps.browser_agent.models import BrowserStep, BrowserTask


class TaskCreateSerializer(serializers.Serializer):
    goal = serializers.CharField(max_length=2000, trim_whitespace=True)
    # DRF's URLField also allows ftp; the agent opens only http(s).
    start_url = serializers.URLField(
        max_length=2000,
        required=False,
        allow_blank=True,
        validators=[URLValidator(schemes=["http", "https"])],
    )


class StepSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrowserStep
        fields = ["number", "action", "domain", "verdict", "note", "duration_ms"]


class TaskSerializer(serializers.ModelSerializer):
    """What the teacher sees. Tokens and cost stay with the platform (pilot report)."""

    class Meta:
        model = BrowserTask
        fields = [
            "id",
            "goal",
            "start_url",
            "status",
            "answer",
            "failure_reason",
            "steps_taken",
            "created_at",
            "started_at",
            "finished_at",
        ]
        read_only_fields = fields


class TaskDetailSerializer(TaskSerializer):
    steps = serializers.SerializerMethodField()

    class Meta(TaskSerializer.Meta):
        fields = [*TaskSerializer.Meta.fields, "steps"]
        read_only_fields = fields

    def get_steps(self, task):
        return StepSerializer(self.context["steps"], many=True).data
