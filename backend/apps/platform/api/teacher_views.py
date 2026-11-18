"""Individual teachers, for the Super Admin. Platform admins only."""

from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.audit.services import actor_from_request
from apps.platform.api.views import IsPlatformAdmin
from apps.platform.selectors import get_individual_teacher, list_individual_teachers
from apps.platform.services import activate_teacher_plan, extend_teacher_trial

MAX_TRIAL_EXTENSION_DAYS = 30


class TeacherFilterSerializer(serializers.Serializer):
    search = serializers.CharField(required=False, max_length=100)
    status = serializers.ChoiceField(required=False, choices=["trial", "paid", "ended"])


class ExtendTrialSerializer(serializers.Serializer):
    days = serializers.IntegerField(min_value=1, max_value=MAX_TRIAL_EXTENSION_DAYS)


class ActivatePlanSerializer(serializers.Serializer):
    plan = serializers.ChoiceField(choices=["teacher", "teacher_pro"])


class IndividualTeacherSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField(source="name_en")
    is_active = serializers.BooleanField()
    email = serializers.EmailField(source="teacher_email", allow_null=True)
    created_at = serializers.DateTimeField()
    class_count = serializers.IntegerField()
    student_count = serializers.IntegerField()
    plan_code = serializers.CharField(allow_null=True)
    is_trial = serializers.BooleanField(allow_null=True)
    ends_on = serializers.DateField(allow_null=True)
    requested_plan = serializers.CharField(allow_null=True)


class IndividualTeacherViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsPlatformAdmin]
    serializer_class = IndividualTeacherSerializer
    lookup_value_regex = r"\d+"

    def get_queryset(self):
        filters = TeacherFilterSerializer(data=self.request.query_params)
        filters.is_valid(raise_exception=True)
        return list_individual_teachers(**filters.validated_data)

    def _respond(self, pk):
        return Response(self.get_serializer(get_individual_teacher(pk)).data)

    @action(detail=True, methods=["post"], url_path="extend-trial")
    def extend_trial(self, request, pk=None):
        data = ExtendTrialSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        workspace = get_individual_teacher(pk)
        extend_teacher_trial(
            actor=actor_from_request(request), school=workspace, days=data.validated_data["days"]
        )
        return self._respond(pk)

    @action(detail=True, methods=["post"], url_path="activate-plan")
    def activate_plan(self, request, pk=None):
        data = ActivatePlanSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        workspace = get_individual_teacher(pk)
        activate_teacher_plan(
            actor=actor_from_request(request),
            school=workspace,
            plan_code=data.validated_data["plan"],
        )
        return self._respond(pk)
