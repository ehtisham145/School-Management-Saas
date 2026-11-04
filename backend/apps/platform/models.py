from django.db import models


class Lead(models.Model):
    name = models.CharField(max_length=120)
    school_name = models.CharField(max_length=200)
    email = models.EmailField()
    message = models.TextField(max_length=2000)
    is_handled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.email})"


class DemoRequest(Lead):
    class Plan(models.TextChoices):
        BASIC = "basic", "Basic"
        PREMIUM = "premium", "Premium"
        ADVANCED = "advanced", "Advanced"

    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        DEMO_SCHEDULED = "demo_scheduled", "Demo scheduled"
        CONVERTED = "converted", "Converted"
        REJECTED = "rejected", "Rejected"

    phone = models.CharField(max_length=30, blank=True)
    plan = models.CharField(max_length=20, choices=Plan.choices, blank=True)
    message = models.TextField(max_length=2000, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.NEW, db_index=True
    )
    admin_notes = models.TextField(max_length=2000, blank=True)
    converted_school = models.ForeignKey(
        "tenancy.School", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    def save(self, *args, **kwargs):
        # Status is the source of truth: a request is handled once someone has picked it up.
        self.is_handled = self.status != self.Status.NEW
        super().save(*args, **kwargs)


class ContactMessage(Lead):
    school_name = models.CharField(max_length=200, blank=True)
