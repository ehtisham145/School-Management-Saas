"""Browser agent API for the teacher of an individual workspace (ADR-0028).

POST /api/browser-agent/tasks/            start a task (throttled, capped, budget-checked)
GET  /api/browser-agent/tasks/            the teacher's tasks
GET  /api/browser-agent/tasks/{id}/       one task with its steps
POST /api/browser-agent/tasks/{id}/cancel/
GET  /api/browser-agent/status/           allowance, consent and the running task
POST /api/browser-agent/consent/          accept the current notice
Another workspace's or user's task answers 404."""

from django.conf import settings
from django.http import Http404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.browser_agent import selectors, services
from apps.browser_agent.api.errors import AgentError
from apps.browser_agent.api.serializers import (
    TaskCreateSerializer,
    TaskDetailSerializer,
    TaskSerializer,
)
from apps.classroom.entitlements import get_workspace_access
from apps.core.policies import can
from apps.tenancy.selectors import is_individual_workspace


class BrowserAgentAccess(BasePermission):
    """Signed in, the TEACHER of an individual workspace, feature switched on. Starting or
    cancelling a task also needs a plan that covers today."""

    def has_permission(self, request, view):
        school = getattr(request, "school", None)
        if not (
            request.user.is_authenticated
            and is_individual_workspace(school)
            and can(getattr(request, "role", None), "browser_agent.use")
        ):
            return False
        if not settings.BROWSER_AGENT_ENABLED:
            raise AgentError("browser_agent_disabled")
        if request.method not in SAFE_METHODS and get_workspace_access(school).read_only:
            raise AgentError("workspace_read_only")
        return True


class BrowserTaskViewSet(viewsets.GenericViewSet):
    permission_classes = [BrowserAgentAccess]
    serializer_class = TaskSerializer
    lookup_value_regex = r"\d+"
    throttle_scope = "browser_agent"

    def get_throttles(self):
        # Only starting a task is limited (BROWSER_AGENT_THROTTLE_RATE, default 10/hour).
        if self.action == "create":
            return [ScopedRateThrottle()]
        return super().get_throttles()

    def get_queryset(self):
        return selectors.list_tasks(self.request.school, user=self.request.user)

    def _task(self, pk):
        task = selectors.get_task(self.request.school, pk, user=self.request.user)
        if task is None:
            raise Http404
        return task

    def create(self, request):
        serializer = TaskCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            task = services.queue_task(
                request.school, user=request.user, **serializer.validated_data
            )
        except (services.QueueRefused, services.TaskInputError) as error:
            raise AgentError(error.code) from error
        task.refresh_from_db()
        return Response(TaskSerializer(task).data, status=202)

    def list(self, request):
        page = self.paginate_queryset(self.get_queryset())
        return self.get_paginated_response(TaskSerializer(page, many=True).data)

    def retrieve(self, request, pk=None):
        task = self._task(pk)
        steps = selectors.list_steps(request.school, task.pk)
        return Response(TaskDetailSerializer(task, context={"steps": steps}).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        task = services.cancel_task(self._task(pk))
        return Response(TaskSerializer(task).data)


class StatusView(APIView):
    """Everything the agent page needs before the teacher starts a task."""

    permission_classes = [BrowserAgentAccess]

    def get(self, request):
        used, limit, period = services.allowance(request.school)
        active = selectors.get_active_task(request.school, request.user)
        return Response(
            {
                "consent_version": services.CONSENT_VERSION,
                "consent_given": selectors.has_consent(
                    request.school, request.user, services.CONSENT_VERSION
                ),
                "allowance": {
                    "used": used,
                    "limit": limit,
                    "left": max(limit - used, 0),
                    "period": period,
                },
                "active_task": active and TaskSerializer(active).data,
            }
        )


class ConsentView(APIView):
    permission_classes = [BrowserAgentAccess]

    def post(self, request):
        if request.data.get("version") != services.CONSENT_VERSION:
            # The page showed an older notice: it must show the current one first.
            raise AgentError("consent_required")
        services.give_consent(request.school, request.user)
        return Response(status=204)
