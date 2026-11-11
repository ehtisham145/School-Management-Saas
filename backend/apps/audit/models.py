from django.conf import settings
from django.db import models


class AuditEvent(models.Model):
    """One action someone took on the platform. Rows are only ever added, never changed.

    Platform-owned, so it is not a TenantModel: `school` says which school the action
    was about, when there is one, and is kept as plain data if the school changes.
    """

    class Action(models.TextChoices):
        SCHOOL_CREATED = "school.created", "School created"
        SCHOOL_ACTIVATED = "school.activated", "School activated"
        SCHOOL_DEACTIVATED = "school.deactivated", "School deactivated"
        DEMO_REQUEST_UPDATED = "demo_request.updated", "Demo request updated"
        PLAN_CREATED = "plan.created", "Plan created"
        PLAN_UPDATED = "plan.updated", "Plan updated"
        SUBSCRIPTION_ACTIVATED = "subscription.activated", "Subscription activated"
        SUBSCRIPTION_EXPIRED = "subscription.expired", "Subscription expired"
        QUOTATION_CREATED = "quotation.created", "Quotation created"
        QUOTATION_UPDATED = "quotation.updated", "Quotation updated"
        QUOTATION_SENT = "quotation.sent", "Quotation sent"
        QUOTATION_ACCEPTED = "quotation.accepted", "Quotation accepted"
        QUOTATION_REJECTED = "quotation.rejected", "Quotation rejected"

    # Null means the system did it, such as a scheduled job.
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    # Kept as text too, so the log still says who it was after the user is deleted.
    actor_label = models.CharField(max_length=254, blank=True)
    action = models.CharField(max_length=40, choices=Action.choices, db_index=True)
    target_type = models.CharField(max_length=40)
    target_id = models.PositiveBigIntegerField()
    target_label = models.CharField(max_length=300, blank=True)
    school = models.ForeignKey(
        "tenancy.School",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["target_type", "target_id"])]

    def __str__(self):
        return f"{self.action} {self.target_type}:{self.target_id}"
