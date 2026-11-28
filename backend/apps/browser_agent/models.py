"""Browser agent tasks (ADR-0028, docs/browser-agent.md).

Nothing here stores page content or values the agent typed: a step keeps only the action
kind, the domain and a short reason code."""

from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.core.models import TenantModel


class BrowserTask(TenantModel):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        # Paused for the teacher: a login, a code or a confirmation (Phase 2).
        AWAITING_USER = "awaiting_user", "Waiting for the user"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
        LIMIT_REACHED = "limit_reached", "Limit reached"

    ACTIVE = (Status.QUEUED, Status.RUNNING, Status.AWAITING_USER)
    FINISHED = (Status.DONE, Status.FAILED, Status.CANCELLED, Status.LIMIT_REACHED)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="browser_tasks"
    )
    goal = models.TextField(max_length=2000)
    start_url = models.URLField(max_length=2000, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    answer = models.TextField(max_length=10000, blank=True)
    # A short code such as "blocked_url" or "max_steps", never page text.
    failure_reason = models.CharField(max_length=40, blank=True)
    steps_taken = models.PositiveIntegerField(default=0)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    cost_usd = models.DecimalField(max_digits=10, decimal_places=6, default=Decimal("0"))
    model = models.CharField(max_length=50, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            # Concurrency caps and the stale-task sweep filter on status.
            models.Index(fields=["status", "created_by"], name="browser_task_status_user"),
        ]

    def __str__(self):
        return f"Browser task {self.pk} ({self.status})"


class AgentConsent(TenantModel):
    """The teacher accepted the Lesson Lab Agent notice (version = the notice's date).
    A new notice version asks again."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="agent_consents"
    )
    version = models.CharField(max_length=20)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["school", "user", "version"], name="unique_agent_consent_version"
            ),
        ]

    def __str__(self):
        return f"Agent consent {self.version} by {self.user_id}"


class BrowserStep(TenantModel):
    class Verdict(models.TextChoices):
        OK = "ok", "Done"
        BLOCKED = "blocked", "Blocked by policy"
        FAILED = "failed", "Failed on the page"
        INVALID = "invalid", "Invalid action from the AI"

    task = models.ForeignKey(BrowserTask, on_delete=models.CASCADE, related_name="steps")
    number = models.PositiveIntegerField()
    action = models.CharField(max_length=20)
    domain = models.CharField(max_length=253, blank=True)
    verdict = models.CharField(max_length=10, choices=Verdict.choices)
    note = models.CharField(max_length=60, blank=True)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    duration_ms = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["task", "number"]
        constraints = [
            models.UniqueConstraint(fields=["task", "number"], name="unique_browser_step_number"),
        ]

    def __str__(self):
        return f"Step {self.number} of task {self.task_id}: {self.action}"
